"""Current forecast window and source checks; no inferred physical allocation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from .data_functions import connect_shooju
from .evaluation import load_policy
from .project_data import get_prospective_forecast
from .routing_sources import source_requirements, check_registered


def provisional_capacities(model, months, maintenance, scenario):
    """Approved unchanged 19-envelope scenario; signed Kollsnes plan once.

    No other future availability is assumed verified. This is scenario capacity,
    independent of the failed production-population gate and never solver output.
    """
    from .routing import monthly_available_capacity
    if scenario not in {'baseline_prospective','provisional_kollsnes_143','provisional_kollsnes_156'}:
        raise ValueError('A named F2.2 provisional capacity scenario is required.')
    assets=model['routing']['assets']
    if len(assets)!=19 or assets['KOLLSNES_EXPORT'].get('maintenance_series')!='kollsnes_maint_d':
        raise ValueError('Approved provisional scenario requires the existing 19 model envelopes and Kollsnes maintenance contract.')
    days=pd.date_range(months.min().start_time,months.max().end_time.normalize())
    if not maintenance.index.equals(days):
        raise ValueError('Kollsnes maintenance requires exact daily coverage; no filling.')
    capacities={}; daily=[]
    for asset,entry in assets.items():
        rate=entry['mcm_d'] if 'mcm_d' in entry else entry['annual_bcm']*1000/365
        if asset=='KOLLSNES_EXPORT': rate=156. if scenario=='provisional_kollsnes_156' else 143.
        if asset=='KOLLSNES_EXPORT' and maintenance.gt(rate).any():
            bad=maintenance.loc[maintenance.gt(rate)]
            raise ValueError('KOLLSNES_EXPORT: signed maintenance reaches '+str(bad.max())+
                ' mcm/day above the '+str(rate)+' envelope on '+str(len(bad))+
                ' days (first '+str(bad.index.min().date())+'); obtain a compatible reference/maintenance contract. No clipping, zero floor or rescaling.')
        if entry.get('maintenance_series') and asset!='KOLLSNES_EXPORT':
            raise ValueError(asset+': unreviewed prospective maintenance input.')
        technical=pd.Series([rate],index=pd.DatetimeIndex([months.min().start_time]))
        monthly,detail=monthly_available_capacity(technical,months,maintenance if asset=='KOLLSNES_EXPORT' else None)
        capacities[asset]=monthly.available_capacity_bcm
        daily.append(detail.rename_axis('date').reset_index().assign(asset=asset,
            availability_status='Signed Kollsnes plan applied once' if asset=='KOLLSNES_EXPORT' else 'Unknown future availability; provisional envelope held constant'))
    return pd.DataFrame(capacities),pd.concat(daily,ignore_index=True)


def forecast_window(origin=None, horizon_months=12, forecast_end_month=None):
    """Next complete month through a count or explicit endpoint, ending by 2030.

    An explicit endpoint takes precedence over the length setting. The caller
    records the resolved month count alongside that endpoint in provenance.
    """
    load_policy()
    now=pd.Timestamp.now(tz='UTC')
    if origin is not None and not isinstance(origin,(str,pd.Timestamp)):
        raise ValueError('origin must be a quoted UTC timestamp or null.')
    origin=now.floor('s') if origin is None else pd.to_datetime(origin,utc=True)
    if pd.isna(origin) or origin<now.normalize().replace(day=1) or origin>now:
        raise ValueError('Current forecast origin must be within this UTC month and no later than now; historical replay is separate.')
    if isinstance(horizon_months,bool) or not isinstance(horizon_months,int) or not 1<=horizon_months<=60:
        raise ValueError('horizon_months must be an integer between 1 and 60.')
    origin=origin.floor('s')
    first=origin.tz_localize(None).to_period('M')+1
    if forecast_end_month is not None:
        if not isinstance(forecast_end_month,str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',forecast_end_month):
            raise ValueError('forecast_end_month must be a quoted YYYY-MM month or null.')
        last=pd.Period(forecast_end_month,'M')
        if last<first:
            raise ValueError('forecast_end_month must include at least the first complete delivery month '+str(first)+'.')
        if last>pd.Period('2030-12','M'):
            raise ValueError('Current forecast deliveries must exclude the locked holdout and end by December 2030.')
        months=pd.period_range(first,last,freq='M')
    else:
        months=pd.period_range(first,periods=horizon_months,freq='M')
    if months.min()<pd.Period('2026-10','M') or months.max()>pd.Period('2030-12','M'):
        raise ValueError('Current forecast deliveries must exclude the locked holdout and end by December 2030.')
    return origin.isoformat(),months


def forecast_requirements(root,model,registry,request):
    """Use existing physical memberships; historical field identity is not a forecast."""
    requirements,components,contract=source_requirements(root,model,registry)
    requirements=requirements.copy()
    npd=requirements.key.isin([m['key'] for m in contract.get('historical_components',{}).values()])
    requirements.loc[npd,'blocked']=True
    requirements.loc[npd,'status']='BLOCKED: 2024 historical leaf for frozen residual allocation; complete population gate must pass first'
    requirements.loc[requirements.key.eq('snohvit_net_prod'),'status']='BLOCKED: forecast bcm label versus mcm/day interpretation needs physical-design validation; historical conversion is not approved for forecasts'
    requirements.loc[requirements.key.eq('snohvit_net_prod'),'blocked']=True
    capacities=requirements.classification.eq('essential_assumption')
    requirements.loc[capacities,'blocked']=False
    requirements.loc[capacities,'status']='Approved F2.2 provisional envelope; Kollsnes 143 central / 156 sensitivity; maintenance once; other future availability unknown'
    requirements['origin']=request['origin']
    requirements['start'],requirements['end']=request['start'],request['end']
    training=requirements.classification.eq('essential_training')
    requirements.loc[training,'start']=model['routing']['baseline_start']
    requirements.loc[training,'end']=model['routing']['baseline_end']
    requirements.loc[training,'status']='Existing earlier development-window shares; current-origin training retrieval required after physical contract approval'
    optional=requirements.classification.eq('optional_comparison')
    requirements.loc[optional,'status']='Unavailable: future actual comparisons are not retrieved or scored'
    from .production_population import POPULATION
    if (Path(root)/POPULATION).is_file():
        ledger=pd.read_csv(Path(root)/POPULATION,keep_default_na=False,dtype=str)
        extra=ledger.loc[ledger.classification.isin({'2','5'})]
        rows=[dict(key=row.source_key,identifier=row.sid,consumer=row.node,
            classification='essential_population',status='2024 population: '+row.coverage_status+'; physical entry/ownership '+row.reason,
            blocked=row.coverage_verified!='True' or row.classification_verified!='True',
            raw_unit='bcm',metadata_unit='bcm',model_unit='bcm/month',frequency='monthly',
            transformation='Historical-only component for full-population reconciliation; no forecast or cached-workbook substitution',
            evidence=POPULATION,origin=None,start='2024-01',end='2024-12') for row in extra.itertuples()]
        requirements=pd.concat([requirements,pd.DataFrame(rows)],ignore_index=True)
    return requirements,components,contract


def inspect_forecast_source(root,key,dates,registry,contract,records,output,origin,client):
    """Retain original forecast response, then verify identity/units/exact coverage."""
    spec=check_registered(key,registry,contract)
    record=dict(key=key,sid=spec['sid'],category=spec['category'],kind='forecast',asof=origin,
        query='sid="'+spec['sid']+'"@asof:'+pd.Timestamp(origin).strftime('%Y-%m-%dT%H:%M:%S'),
        start=str(dates.min().date()),end=str(dates.max().date()),status='REQUESTED',
        retrieved_at=datetime.now(timezone.utc).isoformat(),raw_unit=spec['raw_unit'],reported_unit=spec['metadata_unit'],
        target_unit='mcm/day (signed capacity adjustment)' if spec['frequency']=='daily' else 'bcm/month (required; transformation pending)' if key=='snohvit_net_prod' else 'bcm/month',
        transformation='Signed daily mcm/day derate; applied once in approved provisional scenario, reference compatibility checked separately' if spec['frequency']=='daily' else 'Unchanged monthly bcm' if spec['raw_unit']=='bcm' else 'Unchanged raw forecast rate; conversion requires explicit forecast-unit approval',
        vintage_status='Current-origin archived service state, not a historical forecast backtest')
    records.append(record)
    try:
        end=str(dates.max().to_period('M').end_time.date()) if spec['frequency']=='monthly' else str(dates.max().date())
        record['end']=end
        try:
            result=get_prospective_forecast(key,str(dates.min().date()),end,registry=registry,client=client,origin=origin)
        except Exception as exc:
            if isinstance(exc,ValueError): raise
            raise ValueError(key+': forecast retrieval failed ('+type(exc).__name__+'); check credentials/service/SID. No fallback.') from None
        record.update(metadata=result['metadata'],registry=result['registry'],query=result['query'],returned_asof=result['asof'])
        values=result['values']
        raw=Path(output)/'raw'
        raw.mkdir(exist_ok=True)
        path=raw/(key+'_forecast.csv')
        if path.exists(): raise ValueError(key+': raw forecast destination already exists; no overwrite.')
        values.rename('value').rename_axis('date').to_csv(path,float_format='%.17g')
        record.update(raw_file=path.relative_to(Path(output).parent).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        meta=result['metadata']
        if result['asof']!=origin or '@asof:'+pd.Timestamp(origin).strftime('%Y-%m-%dT%H:%M:%S') not in result['query']:
            raise ValueError(key+': forecast origin mismatch; no latest/revised substitution.')
        if meta.get('series_id',spec['sid'])!=spec['sid'] or not str(meta.get('source_file','')).replace('\\','/').endswith(spec['source_file']):
            raise ValueError(key+': forecast source identity differs from canonical contract.')
        if meta.get('unit')!=spec['metadata_unit'] or meta.get('frequency')!=spec['frequency']:
            raise ValueError(key+': inconsistent forecast units/frequency.')
        if meta.get('lifecycle_stage')!='forecast' or not meta.get('forecast_start_date') or pd.Period(meta['forecast_start_date'],'M')>dates.min().to_period('M'):
            raise ValueError(key+': requested delivery values are not genuine forecast segments.')
        actual=pd.DatetimeIndex(values.index)
        if actual.tz is not None:
            if str(actual.tz)!='UTC': raise ValueError(key+': unapproved forecast timezone.')
            actual=actual.tz_localize(None)
        missing=dates.difference(actual)
        unexpected=actual.difference(dates)
        record.update(expected_points=len(dates),returned_points=len(actual),
            missing_dates=missing.strftime('%Y-%m-%d').tolist(),
            missing_delivery_months=missing.to_period('M').unique().astype(str).tolist(),
            unexpected_dates=unexpected.dropna().strftime('%Y-%m-%d').tolist(),
            duplicate_dates=actual[actual.duplicated()].dropna().strftime('%Y-%m-%d').tolist())
        if (actual.hasnans or not actual.is_unique or not actual.sort_values().equals(dates)):
            raise ValueError(key+': incomplete/duplicate forecast coverage; missing delivery months '+
                ', '.join(record['missing_delivery_months'])+'; missing dates '+', '.join(record['missing_dates'])+
                '; unexpected/duplicate dates '+', '.join(record['unexpected_dates']+record['duplicate_dates'])+'; no filling.')
        normal=pd.Series(pd.to_numeric(values.to_numpy(),errors='raise'),index=actual,name=key).sort_index()
        invalid=normal.loc[~normal.map(lambda v: pd.notna(v) and abs(v)!=float('inf'))]
        if len(invalid):
            record['invalid_delivery_months']=invalid.index.to_period('M').unique().astype(str).tolist()
            raise ValueError(key+': missing/nonfinite forecast values in delivery months '+', '.join(record['invalid_delivery_months'])+'.')
        if spec['category']=='production' and key!='snohvit_net_prod' and normal.lt(0).any():
            raise ValueError(key+': negative production forecast; no clipping.')
        record['status']='VERIFIED_FORECAST_RESPONSE' if key!='snohvit_net_prod' else 'COVERAGE_VERIFIED_UNITS_PENDING'
        record['forecast_start']=meta['forecast_start_date']
        return normal
    except (ValueError,OSError,KeyError) as exc:
        record.update(status='REJECTED',validation_error=str(exc))
        raise
    finally:
        (Path(output)/'source_metadata.json').write_text(json.dumps(records,default=str,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def prepare_current_inputs(root,model,registry,request):
    """Retrieve usable candidates, then fail on the explicit unapproved contract.

    No national/non-flex split, missing-to-zero, historical forecast substitution
    or partial physical supply vector is allowed into the optimiser.
    """
    inventory,components,contract=forecast_requirements(root,model,registry,request)
    output=Path(request['_provenance_dir'])
    inventory.to_csv(output/'forecast_requirements.csv',index=False)
    dates=pd.period_range(request['start'],request['end'],freq='M').to_timestamp()
    keys=[key for group in components.values() for key in group if contract['sources'][key].get('provider_contract')!='npd_historical']
    keys+=['norway_prod','snohvit_net_prod']
    if len(set(keys))!=len(keys) or len({registry.at[k,'sid'] for k in keys})!=len(keys):
        raise ValueError('Duplicate forecast production key/SID; no double counting.')
    records,failures=[],[]
    candidates={}
    try: client=connect_shooju()
    except Exception as exc:
        raise ValueError('Current forecast service connection failed ('+type(exc).__name__+'); check authorised credentials/environment.') from None
    for key in keys+['kollsnes_maint_d']:
        selected=pd.date_range(dates.min(),dates.max().to_period('M').end_time.normalize()) if key=='kollsnes_maint_d' else dates
        try: candidates[key]=inspect_forecast_source(root,key,selected,registry,contract,records,output,request['origin'],client)
        except (ValueError,OSError,KeyError) as error: failures.append(str(error))
    from .production_population import population_blockers
    blockers=population_blockers(root,components,output)
    if 'kollsnes_maint_d' in candidates:
        try:
            from .operational import save_current_forecast_table
            capacities,daily=provisional_capacities(model,dates.to_period('M'),candidates['kollsnes_maint_d'],request['capacity_scenario'])
            save_current_forecast_table(capacities,output/'provisional_capacity_monthly.csv',request,monthly_index=True)
            save_current_forecast_table(daily,output/'provisional_capacity_daily.csv',request)
        except (ValueError,KeyError) as error: failures.append(str(error))
    sn=candidates.get('snohvit_net_prod'); national=candidates.get('norway_prod')
    if sn is not None and national is not None and sn.gt(national).any():
        error='snohvit_net_prod: returned values labelled monthly bcm exceed national monthly production; incompatible forecast unit contract. No inferred rate conversion.'
        failures.append(error)
        next(record for record in records if record['key']=='snohvit_net_prod').update(status='REJECTED_FORECAST_UNIT_CONTRACT',validation_error=error)
    blockers.append('Snøhvit forecast conversion and vintage compatibility are not approved; historical July-2025 rate guard is unchanged.')
    coverage_failures=[{k:r[k] for k in ['key','sid','missing_delivery_months','missing_dates',
        'unexpected_dates','duplicate_dates','invalid_delivery_months'] if k in r}
        for r in records if any(r.get(k) for k in ['missing_dates','unexpected_dates','duplicate_dates','invalid_delivery_months'])]
    (output/'forecast_blockers.json').write_text(json.dumps(dict(physical_decisions=blockers,source_failures=failures,
        source_coverage_failures=coverage_failures,source_records=len(records)),indent=2)+'\n')
    (output/'source_metadata.json').write_text(json.dumps(records,default=str,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    raise ValueError('Current forecast blocked: '+' '.join(blockers+failures))
