"""Bounded check of existing price candidates at one origin; no realised prices."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
import pandas as pd
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.data_functions import connect_shooju,get_metadata,get_series
from norway_gas_routing.project_data import load_registry
from norway_gas_routing.evaluation import request_bounds,check_dates
origin='2024-12-31T23:59:59Z';start,end=request_bounds('2025-01-01','2025-12-31')
reg=load_registry();client=connect_shooju();records=[]
raw=R/'data/raw/physical_commercial_gate_f213'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
raw.mkdir(parents=True,exist_ok=False)
# Four existing EA forecasts; existing exchange curves only as bounded fallback evidence.
keys=['nbp_forecast_eur','peg_forecast','ztp_forecast','ttf_forecast',
      'nbp_eex_curve','peg_eex_curve','ztp_eex_curve']
for key in keys:
 sid=reg.at[key,'sid'];q=f'sid="{sid}"@asof:2024-12-31T23:59:59'
 record=dict(key=key,sid=sid,query=q,asof=origin,start=start,end=end,
  role='origin_archived_price_candidate_only',retrieved_at=datetime.now(timezone.utc).isoformat())
 try:
  try:record['metadata']=get_metadata(q,client=client)
  except KeyError:record['metadata_status']='No archived metadata'
  try:values=get_series(q,start,end,client=client)
  except KeyError:
   frame=client.sj.get_df(query=q,fields=['series_id'],max_points=-1,df=start,dt=end)
   if not frame.empty:raise ValueError('Unexpected response rather than confirmed empty')
   values=pd.Series(dtype=float,index=pd.DatetimeIndex([]))
  dates=pd.DatetimeIndex(pd.to_datetime(values.index,utc=True)).tz_localize(None)
  check_dates(dates,'read')
  assert not dates.has_duplicates and ((dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end))).all()
  p=raw/(key+'.csv');pd.Series(values.to_numpy(),index=dates).rename('value').rename_axis('date').to_csv(p,float_format='%.17g')
  expected=pd.date_range(start,end,freq='MS')
  record.update(points=len(values),raw_file=p.relative_to(R).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    complete_monthly_grid=dates.equals(expected) and values.notna().all(),
    missing_months=expected.difference(dates).strftime('%Y-%m').tolist(),
    status='ARCHIVED_POINTS_PRESENT_NOT_YET_APPROVED' if len(values) else 'EMPTY_AT_ORIGIN')
 except Exception as exc:record.update(status='BLOCKED',error_type=type(exc).__name__)
 records.append(record)
 (raw/'source_metadata.json').write_text(json.dumps(records,default=str,indent=2)+'\n',encoding='utf-8')
 print(key,record['status'],record.get('points'),flush=True)
print('CAPTURE',raw.relative_to(R).as_posix())
