"""Observed-group feasibility only; no preference/max-export restrictions.

These are partial-boundary diagnostics, not actual node-ledger reconstruction.
Free feeds prove only existence under assumed envelopes. Fixed feeds test forecast
compatibility and cannot by themselves establish physical model infeasibility.
"""
from pathlib import Path
from collections import defaultdict
import sys,json,importlib.util
import pandas as pd,numpy as np,pulp
R=Path.cwd();sys.path.insert(0,str(R/'src'));sys.path.insert(0,str(R/'scripts/run'))
from norway_gas_routing.config import load_config
from norway_gas_routing.routing import network_definition,available_solver,validate_solution
spec=importlib.util.spec_from_file_location('physical_envelopes',R/'scripts/run/run_routing_flexibility.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
base=R/'outputs/revision_tolerant_2025';scratch=R/'.scratch/runs/20261014-01_physical-commercial-gate'
scratch.mkdir(parents=True,exist_ok=True)
read=lambda n:pd.read_csv(base/n,index_col='month')
obs=read('details/observations.csv');production=read('details/production_evaluation.csv')
supply=read('provenance/inputs/supply.csv');account=read('provenance/inputs/reconciliation.csv')
capacities=read('provenance/inputs/capacities.csv')
model,_=load_config(base/'provenance/model.yaml',base/'provenance/data_series.csv')
network=network_definition(model['routing']);solver=available_solver('HiGHS')[1]
rows=[];witness=[];saved={}

def free_feeds(capacities,budget):
    # Identical physical node/arc/asset equations to physical_problem; actual
    # node injections are unknown, so existential feed variables replace RHS.
    p=pulp.LpProblem('partial_observed_feasibility',pulp.LpMinimize)
    feeds={n:p.add_variable('unknown_injection_'+n,lowBound=0) for n,e in network['nodes'].items()
           if e['kind']=='source' and n not in {'UNMAPPED','UK_DIRECT'}}
    flows={a['id']:p.add_variable('flow_'+a['id'],lowBound=0) for a in network['arcs']}
    dest={d:p.add_variable('destination_'+d,lowBound=0) for d in ['UK','FR','BE','DE','NL','DK','PL']}
    unrouted=p.add_variable('unrouted_supply',lowBound=0)
    incoming,outgoing,assets=defaultdict(list),defaultdict(list),defaultdict(list)
    for a in network['arcs']:
        incoming[a['to']].append(flows[a['id']]);outgoing[a['from']].append(flows[a['id']])
        if a['asset']:assets[a['asset']].append(flows[a['id']])
    for n,e in network['nodes'].items():
        sink=dest[n] if e['kind']=='destination' else unrouted if e['kind']=='unrouted' else 0
        p+=feeds.get(n,0)+pulp.lpSum(incoming[n])==pulp.lpSum(outgoing[n])+sink,'balance_'+n
    for a,v in assets.items():p+=pulp.lpSum(v)<=capacities[a],'capacity_'+a
    p+=pulp.lpSum(feeds.values())<=budget,'national_pipeline_upper_bound'
    return dict(problem=p,feeds=feeds,flows=flows,destinations=dest,unrouted=unrouted)

for month in obs.index:
    for scenario,rate in [('Reference156',156),('Planning143',143)]:
        caps=capacities.loc[month].to_dict();caps['KOLLSNES_EXPORT']=rate*pd.Period(month,'M').days_in_month/1000
        for case in ['free Gassco feeds','frozen forecast feeds']:
            correction=account.at[month,'legacy_excluded_uk_direct_bcm'] if case.startswith('frozen') else 0.
            if case.startswith('free'):
                built=free_feeds(caps,production.at[month,'pipeline_actual_bcm'])
            else:built=module.physical_problem(network,supply.loc[month].to_dict(),caps)
            p=built['problem'];d=built['destinations']
            p+=d['UK']==obs.at[month,'UK']+correction,'observed_UK_scope'
            p+=d['FR']+d['BE']==obs.at[month,'FR+BE'],'observed_FR_BE'
            p+=d['NL']+d['DE']==obs.at[month,'NL+DE'],'observed_DE_NL'
            # Pure existence: no preference variables and no stage-1 export optimum.
            p.setObjective(pulp.lpSum([]));assert not any('preference' in str(c) for c in p.constraints())
            stats=p.solve(solver);status=stats.status_str
            row=dict(month=month,scenario=scenario,case=case,status=status,
                observed_common_bcm=obs.at[month,'Common total'],UK_scope_packet_bcm=correction,
                observed_pipeline_upper_bound_bcm=production.at[month,'pipeline_actual_bcm'],
                source_policy='Unknown feeds, UK_DIRECT=UNMAPPED=0; witnesses are not actual production' if case.startswith('free') else 'Origin-frozen forecasts; non-Gassco UK packet is forecast, not observed',
                missing_boundaries='DK/PL unconstrained; FR/BE and DE/NL splits free; terminal limits not independently validated')
            if stats.status==pulp.LpSolveStatus.Optimal:
                result=dict(flows={k:float(v.varValue) for k,v in built['flows'].items()},
                    destinations={k:float(v.varValue) for k,v in d.items()},unrouted=float(pulp.value(built['unrouted'])))
                inputs={n:float(built['feeds'][n].varValue) if n in built.get('feeds',{}) else 0.
                    for n,e in network['nodes'].items() if e['kind']=='source'} if case.startswith('free') else supply.loc[month].to_dict()
                row.update(validate_solution(network,inputs,caps,result))
                row['unknown_feed_total_bcm']=sum(inputs.values())
                row['disposal_bcm']=result['unrouted']
                for g,ds in {'FR+BE':['FR','BE'],'NL+DE':['NL','DE'],'UK':['UK']}.items():
                    assert abs(sum(result['destinations'][x] for x in ds)-obs.at[month,g]-(correction if g=='UK' else 0))<1e-7
                saved[month+'|'+scenario+'|'+case]=dict(result=result,inputs=inputs,capacities=caps)
                for n,value in inputs.items():witness.append(dict(month=month,scenario=scenario,case=case,node=n,bcm=value,
                    interpretation='Existence witness only; never a calibrated source vector' if case.startswith('free') else 'Frozen forecast input'))
            rows.append(row)

# Analytic domain for UK-France-only swaps, holding every other arc fixed.
# No price objective is implemented. Existing three optima and all capacities stay fixed.
solved=json.loads((base/'provenance/solver_results.json').read_text())['Physical156']
prefs=json.loads((base/'provenance/inputs/preferences.json').read_text());domains=[]
for month,s in solved.items():
    total=sum(s['destinations'].values());uk=s['destinations']['UK'];fr=s['destinations']['FR']
    a=uk-prefs['UK']*total;b=fr-prefs['FR']*total
    pair=abs(a)+abs(b);pair_min=abs(a+b)
    # If the pair is not already on its flat minimum, convexity and the global
    # saved optimum preclude any nonzero feasible equal-loss interval.
    lo,hi=(min(-a,b),max(-a,b)) if abs(pair-pair_min)<1e-7 else (0.,0.)
    lo=max(lo,-s['flows']['LANGELED_SOUTH'],fr-capacities.at[month,'FRANPIPE'],
        prefs['UK']*total*(1-s['maximum_fractional_shortfall'])-uk)
    hi=min(hi,capacities.at[month,'LANGELED_SOUTH']-s['flows']['LANGELED_SOUTH'],fr,
        fr-prefs['FR']*total*(1-s['maximum_fractional_shortfall']))
    assert lo<=1e-7 and hi>=-1e-7
    lo,hi=min(lo,0.),max(hi,0.)
    for delta in [lo,hi,0.]:
        assert abs(abs(a+delta)+abs(b-delta)-pair)<1e-7
        trial=json.loads(json.dumps(s));trial['flows']['LANGELED_SOUTH']+=delta;trial['flows']['FRANPIPE']-=delta
        trial['destinations']['UK']+=delta;trial['destinations']['FR']-=delta
        validate_solution(network,supply.loc[month].to_dict(),capacities.loc[month].to_dict(),trial)
        assert abs(sum(trial['destinations'].values())-total)<1e-7
        assert trial['unrouted']==s['unrouted']
        loss=sum(abs(trial['destinations'][d]-prefs[d]*total) for d in prefs)
        original_loss=sum(abs(s['destinations'][d]-prefs[d]*total) for d in prefs)
        assert abs(loss-original_loss)<1e-7
        shortfall=max(max(0.,1-trial['destinations'][d]/(prefs[d]*total))
                      for d in prefs if prefs[d]>0)
        assert abs(shortfall-s['maximum_fractional_shortfall'])<1e-7
    domains.append(dict(month=month,UK_increment_min_bcm=lo,UK_increment_max_bcm=hi,
        physical_optimal_width_bcm=hi-lo,commercial_access='Unknown; no rights assumed by this calculation',
        fixed_routes='UK_DIRECT,VESTERLED,ZEEPIPE_EXPORT,DE/NL,Nordic and all upstream arcs'))
pd.DataFrame(rows).to_csv(scratch/'feasibility.csv',index=False)
pd.DataFrame(witness).to_csv(scratch/'source_witnesses.csv',index=False)
pd.DataFrame(domains).to_csv(scratch/'two_route_domains.csv',index=False)
(scratch/'physical_witnesses.json').write_text(json.dumps(saved,indent=2)+'\n')
print(pd.DataFrame(rows)[['month','scenario','case','status']].to_string(index=False))
print('TWO-ROUTE DOMAINS',pd.DataFrame(domains)[['month','UK_increment_min_bcm','UK_increment_max_bcm']].to_string(index=False))
