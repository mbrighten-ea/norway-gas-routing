import pandas as pd
import pytest

from norway_gas_routing.config import load_config
from norway_gas_routing.data import time_series
from norway_gas_routing.maintenance import capacity_for_asset, daily_maintenance_capacity
from norway_gas_routing.units import mcm_d_to_monthly_bcm
from norway_gas_routing.validation import ValidationError


@pytest.mark.parametrize("start,end,days", [
    ("2024-01-01", "2024-01-31", 31),
    ("2024-02-01", "2024-02-29", 29),
    ("2023-02-01", "2023-02-28", 28),
])
def test_calendar_conversion(daily, start, end, days):
    result = mcm_d_to_monthly_bcm(daily(100, start=start, end=end))
    assert result["unit"] == "bcm" and result["frequency"] == "monthly"
    assert result["values"].iloc[0] == pytest.approx(days * .1)


def test_daily_varying_rates_are_summed(daily):
    rates = daily(100)
    rates["values"].iloc[0] = 200
    assert mcm_d_to_monthly_bcm(rates)["values"].iloc[0] == pytest.approx(3.2)


def test_multiple_months_and_leap_year(daily):
    result = mcm_d_to_monthly_bcm(daily(100, start="2024-01-01", end="2024-03-31"))
    assert result["values"].tolist() == pytest.approx([3.1, 2.9, 3.1])


@pytest.mark.parametrize("drop", [[0], [10], [30], list(range(31, 60))])
def test_missing_days_or_months_rejected(daily, drop):
    rates = daily(100, end="2024-03-31")
    incomplete = time_series("x", rates["values"].drop(rates["values"].index[drop]), "mcm_d", "daily")
    with pytest.raises(ValidationError, match="complete calendar months"):
        mcm_d_to_monthly_bcm(incomplete)


def test_partial_month_rejected(daily):
    with pytest.raises(ValidationError):
        mcm_d_to_monthly_bcm(daily(100, start="2024-01-02"))


def test_duplicate_daily_dates_rejected():
    with pytest.raises(ValidationError, match="Duplicate"):
        time_series("x", pd.Series([1, 2], index=pd.to_datetime(["2024-01-01"] * 2)), "mcm_d", "daily")


@pytest.mark.parametrize("index", [
    pd.date_range("2024-01-01", periods=31, tz="UTC"),
    pd.date_range("2024-01-01 12:00", periods=31),
])
def test_daily_calendar_semantics_require_normalisation_upstream(index):
    with pytest.raises(ValidationError, match="calendar dates"):
        time_series("x", pd.Series(1, index=index), "mcm_d", "daily")


def test_daily_maintenance_derating_and_determinism(daily):
    derate = daily(20)
    derate["values"].iloc[0] = 50
    capacity = daily_maintenance_capacity(150, derate)
    assert capacity["daily"]["values"].iloc[0] == 100
    assert capacity["daily"]["values"].iloc[1] == 130
    assert capacity["monthly"]["values"].iloc[0] == pytest.approx((100 + 30 * 130) / 1000)
    assert capacity["daily"]["values"].le(150).all()
    pd.testing.assert_series_equal(capacity["monthly"]["values"], daily_maintenance_capacity(150, derate)["monthly"]["values"])


@pytest.mark.parametrize("value", [0, 150])
def test_zero_derate_and_full_outage(daily, value):
    capacity = daily_maintenance_capacity(150, daily(value))
    assert capacity["monthly"]["values"].iloc[0] == pytest.approx((150 - value) * 31 / 1000)


def test_missing_capacity_is_not_inferred(daily):
    with pytest.raises(ValidationError, match="Missing reference capacity"):
        daily_maintenance_capacity(None, daily(20))


def test_negative_maintenance_does_not_supply_missing_baseline(daily):
    with pytest.raises(ValidationError, match="Missing reference capacity"):
        daily_maintenance_capacity(None, daily(-1))


def test_signed_maintenance_increases_capacity_without_clipping(daily):
    maintenance = daily(-6)
    maintenance["values"].iloc[0] = 20
    original = maintenance["values"].copy()
    capacity = daily_maintenance_capacity(150, maintenance)
    assert capacity["daily"]["values"].iloc[0] == 130
    assert capacity["daily"]["values"].iloc[1] == 156
    assert capacity["monthly"]["values"].iloc[0] == pytest.approx((130 + 30 * 156) / 1000)
    pd.testing.assert_series_equal(maintenance["values"], original)


def test_outage_above_capacity_is_not_clipped(daily):
    with pytest.raises(ValidationError, match="exceeds reference"):
        daily_maintenance_capacity(150, daily(151))


@pytest.mark.parametrize("technical", [-1, float("nan"), True])
def test_invalid_technical_capacity(daily, technical):
    with pytest.raises(ValidationError):
        daily_maintenance_capacity(technical, daily(0))


def test_wrong_derate_units(monthly):
    with pytest.raises(ValidationError, match="daily mcm_d"):
        daily_maintenance_capacity(150, monthly("derate", [1]))


def test_configured_kollsnes_input_respects_missing_capacity(config_files, daily):
    model, _ = load_config(*config_files)
    with pytest.raises(ValidationError, match="KOLLSNES_INJECTION"):
        capacity_for_asset(model, "KOLLSNES_INJECTION", daily(20))
    with pytest.raises(ValidationError, match="declared asset"):
        capacity_for_asset(model, "KOLLSNES_INJECTION", daily(20, key="some_other_series"))


def test_conversion_rejects_wrong_units_and_negative_rates(monthly, daily):
    with pytest.raises(ValidationError, match="daily mcm_d"):
        mcm_d_to_monthly_bcm(monthly("x", [1]))
    with pytest.raises(ValidationError, match="Negative daily"):
        mcm_d_to_monthly_bcm(daily(-1))
