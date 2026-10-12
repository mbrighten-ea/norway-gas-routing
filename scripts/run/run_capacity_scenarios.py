"""Explicit capacity experiment on an authorised frozen prepared-input bundle.

No workbook/cache sourcing, fresh-input claim, scoring or baseline publication.
The SID-only exception must be authorised before passing the comparison flag.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
import yaml
import pulp

from norway_gas_routing.capacity_inputs import SCENARIOS, baseline_rate, database_candidates, select_capacity_scenario
from norway_gas_routing.evaluation import check_dates, load_policy
from norway_gas_routing.poc import DESTINATIONS, available_solver, build_month, network_definition, solve_month, validate_solution
from norway_gas_routing.public_capacity import sha256


def frozen_inputs(model, year):
    """Saved prepared inputs only, under explicit experiment-specific permission.

    Rates without maintenance are reconstructed from unchanged configuration to
    avoid rounded CSV capacities. Kollsnes preserves saved effective capacity.
    2025 maintenance is recovered algebraically from the frozen effective limit,
    and is labelled a monthly-equivalent assumption, not a daily outage history.
    """
    months = pd.period_range(f'{year}-01', f'{year}-12', freq='M')
    check_dates(months, 'analysis')
    selected_files = []
    if year == 2024:
        folder = ROOT / 'outputs/reconstruction/provenance'
        paths = {name: folder / 'inputs' / name for name in ('source_supply.csv', 'monthly_capacities.csv', 'daily_capacities.csv')}
        source = pd.read_csv(paths['source_supply.csv'])
        source.columns = [c.removesuffix('_supply_bcm') for c in source.columns]
        caps = pd.read_csv(paths['monthly_capacities.csv'])
        daily = pd.read_csv(paths['daily_capacities.csv'])
        manifest_path = folder / 'run_manifest.json'
        preferences = json.loads(manifest_path.read_text(encoding='utf-8'))['baseline_preferences']
    else:
        folder = ROOT / 'archive/20261009-13_snohvit-sensitivity'
        paths = {name: folder / name for name in ('source_supply.csv', 'asset_constraints.csv')}
        source = pd.read_csv(paths['source_supply.csv']).query("scenario == 'official-net-production'").drop(columns='scenario')
        caps = pd.read_csv(paths['asset_constraints.csv']).query("scenario == 'official-net-production'")
        caps = caps.rename(columns={'capacity_bcm': 'available_capacity_bcm'})
        manifest_path = folder / 'manifest.json'
        preferences = json.loads(manifest_path.read_text(encoding='utf-8'))['preferences']
        daily = None
    selected_files.extend([*paths.values(), manifest_path])
    source.index = pd.PeriodIndex(source.pop('month'), freq='M')
    source = source.reindex(months)
    caps['month'] = pd.PeriodIndex(caps.month, freq='M')
    capacity = caps.pivot(index='month', columns='asset', values='available_capacity_bcm').reindex(months)
    for asset, entry in model['poc']['assets'].items():
        if not entry.get('maintenance_series'):
            rate = baseline_rate(entry)
            capacity[asset] = months.days_in_month * rate / 1000
    if daily is None:
        records = []
        for asset, entry in model['poc']['assets'].items():
            rate = baseline_rate(entry)
            for month in months:
                derate = rate - capacity.at[month, asset] * 1000 / month.days_in_month
                for day in pd.date_range(month.start_time, month.end_time.normalize()):
                    records.append(dict(date=day, asset=asset, technical_capacity_mcm_d=rate,
                        maintenance_derate_mcm_d=derate, available_capacity_mcm_d=rate-derate,
                        coverage_status='monthly equivalent of saved effective limit; daily restrictions unknown'))
        daily = pd.DataFrame(records)
    else:
        daily['date'] = pd.to_datetime(daily.date)
    if source.isna().any().any() or capacity.isna().any().any():
        raise ValueError('Incomplete frozen bundle; no fill/substitution')
    return dict(months=months, supply=source, capacities=capacity,
        capacity_daily=daily, preferences=preferences, provenance=[]), {
            p.relative_to(ROOT).as_posix(): sha256(p) for p in selected_files}


def run_scenarios(output, scenarios, years, *, authorization_reference):
    if not authorization_reference.strip():
        raise ValueError('Explicit user authorization reference required for frozen inputs')
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.scratch/runs'):
        raise ValueError('Use a new repository scratch experiment directory')
    output.mkdir()  # Never overwrite previous output.
    model = yaml.safe_load((ROOT / 'config/model.yaml').read_text(encoding='utf-8'))
    network = network_definition(model['poc'])
    solver_name, solver = available_solver('HiGHS')
    rows, arcs, constraints, balances, selected, evidence, source_rows, replay = [], [], [], [], [], [], [], []
    file_hashes = {}
    for year in years:
        inputs, hashes = frozen_inputs(model, year)
        file_hashes.update(hashes)
        candidates = database_candidates(ROOT, model, inputs['months'])
        evidence.append(candidates)
        source_rows.append(inputs['supply'].rename_axis('month').reset_index().assign(year=year))
        results = {}
        for scenario in dict.fromkeys(['baseline', *scenarios]):
            candidate = select_capacity_scenario(inputs, model, scenario=scenario, candidates=candidates)
            selected.append(candidate['selected_capacity_inputs'].assign(year=year))
            for month in inputs['months']:
                supply = inputs['supply'].loc[month].to_dict()
                caps = candidate['capacities'].loc[month].to_dict()
                physical = build_month(network,supply,caps,inputs['preferences'],str(month))
                stats = physical['problem'].solve(solver)
                if stats.status != pulp.LpSolveStatus.Optimal:
                    raise RuntimeError('Stage-1 marginal LP failed')
                duals = {c.name.removeprefix('capacity_'): c.pi for c in physical['problem'].constraints() if c.name.startswith('capacity_')}
                result = solve_month(build_month(network,supply,caps,inputs['preferences'],str(month)),solver)
                checks = validate_solution(network,supply,caps,result)
                results[scenario,str(month)] = result
                total = sum(result['destinations'].values())
                row=dict(year=year,month=str(month),scenario=scenario,total_exports_bcm=total,
                    total_unrouted_bcm=result['unrouted'],UNMAPPED_bcm=supply['UNMAPPED'],
                    mapped_disposal_bcm=result['unrouted']-supply['UNMAPPED'],
                    **result['destinations'], **checks)
                for asset,arc in [('KOLLSNES_EXPORT','KOLLSNES_PROCESSING'),('KARSTO_PROCESSING','KARSTO_PROCESSING'),('NORTH_SEA_ENTRY','NORTH_SEA_ENTRY'),('BALTIC_PIPE','BALTIC_PIPE')]:
                    row[asset+'_flow_bcm']=result['flows'][arc]
                    row[asset+'_capacity_bcm']=caps[asset]
                    row[asset+'_utilisation_pct']=result['flows'][arc]/caps[asset]*100 if caps[asset] else None
                row.update({'FR+BE':row['FR']+row['BE'], 'NL+DE':row['NL']+row['DE'], 'Baltic Pipe':row['PL']})
                rows.append(row)
                incoming, outgoing, asset_flows = {}, {}, {}
                for arc in network['arcs']:
                    flow=result['flows'][arc['id']]
                    incoming[arc['to']]=incoming.get(arc['to'],0)+flow
                    outgoing[arc['from']]=outgoing.get(arc['from'],0)+flow
                    if arc['asset']: asset_flows[arc['asset']]=asset_flows.get(arc['asset'],0)+flow
                    arcs.append(dict(year=year,month=str(month),scenario=scenario,arc=arc['id'],flow_bcm=flow))
                for asset,flow in asset_flows.items():
                    constraints.append(dict(year=year,month=str(month),scenario=scenario,asset=asset,
                        flow_bcm=flow,capacity_bcm=caps[asset],margin_bcm=caps[asset]-flow,
                        binding=abs(caps[asset]-flow)<=1e-7,
                        stage1_export_gain_per_capacity_bcm=-duals[asset] if duals[asset] is not None else None,
                        marginal_basis='stage-1 minimum disposal LP; local possibly nonunique dual; no preference/price interpretation'))
                for node,entry in network['nodes'].items():
                    sink=result['destinations'].get(node,0) if entry['kind']=='destination' else result['unrouted'] if entry['kind']=='unrouted' else 0
                    balances.append(dict(year=year,month=str(month),scenario=scenario,node=node,
                        source_bcm=supply.get(node,0),incoming_bcm=incoming.get(node,0),outgoing_bcm=outgoing.get(node,0),
                        sink_bcm=sink,residual_bcm=supply.get(node,0)+incoming.get(node,0)-outgoing.get(node,0)-sink))
        if year == 2024:
            old=pd.read_csv(ROOT/'outputs/reconstruction/results.csv')
            old.index=pd.PeriodIndex(old.month,freq='M').astype(str)
            for month in inputs['months']:
                result=results['baseline',str(month)]
                errors={d: result['destinations'][d]-old.at[str(month),d+'_volume_bcm'] for d in DESTINATIONS}
                errors['unrouted']=result['unrouted']-old.at[str(month),'unrouted_supply_bcm']
                errors['total_exports']=sum(result['destinations'].values())-old.at[str(month),'total_exports_bcm']
                replay.append(dict(year=year,month=str(month),max_absolute_difference_bcm=max(abs(v) for v in errors.values()),**errors))
        else:
            old=pd.read_csv(ROOT/'archive/20261009-13_snohvit-sensitivity/monthly_seven_countries.csv').query("scenario == 'official-net-production'").set_index('month')
            for month in inputs['months']:
                result=results['baseline',str(month)]
                errors={d: result['destinations'][d]-old.at[str(month),d] for d in DESTINATIONS}
                errors['unrouted']=result['unrouted']-old.at[str(month),'unrouted_bcm']
                errors['total_exports']=sum(result['destinations'].values())-old.at[str(month),'exports_bcm']
                replay.append(dict(year=year,month=str(month),max_absolute_difference_bcm=max(abs(v) for v in errors.values()),**errors))
    if max(r['max_absolute_difference_bcm'] for r in replay)>1e-9:
        raise ValueError('Frozen baseline replay exceeds established 1e-9 bcm tolerance')
    frame=pd.DataFrame(rows)
    reported_assets=('KOLLSNES_EXPORT','KARSTO_PROCESSING','NORTH_SEA_ENTRY','BALTIC_PIPE')
    metrics=['total_exports_bcm','total_unrouted_bcm','UNMAPPED_bcm','mapped_disposal_bcm',*DESTINATIONS,'FR+BE','NL+DE','Baltic Pipe',
        *[a+s for a in reported_assets for s in ('_flow_bcm','_capacity_bcm')]]
    utilisation_metrics=[a+'_utilisation_pct' for a in reported_assets]
    deltas=[]
    for row in rows:
        base=frame.loc[frame.year.eq(row['year']) & frame.month.eq(row['month']) & frame.scenario.eq('baseline')].iloc[0]
        deltas.append({k:row[k] for k in ('year','month','scenario')} | {k:row[k]-base[k] if row[k] is not None else None for k in metrics+utilisation_metrics})
    delta_frame=pd.DataFrame(deltas)
    annual=frame.groupby(['year','scenario'])[metrics].sum().reset_index()
    annual_delta=delta_frame.groupby(['year','scenario'])[metrics].sum().reset_index()
    for asset in reported_assets:
        annual[asset+'_utilisation_pct']=100*annual[asset+'_flow_bcm']/annual[asset+'_capacity_bcm'].replace(0,float('nan'))
    for column in utilisation_metrics:
        annual_delta[column]=[annual.loc[annual.year.eq(row.year) & annual.scenario.eq(row.scenario),column].iloc[0]-
            annual.loc[annual.year.eq(row.year) & annual.scenario.eq('baseline'),column].iloc[0] for row in annual_delta.itertuples()]
    for name,table in [('monthly_results',frame),('monthly_differences',delta_frame),('annual_results',annual),('annual_differences',annual_delta),
            ('arc_flows',pd.DataFrame(arcs)),('asset_constraints',pd.DataFrame(constraints)),('node_balances',pd.DataFrame(balances)),
            ('selected_capacity_inputs',pd.concat(selected)),('database_candidates',pd.concat(evidence)),
            ('source_supply',pd.concat(source_rows)),('baseline_replay',pd.DataFrame(replay))]:
        table.to_csv(output/(name+'.csv'),index=False,float_format='%.12g')
    manifest=dict(run_at=datetime.now(timezone.utc).isoformat(),analysis='authorised frozen-input model-to-model capacity sensitivity',
        authorization_reference=authorization_reference,scenarios=scenarios,years=years,solver=solver_name,
        objective='unchanged maximum exports; minimum L1; minimum worst fractional shortfall',
        input_sha256=file_hashes,config_sha256=sha256(ROOT/'config/model.yaml'),policy=load_policy(),
        holdout_loaded=False,holdout_scored=False,price_response=False,public_capacity_replacements=0,
        baseline_max_difference_bcm=max(r['max_absolute_difference_bcm'] for r in replay),
        caveat_2025='Explicit saved official-net-production diagnostic; monthly equivalent maintenance is not reconstructed daily availability',
        code_sha256={p.relative_to(ROOT).as_posix():sha256(p) for p in [Path(__file__), *[(ROOT/'src/norway_gas_routing'/n) for n in ('poc.py','poc_inputs.py','capacity_inputs.py','capacity_conversion.py','capacity_constraints.py')]]})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(annual_delta[['year','scenario','total_exports_bcm',*DESTINATIONS]].to_string(index=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--scenario',choices=SCENARIOS,action='append',required=True)
    parser.add_argument('--year',type=int,choices=[2024,2025],action='append',required=True)
    parser.add_argument('--frozen-input-comparison',action='store_true')
    parser.add_argument('--authorization-reference',default='')
    args=parser.parse_args()
    if not args.frozen_input_comparison:
        parser.error('Fresh-SID sourcing remains required; frozen comparison needs explicit user permission and flag')
    run_scenarios(args.output,args.scenario,list(dict.fromkeys(args.year)),authorization_reference=args.authorization_reference)


if __name__=='__main__': main()
