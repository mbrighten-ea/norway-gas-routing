"""One December-2024 package attempt; no model change, solving or scoring."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib
import pandas as pd

ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.data_functions import connect_shooju,get_metadata
from norway_gas_routing.project_data import load_registry
from norway_gas_routing.evaluation import check_dates,request_bounds

ORIGIN='2024-12-31T23:59:59Z'
raw=ROOT/'data/raw/minimum_backtest_f29'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
raw.mkdir(parents=True,exist_ok=False)
registry=load_registry();client=connect_shooju();records=[]
owners=pd.read_csv(ROOT/'outputs/routing_runs/20261013T165918528411Z_87c4eb40/provenance/frozen_2024_owners.csv',keep_default_na=False)

def capture(name,sid,start,end,purpose):
    start,end=request_bounds(start,end)
    q='sid="'+sid+'"@asof:2024-12-31T23:59:59'
    r=dict(name=name,sid=sid,query=q,information_origin=ORIGIN,start=start,end=end,purpose=purpose,
        retrieved_at=datetime.now(timezone.utc).isoformat(),information_date_basis='Archived service state, not proof of original public issuance')
    try:
        f=client.sj.get_df(query=q,fields=None,max_points=-1,df=start,dt=end)
        r['response_columns']=f.columns.tolist()
        if f.empty:
            v=pd.Series(dtype=float,index=pd.DatetimeIndex([]));r['status']='EMPTY_ARCHIVE; no filling'
        else:
            if not {'dt','val'}.issubset(f.columns):raise ValueError('Unexpected archived point schema')
            dates=pd.DatetimeIndex(pd.to_datetime(f.dt,utc=True)).tz_localize(None)
            check_dates(dates,'read')
            if dates.has_duplicates or ((dates<pd.Timestamp(start))|(dates>pd.Timestamp(end))).any():
                raise ValueError('Unexpected/duplicate source dates')
            v=pd.Series(pd.to_numeric(f.val,errors='raise').to_numpy(),index=dates).sort_index()
            meta=get_metadata(q,client=client);r['metadata']=meta
            r['status']='ARCHIVE_POINTS_PRESENT'
            first=meta.get('forecast_start_date')
            r['historical_months']=v.index[v.index<pd.Timestamp(first)].strftime('%Y-%m').tolist() if first else v.index.strftime('%Y-%m').tolist() if meta.get('lifecycle_stage') in {'actual','historical'} else []
            r['forecast_months']=v.index[v.index>=pd.Timestamp(first)].strftime('%Y-%m').tolist() if first else []
            job=meta.get('api_obj',{}).get('snap_shooju_job_id')
            if job:
                try:
                    jobs=client.get_active_jobs('id='+str(job),max_pages=1)
                    info=jobs.get(str(job),jobs.get(job,{}))
                    r['import_job']={k:info.get(k) for k in ['created_at','description']}
                except Exception as e:r['import_metadata_error_type']=type(e).__name__
        path=raw/(name+'.csv');v.rename('value').rename_axis('date').to_csv(path,float_format='%.17g')
        expected=pd.date_range(start,end,freq='MS')
        r.update(raw_file=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),points=len(v),
            missing_months=expected.difference(v.index).strftime('%Y-%m').tolist(),
            observed_subtotal=float(v.sum()) if len(v) else None,
            signed_negative_months=v.loc[v.lt(0)].index.strftime('%Y-%m').tolist())
    except Exception as e:
        r.update(status='BLOCKED',error_type=type(e).__name__)
        if isinstance(e,ValueError):r['validation_error']=str(e)
    records.append(r)
    (raw/'source_metadata.json').write_text(json.dumps(records,default=str,indent=2)+'\n',encoding='utf-8')
    print(name,r['status'],r.get('points'),flush=True)

# Reuse identities only, never 2024 quantities/weights. This is the entire known
# owner certificate plus separate LNG; no further SID discovery or zero cohorts
# inferred from their 2024 values.
for row in owners.itertuples():
    capture('ledger2023_'+row.component_id,row.sid,'2023-01-01','2023-12-31','2023 owner archive; current mapping identity only, not historical certification')
capture('ledger2023_national',registry.at['norway_prod','sid'],'2023-01-01','2023-12-31','Matching EA national historical boundary')
for key in ['snohvit_net_prod','snohvit_net_prod_legacy']:
    capture('seasonal_'+key,registry.at[key,'sid'],'2022-01-01','2023-12-31','Seek complete historical net-saleable years; forecast cells are ineligible')
capture('seasonal_native',r'NPD\monthly_by_field\marketed_production\snohvit\gas-saleable','2022-01-01','2023-12-31','Seek origin-available native net-saleable history')
capture('legacy_exclusion_lineage',registry.at['norway_prod_ex_snohvit','sid'],'2022-01-01','2023-12-31','Existing exclusion identity reference only, not an alternative forecast method')
for key in ['norway_prod']+registry.loc[registry.index.isin(json.loads((ROOT/'evidence/inputs/routing_sources_b1/verified_sources.json').read_text())['component_columns'])].index.tolist():
    capture('forecast2025_'+key,registry.at[key,'sid'],'2025-01-01','2025-12-31','Original origin-matched EA production forecast')
for key in ['uk_flow_qa','fr_be_flow_qa','nl_de_flow_qa','norway_exports_qa']:
    capture('legacy2025_'+key,registry.at[key,'sid'],'2025-01-01','2025-12-31','Original EA forecast; no realised deliveries retrieved')
for country in ['uk','fr','be','nl','de','dk','pl']:
    key=country+'_flow_qa'
    capture('preference2023_'+country,registry.at[key,'sid'],'2023-01-01','2023-12-31','Origin-available destination preference history, not 2025 evaluation')

manifest=dict(status='INPUT_AUDIT_ONLY',origin=ORIGIN,target_start='2025-01',target_end='2025-12',
    base_revision='4465c8710f42fc732f9e655912f4fd33760318ab',
    owner_identity_source='F2.4 certificate identifies existing SIDs only; no 2024 weights/quantities used',
    source_records=len(records),protected_actuals_queried=False,actual2025_deliveries_queried=False,
    optimiser_runs=0,forecast_scores_computed=False,sid_discovery_performed=False)
(raw/'attempt.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('RAW',raw.relative_to(ROOT).as_posix(),flush=True)
