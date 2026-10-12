"""Registry-aware retrieval for Norway gas routing; no model transformations.

Use the readable registry keys. REVIEW series can be retrieved for inspection;
retrieval does not approve their use. Metadata, units and values remain separate.
The generic, portable Shooju functions live in data_functions.py.
"""
from pathlib import Path

from . import data_functions as sj
from .config import load_series
from .series_audit import profile
from .evaluation import request_bounds, check_dates


DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / 'config/data_series.csv'


def load_registry(path=DEFAULT_REGISTRY):
    """Load and validate the canonical series registry, indexed by model key."""
    return load_series(path)


def select_series(*, category=None, asset=None, status=None, model_role=None,
                  country_iso=None, balance_item=None, data_item=None,
                  asset_type=None, market_area=None, price_type=None, registry=None):
    """Return registry rows matching the supplied exact filters, without retrieval.

    For example category='maintenance', status='CONFIRMED'. No status is excluded
    by default: TODO and REVIEW rows remain visible in sourcing inventories.
    """
    registry = load_registry() if registry is None else registry
    selected = registry
    for column, value in {'category': category, 'asset': asset,
                          'status': status, 'model_role': model_role,
                          'country_iso': country_iso, 'balance_item': balance_item,
                          'data_item': data_item, 'asset_type': asset_type,
                          'market_area': market_area, 'price_type': price_type}.items():
        if value is not None:
            mask = (selected[column].str.split(';').apply(lambda items: value in items)
                    if column == 'country_iso' else selected[column] == value)
            selected = selected.loc[mask]
    return selected.copy()


def series_info(identifier, *, registry=None):
    """Resolve a registry key to a plain dictionary including notes."""
    registry = load_registry() if registry is None else registry
    matches = registry.loc[registry.index == identifier]
    if len(matches) == 0:
        raise KeyError(f'Unknown series key: {identifier}')
    if len(matches) != 1:
        raise ValueError(f'Ambiguous series key: {identifier}')
    return {'key': matches.index[0], **matches.iloc[0].to_dict()}


def _retrievable(info):
    if not info['sid'].strip():
        raise ValueError(f"{info['key']}: no SID is registered ({info['status']})")
    hint = info.get('query_or_transform_hint', '')
    if 'contract_obj.id=' in hint:
        raise ValueError(f"{info['key']}: contract identifier, not an exact SID. Retrieval hint: {hint}")


def get_registered_series(identifier, start='MIN', end='MAX', *, max_points=-1,
                          registry=None, client=None, asof=None):
    """Retrieve one registry series with source metadata and existing audit checks.

    Return {'registry': {...}, 'metadata': {...}, 'values': Series,
    'evidence/inputs': {...}}. This is raw inspection data, not a model-ready input.
    Negative maintenance is preserved. No Snøhvit, energy, price, gas-day or
    monthly-volume conversion is performed. Bounds are observation dates, not
    forecast vintages or backtest information cutoffs. Optional ``asof`` queries
    the exact SID archive directly on every call, with metadata from that same
    query. Archive retrieval alone does not verify release availability.
    """
    info = series_info(identifier, registry=registry)
    _retrievable(info)
    sj._check_request(info['sid'], max_points)
    start, end = request_bounds(start, end)
    query = None
    if asof is not None:
        import pandas as pd
        origin = pd.Timestamp(asof)
        if pd.isna(origin):
            raise ValueError('Explicit valid forecast-origin timestamp required')
        origin = origin.tz_localize('UTC') if origin.tzinfo is None else origin.tz_convert('UTC')
        check_dates([origin], 'read')
        bare_sid = info['sid'].removeprefix('sid=')
        if any(c in bare_sid for c in ['"', '\n', '\r']):
            raise ValueError('Archive retrieval requires a bare exact SID')
        query = f'sid="{bare_sid}"@asof:{origin.strftime("%Y-%m-%dT%H:%M:%S")}'
    client = sj._client(client)
    if query is None:
        values = sj.get_series(info['sid'], start, end, max_points=max_points, client=client)
        metadata = sj.get_metadata(info['sid'], client=client)
    else:
        import pandas as pd
        frame = client.sj.get_df(query=query, fields=None, max_points=max_points, df=start, dt=end)
        if frame.empty:
            raise ValueError(f'{identifier}: no SID values at requested origin; no cached fallback')
        if not {'dt', 'val'}.issubset(frame.columns):
            raise ValueError(f'{identifier}: unexpected archived SID response schema')
        dates = pd.DatetimeIndex(pd.to_datetime(frame.dt, utc=True))
        check_dates(dates, 'read')
        if dates.hasnans or not dates.is_unique:
            raise ValueError(f'{identifier}: missing or duplicate archived timestamps')
        values = pd.Series(frame.val.to_numpy(), index=dates, name=identifier).sort_index()
        metadata = sj.get_metadata(query, client=client)
    check_dates(values.index, 'read')
    # Coverage profiling uses calendar dates; leave the returned source timezone
    # intact while avoiding implicit timezone conversion warnings in the audit.
    profile_values = values
    if getattr(values.index, 'tz', None) is not None:
        profile_values = values.copy()
        profile_values.index = values.index.tz_localize(None)
    return {'registry': info,
            'metadata': metadata, 'query': query, 'asof': asof,
            'values': values, 'evidence/inputs': profile(profile_values)}


def get_registered_frame(identifiers, start='MIN', end='MAX', *, max_points=-1,
                         registry=None, client=None):
    """Retrieve an explicit group, returning (values_frame, registry_frame).

    Values columns use the supplied keys. Registry rows use the same
    labels and include model keys, source units, status and notes. Dates are
    aligned by union; no filling or frequency harmonisation is performed.
    Select an appropriate group explicitly, rather than downloading all inputs.
    """
    import pandas as pd

    if isinstance(identifiers, str):
        raise ValueError('Supply a list of keys, not one string')
    identifiers = list(identifiers)
    if not identifiers or len(set(identifiers)) != len(identifiers):
        raise ValueError('Supply a nonempty list of distinct keys')
    registry = load_registry() if registry is None else registry
    records = {}
    for identifier in identifiers:
        info = series_info(identifier, registry=registry)
        _retrievable(info)
        records[identifier] = info
    start, end = request_bounds(start, end)
    frame = sj.get_series_frame({name: info['sid'] for name, info in records.items()},
                                start, end, max_points=max_points, client=client)
    check_dates(frame.index, 'read')
    return frame, pd.DataFrame.from_dict(records, orient='index')
