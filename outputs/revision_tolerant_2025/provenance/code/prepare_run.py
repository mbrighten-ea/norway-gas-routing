"""Single-origin pilot: prepare/freeze and solve before any target actual I/O."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
import pandas as pd,numpy as np
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.config import load_config
from norway_gas_routing.seasonal_snohvit import seasonal_profile
from norway_gas_routing.forward_supply import allocate_forward
from norway_gas_routing.routing import historical_preferences,network_definition,monthly_available_capacity
from norway_gas_routing.operational import optimise,save_csv
raw=next((R/'data/raw/revision_tolerant_2025').iterdir())
records=json.loads((raw/'source_metadata.json').read_text());by={r['name']:r for r in records}
out=R/'outputs/revision_tolerant_2025'
if (out/'provenance/forecast_freeze.json').exists():raise ValueError('Forecast already frozen; no post-score parameter rerun')
(out/'provenance/inputs').mkdir(parents=True,exist_ok=True);(out/'details').mkdir(exist_ok=True)
origin='2024-12-31T23:59:59Z';months=pd.period_range('2025-01','2025-12',freq='M')
def points(name,monthly=True):
 rec=by[name];v=pd.read_csv(R/rec['raw_file'],index_col='date',parse_dates=True).value
 if monthly:v.index=pd.DatetimeIndex(v.index).to_period('M')
 if rec['role']=='pre_origin_revision_tolerant_history':
  historical_months=v.index if monthly else pd.DatetimeIndex(v.index).to_period('M')
  assert (historical_months<pd.Period('2024-12','M')).all()
 meta=rec.get('metadata',{})
 if len(v):
  assert meta.get('frequency')=='monthly' and meta.get('unit')=='bcm'
  if meta.get('lifecycle_stage')=='forecast':assert pd.Period(meta['forecast_start_date'],'M')>(v.index.max() if monthly else v.index.max().to_period('M')) or rec['role'].startswith('origin_archived')
 return v
model,registry=load_config(R/'config/model.yaml',R/'config/data_series.csv')
network=network_definition(model['routing'])
owners=pd.read_csv(R/'outputs/routing_runs/20261013T165918528411Z_87c4eb40/provenance/frozen_2024_owners.csv',keep_default_na=False)
owners=owners[['component_id','field','sid','node','role']].copy()
owners.loc[owners.component_id.isin(['CI','EU']),'node']='KARSTO_FEED'
owners.loc[owners.component_id.eq('EB'),'node']='UK_DIRECT'
assert owners.component_id.is_unique and owners.sid.is_unique
hist={r.component_id:points('history_'+r.component_id) for r in owners.itertuples()}
historical=pd.DataFrame(hist,index=pd.period_range('2023-01','2023-12',freq='M'))
historical.to_csv(out/'provenance/inputs/historical_owner_observations.csv',index_label='month')
owners['observed_months']=[len(hist[c]) for c in owners.component_id]
owners['observed_subtotal_bcm']=[float(hist[c].sum()) if len(hist[c]) else np.nan for c in owners.component_id]
owners['missing_months']=[';'.join(by['history_'+c]['missing_months']) for c in owners.component_id]
owners['mapping_assumption']='Existing physical membership applied retrospectively; Core Balder/Urd/Rev decisions; origin availability not claimed'
nat_hist=points('history_national');sn_hist=points('history_GD')
explicit_owners=owners.loc[owners.role.eq('explicit')]
assert len(explicit_owners)==16 and 'AQ' in explicit_owners.component_id.values
explicit_hist=historical[explicit_owners.component_id].sum(axis=1)
residual_hist=nat_hist-sn_hist-explicit_hist
residual_owners=owners.loc[owners.role.eq('residual')].copy()
known_hist=historical[residual_owners.component_id].sum(axis=1,min_count=1)
unresolved=residual_hist-known_hist
if unresolved.lt(-1e-9).any():raise ValueError('Known production exceeds compatible national boundary; no balancing adjustment')
if unresolved.abs().max()<1e-9:
 # Numerical tolerance only: no source observation is filled or modified.
 unresolved_accounted=pd.Series(0.,index=residual_hist.index)
else:unresolved_accounted=unresolved
ledger=pd.DataFrame(dict(national_EA_bcm=nat_hist,snohvit_bcm=sn_hist,explicit16_bcm=explicit_hist,
 residual_bcm=residual_hist,observed_residual_subtotal_bcm=known_hist,
 unresolved_bcm=unresolved_accounted,numerical_balance_bcm=unresolved-unresolved_accounted))
ledger.to_csv(out/'details/ledger_2023.csv',index_label='month')
# Signed observations aggregate by physical node before becoming nonnegative
# injection weights. Empty owners retain NaN subtotals, not assumed zero values.
grouped=residual_owners.groupby('node').observed_subtotal_bcm.sum(min_count=1)
grouped=grouped.dropna();grouped['UNMAPPED']=grouped.get('UNMAPPED',0.)+unresolved_accounted.sum()
denominator=float(residual_hist.sum())
assert abs(grouped.sum()-denominator)<1e-9
assert grouped.ge(0).all() and denominator>0
weights=grouped.rename('annual_bcm').rename_axis('node').reset_index()
weights['denominator_bcm']=denominator;weights['weight']=weights.annual_bcm/denominator
weights['component_id']='NODE_'+weights.node
weights['memberships']=[';'.join(residual_owners.loc[residual_owners.node.eq(n),'component_id']) for n in weights.node]
assert abs(weights.weight.sum()-1)<1e-9
weights.to_csv(out/'provenance/inputs/weights_2023.csv',index=False)
owners.to_csv(out/'provenance/inputs/owners_2023.csv',index=False)
# Show complete ownership checks for Oseberg aggregate; children never added.
oseberg_gap=points('history_Q')-(points('native_oseberg')+points('native_oseberg_sor')+points('native_oseberg_ost'))
assert oseberg_gap.abs().max()<1e-9
asgard_gap=points('history_AF')-points('native_asgard')
assert asgard_gap.abs().max()<1e-9
# No Halten Øst observations occur in the calibration year. Its Core route is
# recorded but no volume is invented or added to the Åsgard parent.
assert points('history_GK').empty
sn_points=points('seasonal_snohvit',False)
observations=pd.DataFrame(dict(date=sn_points.index,monthly_bcm=sn_points.to_numpy(),
 available_at=by['seasonal_snohvit']['retrieved_at']))
sn,selected,rates,years,gaps=seasonal_profile(observations,months,origin,allow_partial=True,revision_tolerant=True)
selected.to_csv(out/'provenance/inputs/seasonal_observations.csv',index=False)
profile=pd.DataFrame(dict(calendar_month=list(range(1,13)),rate_mcmd=rates.to_numpy(),
 observations=[rates.attrs['observation_counts'][m] for m in range(1,13)],
 imputed=[m in rates.attrs['imputed_calendar_months'] for m in range(1,13)]))
profile.to_csv(out/'provenance/inputs/seasonal_profile.csv',index=False)
preferences,excluded=historical_preferences(pd.DataFrame({country:points('preference_'+country.lower()) for country in ['UK','FR','BE','NL','DE','DK','PL']}))
contract=json.loads((R/'evidence/inputs/routing_sources_b1/verified_sources.json').read_text())
membership={key:owners.loc[owners.component_id.eq(component),'node'].iloc[0] for key,component in contract['component_columns'].items()}
fields=pd.DataFrame({key:points('forecast_'+key) for key in membership},index=months)
national=points('forecast_norway_prod')
supply,reconciliation=allocate_forward(fields,national,sn,weights,membership,
 [n for n,e in network['nodes'].items() if e['kind']=='source'],'export_eligible')
excluded_ids=['EB','FD','FF','CK','FS','CG']
excluded_subtotal=residual_owners.loc[residual_owners.component_id.isin(excluded_ids),'observed_subtotal_bcm'].sum()
assert excluded_subtotal>=0
reconciliation['legacy_excluded_uk_direct_bcm']=fields.martin_linge_prod+reconciliation.residual_bcm*excluded_subtotal/denominator
legacy=pd.DataFrame({group:points('legacy_'+key) for group,key in {'UK':'uk_flow_qa','FR+BE':'fr_be_flow_qa','NL+DE':'nl_de_flow_qa','Gassco total':'norway_exports_qa'}.items()},index=months)
for name,frame in [('supply',supply),('reconciliation',reconciliation),('fields',fields),('legacy_forecasts',legacy)]:
 frame.to_csv(out/'provenance/inputs'/f'{name}.csv',index_label='month')
capacities={};capacity_detail=[]
for asset,entry in model['routing']['assets'].items():
 rate=156 if asset=='KOLLSNES_EXPORT' else entry.get('mcm_d',entry.get('annual_bcm',0)*1000/365)
 monthly,daily=monthly_available_capacity(pd.Series([rate],index=pd.to_datetime(['2025-01-01'])),months)
 capacities[asset]=monthly.available_capacity_bcm
 capacity_detail.append(monthly.assign(asset=asset).reset_index())
caps=pd.DataFrame(capacities,index=months);caps.to_csv(out/'provenance/inputs/capacities.csv',index_label='month')
pd.concat(capacity_detail,ignore_index=True).to_csv(out/'details/capacity_assumptions.csv',index=False)
(out/'provenance/inputs/preferences.json').write_text(json.dumps(preferences,indent=2)+'\n',encoding='utf-8')
for name in ['model.yaml','data_series.csv','evaluation.yaml']:
 (out/'provenance'/name).write_bytes((R/'config'/name).read_bytes())
freeze=dict(origin=origin,revision_policy='Currently revised histories allowed only for pre-origin production periods',
 weights_window='2023-01 through 2023-12 as requested; newer-window Trym has 11 missing months and is not activated',
 national_historical_bcm=float(nat_hist.sum()),residual_denominator_bcm=denominator,monthly_ledger_max_bcm=float(ledger.numerical_balance_bcm.abs().max()),
 source_weights_sum=float(weights.weight.sum()),unmapped_historical_bcm=float(grouped.UNMAPPED),
 missing_owner_observations=owners.loc[owners.observed_months.lt(12),['component_id','field','observed_months','missing_months']].to_dict('records'),
 missing_owner_policy='Observed subtotals only; blank observations retained. National/known cohort closes every month; no missing-to-zero or arbitrary routing.',
 core_routes={'Halten Øst':'KARSTO_FEED','Rev':'UK_DIRECT','Balder':'KARSTO_FEED','Urd':'KARSTO_FEED'},
 oseberg_max_gap_bcm=float(oseberg_gap.abs().max()),asgard_max_gap_bcm=float(asgard_gap.abs().max()),
 snohvit_method='seasonal_two_year',selected_years=years,imputed_calendar_months=rates.attrs['imputed_calendar_months'],
 seasonal_total_bcm=float(sn.sum()),preferences=preferences,excluded_preference_months=excluded,
 capacity_reference_mcmd=156,capacity_stress_mcmd=143,capacity_status='Declared planning assumptions; not verified December-2024 operating ratings; zero assumed planned-maintenance deductions',
 heidrun_treatment='No additional domestic deduction, as operational reference',
 unknown_future_availability='Other existing engineering envelopes held constant; no actual outage information',
 actual2025_inputs_used=False,protected_actuals_queried=False,created_at=datetime.now(timezone.utc).isoformat(),
 input_files_sha256={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'provenance/inputs').glob('*')})
(out/'provenance/input_freeze.json').write_text(json.dumps(freeze,default=str,indent=2)+'\n',encoding='utf-8')
all_results={};check_frames=[];flows=[];bindings=[]
for scenario,rate in [('Physical156',156),('Capacity143',143)]:
 scenario_caps=caps.copy();scenario_caps.KOLLSNES_EXPORT=months.days_in_month*rate/1000
 solver,solved,checks=optimise(dict(months=months,supply=supply,capacities=scenario_caps,preferences=preferences),network,'HiGHS')
 all_results[scenario]=solved;check_frames.append(checks.assign(scenario=scenario))
 for month in months:
  result=solved[str(month)];assert sum(v for k,v in result['flows'].items() if k.startswith('UK_DIRECT') and 'DISPOS' in k)<1e-8
  row=dict(month=str(month),scenario=scenario,**result['destinations'],exports_bcm=sum(result['destinations'].values()),disposal_bcm=result['unrouted'])
  row['UK_comparable_bcm']=row['UK']-reconciliation.at[month,'legacy_excluded_uk_direct_bcm']
  row['FR+BE']=row['FR']+row['BE'];row['NL+DE']=row['NL']+row['DE']
  row['Common total']=row['UK_comparable_bcm']+row['FR+BE']+row['NL+DE'];flows.append(row)
  for asset in scenario_caps:
   used=sum(result['flows'][a['id']] for a in network['arcs'] if a['asset']==asset)
   cap=scenario_caps.at[month,asset];bindings.append(dict(month=str(month),scenario=scenario,asset=asset,capacity_bcm=cap,used_bcm=used,slack_bcm=cap-used,binding=cap-used<1e-7))
pd.DataFrame(flows).to_csv(out/'details/frozen_forecasts.csv',index=False)
pd.concat(check_frames,ignore_index=True).to_csv(out/'details/solver_checks.csv',index=False)
pd.DataFrame(bindings).to_csv(out/'details/binding_constraints.csv',index=False)
(out/'provenance/solver_results.json').write_text(json.dumps(all_results,indent=2)+'\n',encoding='utf-8')
(out/'provenance/forecast_freeze.json').write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(),
 forecast_file_sha256=hashlib.sha256((out/'details/frozen_forecasts.csv').read_bytes()).hexdigest(),
 solver=solver,monthly_solves=24,actual2025_queried=False),indent=2)+'\n',encoding='utf-8')
print('FROZEN',24,'solves',denominator,'residual denominator; Snøhvit',sn.sum())
print(pd.DataFrame(flows).groupby('scenario')[['exports_bcm','disposal_bcm','Common total']].sum().to_string())
