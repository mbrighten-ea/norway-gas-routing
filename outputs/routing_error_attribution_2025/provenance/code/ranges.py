"""Bound queries on unchanged saved LP constraints, not new issued forecasts.

Uses the existing optimal-face diagnostic pattern. No target actual enters an LP.
"""
from pathlib import Path
import sys,json
import pandas as pd,pulp
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.config import load_config
from norway_gas_routing.routing import network_definition,build_month,available_solver,validate_solution
base=R/'outputs/revision_tolerant_2025';scratch=R/'.scratch/runs/20261014-01_routing-error-attribution'
selected=json.loads((scratch/'selected.json').read_text())['months']
model,_=load_config(base/'provenance/model.yaml',base/'provenance/data_series.csv')
network=network_definition(model['routing'])
read=lambda name:pd.read_csv(base/name,index_col='month')
supplies=read('provenance/inputs/supply.csv');capacities=read('provenance/inputs/capacities.csv')
account=read('provenance/inputs/reconciliation.csv')
prefs=json.loads((base/'provenance/inputs/preferences.json').read_text())
saved=json.loads((base/'provenance/solver_results.json').read_text())
solver=available_solver('HiGHS')[1];rows=[]
for month in selected:
 s=saved['Physical156'][month];supply=supplies.loc[month].to_dict();caps=capacities.loc[month].to_dict()
 for face in ['maximum exports','maximum exports and optimal L1','all saved objective optima']:
  for group,ds in {'UK':['UK'],'FR+BE':['FR','BE'],'NL+DE':['NL','DE']}.items():
   for bound,sign in [('minimum',1),('maximum',-1)]:
    built=build_month(network,supply,caps,prefs,month)
    built['problem']+=built['unrouted']==s['unrouted']
    if face != 'maximum exports':
     built['problem']+=built['deviation']<=s['minimum_baseline_deviation_bcm']+1e-8
    if face=='all saved objective optima':
     exports=sum(supply.values())-s['unrouted']
     for d,share in prefs.items():
      built['problem']+=built['destinations'][d]>=share*exports*(1-s['maximum_fractional_shortfall'])-1e-8
    built['problem'].setObjective(sign*pulp.lpSum(built['destinations'][d] for d in ds))
    stats=built['problem'].solve(solver)
    assert stats.status==pulp.LpSolveStatus.Optimal
    result=dict(flows={a:float(v.varValue) for a,v in built['flows'].items()},
      destinations={d:float(v.varValue) for d,v in built['destinations'].items()},
      unrouted=float(pulp.value(built['unrouted'])))
    checks=validate_solution(network,supply,caps,result)
    volume=sum(result['destinations'][d] for d in ds)
    correction=account.at[month,'legacy_excluded_uk_direct_bcm'] if group=='UK' else 0
    rows.append(dict(month=month,face=face,group=group,bound=bound,
      comparable_bcm=volume-correction,gross_bcm=volume,
      saved_comparable_bcm=sum(s['destinations'][d] for d in ds)-correction,
      L1_bcm=float(pulp.value(built['deviation'])),**checks,
      status='Optimal; diagnostic only, no target actual inputs'))
r=pd.DataFrame(rows);r.to_csv(scratch/'ranges.csv',index=False)
print(r[['month','face','group','bound','comparable_bcm','saved_comparable_bcm']].to_string(index=False))
