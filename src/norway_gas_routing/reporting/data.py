"""Saved-solution adapters and strict reporting arithmetic; never call a solver."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..evaluation import check_dates

COUNTRIES = ['UK', 'FR', 'BE', 'NL', 'DE', 'DK', 'PL']
GROUPS = {'UK': ['UK'], 'FR+BE': ['FR', 'BE'], 'NL+DE': ['NL', 'DE'],
          'Baltic Pipe': ['PL'], 'DK': ['DK']}
NAMES = {'UK': 'United Kingdom', 'FR': 'France', 'BE': 'Belgium', 'NL': 'Netherlands',
         'DE': 'Germany', 'DK': 'Denmark', 'PL': 'Poland', 'FR+BE': 'France + Belgium',
         'NL+DE': 'Netherlands + Germany', 'Baltic Pipe': 'Poland / Baltic Pipe'}
COLORS = {'UK': '#2563a6', 'FR': '#8664ad', 'BE': '#bc8c32', 'NL': '#e48039',
          'DE': '#4c6575', 'DK': '#c45767', 'PL': '#2d9a88', 'FR+BE': '#8664ad',
          'NL+DE': '#4c6575', 'Baltic Pipe': '#2d9a88'}
TOL = 2e-8  # Saved 2024 cells have nine decimal places; no solver is replayed.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_sum(values):
    """A sum is unavailable if any required component is unavailable."""
    values = pd.Series(values, dtype=float)
    return float(values.sum()) if len(values) and np.isfinite(values).all() else np.nan


def aggregate_groups(countries):
    return pd.DataFrame({name: countries[items].sum(axis=1, min_count=len(items))
                         for name, items in GROUPS.items()}, index=countries.index)


def safe_percent(numerator, denominator):
    return 100 * numerator / denominator if (pd.notna(numerator) and
        pd.notna(denominator) and denominator > 0) else np.nan


def shares(values):
    values = pd.Series(values, dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or values.sum() <= 0:
        return values * np.nan
    return 100 * values / values.sum()


def dated_csv(path, month='month'):
    """Read date column first and reject unsafe files before loading values."""
    dates = pd.read_csv(path, usecols=[month])[month]
    check_dates(dates, 'plot')
    frame = pd.read_csv(path)
    frame[month] = pd.to_datetime(frame[month]).dt.to_period('M').astype(str)
    return frame


def choose(frame, column, value):
    if column not in frame:
        return frame
    choices = frame[column].unique().tolist()
    if value not in choices:
        raise ValueError(f'{column}={value!r} unavailable; choices: {choices}')
    return frame.loc[frame[column].eq(value)].drop(columns=column).copy()


def load_run(path, scenario=None, start=None, end=None, topology=None):
    """Adapt current reconstruction layout or retained diagnostic layout.

    Archived diagnostics lack their own network YAML. Use only a retained network
    whose hash was recorded in that diagnostic, with the same optimiser identity.
    """
    path = Path(path).resolve()
    consumed = []

    def csv(rel):
        file = path / rel
        consumed.append(file)
        return dated_csv(file)

    if (path/'provenance/run_manifest.json').exists():
        manifest_path = path/'provenance/run_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        scenario = scenario or 'refined_broader_boundary'
        if scenario != 'refined_broader_boundary':
            raise ValueError('Current assessment results.csv is the refined_broader_boundary case only')
        monthly = csv('results.csv').rename(columns={f'{c}_volume_bcm': c for c in COUNTRIES} |
            {'total_exports_bcm': 'exports_bcm', 'unrouted_supply_bcm': 'unrouted_bcm',
             'pipeline_supply_proxy_bcm': 'supply_bcm', 'unclassified_supply_bcm': 'unmapped_bcm'})
        if not monthly.solver_status.eq('OPTIMAL').all():
            raise ValueError('Report requires an optimal saved solution')
        arcs = csv('details/network_flows.csv').rename(columns={
            'arc_id': 'arc', 'from_node': 'from', 'to_node': 'to'})
        assets = choose(csv('details/monthly_asset_utilisation.csv'), 'case', scenario)
        observations = choose(csv('details/monthly_comparisons.csv'), 'case', scenario)
        network_path = path/'provenance/network_definition.yaml'
        title = 'Historical reconstruction'
    else:
        manifest_path = path/'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('analysis_mode') != 'snohvit_sensitivity':
            raise ValueError('Unrecognised archive schema; a saved-result adapter is required')
        scenario = scenario or 'official-net-production'
        monthly = choose(csv('monthly_seven_countries.csv'), 'scenario', scenario).rename(
            columns={'total_pipeline_supply_bcm': 'supply_bcm'})
        reconciliation = choose(csv('source_reconciliation.csv'), 'scenario', scenario)
        monthly = monthly.merge(reconciliation[['month', 'unclassified_supply_bcm']].rename(
            columns={'unclassified_supply_bcm': 'unmapped_bcm'}), on='month', validate='one_to_one')
        arcs = choose(csv('arc_flows.csv'), 'scenario', scenario)
        assets = choose(csv('asset_constraints.csv'), 'scenario', scenario)
        observations = choose(csv('observed_comparison.csv'), 'scenario', scenario)
        root = Path(__file__).resolve().parents[3]
        network_path = Path(topology) if topology else root/'outputs/reconstruction/provenance/network_definition.yaml'
        key = network_path.resolve().relative_to(root).as_posix()
        if sha(network_path) != manifest.get('protected_sha256', {}).get(key):
            raise ValueError('Archived topology hash does not match the selected diagnostic')
        reference = json.loads((network_path.parent/'run_manifest.json').read_text())
        def optimiser_hash(m):
            return next((v for k, v in m['code_sha256'].items() if k.replace('\\', '/').endswith(('/routing.py', '/poc.py'))), None)
        if not optimiser_hash(manifest) or optimiser_hash(manifest) != optimiser_hash(reference):
            raise ValueError('Topology and diagnostic optimiser identities differ')
        title = 'Provisional revised-input reconstruction / diagnostic'
    consumed += [manifest_path, network_path]
    network = yaml.safe_load(network_path.read_text(encoding='utf-8'))
    if manifest.get('network') is not None and network != manifest['network']:
        raise ValueError('Retained topology differs from the producing run manifest')
    for file in consumed:
        if file.is_relative_to(path):
            expected = manifest.get('retained_files_sha256', {}).get(file.relative_to(path).as_posix())
            if expected is not None and sha(file) != expected:
                raise ValueError('Archived saved-result hash differs from its retained manifest')
    monthly = monthly.sort_values('month').reset_index(drop=True)
    if monthly.month.duplicated().any():
        raise ValueError('Duplicate solution months')
    if start:
        check_dates([start], 'plot')
        monthly = monthly.loc[monthly.month.ge(str(pd.Period(start, 'M')))]
    if end:
        check_dates([end], 'plot')
        monthly = monthly.loc[monthly.month.le(str(pd.Period(end, 'M')))]
    if monthly.empty:
        raise ValueError(f'No saved results in selected period: {path}')
    months = monthly.month.tolist()
    if months != pd.period_range(months[0], months[-1], freq='M').astype(str).tolist():
        raise ValueError('Saved solution has missing intervening months')
    arcs = arcs.loc[arcs.month.isin(months)].copy()
    assets = assets.loc[assets.month.isin(months)].copy()
    observations = observations.loc[observations.month.isin(months) & observations.destination.isin(COUNTRIES)].copy()
    for frame, key in [(arcs, 'arc'), (assets, 'asset')]:
        if frame.duplicated(['month', key]).any():
            raise ValueError(f'Duplicate saved {key} rows')
    monthly['mapped_disposal_bcm'] = monthly.unrouted_bcm - monthly.unmapped_bcm
    run = {'monthly': monthly, 'arcs': arcs, 'assets': assets, 'observations': observations,
           'network': network, 'manifest': manifest, 'scenario': scenario, 'title': title,
           'id': manifest['run_id'], 'path': str(path),
           'source_hashes': {str(p): sha(p) for p in consumed}}
    run['checks'] = validate_run(run)
    return run


def validate_run(run):
    """Reconcile destination, node, constraint and disposal tables independently."""
    monthly, arcs, assets = (run[k] for k in ['monthly', 'arcs', 'assets'])
    numeric = monthly[COUNTRIES+['exports_bcm', 'supply_bcm', 'unrouted_bcm', 'unmapped_bcm', 'mapped_disposal_bcm']]
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError('Incomplete or nonfinite saved solution')
    if numeric.min().min() < -TOL:
        raise ValueError('Negative physical solution volume')
    residuals = []
    for _, row in monthly.iterrows():
        flow = arcs.loc[arcs.month.eq(row.month)]
        cap = assets.loc[assets.month.eq(row.month)]
        expected = {a['id']: a for a in run['network']['arcs']}
        if set(flow.arc) != set(expected):
            raise ValueError('Saved arc IDs differ from retained topology')
        if not np.isfinite(flow.flow_bcm).all() or flow.flow_bcm.min() < -TOL:
            raise ValueError('Invalid saved arc volumes')
        for _, arc in flow.iterrows():
            definition = expected[arc.arc]
            for field in ['from', 'to', 'asset']:
                saved = None if pd.isna(arc[field]) else arc[field]
                if saved != definition.get(field):
                    raise ValueError(f'Saved {arc.arc} {field} differs from topology')
        residuals += [abs(row[COUNTRIES].sum()-row.exports_bcm),
            abs(strict_sum(aggregate_groups(pd.DataFrame([row])) .iloc[0])-row.exports_bcm),
            abs(row.supply_bcm-row.exports_bcm-row.unrouted_bcm)]
        for node, definition in run['network']['nodes'].items():
            incoming = flow.loc[flow['to'].eq(node), 'flow_bcm'].sum()
            outgoing = flow.loc[flow['from'].eq(node), 'flow_bcm'].sum()
            if definition['kind'] == 'junction':
                residuals.append(abs(incoming-outgoing))
            elif node in COUNTRIES:
                residuals.append(abs(incoming-row[node]))
        disposal = flow.loc[flow['to'].eq('UNROUTED')]
        residuals += [abs(disposal.flow_bcm.sum()-row.unrouted_bcm),
            abs(disposal.loc[disposal['from'].eq('UNMAPPED'), 'flow_bcm'].sum()-row.unmapped_bcm)]
        if set(cap.asset) != set(flow.asset.dropna()):
            raise ValueError('Constraint rows do not cover exactly the saved asset set')
        for _, asset in cap.iterrows():
            physical = flow.loc[flow.asset.eq(asset.asset), 'flow_bcm'].sum()
            residuals.append(abs(physical-asset.flow_bcm))
            if pd.notna(asset.capacity_bcm) and asset.flow_bcm > asset.capacity_bcm+TOL:
                raise ValueError('Saved capacity violation')
    maximum = max(residuals)
    if maximum > TOL:
        raise ValueError(f'Saved reporting reconciliation failed: {maximum} bcm')
    return {'max_reconciliation_residual_bcm': maximum, 'tolerance_bcm': TOL,
            'country_and_group_totals': 'PASS', 'node_and_map_balances': 'PASS',
            'asset_flows_and_capacities': 'PASS', 'disposal_split': 'PASS',
            'holdout_loaded': False, 'solver_calls': 0}


def period_map(run, months):
    """Aggregate each unique arc and each asset once, using monthly bcm limits."""
    flow = run['arcs'].loc[run['arcs'].month.isin(months)]
    capacities = run['assets'].loc[run['assets'].month.isin(months)]
    asset_rows = []
    for name, group in capacities.groupby('asset', sort=False):
        f = strict_sum(group.flow_bcm) if len(group) == len(months) else np.nan
        c = strict_sum(group.capacity_bcm) if len(group) == len(months) else np.nan
        asset_rows.append({'asset': name, 'asset_flow_bcm': f, 'capacity_bcm': c,
            'utilisation_pct': safe_percent(f, c),
            'binding_months': int((group.flow_bcm-group.capacity_bcm).abs().le(TOL).sum()),
            'high_utilisation_months': int((group.flow_bcm/group.capacity_bcm).ge(.95).sum())})
    summary = pd.DataFrame(asset_rows)
    rows = []
    for name, group in flow.groupby('arc', sort=False):
        first = group.iloc[0]
        rows.append({'arc': name, 'from': first['from'], 'to': first['to'], 'asset': first.asset,
            'flow_bcm': strict_sum(group.flow_bcm) if len(group) == len(months) else np.nan,
            'kind': 'accounting' if first['to'] == 'UNROUTED' else
                ('allocation proxy' if 'PROXY' in name else 'modelled route')})
    return pd.DataFrame(rows).merge(summary, on='asset', how='left', validate='many_to_one'), summary


def comparison(run, legacy, actuals=None):
    """Outer-complete chart grid. Unavailable or incompatible models stay missing."""
    country = run['monthly'].set_index('month')[COUNTRIES]
    groups = aggregate_groups(country)
    rows = []
    lookup = legacy['data'].set_index(['month', 'level', 'destination'])
    for level, frame in [('countries', country), ('groups', groups)]:
        for month, values in frame.iterrows():
            for destination, model in values.items():
                key = (month, level, destination)
                source = lookup.loc[key] if key in lookup.index else None
                compatible = bool(source is not None and source.compatible)
                cached = source.value_bcm if source is not None else np.nan
                legacy_model = cached if compatible and legacy['kind'] == 'forecast' else np.nan
                context = cached if legacy['kind'] == 'workbook_history' and destination not in ['PL', 'Baltic Pipe'] else np.nan
                delta = model-legacy_model
                rows.append({'run_id': run['id'], 'scenario': run['scenario'], 'month': month,
                    'level': level, 'destination': destination, 'unit': 'bcm/month',
                    'model_bcm': model, 'legacy_model_bcm': legacy_model,
                    'workbook_history_bcm': context, 'legacy_source_bcm': cached,
                    'compatible': compatible, 'delta_bcm': delta,
                    'delta_pct': safe_percent(delta, legacy_model),
                    'legacy_kind': legacy['kind'], 'legacy_vintage': legacy['vintage'],
                    'status': source.status if source is not None else 'Legacy output unavailable; no disaggregation',
                    'cell': source.cell if source is not None else ''})
    prepared = pd.DataFrame(rows)
    prepared['analysis_type'] = run.get('title', 'Saved model result')
    if actuals is not None:
        references = actuals['data'].rename(columns={'value_bcm': 'ea_actual_bcm',
            'compatible': 'actual_definition_compatible', 'status': 'actual_status'})
        prepared = prepared.merge(references[['month', 'level', 'destination', 'ea_actual_bcm',
            'actual_definition_compatible', 'actual_status']], on=['month', 'level', 'destination'],
            how='left', validate='one_to_one')
        prepared['actual_definition_compatible'] = prepared.actual_definition_compatible.eq(True)
        prepared['actual_chart_bcm'] = prepared.ea_actual_bcm.where(prepared.actual_definition_compatible)
        prepared['ea_net_context_bcm'] = prepared.ea_actual_bcm.where(prepared.destination.eq('DK'))
        prepared['reconstruction_residual_bcm'] = prepared.model_bcm-prepared.actual_chart_bcm
        prepared['legacy_error_bcm'] = prepared.legacy_model_bcm-prepared.actual_chart_bcm
        prepared['legacy_error_pct'] = [safe_percent(e, a) for e, a in zip(prepared.legacy_error_bcm, prepared.actual_chart_bcm)]
        # Neither current saved run is an origin-only routing forecast.
        prepared['routing_forecast_error_bcm'] = np.nan
        prepared['routing_forecast_status'] = 'Unavailable: complete origin SID bundle and routing forecast required'
    return prepared


def actual_error_summary(frame):
    """Score legacy forecasts only; never rank revised reconstructions as forecasts."""
    rows = []
    for (level, destination), group in frame.groupby(['level', 'destination'], sort=False):
        matched = group.dropna(subset=['legacy_error_bcm', 'actual_chart_bcm'])
        error = matched.legacy_error_bcm
        denominator = matched.actual_chart_bcm.abs().sum()
        rows.append({'level': level, 'destination': destination, 'matched_months': len(matched),
            'matched_month_list': ','.join(matched.month), 'unit': 'bcm/month',
            'legacy_mae_bcm_month': error.abs().mean(), 'legacy_rmse_bcm_month': np.sqrt((error**2).mean()),
            'legacy_bias_bcm_month': error.mean(), 'legacy_bias_total_bcm': strict_sum(error),
            'legacy_wape_pct': 100*error.abs().sum()/denominator if denominator>0 else np.nan,
            'routing_forecast_mae_bcm_month': np.nan,
            'status': 'Legacy retained-state forecast versus EA historical actuals; routing forecast unavailable'})
    return pd.DataFrame(rows)


def annual_comparison(frame, expected_months):
    rows = []
    for (level, destination), group in frame.groupby(['level', 'destination'], sort=False):
        complete = len(group) == len(expected_months)
        row = {'level': level, 'destination': destination, 'months': len(group),
               'matched_model_months': int(group.legacy_model_bcm.notna().sum())}
        for col in ['model_bcm', 'legacy_model_bcm', 'workbook_history_bcm', 'delta_bcm']:
            row[col] = strict_sum(group[col]) if complete else np.nan
        for col in ['actual_chart_bcm', 'legacy_error_bcm', 'reconstruction_residual_bcm']:
            if col in group:
                row[col] = strict_sum(group[col]) if complete else np.nan
        row['delta_pct'] = safe_percent(row['delta_bcm'], row['legacy_model_bcm'])
        rows.append(row)
    return pd.DataFrame(rows)
