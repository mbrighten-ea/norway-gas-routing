"""Dimensional diagnostics do not grant prospective source-contract approval."""
import pandas as pd


def monthly_rate_diagnostic(values, months):
    """Convert a hypothesised monthly-average mcm/day series, without filling.

    Source-specific reference conditions and net-saleable compatibility remain
    separate evidence requirements. Signed historical values are retained.
    """
    expected = pd.PeriodIndex(months, freq='M')
    index = pd.DatetimeIndex(values.index)
    if index.tz is not None:
        index = index.tz_convert('UTC').tz_localize(None)
    if (not index.equals(expected.to_timestamp()) or expected.has_duplicates
            or not expected.is_monotonic_increasing
            or not pd.to_numeric(values, errors='coerce').map(
                lambda v: float('-inf') < v < float('inf')).all()):
        raise ValueError('Exact ordered finite monthly observations required; no filling or aggregation.')
    return pd.Series(values.to_numpy()*expected.days_in_month/1000,
                     index=expected, name='diagnostic_monthly_bcm')
