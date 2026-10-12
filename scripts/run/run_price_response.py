"""Optional 2024 empirical price experiment; frozen supply needs separate approval."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
import pandas as pd
import yaml
from norway_gas_routing.capacity.inputs import select_capacity_scenario
from norway_gas_routing.price_response import retrieve_features, PRICE_SCALE, STRENGTHS
from norway_gas_routing.routing import (DESTINATIONS, network_definition, available_solver,
                                       build_month, solve_month, validate_solution)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(output, authorization_reference):
    if not authorization_reference.strip():
        raise ValueError('Separate explicit authorisation for frozen 2024 price experiments is required')
    output = Path(output).resolve()
    if output.parent != ROOT/'.scratch/runs':
        raise ValueError('Use a new uniquely named scratch experiment')
    model = yaml.safe_load((ROOT/'config/model.yaml').read_text(encoding='utf-8'))
    saved = ROOT/'archive/20261012-02_capacity-sensitivity'
    capacity_manifest = json.loads((saved/'manifest.json').read_bytes())
    if sha(ROOT/'config/model.yaml') != capacity_manifest['config_sha256']:
        raise ValueError('Capacity comparison configuration changed')
    for name, expected in capacity_manifest['input_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Frozen input identity changed: '+name)
    output.mkdir()
    prices = retrieve_features(output/'prices')
    spec = importlib.util.spec_from_file_location('capacity_runner', ROOT/'scripts/run/run_capacity_scenarios.py')
    capacity_runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capacity_runner)
    inputs, hashes = capacity_runner.frozen_inputs(model, 2024)
    network = network_definition(model['routing'])
    solver_name, solver = available_solver('HiGHS')
    prior = pd.read_csv(saved/'monthly_results.csv').set_index(['scenario', 'month'])
    rows, asset_rows, arc_rows = [], [], []
    zero_results = {}
    replay_max = 0.
    shocks = {'observed': None}
    for market in ['UK', 'FR', 'DE_NL']:
        for sign in [-1, 1]:
            shocks[f'{market}_{sign*20:+d}'] = (market, sign*20.)
    for capacity in ['baseline', 'kollsnes-156']:
        prepared = select_capacity_scenario(inputs, model, scenario=capacity)
        for month in inputs['months']:
            supply = inputs['supply'].loc[month].to_dict()
            caps = prepared['capacities'].loc[month].to_dict()
            baseline = solve_month(build_month(network, supply, caps, inputs['preferences'], str(month)), solver)
            old = prior.loc[capacity, str(month)]
            replay_max = max(replay_max, abs(baseline['unrouted']-old.total_unrouted_bcm),
                             *[abs(baseline['destinations'][d]-old[d]) for d in DESTINATIONS])
            if replay_max > 1e-9:
                raise ValueError('Price-free capacity replay failed 1e-9 bcm tolerance')
            zero_results[capacity, str(month)] = baseline
            for shock, change in shocks.items():
                spreads = prices.loc[month, ['UK', 'FR', 'DE_NL']].to_dict()
                if change:
                    spreads[change[0]] += change[1]
                for label, strength in STRENGTHS.items():
                    built = build_month(network, supply, caps, inputs['preferences'], str(month))
                    result = solve_month(built, solver, price_spreads=spreads,
                                         responsiveness=strength, price_scale_eur_mwh=PRICE_SCALE)
                    checks = validate_solution(network, supply, caps, result, tolerance=1e-8)
                    if abs(result['unrouted']-baseline['unrouted']) > 1e-8:
                        raise ValueError('Price incentive changed maximum exports')
                    if abs(result['stage2_final_bcm_equivalent']-result['stage2_optimum_bcm_equivalent']) > 1e-8:
                        raise ValueError('Stage 3 failed to preserve combined Stage 2 optimum')
                    differences = {d: result['destinations'][d]-baseline['destinations'][d] for d in DESTINATIONS}
                    if not strength and max(abs(v) for v in differences.values()) > 1e-9:
                        raise ValueError('Zero responsiveness failed corresponding capacity baseline')
                    row = dict(capacity=capacity, month=str(month), shock=shock, responsiveness_label=label,
                               responsiveness=strength, exports_bcm=sum(result['destinations'].values()),
                               unrouted_bcm=result['unrouted'], **result['destinations'], **checks,
                               combined_stage2_optimum=result['stage2_optimum_bcm_equivalent'],
                               combined_stage2_final=result['stage2_final_bcm_equivalent'],
                               price_reallocation_bcm=sum(abs(v) for v in differences.values())/2,
                               **{d+'_price_delta_bcm': v for d, v in differences.items()})
                    for market, spread in spreads.items():
                        row[market+'_spread_eur_mwh'] = spread
                    asset_flows = {}
                    for arc in network['arcs']:
                        flow = result['flows'][arc['id']]
                        arc_rows.append(dict(capacity=capacity, month=str(month), shock=shock,
                                             responsiveness_label=label, arc=arc['id'], flow_bcm=flow))
                        if arc['asset']:
                            asset_flows[arc['asset']] = asset_flows.get(arc['asset'], 0.)+flow
                    for asset, flow in asset_flows.items():
                        asset_rows.append(dict(capacity=capacity, month=str(month), shock=shock,
                                               responsiveness_label=label, asset=asset, flow_bcm=flow,
                                               capacity_bcm=caps[asset], utilisation_pct=100*flow/caps[asset] if caps[asset] else None,
                                               binding=abs(flow-caps[asset]) <= 1e-7))
                    row['DE_NL'] = row['DE']+row['NL']
                    row['DE_NL_price_delta_bcm'] = differences['DE']+differences['NL']
                    rows.append(row)
    frame = pd.DataFrame(rows)
    # Separate capacity effect, price effect and their interaction for every target.
    for index, row in frame.iterrows():
        base = zero_results['baseline', row.month]
        own = zero_results[row.capacity, row.month]
        for d in DESTINATIONS:
            frame.at[index, d+'_capacity_delta_bcm'] = own['destinations'][d]-base['destinations'][d]
    frame.to_csv(output/'monthly_results.csv', index=False, float_format='%.15g')
    annual_columns = ['exports_bcm', 'unrouted_bcm', *DESTINATIONS, 'DE_NL', 'price_reallocation_bcm',
                      *[d+s for d in DESTINATIONS for s in ['_price_delta_bcm', '_capacity_delta_bcm']]]
    annual = frame.groupby(['capacity', 'shock', 'responsiveness_label', 'responsiveness'])[annual_columns].sum().reset_index()
    annual.to_csv(output/'annual_results.csv', index=False, float_format='%.15g')
    pd.DataFrame(asset_rows).to_csv(output/'asset_constraints.csv', index=False, float_format='%.15g')
    pd.DataFrame(arc_rows).to_csv(output/'arc_flows.csv', index=False, float_format='%.15g')
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), analysis='2024 realised-price offline empirical sensitivity',
                    authorization_reference=authorization_reference, years=[2024], strengths=STRENGTHS,
                    feature_scale_eur_mwh=PRICE_SCALE, input_sha256=hashes, config_sha256=sha(ROOT/'config/model.yaml'),
                    policy_sha256=sha(ROOT/'config/evaluation.yaml'), registry_sha256=sha(ROOT/'config/data_series.csv'),
                    solver=solver_name, baseline_max_difference_bcm=replay_max,
                    stage2='L1 allocation deviation - lambda * sum(spread/10 EUR per MWh * destination bcm)',
                    stage3='Minimum worst fractional shortfall preserving Stage 1 and combined Stage 2 optima',
                    active_price_markets=['UK', 'FR', 'DE_NL'], neutral_markets=['BE', 'DK', 'PL'],
                    synthetic_shocks_eur_mwh=[-20, 20], calibrated=False, forecast_validation=False,
                    holdout_loaded=False, holdout_scored=False, capacity_default_changed=False,
                    capacity_caveat='156 dry-boundary assumption; signed maintenance applied once; no verified engineering upgrade schedule',
                    code_sha256={n: sha(ROOT/n) for n in ['src/norway_gas_routing/routing.py',
                        'src/norway_gas_routing/price_response.py', 'scripts/run/run_price_response.py']})
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(annual.loc[annual.shock.eq('observed'), ['capacity', 'responsiveness_label', 'exports_bcm',
                                                    'price_reallocation_bcm', 'UK_price_delta_bcm', 'FR_price_delta_bcm']].to_string(index=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frozen-2024-price-exception', action='store_true')
    parser.add_argument('--authorization-reference', default='')
    args = parser.parse_args()
    if not args.frozen_2024_price_exception:
        parser.error('Fresh-SID model sourcing remains required; a separate frozen price-experiment exception is needed')
    run(args.output, args.authorization_reference)
