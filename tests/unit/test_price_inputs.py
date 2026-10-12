import pandas as pd
import pytest
from norway_gas_routing.price_response import monthly_features, THERM_MWH


def quotes():
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='MS')
    return {name: pd.Series(value, index=dates) for name, value in
            {'nbp_day_ahead': 100., 'peg_day_ahead': 31., 'ttf_day_ahead': 30., 'eur_gbp': .8}.items()}


def test_dated_conversion_and_common_quote_means():
    monthly, daily = monthly_features(quotes())
    assert monthly.UK.iloc[0] == pytest.approx(1./THERM_MWH/.8-30.)
    assert monthly.FR.eq(1.).all() and monthly.DE_NL.eq(0.).all()
    assert monthly.matched_quote_dates.eq(1).all()


@pytest.mark.parametrize('bad', ['missing_month', 'zero_fx', 'duplicate', 'holdout', 'nonfinite'])
def test_bad_quotes_fail_closed(bad):
    data = quotes()
    if bad == 'missing_month': data['peg_day_ahead'] = data['peg_day_ahead'].iloc[1:]
    if bad == 'zero_fx': data['eur_gbp'].iloc[0] = 0.
    if bad == 'duplicate': data['nbp_day_ahead'] = pd.concat([data['nbp_day_ahead'], data['nbp_day_ahead'].iloc[:1]])
    if bad == 'holdout': data['nbp_day_ahead'].index = pd.date_range('2026-01-01', periods=12, freq='MS')
    if bad == 'nonfinite': data['nbp_day_ahead'].iloc[0] = float('nan')
    with pytest.raises(ValueError): monthly_features(data)
