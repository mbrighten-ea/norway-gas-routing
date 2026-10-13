"""Synthetic dimensional/capacity evidence; no approval or live SID dependency."""
import pandas as pd
import pytest

from norway_gas_routing.production_diagnostics import monthly_rate_diagnostic
from norway_gas_routing.capacity.diagnostics import kollsnes_hypotheses


def test_signed_calendar_conversion_including_leap_year():
    months = pd.period_range('2028-01', '2028-03', freq='M')
    result = monthly_rate_diagnostic(pd.Series([10., -2., 0.], index=months.to_timestamp()), months)
    assert result.tolist() == pytest.approx([.31, -.058, 0.])


@pytest.mark.parametrize('case', ['gap', 'nan', 'duplicate', 'reverse', 'midmonth'])
def test_rate_diagnostic_cannot_fill_or_reorder(case):
    months = pd.period_range('2026-11', '2026-12', freq='M')
    values = pd.Series([10., 10.], index=months.to_timestamp())
    if case == 'gap': values = values.iloc[:1]
    if case == 'nan': values.iloc[0] = float('nan')
    if case == 'duplicate': values.index = [values.index[0]]*2
    if case == 'reverse': values = values.iloc[::-1]
    if case == 'midmonth': values.index = pd.DatetimeIndex([date.replace(day=2) for date in values.index])
    with pytest.raises(ValueError): monthly_rate_diagnostic(values, months)


def test_dual_is_only_an_upper_limit_and_preserves_invalid_central():
    values = pd.Series([0., 10., 20., 156.], index=pd.date_range('2027-09-01', periods=4))
    daily, monthly = kollsnes_hypotheses(values, '2027-09-01', '2027-09-04')
    assert daily.hypothetical_dual_mcmd.tolist() == [143., 143., 136., 0.]
    assert daily.central_143_minus_loss_mcmd.iloc[-1] == -13
    assert monthly.central_invalid_days.iloc[0] == 1
    assert monthly.hypothetical_dual_bcm.iloc[0] == pytest.approx(.422)
    assert monthly.diagnostic_only.all()


@pytest.mark.parametrize('case', ['gap', 'nan', 'negative', 'above_reference', 'duplicate'])
def test_capacity_diagnostic_cannot_manufacture_availability(case):
    values = pd.Series([0., 10.], index=pd.date_range('2027-09-01', periods=2))
    if case == 'gap': values = values.iloc[:1]
    if case == 'nan': values.iloc[0] = float('nan')
    if case == 'negative': values.iloc[0] = -1
    if case == 'above_reference': values.iloc[0] = 157
    if case == 'duplicate': values.index = [values.index[0]]*2
    with pytest.raises(ValueError): kollsnes_hypotheses(values, '2027-09-01', '2027-09-02')
