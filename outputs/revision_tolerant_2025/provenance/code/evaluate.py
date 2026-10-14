"""Evaluation-only actual I/O after immutable forecast/input freeze."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
import pandas as pd,numpy as np
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.data_functions import connect_shooju,get_series,get_metadata
from norway_gas_routing.project_data import load_registry
from norway_gas_routing.evaluation import check_dates
from norway_gas_routing.benchmark import metric_table
out=R/'outputs/revision_tolerant_2025';freeze=json.loads((out/'provenance/input_freeze.json').read_text())
ff=json.loads((out/'provenance/forecast_freeze.json').read_text())
assert hashlib.sha256((out/'details/frozen_forecasts.csv').read_bytes()).hexdigest()==ff['forecast_file_sha256']
for file,sha in freeze['input_files_sha256'].items():assert hashlib.sha256((out/file).read_bytes()).hexdigest()==sha
raw=next((R/'data/raw/revision_tolerant_2025').iterdir());evaluation=raw/'evaluation_only';evaluation.mkdir(exist_ok=False)
client=connect_shooju();reg=load_registry();records=[]
months=pd.period_range('2025-01','2025-12',freq='M')
def actual(key,sid=None):
 sid=sid or reg.at[key,'sid'];meta=get_metadata(sid,client=client)
 rec=dict(key=key,sid=sid,metadata=meta,role='evaluation_only_never_input',retrieved_at=datetime.now(timezone.utc).isoformat(),
 start='2025-01-01',end='2025-12-31',input_freeze_created_at=freeze['created_at'],forecast_freeze_created_at=ff['created_at'])
 records.append(rec)
 assert pd.Timestamp(rec['retrieved_at'])>pd.Timestamp(ff['created_at'])
 if meta.get('unit')!='bcm' or meta.get('frequency')!='monthly':raise ValueError('Incompatible scoring units')
 if meta.get('lifecycle_stage')=='forecast' and pd.Period(meta['forecast_start_date'],'M')<=months.max():
  rec['status']='REJECTED_FORECAST_SEGMENT; actuals not retrieved';return None
 v=get_series(sid,'2025-01-01','2025-12-31',client=client)
 ix=pd.DatetimeIndex(v.index)
 if ix.tz is not None:ix=ix.tz_convert('UTC').tz_localize(None)
 check_dates(ix,'score');assert ix.to_period('M').equals(months) and v.notna().all()
 p=evaluation/(key+'.csv');v.rename('value').rename_axis('date').to_csv(p,float_format='%.17g')
 rec.update(raw_file=p.relative_to(R).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status='VERIFIED_2025_HISTORICAL_SEGMENT',points=len(v))
 return pd.Series(v.to_numpy(),index=months)
observed=pd.DataFrame({g:actual(k) for g,k in {'UK':'uk_flow_qa','FR+BE':'fr_be_flow_qa','NL+DE':'nl_de_flow_qa'}.items()},index=months)
observed['Common total']=observed.sum(axis=1,min_count=3)
observed_national=actual('norway_prod')
observed_lng=actual('snohvit_native',r'NPD\monthly_by_field\marketed_production\snohvit\gas-saleable')
total=actual('norway_exports_qa')
(evaluation/'source_metadata.json').write_text(json.dumps(records,default=str,indent=2)+'\n',encoding='utf-8')
observed.to_csv(out/'details/observations.csv',index_label='month')
flows=pd.read_csv(out/'details/frozen_forecasts.csv');legacy=pd.read_csv(out/'provenance/inputs/legacy_forecasts.csv',index_col='month')
legacy.index=pd.PeriodIndex(legacy.index,freq='M');legacy['Common total']=legacy[['UK','FR+BE','NL+DE']].sum(axis=1)
rows=[];conditional=[]
for method in ['Physical156','Capacity143','EA legacy']:
 for month in months:
  if method=='EA legacy':p=legacy.loc[month]
  else:
   f=flows.loc[flows.scenario.eq(method)&flows.month.eq(str(month))].iloc[0]
   p=pd.Series({'UK':f.UK_comparable_bcm,'FR+BE':f['FR+BE'],'NL+DE':f['NL+DE'],'Common total':f['Common total']})
  for g in ['UK','FR+BE','NL+DE','Common total']:
   pred=float(p[g]);obs=float(observed.at[month,g]);err=pred-obs
   rows.append(dict(target_month=str(month),origin=freeze['origin'],level='compatible_groups',destination=g,method=method,
     prediction_bcm=pred,actual_bcm=obs,error_bcm=err,share_error_pp=np.nan,
     analysis_type='Revision-tolerant historical reconstruction; no parameter changes after scoring'))
   if g!='Common total':
    share=pred/float(p['Common total']);actual_total=float(observed.at[month,'Common total'])
    conditional.append(dict(month=str(month),group=g,method=method,forecast_share=share,
     actual_common_total_bcm=actual_total,conditional_prediction_bcm=share*actual_total,
     conditional_routing_error_bcm=share*actual_total-obs,
     forecast_total_error_component_bcm=share*(float(p['Common total'])-actual_total),
     full_forecast_error_bcm=err,conditional_status='Actual total used only in scoring decomposition; never an issued forecast/model input'))
comparison=pd.DataFrame(rows);metrics=metric_table(comparison)
comparison.to_csv(out/'results.csv',index=False);metrics.to_csv(out/'details/metrics.csv',index=False)
pd.DataFrame(conditional).to_csv(out/'details/conditional_routing.csv',index=False)
ledger=pd.read_csv(out/'provenance/inputs/reconciliation.csv',index_col='month');ledger.index=pd.PeriodIndex(ledger.index,freq='M')
production=pd.DataFrame(dict(national_forecast_bcm=ledger.national_production_bcm,national_actual_bcm=observed_national,
 snohvit_seasonal_forecast_bcm=ledger.snohvit_bcm,snohvit_actual_bcm=observed_lng,
 pipeline_forecast_bcm=ledger.pipeline_supply_bcm,pipeline_actual_bcm=observed_national-observed_lng))
for name in ['national','snohvit','pipeline']:
 forecast='snohvit_seasonal_forecast_bcm' if name=='snohvit' else name+'_forecast_bcm'
 production[name+'_error_bcm']=production[forecast]-production[name+'_actual_bcm']
production.to_csv(out/'details/production_evaluation.csv',index_label='month')
assert np.allclose(pd.DataFrame(conditional).full_forecast_error_bcm,
 pd.DataFrame(conditional).conditional_routing_error_bcm+pd.DataFrame(conditional).forecast_total_error_component_bcm,atol=1e-10)
assert hashlib.sha256((out/'details/frozen_forecasts.csv').read_bytes()).hexdigest()==ff['forecast_file_sha256']
(out/'provenance/evaluation.json').write_text(json.dumps(dict(status='COMPLETED_REVISION_TOLERANT_DIAGNOSTIC',
 compatible_groups=['UK adjusted for evidenced non-Gassco packets','FR+BE','NL+DE','Common total of those three groups'],
 full_gassco_total_scored=False,total_boundary='Common subset only; DK/PL and wider total remain unranked',
 actual_inputs_used=False,forecast_file_sha256=ff['forecast_file_sha256'],protected_actuals_queried=False,
 observed_national_total_bcm=float(observed_national.sum()),forecast_national_total_bcm=float(ledger.national_production_bcm.sum()),
 national_bias_total_bcm=float(production.national_error_bcm.sum()),
 pipeline_bias_total_bcm=float(production.pipeline_error_bcm.sum()),
 realised_data_policy='2025 actuals were retrieved after all inputs and forecasts were frozen; evaluation only'),indent=2)+'\n',encoding='utf-8')
print(metrics[['method','destination','n','mae_bcm_month','wape_pct','bias_total_bcm']].to_string(index=False))
print('PRODUCTION',production[['national_error_bcm','snohvit_error_bcm','pipeline_error_bcm']].sum().to_dict())
