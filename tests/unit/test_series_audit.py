import numpy as np
import pandas as pd
import pytest

from norway_gas_routing.data import derive_de_nl, time_series
from norway_gas_routing.series_audit import (compare_series, forecast_coverage,
                                            observed_frequency, overall_status,
                                            profile, st_fergus_overlap)


@pytest.mark.parametrize("freq,expected", [("h", "hourly"), ("D", "daily"), ("MS", "monthly"), ("15min", "subhourly")])
def test_actual_frequency(freq, expected):
    assert observed_frequency(pd.date_range("2024-01-01", periods=6, freq=freq)) == expected


def test_missing_days_duplicates_negative_maintenance_and_nonfinite():
    index = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-04", "2024-01-05"])
    result = profile(pd.Series([0, -6, 1, np.nan, np.inf], index=index))
    assert result["duplicate_count"] == 1
    assert result["negative_count"] == 1
    assert result["zero_count"] == 1
    assert result["missing_count"] == 1
    assert result["nonfinite_count"] == 1
    assert result["missing_periods"] == 1
    assert result["missing_pct"] == 20
    assert result["last_date"].startswith("2024-01-02")


def test_internal_gap_measured_from_valid_observations():
    values = pd.Series([1, np.nan, 2, 3], index=pd.date_range("2024-01-01", periods=4))
    result = profile(values)
    assert result["largest_internal_gap"] == "2 days 00:00:00"
    assert result["grid_missing_pct"] == 25


def test_mixed_intraday_sampling_is_not_an_hourly_missing_data_grid():
    dates = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 01:10", "2024-01-01 02:10", "2024-01-01 03:10"])
    result = profile(pd.Series(range(5), index=dates))
    assert result["observed_frequency"] == "mixed_intraday"
    assert result["missing_periods"] == 0


def test_forecast_cannot_be_confirmed_from_last_date_alone():
    values = pd.Series([1, 2], index=pd.to_datetime(["2025-10-01", "2025-12-01"]))
    assert forecast_coverage(values, "2025-10-01", "2025-12-31", "monthly") == "false"
    assert forecast_coverage(values, "", "2025-12-31", "monthly") == "UNRESOLVED"


def test_monthly_coverage_includes_leap_day():
    values = pd.Series(0, index=pd.date_range("2024-02-01", "2024-02-29"))
    assert forecast_coverage(values, "2024-02-01", "2024-02-29", "daily") == "true"
    assert forecast_coverage(values.iloc[:-1], "2024-02-01", "2024-02-29", "daily") == "false"


def test_st_fergus_shifted_timestamps_do_not_prove_disjoint_definitions():
    left = pd.Series([2, 3, 4], index=pd.date_range("2020-10-15", periods=3))
    right = pd.Series([3, 4, 5], index=left.index + pd.DateOffset(hours=1))
    result = st_fergus_overlap(left, right)
    assert result["overlap_count"] == 0
    assert result["calendar_day_sample_means_exploratory"]["overlap_count"] == 3
    assert result["treatment"].startswith("REVIEW")
    assert st_fergus_overlap(left, right.set_axis(right.index + pd.DateOffset(days=10)))["relationship"] == "consecutive_coverage"


def test_duplicates_block_cross_series_alignment():
    values = pd.Series([1, 2], index=pd.to_datetime(["2024-01-01", "2024-01-01"]))
    assert compare_series(values, values)["status"] == "REVIEW"


def test_status_requires_all_validations():
    assert overall_status(False, ["PASS"] * 4) == "TODO"
    assert overall_status(True, ["PASS"] * 4) == "CONFIRMED"
    assert overall_status(True, ["PASS", "REVIEW"]) == "REVIEW"


def test_de_nl_preserves_approved_identity():
    index = pd.period_range("2024-01", periods=2, freq="M")
    def monthly(key, values):
        return time_series(key, pd.Series(values, index=index), "bcm", "monthly")
    derived = derive_de_nl(monthly("Emden", [2, 3]), monthly("Dornum", [1, 1]), monthly("NL", [1, 2]))
    assert derived.DE.tolist() == [2, 2]
    assert derived.DE_NL_total.tolist() == [3, 4]
