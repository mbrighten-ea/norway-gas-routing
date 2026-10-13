"""Prepare retained EA data for the routing model; no network access or helper writes."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from .routing import DESTINATIONS, finite_nonnegative, historical_preferences, monthly_available_capacity
from .evaluation import check_dates, read_parquet, EvaluationError

# Exact raw field columns behind the accepted component SIDs. Workbook additions
# must not count a field already represented by a retained SID a second time.
PRODUCTION_COLUMNS = dict(zip(
    ["troll_prod", "kvitebjorn_prod", "visund_prod", "ormen_lange_prod",
     "aasta_hansteen_prod", "dvalin_prod", "asgard_prod", "gullfaks_sor_prod",
     "heidrun_prod", "kristin_prod", "norne_prod", "skarv_prod", "oseberg_prod",
     "sleipner_prod", "gina_krog_prod", "martin_linge_prod"],
    ["L", "AZ", "BU", "BI", "AC", "BX", "AF", "AN", "AQ", "AW", "BF", "BL",
     "Q", "BP", "AI", "BC"]))


def workbook_source_columns(nodes, assigned_series):
    columns = [c for entry in nodes.values() for c in entry.get("workbook_columns", [])]
    if len(columns) != len(set(columns)) or set(columns).intersection(
            PRODUCTION_COLUMNS[k] for k in assigned_series if k in PRODUCTION_COLUMNS):
        raise ValueError("Workbook production field appears in multiple routing model sources")
    return columns


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def monthly_points(series, months, name):
    if not isinstance(series.index, pd.DatetimeIndex) or not series.index.is_unique:
        raise ValueError(f"{name}: unique timestamp index required")
    if not series.index.equals(series.index.to_period("M").to_timestamp()):
        raise ValueError(f"{name}: expected monthly first-day observations")
    values = series.copy()
    values.index = values.index.to_period("M")
    values = values.reindex(months)
    if values.isna().any():
        raise ValueError(f"{name}: missing requested monthly observations")
    return values


def technical_capacity_points(path):
    """Check a capacity file's dates before loading any capacity observations."""
    dates = pd.read_csv(path, usecols=['date'])['date']
    check_dates(dates, 'read')
    return pd.read_csv(path, parse_dates=['date']).set_index('date')['technical_capacity_mcm_d']


def diagnostic_snohvit_values(months, values, scenario):
    """Accept signed monthly bcm only for the authorised full-year sensitivity."""
    if scenario not in {'official-net-production', 'selected-series-mixed-vintage'}:
        raise ValueError('Explicit Snøhvit diagnostic scenario required')
    expected = pd.period_range('2025-01', '2025-12', freq='M')
    if not months.equals(expected):
        raise ValueError('Snøhvit diagnostic override is restricted to full-year 2025')
    if not isinstance(values, pd.Series) or not values.index.equals(expected):
        raise ValueError('Snøhvit diagnostic requires exactly twelve indexed monthly bcm values')
    values = pd.to_numeric(values, errors='raise').astype(float).copy()
    if values.isna().any() or not values.map(lambda v: float('-inf') < v < float('inf')).all():
        raise ValueError('Snøhvit diagnostic monthly bcm must be finite and complete')
    return values


def prepare_fresh_inputs(root, model, registry, *, provenance_dir=None, client=None):
    """Fresh historical SID preparation; missing essential mappings stop before I/O.

    The reviewed contracts cover existing selected inputs only. Workbook formula
    lineage cannot authorise a discovered SID or a new field allocation. Optional
    current comparisons never substitute for earlier preference observations.
    """
    from .data_functions import connect_shooju
    from .routing_sources import source_requirements, retrieve_checked, OPTIONAL_GROUPS
    from .reporting.sids import monthly_reference
    settings = model['routing']
    months = pd.period_range(settings['start'], settings['end'], freq='M')
    training = pd.period_range(settings['baseline_start'], settings['baseline_end'], freq='M')
    check_dates(months, 'analysis')
    check_dates(training, 'fit')
    if months.empty or training.empty or training.max() >= months.min():
        raise ValueError('Nonempty earlier training and later target months are required.')
    if months.max() > pd.Period('2025-07', 'M'):
        raise ValueError('Snohvit actual conversion validated only through July 2025 for this routing model')
    requirements, components, contract = source_requirements(root, model, registry)
    blocked = requirements.loc[requirements.blocked & requirements.classification.str.startswith('essential')]
    if len(blocked):
        names = ', '.join(blocked.key)
        reasons = '; '.join(blocked.status.head(3))
        raise ValueError(f'Fresh-SID preparation blocked: {len(blocked)} essential inputs unresolved: {names}. {reasons}. See input_sources.csv and evidence/inputs/routing_sources_b1/routing_source_mapping.csv. Independently verify canonical SID mappings; no workbook or frozen-input fallback.')
    # Detect aliases of one SID before retrieval/aggregation, not after solving.
    selected_keys = [key for keys in components.values() for key in keys]
    selected_sids = [registry.at[key, 'sid'].removeprefix('sid=') for key in selected_keys]
    if len(set(selected_sids)) != len(selected_sids):
        raise ValueError('Duplicate production SID across source components; cannot double count.')
    client = connect_shooju() if client is None else client
    records = []
    def get(key, periods):
        dates = periods.to_timestamp()
        return retrieve_checked(root, key, dates, registry, contract, records, provenance_dir, client=client).set_axis(periods)
    supply = pd.DataFrame(index=months)
    for node, keys in components.items():
        fields = pd.DataFrame({key: get(key, months) for key in keys})
        finite_nonnegative(fields.to_numpy().ravel(), node+' field production')
        supply[node] = fields.sum(axis=1)
    total = get('norway_prod', months)
    finite_nonnegative(total, 'national production')
    # Preserve the independently checked historical unit-label exception and sign.
    snohvit = get('snohvit_net_prod', months) * pd.Series(months.days_in_month/1000, index=months)
    supply['UNMAPPED'] = total-snohvit-supply.sum(axis=1)
    finite_nonnegative(supply.to_numpy().ravel(), 'source/residual supply; verify aggregate boundaries')
    # EA workbook cohort only. Directorate leaves are separate latest-revised
    # historical sources; no shared EA import job or cache equality is required.
    cohort = {r['metadata'].get('api_obj', {}).get('snap_shooju_job_id') for r in records
              if r['category']=='production' and r['key'] in selected_keys+['norway_prod']}
    if len(cohort-{None}) > 1:
        raise ValueError('Mixed production import vintages; retrieve a consistent national/component cohort. No silent revised substitution.')
    observations = pd.DataFrame({d: get(d.lower()+'_flow_qa', training) for d in DESTINATIONS})
    preferences, excluded = historical_preferences(observations)
    capacities, daily_rows, monthly_rows = {}, [], []
    days = pd.date_range(months.min().start_time, months.max().end_time.normalize())
    for asset, entry in settings['assets'].items():
        if entry.get('technical_series_file'):
            raise ValueError(asset+': a local capacity schedule is not a verified fresh SID; review its sourcing separately.')
        if 'mcm_d' not in entry and 'annual_bcm' not in entry:
            raise ValueError(asset+': missing technical capacity assumption; do not assume zero.')
        rate = entry['mcm_d'] if 'mcm_d' in entry else entry['annual_bcm']*1000/365
        records.append(dict(key=asset, category='technical_capacity', status='EXISTING_PROVISIONAL_ASSUMPTION',
            source_config='provenance/resolved_settings.yaml:model.routing.assets.'+asset,
            source_url=settings['capacity_sources'][entry['source']], technical_capacity=entry,
            sha256=hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest(),
            unit='mcm/day' if 'mcm_d' in entry else 'bcm/year', target_unit='bcm/month',
            target_months=months.astype(str).tolist(), asof=None, available_at=None, effective_at=None,
            transformation='Calendar-day sum of existing technical rate minus signed derate / 1000; annual rate uses 365-day envelope',
            vintage_status='Existing baseline assumption; historical effectiveness/volume-basis compatibility unverified'))
        technical = pd.Series([rate], index=pd.DatetimeIndex([months.min().start_time]))
        derate = retrieve_checked(root, entry['maintenance_series'], days, registry, contract, records,
            provenance_dir, client=client) if entry.get('maintenance_series') else None
        monthly, daily = monthly_available_capacity(technical, months, derate)
        capacities[asset] = monthly.available_capacity_bcm
        daily_rows.append(daily.rename_axis('date').reset_index().assign(asset=asset))
        monthly_rows.append(monthly.rename_axis('month').reset_index().assign(asset=asset))
    # Preserve source records, including optional rejected responses. No exception
    # in this section can authorise a substitute or block valid physical inputs.
    comparisons, optional_status = {}, {}
    for group, key in OPTIONAL_GROUPS.items():
        try:
            series = get(key, months)
            response = {'metadata': records[-1]['metadata'], 'values': series.set_axis(months.to_timestamp())}
            monthly_reference(response, months.astype(str).tolist())
            comparisons[group] = series
            optional_status[group] = 'EA revised historical allocation proxy' if group not in {'DK', 'Baltic Pipe'} else 'Incompatible gross-export definition; reference retained as signed net/Nybro context only'
        except (ValueError, OSError, KeyError) as error:
            comparisons[group] = pd.Series(float('nan'), index=months)
            optional_status[group] = 'Unavailable: '+str(error)
    return dict(months=months, supply=supply, capacities=pd.DataFrame(capacities),
        capacity_daily=pd.concat(daily_rows, ignore_index=True),
        capacity_monthly=pd.concat(monthly_rows, ignore_index=True),
        training_observations=observations, preferences=preferences, excluded_training_months=excluded,
        provenance=records, input_inventory=requirements,
        actual_comparisons=pd.DataFrame(comparisons), comparison_status=optional_status,
        reconciliation=pd.DataFrame(dict(national_production_bcm=total, snohvit_bcm=snohvit,
            pipeline_supply_bcm=total-snohvit, mapped_supply_bcm=supply.drop(columns='UNMAPPED').sum(axis=1),
            unmapped_supply_bcm=supply.UNMAPPED)))


def prepare_inputs(root, model, registry, *, analysis_mode='historical_reconstruction',
                   diagnostic_snohvit_bcm=None, diagnostic_scenario=None,
                   capacity_scenario='baseline'):
    from .capacity.inputs import SCENARIOS
    if capacity_scenario not in SCENARIOS:
        raise ValueError('Explicit known capacity scenario required')
    diagnostic = analysis_mode == 'snohvit_sensitivity'
    if analysis_mode not in {'historical_reconstruction', 'snohvit_sensitivity'}:
        raise EvaluationError('routing model reader has no complete verified forecast-origin bundle; historical reconstruction only')
    if not diagnostic and (diagnostic_snohvit_bcm is not None or diagnostic_scenario is not None):
        raise ValueError('Snøhvit override requires explicit snohvit_sensitivity mode')
    settings = model["routing"]
    months = pd.period_range(settings["start"], settings["end"], freq="M")
    training = pd.period_range(settings["baseline_start"], settings["baseline_end"], freq="M")
    check_dates(months, 'analysis')
    check_dates(training, 'fit')
    if diagnostic:
        diagnostic_snohvit_bcm = diagnostic_snohvit_values(
            months, diagnostic_snohvit_bcm, diagnostic_scenario)
    if training.max() >= months.min():
        raise ValueError("Baseline observations must precede all routing model months")
    audit = pd.read_csv(root / "evidence/inputs/data_series_audit.csv", keep_default_na=False)
    provenance, retained = [], {}

    def cached(key, coverage=None):
        if key in retained:
            return retained[key]
        sid = registry.at[key, "sid"]
        matches = audit.loc[audit.sid.str.casefold().eq(sid.casefold())]
        if len(matches) != 1:
            raise ValueError(f"{key}: expected one retained SID audit record")
        row = matches.iloc[0]
        path, metadata_path = root / row.raw_file, root / row.metadata_file
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        coverage = months if coverage is None else coverage
        category = registry.at[key, 'category']
        category = 'historical_flows' if category == 'existing_model_output' else category
        provenance.append({"key": key, "sid": sid, "raw_file": str(path.relative_to(root)),
                           "category": category, "target_months": coverage.astype(str).tolist(),
                           "unit": registry.at[key, 'raw_unit'], "target_unit": registry.at[key, 'target_unit'],
                           "training_target_months": training.astype(str).tolist() if key in {
                               d.lower() + '_flow_qa' for d in DESTINATIONS} else [],
                           "sha256": file_hash(path), "metadata_file": str(metadata_path.relative_to(root)),
                           "metadata_sha256": file_hash(metadata_path),
                           "retrieved_at": metadata.get("retrieved_at"),
                           "settings": {k: metadata.get(k) for k in ["date_start", "date_finish", "max_points", "query"]},
                           "metadata": metadata.get("metadata", {}), "asof": None})
        retained[key] = read_parquet(path, end=str(months.max().end_time.date()))["value"]
        return retained[key]

    supply = pd.DataFrame(index=months)
    assigned = set()
    for node, entry in settings["nodes"].items():
        if "source_group" not in entry:
            continue
        keys = model["sources"][entry["source_group"]]["series"]
        if assigned.intersection(keys):
            raise ValueError("Production field appears in multiple routing model sources")
        assigned.update(keys)
        fields = pd.DataFrame({k: monthly_points(cached(k), months, k) for k in keys})
        finite_nonnegative(fields.to_numpy().ravel(), "monthly component production")
        supply[node] = fields.sum(axis=1)

    # These independently named fields are absent from the SID registry. Read
    # their cached historic EA worksheet values, never evaluate forecast formulas.
    workbook = root / "data/raw/legacy/Norwegian production model.xlsx"
    book = load_workbook(workbook, read_only=True, data_only=True, keep_links=False)
    additions = workbook_source_columns(settings["nodes"], assigned)
    columns = list(dict.fromkeys(additions + ["EB", "HG", "HH", "HM", "HN", "GD"]))
    from openpyxl.utils.cell import column_index_from_string
    positions = {c: column_index_from_string(c) - 1 for c in columns}
    worksheet = {}
    try:
        source_sheet = book['Production mcm_d']
        # Scan only the date column, then request cells only in the allowed rows.
        dated_rows = {i: pd.Period(date, freq='M') for i, (date,) in enumerate(
            source_sheet.iter_rows(min_col=5, max_col=5, values_only=True), 1)
            if isinstance(date, datetime) and pd.Period(date, freq='M') in months}
        if not dated_rows:
            raise ValueError('No requested historical production workbook dates')
        for row_number, row in enumerate(source_sheet.iter_rows(
                min_row=min(dated_rows), max_row=max(dated_rows), values_only=True), min(dated_rows)):
            if len(row) < 5 or not isinstance(row[4], datetime):
                continue
            month = pd.Period(row[4], freq="M")
            if month in months:
                worksheet[month] = {c: row[pos] for c, pos in positions.items()}
                worksheet[month]["excel_row"] = row_number
    finally:
        book.close()
    sheet = pd.DataFrame.from_dict(worksheet, orient="index").reindex(months)
    if sheet.isna().any().any():
        raise ValueError("Missing cached production workbook cells for requested period")
    provenance.append({"file": str(workbook.relative_to(root)), "sha256": file_hash(workbook),
                       "sheet": "Production mcm_d", "columns": list(columns),
                       "excel_rows": sheet.excel_row.astype(int).tolist(),
                       "unit": "monthly-average mcm/d (bcm=rate*calendar_days/1000)",
                       "key": "production_workbook", "category": "production",
                       "target_months": months.astype(str).tolist(), "target_unit": "bcm/month",
                       "asof": None, "cached_values_only": True})
    days = pd.Series(months.days_in_month / 1000, index=months)
    for node, entry in settings["nodes"].items():
        if "workbook_columns" in entry:
            fields = sheet[entry["workbook_columns"]]
            finite_nonnegative(fields.to_numpy().ravel(), "workbook component production")
            # Extend an existing source rather than replacing its retained SIDs.
            supply[node] = supply.get(node, 0) + fields.sum(axis=1) * days

    total = monthly_points(cached("norway_prod"), months, "Norway total")
    # Retained official-source checks validate the historical rate interpretation.
    # No use of the stale 2022 ex-Snohvit forecast or forecast-period unit inference.
    if not diagnostic and months.max() > pd.Period("2025-07", freq="M"):
        raise ValueError("Snohvit actual conversion validated only through July 2025 for this routing model")
    if diagnostic:
        snohvit = diagnostic_snohvit_bcm
        provenance.append({'key': 'snohvit_diagnostic_override', 'category': 'production',
                           'scenario': diagnostic_scenario, 'unit': 'bcm/month',
                           'target_months': months.astype(str).tolist(),
                           'values_bcm': snohvit.to_list(), 'validated_baseline': False,
                           'analysis_mode': 'snohvit_sensitivity'})
    else:
        snohvit = monthly_points(cached("snohvit_net_prod"), months, "Snohvit") * days
    eligible = total - snohvit
    # Identity, not additional aggregate supply: total already contains fields.
    supply["UNMAPPED"] = eligible - supply.sum(axis=1)
    finite_nonnegative(supply.to_numpy().ravel(), "source/residual supply")

    observed = pd.DataFrame({d: monthly_points(cached(d.lower() + "_flow_qa", training.union(months)),
                            training.union(months), d) for d in DESTINATIONS})
    preferences, excluded_training = historical_preferences(observed.loc[training])
    qa_total = monthly_points(cached("norway_exports_qa"), months, "Legacy gassco_total")
    comparisons = observed.loc[months].copy()
    comparisons["FR_BE"] = monthly_points(cached("fr_be_flow_qa"), months, "FR+BE")
    comparisons["NL_DE"] = monthly_points(cached("nl_de_flow_qa"), months, "NL+DE")
    capacities, daily_rows, monthly_rows = {}, [], []
    for asset, entry in settings["assets"].items():
        # Optional technical_series_file is a dated daily mcm/d CSV, not an
        # availability series. Original values and retained derates stay separate.
        if entry.get("technical_series_file"):
            path = (root / entry["technical_series_file"]).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Technical-capacity CSV must be inside this repository")
            points = technical_capacity_points(path)
            provenance.append({"key": asset + '_schedule', "category": "technical_capacity",
                               "file": str(path.relative_to(root.resolve())), "sha256": file_hash(path),
                               "target_months": months.astype(str).tolist(), "unit": "mcm/d",
                               "target_unit": "bcm/month", "effective_at": None})
        else:
            value = entry.get("mcm_d", entry.get("annual_bcm", 0) * 1000 / 365)
            points = pd.Series([value], index=pd.DatetimeIndex([months.min().start_time]))
        derate = cached(entry["maintenance_series"]) if entry.get("maintenance_series") else None
        provenance.append({'key': asset, 'category': 'technical_capacity',
                           'file': 'config/model.yaml', 'sha256': file_hash(root / 'config/model.yaml'),
                           'target_months': months.astype(str).tolist(), 'unit': 'mcm/d', 'target_unit': 'bcm/month',
                           'technical_capacity': entry, 'source_url': settings['capacity_sources'][entry['source']],
                           'effective_at': None, 'available_at': None, 'asof': None})
        monthly, daily = monthly_available_capacity(points, months, derate)
        capacities[asset] = monthly.available_capacity_bcm
        daily_rows.append(daily.rename_axis("date").reset_index().assign(asset=asset,
                          source_url=settings["capacity_sources"][entry["source"]]))
        monthly_rows.append(monthly.rename_axis("month").reset_index().assign(asset=asset))
    reconciliation = pd.DataFrame({"norway_total_production_bcm": total,
        "snohvit_net_production_bcm": snohvit, "pipeline_supply_proxy_bcm": eligible,
        "mapped_source_supply_bcm": supply.drop(columns="UNMAPPED").sum(axis=1),
        "unclassified_supply_bcm": supply.UNMAPPED,
        "legacy_gassco_total_bcm": qa_total,
        "workbook_gassco_total_bcm": sheet.HM,
        "workbook_duplicate_rev_deduction_bcm": sheet.EB * days,
        "workbook_gassco_total_without_duplicate_rev_bcm": sheet.HM + sheet.EB * days,
        "observed_seven_destination_sum_bcm": observed.loc[months].sum(axis=1)})
    reconciliation["observed_sum_minus_legacy_total_bcm"] = reconciliation.observed_seven_destination_sum_bcm - qa_total
    reconciliation["observed_sum_vs_legacy_total_error_pct"] = reconciliation.observed_sum_minus_legacy_total_bcm / qa_total.abs() * 100
    reconciliation["within_5pct_legacy_reconciliation"] = reconciliation.observed_sum_vs_legacy_total_error_pct.abs().le(5)
    reconciliation["observed_sum_vs_pipeline_supply_error_pct"] = (reconciliation.observed_seven_destination_sum_bcm - eligible) / eligible * 100
    reconciliation["negative_destination_observation"] = observed.loc[months].lt(0).any(axis=1)
    prepared = {"months": months, "supply": supply, "capacities": pd.DataFrame(capacities),
            "capacity_daily": pd.concat(daily_rows, ignore_index=True),
            "capacity_monthly": pd.concat(monthly_rows, ignore_index=True),
            "observed": comparisons, "preferences": preferences,
            "excluded_training_months": excluded_training,
            "training_observations": observed.loc[training],
            "reconciliation": reconciliation, "provenance": provenance}
    from .capacity.inputs import database_candidates, select_capacity_scenario
    candidates = database_candidates(root, model, months) if capacity_scenario != 'baseline' else None
    return select_capacity_scenario(prepared, model, scenario=capacity_scenario, candidates=candidates)
