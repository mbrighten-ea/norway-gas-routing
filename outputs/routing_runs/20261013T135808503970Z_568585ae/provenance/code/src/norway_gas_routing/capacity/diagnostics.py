"""Unapproved Kollsnes hypotheses for evidence comparison, never live inputs."""
import pandas as pd


def kollsnes_hypotheses(unavailable, start, end):
    """Require every daily observation; retain the invalid 143-minus-loss case.

    Numerical feasibility cannot certify a rating's physical definition, date,
    reference conditions or the source's event aggregation. No clipping/filling.
    """
    expected = pd.date_range(start, end, freq='D')
    values = unavailable.copy()
    index = pd.DatetimeIndex(values.index)
    if index.tz is not None:
        index = index.tz_convert('UTC').tz_localize(None)
    values.index = index
    if not index.equals(expected) or not pd.to_numeric(values, errors='coerce').map(
            lambda v: 0 <= v <= 156).all():
        raise ValueError('Complete finite daily unavailable capacity in [0,156] required; no filling.')
    daily = pd.DataFrame({'unavailable_mcmd': values})
    daily['central_143_minus_loss_mcmd'] = 143 - values
    daily['sensitivity_156_minus_loss_mcmd'] = 156 - values
    daily['hypothetical_dual_mcmd'] = daily['sensitivity_156_minus_loss_mcmd'].clip(upper=143)
    daily['central_invalid'] = daily.central_143_minus_loss_mcmd.lt(0)
    monthly = daily.drop(columns='central_invalid').groupby(index.to_period('M')).sum()/1000
    monthly.columns = [c.replace('_mcmd', '_bcm') for c in monthly.columns]
    monthly['central_invalid_days'] = daily.central_invalid.groupby(index.to_period('M')).sum()
    monthly['diagnostic_only'] = True
    return daily, monthly
