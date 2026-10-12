"""Bounded forecast sourcing assessment, not a forecast/replay/scoring engine."""
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.config import load_config
from norway_gas_routing.data_functions import connect_shooju, find_series
from norway_gas_routing.project_data import get_registered_series, get_prospective_forecast
from norway_gas_routing.reporting.sids import monthly_reference
from norway_gas_routing.operational import write_json, digest, git_identity
from norway_gas_routing.routing_sources import source_requirements, field_identity


def assess(supplement=False):
    model,registry=load_config(ROOT/'config/model.yaml',ROOT/'config/data_series.csv')
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_'+uuid4().hex[:8]
    output=ROOT/'outputs/forecast_viability'/run_id
    raw=ROOT/'data/raw/forecast_viability_f1'/run_id
    for path in [output/'details',output/'provenance',raw]: path.mkdir(parents=True,exist_ok=False)
    client=connect_shooju()
    current_start=max(pd.Timestamp.now().to_period('M'),pd.Period('2026-10','M'))
    current_months=pd.period_range(current_start,'2030-12',freq='M')
    records,rows,jobs=[],[],{}
    def inspect(key,months,origin=None,role='production',prospective=False):
        row=dict(key=key,sid=registry.at[key,'sid'],role=role,origin=origin or '',
            delivery_start=str(months.min()),delivery_end=str(months.max()),expected_months=len(months),
            status='UNAVAILABLE',finite_months=0,issuance_date='',issuance_status='Not identified; import timestamp is not issuance',
            raw_unit='',frequency='',forecast_start='',snapshot_job_id='',import_created_at='')
        try:
            start,end=str(months.min().start_time.date()),str(months.max().end_time.date())
            result=(get_prospective_forecast(key,start,end,registry=registry,client=client) if prospective else
                    get_registered_series(key,start,end,registry=registry,client=client,
                        asof=origin+'T23:59:59Z' if origin else None))
            values,meta=result['values'],result['metadata']
            filename=f'{len(records):04d}_{key}.csv'
            values.rename('value').rename_axis('date').to_csv(raw/filename,float_format='%.17g')
            job=meta.get('api_obj',{}).get('snap_shooju_job_id')
            if job and job not in jobs:
                try:
                    found=client.get_active_jobs('id='+str(job),max_pages=1)
                    info=found.get(str(job),found.get(job,{}))
                    jobs[job]={k:info.get(k) for k in ['description','created_at']}
                except Exception as exc: jobs[job]={'error_type':type(exc).__name__}
            created=jobs.get(job,{}).get('created_at')
            if created: row['import_created_at']=pd.to_datetime(created,unit='ms',utc=True).isoformat()
            record=dict(key=key,sid=row['sid'],query=result.get('query'),asof=result.get('asof'),
                retrieved_at=datetime.now(timezone.utc).isoformat(),metadata=meta,
                raw_file=(raw/filename).relative_to(ROOT).as_posix(),sha256=digest(raw/filename))
            records.append(record)
            row.update(raw_unit=meta.get('unit'),frequency=meta.get('frequency'),
                forecast_start=meta.get('forecast_start_date'),snapshot_job_id=job or '',raw_file=record['raw_file'],sha256=record['sha256'])
            dates=pd.DatetimeIndex(values.index)
            if dates.tz is not None: dates=dates.tz_localize(None)
            finite=pd.to_numeric(values,errors='coerce').map(lambda v: pd.notna(v) and abs(v)!=float('inf'))
            present=dates[finite.to_numpy()].to_period('M')
            row['finite_months']=len(set(present).intersection(months))
            row['missing_months']=';'.join(str(m) for m in months if m not in set(present))
            if role=='forward_price':
                row['status']='ARCHIVED_CURVE_CANDIDATE; quote/contract vintage unverified' if len(values) else 'UNAVAILABLE'
            elif role=='maintenance':
                row['status']='RETURNED_PLAN_CANDIDATE; scope/available-at unverified' if len(values) else 'UNAVAILABLE'
            else:
                if role in {'terminal_flow','training_flows'}:
                    monthly_reference(result,months.astype(str).tolist(),origin if role=='terminal_flow' else None)
                elif meta.get('frequency')!='monthly' or meta.get('unit')!='bcm':
                    raise ValueError('Production monthly bcm contract incompatible')
                if role=='production':
                    boundary=meta.get('forecast_start_date')
                    if meta.get('lifecycle_stage')!='forecast' or not boundary or pd.Period(boundary,'M')>months.min():
                        raise ValueError('Production forecast segment unverified')
                exact=(dates.equals(dates.to_period('M').to_timestamp()) and not present.has_duplicates
                    and set(present)==set(months) and finite.all())
                label=('VERIFIED_CURRENT_FORECAST_COVERAGE' if prospective else
                       'VERIFIED_ARCHIVED_FORECAST_COVERAGE; issuance unverified' if origin else
                       'VERIFIED_REVISED_ACTUAL_COVERAGE')
                row['status']=label if exact else 'INCOMPLETE_COVERAGE'
                if role=='production' and key=='snohvit_net_prod':
                    row['status']+='; rate interpretation must be validated for this forecast vintage'
        except Exception as exc:
            if row.get('raw_file'): row['status']='CONTRACT_INCOMPATIBLE'
            row['error_type']=type(exc).__name__
            # Local contract errors are actionable; never log opaque service errors.
            if isinstance(exc,ValueError): row['reason']=str(exc)
        rows.append(row)
        print(len(rows),key,origin or 'latest',row['status'],row['finite_months'],flush=True)
        write_json(raw/'responses.json',records)
        return row

    catalogue=[]
    for query in [r'sid:teams\natural_gas\EUR\NO_production*',r'sid:teams\natural_gas\EUR\NO\*']:
        frame=find_series(query,client=client)
        catalogue.extend(dict(query=query,sid=s) for s in frame.series_id)
    pd.DataFrame(catalogue).to_csv(output/'details/discovery.csv',index=False)
    selected=[k for entry in model['routing']['nodes'].values() if entry.get('source_group')
        for k in model['sources'][entry['source_group']]['series']]
    current=list(dict.fromkeys(selected+['norway_prod','snohvit_net_prod','norway_nonflex_prod','norway_prod_ex_snohvit']))
    current=[k for k in current if k in registry.index]
    for key in current if not supplement else ['norway_prod_ex_snohvit','snohvit_net_prod_legacy']:
        inspect(key,current_months,prospective=True)
    for key in ['norway_prod_dashboard','norway_exports_qa','kollsnes_maint_d'] if not supplement else ['norway_prod_dashboard']:
        if key in registry.index: inspect(key,current_months,prospective=True,role='maintenance' if 'maint' in key else 'production')
    _,components,contract=source_requirements(ROOT,model,registry)
    mapping=[]
    discovered={r['sid'] for r in catalogue}
    for reference,entry in contract['historical_components'].items():
        label=contract['sources'][entry['key']]['npd_field']
        candidates=[sid for sid in discovered if field_identity(sid.split('\\')[-1].removeprefix('NO_production_').removesuffix('_field'))==label]
        mapping.append(dict(reference=reference,node=entry['node'],historical_key=entry['key'],
            forecast_sid_candidates=';'.join(candidates),status='DISCOVERABLE_CANDIDATE' if candidates else 'NO_INDIVIDUAL_FORECAST_SID_IDENTIFIED',
            reason='NPD historical actual leaf is not a forecast; no workbook substitution or aggregate split'))
    pd.DataFrame(mapping).to_csv(output/'details/field_forecast_mapping.csv',index=False)

    # First full selected-SID origin, then narrow monthly availability checks.
    first_origin='2023-12-31'
    january=pd.period_range('2024-01',periods=12 if supplement else 1,freq='M')
    for key in selected if not supplement else ['snohvit_net_prod_legacy']:
        inspect(key,january,first_origin)
    for delivery in pd.period_range('2024-01','2024-12',freq='M') if not supplement else []:
        origin=str((delivery-1).end_time.date())
        month=pd.PeriodIndex([delivery])
        for key in ['norway_prod','snohvit_net_prod','kollsnes_maint_d','uk_flow_qa','fr_be_flow_qa','nl_de_flow_qa','pl_flow_qa','dk_flow_qa']:
            role='maintenance' if 'maint' in key else 'terminal_flow' if 'flow' in key else 'production'
            inspect(key,month,origin,role)
    for key in ['uk_flow_qa','fr_be_flow_qa','nl_de_flow_qa','pl_flow_qa','dk_flow_qa'] if not supplement else []:
        row=inspect(key,pd.period_range('2024-01','2024-12',freq='M'),role='terminal_flow')
        row['comparison_compatibility']='WITHHELD: signed net/Nybro differs from gross exports' if key in ['pl_flow_qa','dk_flow_qa'] else 'EA allocation groups only; physical terminal receipts unverified'
    for key in ['ttf_eex_curve','nbp_eex_curve','peg_eex_curve'] if not supplement else []:
        inspect(key,january,first_origin,'forward_price')
    if supplement:
        for destination in ['uk','fr','be','nl','de','dk','pl']:
            inspect(destination+'_flow_qa',pd.period_range('2023-01','2023-12',freq='M'),first_origin,'training_flows')
    matrix=pd.DataFrame(rows)
    matrix.to_csv(output/'results.csv',index=False)
    write_json(raw/'jobs.json',jobs)
    manifest=dict(run_id=run_id,git=git_identity(ROOT),raw_directory=raw.relative_to(ROOT).as_posix(),
        prospective_start=str(current_start),prospective_end='2030-12',historical_origins='preceding month-end cutoffs, not claimed issuance dates',
        supplement=supplement,solver_calls=0,scoring=False,holdout_loaded=False,holdout_scored=False,
        source_files_sha256={p.relative_to(ROOT).as_posix():digest(p) for p in [raw/'responses.json',raw/'jobs.json',ROOT/'config/model.yaml',ROOT/'config/data_series.csv',ROOT/'config/evaluation.yaml']})
    for file in [Path(__file__),ROOT/'src/norway_gas_routing/project_data.py',ROOT/'src/norway_gas_routing/evaluation.py']:
        snapshot=output/'provenance'/file.name
        snapshot.write_bytes(file.read_bytes())
        manifest['source_files_sha256'][snapshot.relative_to(ROOT).as_posix()]=digest(snapshot)
    write_json(output/'provenance/run_manifest.json',manifest)
    (output/'report.html').write_text('<meta charset="utf-8"><h1>F1 forecast input viability</h1><p>Availability inspection only; no forecasts solved or scored. Month-end cutoffs are not verified issuance dates. Locked actuals excluded.</p>'+matrix.to_html(index=False,escape=True),encoding='utf-8')
    print('Assessment:',output)
    return output


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supplement',action='store_true',help='Inspect alternative registered totals/Snohvit and first-origin training segments only')
    assess(parser.parse_args().supplement)
