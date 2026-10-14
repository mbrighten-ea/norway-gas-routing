"""Freeze pre-origin histories/archived forecasts before any 2025 actual query."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
import pandas as pd
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.data_functions import connect_shooju,get_series,get_metadata
from norway_gas_routing.project_data import load_registry,get_registered_series
from norway_gas_routing.evaluation import request_bounds,check_dates
reg=load_registry();c=connect_shooju();rows=[]
raw=R/'data/raw/revision_tolerant_2025'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
raw.mkdir(parents=True,exist_ok=False)
def get(name,sid,start,end,archive=False):
 start,end=request_bounds(start,end)
 if not archive and pd.Period(end,'M')>=pd.Period('2024-12','M'):
  raise ValueError('Input histories must be completed pre-origin production periods; no target actuals')
 q='sid="'+sid+'"@asof:2024-12-31T23:59:59' if archive else sid
 r=dict(name=name,sid=sid,query=q,start=start,end=end,role='origin_archived_forecast_or_preferences' if archive else 'pre_origin_revision_tolerant_history',retrieved_at=datetime.now(timezone.utc).isoformat())
 try:
  try:
   v=get_series(q,start,end,client=c)
  except KeyError:
   f=c.sj.get_df(query=q,fields=['series_id'],max_points=-1,df=start,dt=end)
   if not f.empty:raise ValueError('Unrecognised response, not confirmed empty')
   v=pd.Series(dtype=float,index=pd.DatetimeIndex([]))
  try:r['metadata']=get_metadata(q,client=c)
  except KeyError:r['metadata_status']='Unavailable for empty source'
  ix=pd.DatetimeIndex(pd.to_datetime(v.index,utc=True)).tz_localize(None);check_dates(ix,'read')
  if ix.has_duplicates or ((ix<pd.Timestamp(start))|(ix>pd.Timestamp(end))).any():raise ValueError('Source bounds/uniqueness failure')
  v=pd.Series(v.to_numpy(),index=ix).sort_index()
  p=raw/(name+'.csv');v.rename('value').rename_axis('date').to_csv(p,float_format='%.17g')
  expected=pd.date_range(start,end,freq='MS')
  r.update(raw_file=p.relative_to(R).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),points=len(v),
   missing_months=expected.difference(ix).strftime('%Y-%m').tolist(),observed_subtotal_bcm=float(v.sum()) if len(v) else None,
   negative_months=v.loc[v.lt(0)].index.strftime('%Y-%m').tolist(),status='COMPLETE' if ix.equals(expected) and v.notna().all() else 'PARTIAL_OR_EMPTY; no filling')
 except Exception as e:
  r.update(status='BLOCKED',error_type=type(e).__name__)
  if isinstance(e,ValueError):r['validation_error']=str(e)
 rows.append(r);(raw/'source_metadata.json').write_text(json.dumps(rows,default=str,indent=2)+'\n',encoding='utf-8')
 print(name,r['status'],r.get('points'),flush=True)
owners=pd.read_csv(R/'outputs/routing_runs/20261013T165918528411Z_87c4eb40/provenance/frozen_2024_owners.csv',keep_default_na=False)
for row in owners.itertuples():get('history_'+row.component_id,row.sid,'2023-01-01','2023-12-31')
get('history_national',reg.at['norway_prod','sid'],'2023-01-01','2023-12-31')
get('seasonal_snohvit',r'NPD\monthly_by_field\marketed_production\snohvit\gas-saleable','2022-01-01','2023-12-31')
population=pd.read_csv(R/'evidence/inputs/reconciled_supply_f22/production_population.csv',keep_default_na=False)
for cid in ['GK','GR','GT']:
 row=population.loc[population.component_id.eq(cid)].iloc[0];get('history_'+cid,row.sid,'2023-01-01','2023-12-31')
for field in ['oseberg','oseberg_sor','oseberg_ost','asgard']:
 get('native_'+field,'NPD\\monthly_by_field\\marketed_production\\'+field+r'\gas-saleable','2023-01-01','2023-12-31')
# Bounded newer-window gap checks only; no 2025 histories or weight sensitivity.
for cid in ['EB','EQ']:
 row=owners.loc[owners.component_id.eq(cid)].iloc[0];get('newer_window_'+cid,row.sid,'2023-12-01','2024-11-30')
contract=json.loads((R/'evidence/inputs/routing_sources_b1/verified_sources.json').read_text())
for key in ['norway_prod']+list(contract['component_columns']):get('forecast_'+key,reg.at[key,'sid'],'2025-01-01','2025-12-31',True)
for key in ['uk_flow_qa','fr_be_flow_qa','nl_de_flow_qa','norway_exports_qa']:get('legacy_'+key,reg.at[key,'sid'],'2025-01-01','2025-12-31',True)
for country in ['uk','fr','be','nl','de','dk','pl']:
 key=country+'_flow_qa';get('preference_'+country,reg.at[key,'sid'],'2023-01-01','2023-12-31',True)
(raw/'input_capture.json').write_text(json.dumps(dict(origin='2024-12-31T23:59:59Z',target='2025-01 through 2025-12',
 revision_tolerant=True,actual2025_queried=False,protected_actuals_queried=False,kollsnes_planning_mcmd=156,
 capacity_sensitivity_predeclared_mcmd=143,maintenance_forecast_deduction=0,core_routes={'GK':'KARSTO_FEED','EB':'UK_DIRECT','CI':'KARSTO_FEED','EU':'KARSTO_FEED'},
 weights_requested_window='2023-01 through 2023-12; newer gap checks retained',
 mapping_policy='Retroactive existing memberships plus Core approved routes, subject to unique ownership; uncertain production stays unmapped'),indent=2)+'\n',encoding='utf-8')
print('RAW',raw.relative_to(R).as_posix(),flush=True)
