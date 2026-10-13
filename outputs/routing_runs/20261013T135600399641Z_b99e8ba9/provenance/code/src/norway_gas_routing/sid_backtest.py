"""Inspect a fresh historical SID bundle without substituting inputs or solving."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unicodedata

import pandas as pd

from .data_functions import connect_shooju, find_series
from .evaluation import check_dates, TRAIN_CUTOFF
from .project_data import get_registered_series


def component_references(root, model):
    """Use retained identifier/formula audit metadata, never workbook numbers."""
    components = [(node, col) for node, entry in model['routing']['nodes'].items()
                  for col in entry.get('workbook_columns', [])]
    if not components:
        return pd.DataFrame(columns=['node','column','field','header_sid'])
    inventory = pd.read_csv(Path(root)/'evidence/inputs/network_forecast_production_inventory.csv',
        usecols=['model_source','workbook_column','physical_field','sid'], keep_default_na=False)
    rows = []
    for node, column in components:
        match = inventory.loc[inventory.model_source.eq(node) & inventory.workbook_column.eq(column)]
        if len(match)!=1:
            raise ValueError('Component identifier audit no longer matches the active source mapping')
        rows.append({'node':node, 'column':column, 'field':match.iloc[0].physical_field,
                     'header_sid':match.iloc[0].sid})
    return pd.DataFrame(rows)


def component_candidates(references, discovered):
    """Suggest only returned exact identifiers; suggestions do not approve mapping."""
    def normal(value):
        value = value.replace('Ø','O').replace('ø','o').replace('Æ','Ae').replace('æ','ae')
        return ''.join(c for c in unicodedata.normalize('NFKD',value).lower() if c.isalnum())
    result = references.copy()
    candidates = []
    for label in result.field:
        matches = [sid for sid in discovered if normal(label)==normal(sid.split('\\')[-1]
            .removeprefix('NO_production_').removesuffix('_field'))]
        candidates.append(';'.join(sorted(matches)))
    result['discovered_sid_candidates'] = candidates
    result['status'] = ['REVIEW_EXACT_RETURNED_SID' if v else 'NO_INDIVIDUAL_FORECAST_SID_IDENTIFIED' for v in candidates]
    return result


def inspect_origin(root, model, registry, output, origin='2024-12-31', *, client=None, months_ahead=12):
    """Fetch selected registered inputs directly; report complete blockers explicitly."""
    root, output = Path(root).resolve(), Path(output).resolve()
    if not output.is_relative_to(root/'outputs') and not output.is_relative_to(root/'.scratch'):
        raise ValueError('Origin inspection output must be in repository outputs/ or .scratch/')
    if any(output.is_relative_to(root/p) for p in ['outputs/reconstruction','outputs/benchmark']):
        raise ValueError('Cannot overwrite retained model results')
    timestamp = pd.Timestamp(origin)
    timestamp = timestamp.tz_localize('UTC') if timestamp.tzinfo is None else timestamp.tz_convert('UTC')
    if pd.isna(timestamp):
        raise ValueError('Explicit valid origin required')
    check_dates([timestamp], 'read')
    if isinstance(months_ahead,bool) or not isinstance(months_ahead,int) or not 1<=months_ahead<=12:
        raise ValueError('months_ahead must be between 1 and 12')
    origin = timestamp.strftime('%Y-%m-%d')
    targets = pd.period_range(pd.Period(origin,'M')+1, periods=months_ahead, freq='M')
    check_dates(targets, 'read')
    training = pd.period_range(model['routing']['baseline_start'], model['routing']['baseline_end'], freq='M')
    check_dates(training,'fit')
    if training.max()>=targets.min():
        raise ValueError('Training cannot include target outcomes')
    client = connect_shooju() if client is None else client
    output.mkdir(parents=True, exist_ok=True)
    provenance = output/'provenance'; provenance.mkdir(exist_ok=True)
    query = r'sid:teams\natural_gas\EUR\NO_production*'+f'@asof:{origin}T23:59:59'
    discovery = find_series(query, client=client)
    discovered = discovery.series_id.tolist()
    discovery.to_csv(provenance/'origin_production_sid_discovery.csv',index=False)
    components = component_candidates(component_references(root,model),discovered)
    components.to_csv(output/'required_component_sids.csv',index=False)
    keys = {}
    for _, entry in model['routing']['nodes'].items():
        if 'source_group' in entry:
            for key in model['sources'][entry['source_group']]['series']:
                keys[key] = ('production',targets)
    keys.update({'norway_prod':('production',targets), 'snohvit_net_prod':('production',targets)})
    for entry in model['routing']['assets'].values():
        if entry.get('maintenance_series'):
            keys[entry['maintenance_series']] = ('maintenance',targets)
    for destination in ['UK','FR','BE','NL','DE','DK','PL']:
        keys[destination.lower()+'_flow_qa'] = ('historical_flows',training)
    rows, point_rows, responses = [], [], []
    for key, (category, months) in keys.items():
        sid = registry.at[key,'sid']
        query_origin = min(timestamp,TRAIN_CUTOFF).strftime('%Y-%m-%d') if category=='historical_flows' else origin
        row = {'key':key, 'category':category, 'sid':sid, 'origin':origin,
            'query_origin':query_origin, 'start':str(months.min()), 'end':str(months.max()), 'status':'', 'point_count':0}
        try:
            result = get_registered_series(key, str(months.min().start_time.date()),
                str(months.max().end_time.date()), asof=query_origin+'T23:59:59Z',
                registry=registry, client=client)
            values, meta = result['values'], result['metadata']
            response = {'key':key,'query':result['query'],'metadata':meta,
                'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
                'points':[{'date':str(d),'value':float(v) if pd.notna(v) else None} for d,v in values.items()]}
            responses.append(response)
            row.update({'point_count':len(values),'metadata_unit':meta.get('unit'),
                'metadata_frequency':meta.get('frequency'),'forecast_start':meta.get('forecast_start_date')})
            frequency = meta.get('frequency')
            if frequency=='monthly':
                observed = pd.DatetimeIndex(values.index).tz_localize(None).to_period('M')
                complete = not observed.has_duplicates and set(observed)==set(months) and values.notna().all()
            elif frequency=='daily':
                dates = pd.DatetimeIndex(values.index).tz_localize(None).normalize()
                complete = dates.equals(pd.date_range(months.min().start_time,months.max().end_time.normalize())) and values.notna().all()
            else:
                complete = False
            row['status'] = 'RETURNED_COMPLETE; SOURCE_SEMANTICS_AND_RELEASE_REVIEW_REQUIRED' if complete else 'INCOMPLETE_COVERAGE_OR_FREQUENCY'
            first = meta.get('forecast_start_date')
            if category in ['production','maintenance'] and (meta.get('lifecycle_stage')!='forecast' or
                not first or months.min()<pd.Period(first,'M')):
                row['status'] = 'FORECAST_SEGMENT_UNVERIFIED'
            if category=='historical_flows' and (not first or months.max()>=pd.Period(first,'M')):
                row['status'] = 'TRAINING_HISTORICAL_SEGMENT_UNVERIFIED'
            for date,value in values.items():
                point_rows.append({'key':key,'sid':sid,'category':category,'origin':origin,'date':str(date),
                    'raw_value':value,'raw_unit':meta.get('unit'),'query':result['query']})
        except (ValueError, KeyError) as error:
            row['status'] = 'NO_USABLE_ORIGIN_SID_RESPONSE'
            row['error_type'] = type(error).__name__
        rows.append(row)
    pd.DataFrame(rows).to_csv(output/'origin_input_readiness.csv',index=False)
    pd.DataFrame(point_rows).to_csv(output/'origin_input_points.csv',index=False,float_format='%.15g')
    (provenance/'origin_sid_responses.json').write_text(json.dumps(responses,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    blockers = ['Worksheet source components require approved exact SID mappings; no numerical workbook fallback',
        'Capacity effectiveness/availability at origin not verified', 'Training/public-release availability at origin not independently verified']
    blockers += [r['key']+': '+r['status'] for r in rows if not r['status'].startswith('RETURNED_COMPLETE')]
    manifest = {'origin':origin,'targets':[str(m) for m in targets],'status':'INCOMPLETE_ORIGIN_BUNDLE',
        'training_query_cutoff':min(timestamp,TRAIN_CUTOFF).strftime('%Y-%m-%d'), 'parameter_fitting':False,
        'blockers':blockers,'sid_queries':len(keys),'discovery_query':query,'component_rows':len(components),
        'solver_calls':0,'holdout_loaded':False,'holdout_scored':False,'actuals_scored':False,
        'optimiser_sha256':hashlib.sha256((root/'src/norway_gas_routing/routing.py').read_bytes()).hexdigest(),
        'model_config_sha256':hashlib.sha256((root/'config/model.yaml').read_bytes()).hexdigest()}
    (provenance/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest
