"""Current forecast window and source checks; no inferred physical allocation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from .data_functions import connect_shooju
from .evaluation import load_policy
from .project_data import get_prospective_forecast
from .routing_sources import source_requirements, check_registered


def forecast_window(origin=None, horizon_months=12):
    """Current-month origins only; next complete delivery month, ending by 2030."""
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
    months=pd.period_range(origin.tz_localize(None).to_period('M')+1,periods=horizon_months,freq='M')
    if months.min()<pd.Period('2026-10','M') or months.max()>pd.Period('2030-12','M'):
        raise ValueError('Current forecast deliveries must exclude the locked holdout and end by December 2030.')
    return origin.isoformat(),months


def forecast_requirements(root,model,registry,request):
    """Use existing physical memberships; historical field identity is not a forecast."""
    requirements,components,contract=source_requirements(root,model,registry)
    requirements=requirements.copy()
    npd=requirements.key.isin([m['key'] for m in contract.get('historical_components',{}).values()])
    requirements.loc[npd,'blocked']=True
    requirements.loc[npd,'status']='BLOCKED: historical NPD leaf has no approved current forecast or source-node aggregation contract'
    requirements.loc[requirements.key.eq('snohvit_net_prod'),'status']='BLOCKED: forecast bcm label versus mcm/day interpretation needs physical-design validation; historical conversion is not approved for forecasts'
    requirements.loc[requirements.key.eq('snohvit_net_prod'),'blocked']=True
    capacities=requirements.classification.eq('essential_assumption')
    requirements.loc[capacities,'blocked']=True
    requirements.loc[capacities,'status']='BLOCKED: proposed baseline held constant prospectively; approval and maintenance-overlap decision absent'
    requirements['origin']=request['origin']
    requirements['start'],requirements['end']=request['start'],request['end']
    training=requirements.classification.eq('essential_training')
    requirements.loc[training,'start']=model['routing']['baseline_start']
    requirements.loc[training,'end']=model['routing']['baseline_end']
    requirements.loc[training,'status']='Existing earlier development-window shares; current-origin training retrieval required after physical contract approval'
    optional=requirements.classification.eq('optional_comparison')
    requirements.loc[optional,'status']='Unavailable: future actual comparisons are not retrieved or scored'
    return requirements,components,contract


def inspect_forecast_source(root,key,dates,registry,contract,records,output,origin,client):
    """Retain original forecast response, then verify identity/units/exact coverage."""
    spec=check_registered(key,registry,contract)
    record=dict(key=key,sid=spec['sid'],category=spec['category'],kind='forecast',asof=origin,
        query='sid="'+spec['sid']+'"@asof:'+pd.Timestamp(origin).strftime('%Y-%m-%dT%H:%M:%S'),
        start=str(dates.min().date()),end=str(dates.max().date()),status='REQUESTED',
        retrieved_at=datetime.now(timezone.utc).isoformat(),raw_unit=spec['raw_unit'],reported_unit=spec['metadata_unit'],
        target_unit='mcm/day (signed capacity adjustment)' if spec['frequency']=='daily' else 'bcm/month (required; transformation pending)' if key=='snohvit_net_prod' else 'bcm/month',
        transformation='Signed daily mcm/day derate; prospective scope/overlap pending approval' if spec['frequency']=='daily' else 'Unchanged monthly bcm' if spec['raw_unit']=='bcm' else 'Unchanged raw forecast rate; conversion requires explicit forecast-unit approval',
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
        if (actual.hasnans or not actual.is_unique or not actual.sort_values().equals(dates)):
            raise ValueError(key+': incomplete/duplicate forecast coverage; missing '+', '.join(dates.difference(actual).astype(str))+'; no filling.')
        normal=pd.Series(pd.to_numeric(values.to_numpy(),errors='raise'),index=actual,name=key).sort_index()
        if not normal.map(lambda v: pd.notna(v) and abs(v)!=float('inf')).all():
            raise ValueError(key+': missing/nonfinite forecast values.')
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
    try: client=connect_shooju()
    except Exception as exc:
        raise ValueError('Current forecast service connection failed ('+type(exc).__name__+'); check authorised credentials/environment.') from None
    for key in keys+['kollsnes_maint_d']:
        selected=pd.date_range(dates.min(),dates.max().to_period('M').end_time.normalize()) if key=='kollsnes_maint_d' else dates
        try: inspect_forecast_source(root,key,selected,registry,contract,records,output,request['origin'],client)
        except (ValueError,OSError,KeyError) as error: failures.append(str(error))
    missing=inventory.loc[inventory.blocked & inventory.key.str.endswith('_net_actual')]
    by_node=missing.groupby('consumer').size().to_dict()
    blockers=['Physical-design decision required: '+str(len(missing))+' additional fields lack an approved forecast supply contract ('+
        ', '.join(node+': '+str(count) for node,count in by_node.items())+'). No national/non-flexible remainder may be assigned or dropped.',
        'Snøhvit forecast conversion and vintage compatibility are not approved; historical July-2025 rate guard is unchanged.',
        'Prospective baseline technical capacities and signed Kollsnes maintenance scope/overlap require explicit approval.']
    (output/'forecast_blockers.json').write_text(json.dumps(dict(physical_decisions=blockers,source_failures=failures,source_records=len(records)),indent=2)+'\n')
    raise ValueError('Current forecast blocked: '+' '.join(blockers+failures))
