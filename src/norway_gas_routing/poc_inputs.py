"""Prepare retained EA data for the POC; no network access or helper writes."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from .poc import DESTINATIONS, finite_nonnegative, historical_preferences, monthly_available_capacity
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
        raise ValueError("Workbook production field appears in multiple POC sources")
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


def prepare_inputs(root, model, registry, *, analysis_mode='historical_reconstruction',
                   diagnostic_snohvit_bcm=None, diagnostic_scenario=None,
                   capacity_scenario='baseline'):
    from .capacity_inputs import SCENARIOS
    if capacity_scenario not in SCENARIOS:
        raise ValueError('Explicit known capacity scenario required')
    diagnostic = analysis_mode == 'snohvit_sensitivity'
    if analysis_mode not in {'historical_reconstruction', 'snohvit_sensitivity'}:
        raise EvaluationError('POC reader has no complete verified forecast-origin bundle; historical reconstruction only')
    if not diagnostic and (diagnostic_snohvit_bcm is not None or diagnostic_scenario is not None):
        raise ValueError('Snøhvit override requires explicit snohvit_sensitivity mode')
    settings = model["poc"]
    months = pd.period_range(settings["start"], settings["end"], freq="M")
    training = pd.period_range(settings["baseline_start"], settings["baseline_end"], freq="M")
    check_dates(months, 'analysis')
    check_dates(training, 'fit')
    if diagnostic:
        diagnostic_snohvit_bcm = diagnostic_snohvit_values(
            months, diagnostic_snohvit_bcm, diagnostic_scenario)
    if training.max() >= months.min():
        raise ValueError("Baseline observations must precede all POC months")
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
            raise ValueError("Production field appears in multiple POC sources")
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
        raise ValueError("Snohvit actual conversion validated only through July 2025 for this POC")
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
    from .capacity_inputs import database_candidates, select_capacity_scenario
    candidates = database_candidates(root, model, months) if capacity_scenario != 'baseline' else None
    return select_capacity_scenario(prepared, model, scenario=capacity_scenario, candidates=candidates)
