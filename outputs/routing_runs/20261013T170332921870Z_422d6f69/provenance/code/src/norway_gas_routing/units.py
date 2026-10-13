"""Central calendar-based conversion from daily mcm/d to monthly bcm."""

import pandas as pd

from .data import time_series, validate_values
from .validation import ValidationError


MCM_PER_BCM = 1000.0


def validate_daily_coverage(values: pd.Series) -> pd.Series:
    validate_values(values, "daily")
    ordered = values.sort_index()
    months = ordered.index.to_period("M")
    expected = pd.date_range(months.min().start_time, months.max().end_time.normalize(), freq="D")
    if not ordered.index.equals(expected):
        missing = expected.difference(ordered.index)
        raise ValidationError(f"Daily capacity/flow requires complete calendar months; missing dates: {list(missing)}")
    return ordered


def mcm_d_to_monthly_bcm(daily: dict) -> dict:
    if daily["unit"] != "mcm_d" or daily["frequency"] != "daily":
        raise ValidationError("Conversion requires daily mcm_d")
    values = validate_daily_coverage(daily["values"])
    if (values < 0).any():
        raise ValidationError("Negative daily flow/capacity requires investigation")
    monthly = values.groupby(values.index.to_period("M")).sum() / MCM_PER_BCM
    return time_series(daily["key"], monthly, "bcm", "monthly")
