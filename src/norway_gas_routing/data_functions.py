"""Small, read-only Shooju wrappers, portable to other projects.

Requires the existing ``helper_functions_ea`` package and SHOOJU_SERVER,
SHOOJU_USER and SHOOJU_KEY environment variables. No credentials are stored here.
Importing this module does not connect to Shooju. Reuse one client per session:

    client = connect_shooju()
    values = get_series(sid, '2025-01-01', '2025-12-31', client=client)
    metadata = get_metadata(sid, client=client)
    candidates = find_series(r'sid:teams\\natural_gas\\price', client=client)
    frame = get_series_frame({'nyhamna_maintenance': sid}, client=client)

Dates, frequency, units, missing values and negative values are left unchanged.
No resampling, conversion, filling, clipping or writes are performed. Service
errors propagate to the caller; do not log credentials or raw service errors.
"""

import pandas as pd


def connect_shooju():
    """Load the established environment settings and return a ShoojuTools client.

    check_env() looks for .env in the working directory, then the user's home,
    following the helper's existing rules. This does not install anything.
    """
    from helper_functions_ea import ShoojuTools, check_env

    check_env()
    return ShoojuTools(silence_alerts=True)


def _client(client):
    return connect_shooju() if client is None else client


def _check_request(sid, max_points):
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError('Supply a nonempty SID')
    if (isinstance(max_points, bool) or not isinstance(max_points, int)
            or (max_points != -1 and max_points <= 0)):
        raise ValueError('max_points must be -1 (all points) or a positive integer')


def get_series(sid, start='MIN', end='MAX', *, max_points=-1, client=None):
    """Return the helper's sorted pandas Series for one SID.

    Within this repository MIN/MAX are bounded by the chronological policy and
    dates must be absolute. When copied as a standalone module, helper date
    expressions are passed through. max_points=-1 requests all allowed observations;
    a positive cap can truncate coverage and is not a frequency setting.
    Empty results and missing values are returned as supplied by the helper.
    """
    _check_request(sid, max_points)
    if __package__:
        from .evaluation import request_bounds, check_dates
        start, end = request_bounds(start, end)
    values = _client(client).get_points_from_sid_into_series(
        sid, start, end, max_points)
    if __package__:
        check_dates(values.index, 'read')
    return values


def get_metadata(sid, fields=None, *, client=None):
    """Return a metadata dictionary; None requests all provider fields.

    Metadata unit/frequency labels describe the source; they do not validate
    the observations. Absent requested fields follow the helper's behaviour.
    """
    _check_request(sid, -1)
    if fields is not None and (isinstance(fields, str) or not fields):
        raise ValueError('fields must be a nonempty list of field names')
    return dict(_client(client).get_fields_from_sid(
        sid, fields=['*'] if fields is None else list(fields)))


def find_series(query, fields=None, *, client=None):
    """Discover SIDs using an explicit Shooju query; return a metadata DataFrame.

    Default columns contain only series_id. Additional fields must be named
    explicitly and present on matched series: the helper can raise KeyError
    for missing fields. Use get_metadata(sid) for all fields on one candidate.
    Wildcard field requests are excluded because the existing helper's '*'
    discovery branch can duplicate series_id. No observations are retrieved.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Supply a nonempty Shooju query')
    if fields is not None and (isinstance(fields, str) or not fields):
        raise ValueError('fields must be a nonempty list of field names')
    selected = ['series_id'] + ([] if fields is None else list(fields))
    if '*' in selected:
        raise ValueError('Name discovery fields explicitly; use get_metadata for all fields')
    selected = list(dict.fromkeys(selected))
    return _client(client).get_fields_from_query(query, fields=selected).reset_index(drop=True)


def get_series_frame(sids, start='MIN', end='MAX', *, max_points=-1, client=None):
    """Retrieve a {column_name: SID} mapping into a wide pandas DataFrame.

    Columns retain caller names, so project registry keys can be used here.
    Dates are aligned by their union, preserving gaps as NaN. Mixed frequencies
    are not harmonised. Duplicate timestamps are rejected before alignment;
    inspect those with get_series instead. No partial result is returned on error.
    """
    if not isinstance(sids, dict) or not sids:
        raise ValueError('Supply a nonempty {column_name: SID} dictionary')
    for sid in sids.values():
        _check_request(sid, max_points)
    if __package__:
        from .evaluation import request_bounds
        start, end = request_bounds(start, end)
    client = _client(client)
    columns = {}
    for name, sid in sids.items():
        values = get_series(sid, start, end, max_points=max_points, client=client)
        if values.index.has_duplicates:
            raise ValueError(f'Duplicate timestamps in {name}; inspect the raw series')
        columns[name] = values
    return pd.concat(columns, axis=1).sort_index()
