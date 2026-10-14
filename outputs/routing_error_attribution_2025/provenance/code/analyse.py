from pathlib import Path
import sys,json
import pandas as pd,numpy as np
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.config import load_config
from norway_gas_routing.routing import network_definition,historical_preferences
base=R/'outputs/revision_tolerant_2025'
raw=R/'data/raw/revision_tolerant_2025/20261014T115523673146Z'
read=lambda p:pd.read_csv(p)
pred=read(base/'results.csv');obs=read(base/'details/observations.csv').set_index('month')
flows=read(base/'details/frozen_forecasts.csv').set_index(['scenario','month'])
sources=read(base/'provenance/inputs/supply.csv').set_index('month')
account=read(base/'provenance/inputs/reconciliation.csv').set_index('month')
prefs=json.loads((base/'provenance/inputs/preferences.json').read_text())
groups={'UK':['UK'],'FR+BE':['FR','BE'],'NL+DE':['NL','DE']}
h=pd.DataFrame({d:pd.read_csv(raw/f'preference_{d.lower()}.csv',index_col='date').value for d in prefs})
assert len(h)==12 and h.notna().all().all()
assert pd.DatetimeIndex(h.index).to_period('M').equals(pd.period_range('2023-01','2023-12',freq='M'))
assert all(h[ds].sum(axis=1).ge(0).all() for ds in groups.values())
p,excluded=historical_preferences(h.set_axis(pd.PeriodIndex(h.index,freq='M')))
assert p==prefs
hist={g:h[ds].sum().sum() for g,ds in groups.items()}
hist={g:v/sum(hist.values()) for g,v in hist.items()}
operational={g:sum(prefs[d] for d in ds) for g,ds in groups.items()}
operational={g:v/sum(operational.values()) for g,v in operational.items()}
rows=[]
for month in obs.index:
 for method in ['Physical156','EA legacy','2023 shares','Operational shares','Capacity143']:
  if method in ['2023 shares','Operational shares']:
   shares=hist if method=='2023 shares' else operational
  else:
   frame=pred.loc[pred.method.eq(method)&pred.target_month.eq(month)].set_index('destination')
   shares={g:frame.at[g,'prediction_bcm']/frame.at['Common total','prediction_bcm'] for g in groups}
  for g in groups:
   actual_share=obs.at[month,g]/obs.at[month,'Common total']
   rows.append(dict(month=month,method=method,group=g,share=shares[g],actual_share=actual_share,
     share_error_pp=100*(shares[g]-actual_share),
     conditional_error_bcm=shares[g]*obs.at[month,'Common total']-obs.at[month,g]))
errors=pd.DataFrame(rows)
summary=errors.groupby(['method','group']).agg(share_MAE_pp=('share_error_pp',lambda v:v.abs().mean()),
  conditional_MAE=('conditional_error_bcm',lambda v:v.abs().mean()),bias=('conditional_error_bcm','sum'))
print('BASELINES',hist,operational,'EXCLUDED',excluded)
print(summary.to_string())
monthly=errors.groupby(['month','method']).agg(L1_pp=('share_error_pp',lambda v:v.abs().sum()),
  shifted_bcm=('conditional_error_bcm',lambda v:v.abs().sum()/2)).unstack('method')
monthly['gap_bcm']=monthly[('shifted_bcm','Physical156')]-monthly[('shifted_bcm','EA legacy')]
print('RANK',monthly.sort_values('gap_bcm',ascending=False).to_string())
selected=monthly.sort_values('gap_bcm',ascending=False).index[:3].tolist()
print('SELECTED',selected)
caps=read(base/'provenance/inputs/capacities.csv').set_index('month')
solved=json.loads((base/'provenance/solver_results.json').read_text())
for month in selected:
 f=flows.loc[('Physical156',month)]; s=solved['Physical156'][month]; days=pd.Period(month,'M').days_in_month
 print('\nMONTH',month,'SOURCES',sources.loc[month].to_dict())
 print('DEST',f.to_dict(),'ACTUAL',obs.loc[month].to_dict())
 print('GROSS TARGET',{d:f.exports_bcm*prefs[d] for d in prefs})
 cut=caps.loc[month,['EUROPIPE_I','EUROPIPE_II','NORPIPE','FRANPIPE','ZEEPIPE_EXPORT']].sum()
 floor=f.exports_bcm-cut
 print('UK gross cut floor',floor,'UK boundary-adjusted floor',floor-account.at[month,'legacy_excluded_uk_direct_bcm'],
   'UKDIRECT comparable floor',sources.at[month,'UK_DIRECT']-account.at[month,'legacy_excluded_uk_direct_bcm'])
 print('FRBE target',f.exports_bcm*(prefs['FR']+prefs['BE']), 'LANGELED UK slack',caps.at[month,'LANGELED_SOUTH']-s['flows']['LANGELED_SOUTH'])
 print('BINDING',read(base/'details/binding_constraints.csv').loc[lambda z:z.scenario.eq('Physical156')&z.month.eq(month)&z.binding].asset.tolist())
out=R/'.scratch/runs/20261014-01_routing-error-attribution'
out.mkdir(parents=True,exist_ok=True)
errors.to_csv(out/'errors.csv',index=False)
monthly.to_csv(out/'monthly.csv')
(out/'selected.json').write_text(json.dumps(dict(months=selected,shares_2023=hist,operational_shares=operational)))
