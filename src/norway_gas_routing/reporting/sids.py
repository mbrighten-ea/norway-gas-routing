"""Fresh EA/Shooju references for graphics; no workbook/cache input fallback."""
from datetime import datetime, timezone
import hashlib
import json

import numpy as np
import pandas as pd

from ..evaluation import check_dates
from ..project_data import get_registered_series, load_registry
from .data import COUNTRIES, GROUPS

KEYS = {'UK': 'uk_flow_qa', 'FR': 'fr_flow_qa', 'BE': 'be_flow_qa',
        'NL': 'nl_flow_qa', 'DE': 'de_flow_qa', 'PL': 'pl_flow_qa', 'DK': 'dk_flow_qa',
        'FR+BE': 'fr_be_flow_qa', 'NL+DE': 'nl_de_flow_qa', 'total': 'norway_exports_qa'}


def monthly_reference(result, months, origin=None):
    """Validate exact monthly bcm series; identify historical/forecast segments."""
    meta = result['metadata']
    if meta.get('unit') != 'bcm' or meta.get('frequency') != 'monthly':
        raise ValueError('EA reference must explicitly be monthly bcm; no assumed conversions')
    if not str(meta.get('source_file', '')).endswith('Norwegian flows model.xlsx'):
        raise ValueError('EA reference source identity changed')
    first = meta.get('forecast_start_date')
    if not first:
        raise ValueError('EA historical/forecast boundary is missing')
    values = result['values']
    dates = pd.DatetimeIndex(pd.to_datetime(values.index, utc=True)).tz_localize(None)
    check_dates(dates, 'read')
    if not dates.equals(dates.to_period('M').to_timestamp()) or dates.to_period('M').has_duplicates:
        raise ValueError('EA reference requires unique first-of-month timestamps')
    values = pd.Series(values.to_numpy(), index=dates.to_period('M').astype(str), dtype=float)
    if np.isinf(values).any():
        raise ValueError('Infinite EA reference value')
    target = pd.PeriodIndex(months, freq='M')
    boundary = pd.Period(first, 'M')
    if origin is None:
        if (target >= boundary).any():
            raise ValueError('Requested EA historical actuals cross its forecast-start boundary')
    elif (meta.get('lifecycle_stage') != 'forecast' or
          (target <= pd.Period(origin, 'M')).any() or (target < boundary).any()):
        raise ValueError('Requested origin values are not verified future-forecast segments')
    return values.reindex(months)


def load_sid_reference(months, origin=None, *, registry=None, client=None):
    """Query each exact SID afresh; original group series are never rebuilt."""
    check_dates(months, 'read')
    months = sorted(set(months))
    if not months:
        raise ValueError('Explicit reporting months required')
    if origin is not None:
        timestamp = pd.Timestamp(origin)
        timestamp = timestamp.tz_localize('UTC') if timestamp.tzinfo is None else timestamp.tz_convert('UTC')
        if pd.isna(timestamp):
            raise ValueError('Forecast origin must be an explicit valid timestamp')
        # Validation origins can advance while model parameters remain frozen.
        # Source retrieval does not fit parameters or score the locked holdout.
        check_dates([timestamp], 'read')
        origin = timestamp.strftime('%Y-%m-%d')
        selected = [m for m in months if pd.Period(m, 'M') > pd.Period(origin, 'M')]
        asof = origin+'T23:59:59Z'
    else:
        selected, asof = months, None
    registry = load_registry() if registry is None else registry
    # An origin preceding none of the selected months needs no numerical query.
    values_by_name, ledger, responses, hashes = {}, [], [], {}
    # The declared total's metadata still starts forecasts in May 2023, so it
    # cannot independently establish 2024/2025 actual totals. Do not score it.
    names = list(GROUPS)+['total'] if origin else [n for n in KEYS if n!='total']
    for name in names if selected else []:
        key = KEYS['PL' if name == 'Baltic Pipe' else name]
        result = get_registered_series(key, selected[0]+'-01',
            str(pd.Period(selected[-1], 'M').end_time.date()), max_points=-1,
            asof=asof, registry=registry, client=client)
        values = monthly_reference(result, selected, origin)
        sid = registry.at[key, 'sid']
        query = result['query'] or f'sid="{sid.removeprefix("sid=")}"'
        retrieved = datetime.now(timezone.utc).isoformat()
        response = {'key': key, 'sid': sid, 'query': query, 'origin': origin,
            'retrieved_at_utc': retrieved, 'metadata': result['metadata'],
            'points': [{'month': m, 'value_bcm': float(v) if pd.notna(v) else None} for m, v in values.items()]}
        # Hash numerical response + source metadata independently of retrieval clock.
        digest = hashlib.sha256(json.dumps({k:v for k,v in response.items() if k!='retrieved_at_utc'},
            sort_keys=True, allow_nan=False).encode()).hexdigest()
        hashes[sid] = digest
        responses.append(response)
        values_by_name[name] = values
        for month, value in values.items():
            ledger.append({'month': month, 'destination': name, 'key': key, 'sid': sid,
                'query': query, 'origin': origin or '', 'value_bcm': value, 'source_unit': 'bcm',
                'frequency': 'monthly', 'forecast_start': result['metadata']['forecast_start_date'],
                'retrieved_at_utc': retrieved, 'response_sha256': digest,
                'source_file': result['metadata']['source_file'], 'conversion': 'none'})
    rows = []
    for level, names in [('countries', COUNTRIES), ('groups', list(GROUPS)), ('total', ['total'])]:
        for name in names:
            lookup_name = 'Baltic Pipe' if origin and name=='PL' else 'PL' if not origin and name=='Baltic Pipe' else name
            values = values_by_name.get(lookup_name)
            if values is None:
                continue
            for month, value in values.items():
                compatible = origin is not None or name not in ['PL', 'Baltic Pipe', 'DK', 'total']
                status = 'EA archived destination forecast; release timing independently unverified' if origin else 'EA historical actual allocation series; not independently verified physical terminal receipts'
                if origin is None and name in ['PL', 'Baltic Pipe']:
                    status += '; historical Nybro entry is not Polish delivery; export error withheld'
                if origin is None and name=='DK':
                    status += '; signed net offtake is not gross physical exports; export error withheld'
                if name=='total':
                    status += '; declared accounting total, not a reconciled destination sum'
                rows.append({'month': month, 'level': level, 'destination': name,
                    'value_bcm': value, 'compatible': compatible, 'status': status,
                    'cell': '', 'source_unit': 'bcm', 'conversion': 'none',
                    'source_file': 'Direct EA/Shooju SID query'})
    identifier = 'sid:'+origin if origin else 'sid:actuals'
    data = pd.DataFrame(rows, columns=['month','level','destination','value_bcm','compatible','status','cell','source_unit','conversion','source_file'])
    return {'id': identifier, 'kind': 'forecast' if origin else 'ea_actuals',
        'label': f'EA legacy forecast as of {origin}' if origin else 'EA historical actuals (allocation series)',
        'vintage': f'Origin {origin}; fresh @asof retrieval; release timing unverified' if origin else 'Latest revised EA historical actuals; fresh SID retrieval',
        'data': data, 'ledger': pd.DataFrame(ledger), 'responses': responses,
        'source_hashes': hashes, 'notes': ['Direct SID queries on every run; no workbook or cached numerical inputs.',
            'Original five EA group series are retained without disaggregation.',
            'Historical Poland/Nybro and signed Danish net boundaries prevent direct gross-export scoring.']}
