"""Authorised 2025 Snøhvit diagnostics; never publish a validated baseline."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import pandas as pd
from norway_gas_routing.artifacts import new_experiment
from norway_gas_routing.benchmark import GROUPS
from norway_gas_routing.config import load_config
from norway_gas_routing.evaluation import check_table, load_policy, read_parquet
from norway_gas_routing.poc import DESTINATIONS, available_solver, build_month, network_definition, solve_month, validate_solution
from norway_gas_routing.poc_inputs import prepare_inputs

MONTHS = pd.period_range('2025-01', '2025-12', freq='M')
SCENARIOS = ('official-net-production', 'selected-series-mixed-vintage')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def official_snohvit(path):
    """Parse retained official net gas, selecting 2025 before numeric values."""
    text = path.read_text(encoding='utf-8')
    start = text.index('<caption>Production , saleable</caption>')
    block = text[start:text.index('</table>', start)]
    assert 'bill Sm3' in block[:block.index('</thead>')]
    year, values = None, {}
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', block, re.S):
        cells = re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.S)
        if not cells:
            continue
        first = html.unescape(re.sub('<[^>]+>', ' ', cells[0])).strip()
        if re.fullmatch(r'\d{4}', first):
            year = int(first)
        elif year == 2025 and re.fullmatch(r'\d{1,2}', first):
            month = pd.Period(f'2025-{int(first):02d}', freq='M')
            if month in values:
                raise ValueError('Duplicate official month')
            values[month] = float(html.unescape(re.sub('<[^>]+>', ' ', cells[2])).strip())
    result = pd.Series(values, dtype=float).sort_index()
    if not result.index.equals(MONTHS) or not np.isfinite(result).all():
        raise ValueError('Complete official 2025 net gas required')
    return result


def save(frame, run, name):
    frame = frame.copy()
    if 'month' in frame and isinstance(frame.month.dtype, pd.PeriodDtype):
        frame['month'] = frame.month.astype(str)
    check_table(frame, 'analysis')
    frame.to_csv(run / name, index=False, float_format='%.12g')


def score(comparisons):
    """Matched signed volume errors; WAPE denominator uses absolute observations."""
    check_table(comparisons, 'score')
    rows = []
    for (scenario, level), cells in comparisons.groupby(['scenario', 'level'], sort=False):
        for destination in list(cells.destination.unique()) + ['ALL']:
            frame = cells if destination == 'ALL' else cells.loc[cells.destination.eq(destination)]
            frame = frame.loc[np.isfinite(frame.observed_bcm) & np.isfinite(frame.modelled_bcm)]
            denominator = frame.observed_bcm.abs().sum()
            rows.append({'scenario': scenario, 'level': level, 'destination': destination,
                'matched_months': frame.month.nunique(), 'matched_cells': len(frame),
                'WAPE_pct': 100 * frame.error_bcm.abs().sum() / denominator if denominator else np.nan,
                'MAE_bcm_per_cell': frame.error_bcm.abs().mean(),
                'signed_bias_bcm_per_cell': frame.error_bcm.mean(), 'signed_bias_total_bcm': frame.error_bcm.sum(),
                'modelled_period_bcm': frame.modelled_bcm.sum(), 'observed_period_bcm': frame.observed_bcm.sum(),
                'share_eligible_months': frame.loc[frame.share_eligible].month.nunique(),
                'negative_observation_cells': int(frame.observed_bcm.lt(0).sum()),
                'comparison_boundary': 'retained revised EA destination allocation proxies; not independently verified physical exports'})
    return pd.DataFrame(rows)


def solve(inputs, network, scenario, solver):
    rows, groups, assets, arcs, comparisons = [], [], [], [], []
    for month in inputs['months']:
        supply, capacity = inputs['supply'].loc[month].to_dict(), inputs['capacities'].loc[month].to_dict()
        result = solve_month(build_month(network, supply, capacity, inputs['preferences'], str(month)), solver)
        checks = validate_solution(network, supply, capacity, result)
        reconciliation = inputs['reconciliation'].loc[month]
        np.testing.assert_allclose(sum(supply.values()), reconciliation.norway_total_production_bcm -
            reconciliation.snohvit_net_production_bcm, rtol=0, atol=1e-12)
        np.testing.assert_allclose(supply['UNMAPPED'], reconciliation.pipeline_supply_proxy_bcm -
            reconciliation.mapped_source_supply_bcm, rtol=0, atol=1e-12)
        rows.append({'scenario': scenario, 'month': month, **result['destinations'],
                     'total_pipeline_supply_bcm': sum(supply.values()),
                     'exports_bcm': sum(result['destinations'].values()), 'unrouted_bcm': result['unrouted'], **checks})
        group_values = {group: sum(result['destinations'][d] for d in members) for group, members in GROUPS.items()}
        groups.append({'scenario': scenario, 'month': month, **group_values,
                       'exports_bcm': sum(result['destinations'].values())})
        observed = inputs['observed'].loc[month]
        share_eligible = observed[list(DESTINATIONS)].notna().all() and observed[list(DESTINATIONS)].ge(0).all()
        for level, mapping in [('seven_countries', {d: [d] for d in DESTINATIONS}), ('five_legacy_groups', GROUPS)]:
            for group, members in mapping.items():
                actual = observed[{'FR+BE': 'FR_BE', 'NL+DE': 'NL_DE'}.get(group, members[0])]
                modelled = sum(result['destinations'][d] for d in members)
                comparisons.append({'scenario': scenario, 'month': month, 'level': level, 'destination': group,
                    'modelled_bcm': modelled, 'observed_bcm': actual, 'error_bcm': modelled - actual,
                    'share_eligible': bool(share_eligible),
                    'observation_status': 'signed net allocation proxy' if actual < 0 else 'revised allocation proxy'})
        for asset, cap in capacity.items():
            flow = sum(result['flows'][a['id']] for a in network['arcs'] if a['asset'] == asset)
            assets.append({'scenario': scenario, 'month': month, 'asset': asset, 'flow_bcm': flow,
                           'capacity_bcm': cap, 'margin_bcm': cap - flow, 'binding': abs(cap - flow) <= 1e-7})
        for arc in network['arcs']:
            arcs.append({'scenario': scenario, 'month': month, 'arc': arc['id'], 'from': arc['from'],
                         'to': arc['to'], 'asset': arc['asset'], 'flow_bcm': result['flows'][arc['id']]})
    return [pd.DataFrame(table) for table in (rows, groups, assets, arcs, comparisons)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, help='An already reserved empty named experiment')
    args = parser.parse_args()
    run = args.run_dir.resolve() if args.run_dir else new_experiment(ROOT, 'snohvit-sensitivity')
    if not run.is_relative_to(ROOT / '.scratch/runs') or not run.is_dir() or any(run.iterdir()):
        raise ValueError('Use a new empty repository-local experiment')
    protected_paths = [ROOT / '.git/index']
    for folder in ('src', 'config', 'data/raw', 'outputs'):
        protected_paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file())
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected_paths if p.exists()}
    prior = json.loads((ROOT / 'evidence/inputs/snohvit_2025_baseline_manifest.json').read_text())
    assert prior['baseline_2024_matches_existing_within_bcm'] == 1e-9
    model, registry = load_config(ROOT / 'config/model.yaml', ROOT / 'config/data_series.csv')
    candidate = deepcopy(model)
    candidate['poc'].update(start='2025-01', end='2025-12')
    audit = pd.read_csv(ROOT / 'evidence/inputs/data_series_audit.csv').set_index('sid')
    record = audit.loc[registry.at['snohvit_net_prod', 'sid']]
    raw, metadata = ROOT / record.raw_file, ROOT / record.metadata_file
    primary = ROOT / 'data/raw/series_audit/snohvit_sodir_primary_20261008.html'
    selected_rate = read_parquet(raw, start='2025-01-01', end='2025-12-31').value
    selected_rate.index = selected_rate.index.to_period('M')
    selected = selected_rate * selected_rate.index.days_in_month / 1000
    official = official_snohvit(primary)
    assert selected.index.equals(MONTHS) and np.isfinite(selected).all()
    source_comparison = pd.DataFrame({'official_net_bcm': official, 'selected_rate_mcm_d': selected_rate,
        'calendar_days': MONTHS.days_in_month, 'selected_converted_bcm': selected,
        'selected_minus_official_bcm': selected - official,
        'selected_source_forecast': MONTHS >= pd.Period('2025-10', freq='M')}).rename_axis('month').reset_index()
    save(source_comparison, run, 'snohvit_inputs.csv')
    network = network_definition(candidate['poc'])
    solver_name, solver = available_solver('HiGHS')
    prepared, tables, summaries = {}, {}, {}
    for scenario, values in zip(SCENARIOS, (official, selected)):
        inputs = prepare_inputs(ROOT, candidate, registry, analysis_mode='snohvit_sensitivity',
                                diagnostic_scenario=scenario, diagnostic_snohvit_bcm=values)
        prepared[scenario] = inputs
        assert inputs['training_observations'].index.max() <= pd.Period('2024-12', freq='M')
        outputs = solve(inputs, network, scenario, solver)
        for name, frame in zip(('monthly_seven_countries.csv', 'monthly_five_groups.csv',
                               'asset_constraints.csv', 'arc_flows.csv', 'observed_comparison.csv'), outputs):
            tables.setdefault(name, []).append(frame)
        reconciliation = inputs['reconciliation'].copy()
        reconciliation['scenario'] = scenario
        tables.setdefault('source_reconciliation.csv', []).append(reconciliation.rename_axis('month').reset_index())
        sources = inputs['supply'].copy()
        sources['scenario'] = scenario
        tables.setdefault('source_supply.csv', []).append(sources.rename_axis('month').reset_index())
        flow = outputs[0]
        summaries[scenario] = {'months': len(flow), 'norway_total_bcm': reconciliation.norway_total_production_bcm.sum(),
            'snohvit_bcm': values.sum(), 'pipeline_supply_bcm': flow.total_pipeline_supply_bcm.sum(),
            'exports_bcm': flow.exports_bcm.sum(), 'unrouted_bcm': flow.unrouted_bcm.sum(),
            'max_mass_balance_residual_bcm': flow.max_mass_balance_residual_bcm.max(),
            'max_capacity_violation_bcm': flow.max_capacity_violation_bcm.max()}
    left, right = (prepared[name] for name in SCENARIOS)
    pd.testing.assert_frame_equal(left['capacities'], right['capacities'])
    pd.testing.assert_frame_equal(left['capacity_daily'], right['capacity_daily'])
    pd.testing.assert_frame_equal(left['supply'].drop(columns='UNMAPPED'), right['supply'].drop(columns='UNMAPPED'))
    pd.testing.assert_frame_equal(left['observed'], right['observed'])
    assert left['preferences'] == right['preferences']
    np.testing.assert_allclose(right['supply'].UNMAPPED - left['supply'].UNMAPPED, official - selected, rtol=0, atol=1e-12)
    for name, parts in tables.items():
        save(pd.concat(parts, ignore_index=True), run, name)
    comparisons = pd.concat(tables['observed_comparison.csv'], ignore_index=True)
    scores = score(comparisons)
    save(scores, run, 'metrics.csv')
    frames = [frame.set_index('month').drop(columns='scenario') for frame in tables['monthly_seven_countries.csv']]
    delta = frames[1] - frames[0]
    delta.columns = ['selected_minus_official_' + name for name in delta.columns]
    delta['selected_minus_official_snohvit_bcm'] = selected - official
    delta['selected_minus_official_unmapped_bcm'] = right['supply'].UNMAPPED - left['supply'].UNMAPPED
    save(delta.rename_axis('month').reset_index(), run, 'scenario_changes.csv')
    group_frames = [frame.set_index('month').drop(columns='scenario')
                    for frame in tables['monthly_five_groups.csv']]
    group_delta = group_frames[1] - group_frames[0]
    group_delta.columns = ['selected_minus_official_' + name for name in group_delta.columns]
    save(group_delta.rename_axis('month').reset_index(), run, 'five_group_changes.csv')
    baseline = prepare_inputs(ROOT, model, registry)
    replay = solve(baseline, network_definition(model['poc']), '2024-baseline-replay', solver)[0]
    saved = pd.read_csv(ROOT / 'outputs/reconstruction/results.csv').set_index('month')
    for row in replay.itertuples():
        old = saved.loc[str(row.month.start_time.date())]
        for destination in DESTINATIONS:
            assert abs(getattr(row, destination) - old[destination + '_volume_bcm']) <= 1e-9
        assert abs(row.unrouted_bcm - old.unrouted_supply_bcm) <= 1e-9
    save(replay, run, 'baseline_2024_replay.csv')
    try:
        prepare_inputs(ROOT, candidate, registry)
    except ValueError as exc:
        assert 'Snohvit actual conversion validated only through July 2025' in str(exc)
    else:
        raise AssertionError('Ordinary validated-input guard changed')
    assert protected == {p: sha(ROOT / p) for p in protected}
    manifest = {'run_id': run.name, 'run_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'DIAGNOSTIC_ONLY_NOT_VALIDATED_BASELINE', 'analysis_mode': 'snohvit_sensitivity',
        'period': '2025-01..2025-12', 'policy': load_policy(), 'holdout_loaded': False, 'holdout_scored': False,
        'forecast_claim': False, 'network_requests': 0, 'solver': solver_name, 'interpreter': sys.executable,
        'conversion': 'Selected mcm/day * calendar days / 1000; official already bcm; no fitted coefficients',
        'objective': 'Unchanged maximum exports, minimum L1 deviation, minimum worst fractional shortfall',
        'preferences': left['preferences'], 'training_months': left['training_observations'].index.astype(str).tolist(),
        'excluded_training_months': left['excluded_training_months'], 'parameters_fitted': False,
        'summaries': summaries, 'inputs': {name: inputs['provenance'] for name, inputs in prepared.items()},
        'snohvit_source_evidence': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in
            (primary, raw, metadata, ROOT / 'evidence/inputs/core_production_source_trace.json')],
        'input_pair_checks': 'Identical non-UNMAPPED supply, capacities, maintenance, preferences and observations',
        'baseline_2024_matches_within_bcm': 1e-9, 'ordinary_guard_preserved': True,
        'protected_sha256': protected, 'preservation_verified': True,
        'code_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (Path(__file__),
            ROOT / 'src/norway_gas_routing/poc_inputs.py', ROOT / 'src/norway_gas_routing/poc.py')}}
    (run / 'manifest.json').write_text(json.dumps(manifest, indent=2, default=str) + '\n', encoding='utf-8')
    print(json.dumps({'run': str(run), 'summaries': summaries}, indent=2))
    print(scores.loc[scores.destination.eq('ALL'), ['scenario', 'level', 'matched_months', 'WAPE_pct', 'MAE_bcm_per_cell', 'signed_bias_bcm_per_cell']].to_string(index=False))
    print('Maximum country allocation difference bcm:', float(delta.filter(regex='_(UK|FR|BE|NL|DE|DK|PL)$').abs().max().max()))


if __name__ == '__main__':
    main()
