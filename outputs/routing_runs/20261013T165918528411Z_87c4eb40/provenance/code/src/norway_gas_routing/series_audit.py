"""Small deterministic checks on unmodified provider observations."""

import numpy as np
import pandas as pd
from .evaluation import check_dates, request_bounds, VALIDATION_END


def observed_frequency(index):
    dates = pd.DatetimeIndex(index).dropna().unique().sort_values()
    if len(dates) < 3:
        return "insufficient"
    if dates.to_period("M").is_unique and len(set(dates.day)) == 1 and len(set(dates.time)) == 1:
        return "monthly"
    deltas = dates.to_series().diff().dropna()
    seconds = deltas.dt.total_seconds()
    step = seconds.mode().iloc[0]
    if (seconds < step).any() and (seconds < 86400).any():
        return "mixed_intraday"
    if step == 86400 and (dates == dates.normalize()).all():
        return "daily"
    if step == 3600:
        return "hourly"
    if step < 3600:
        return "subhourly"
    return "irregular"


def expected_index(index, frequency):
    dates = pd.DatetimeIndex(index).dropna().unique().sort_values()
    if len(dates) == 0:
        return dates
    if frequency == "monthly":
        return pd.period_range(dates[0], dates[-1], freq="M")
    if frequency in {"daily", "hourly"}:
        return pd.date_range(dates[0], dates[-1], freq={"daily": "D", "hourly": "h"}[frequency])
    return dates


def profile(values):
    check_dates(values.index, 'analysis')
    numeric = pd.to_numeric(values, errors="coerce")
    finite = numeric.where(np.isfinite(numeric))
    valid = finite.dropna().sort_index()
    frequency = observed_frequency(values.index)
    dates = pd.DatetimeIndex(values.index)
    grid = expected_index(dates, frequency)
    present = dates.dropna().unique()
    valid_dates = pd.DatetimeIndex(valid.index).dropna().unique()
    if frequency == "monthly":
        present = present.to_period("M")
        valid_dates = valid_dates.to_period("M")
    absent = len(grid.difference(present))
    missing_grid = len(grid.difference(valid_dates))
    spacing = pd.Series(pd.DatetimeIndex(valid.index).unique().sort_values()).diff().dropna()
    jumps = valid.diff().abs()
    result = {
        "observed_frequency": frequency, "n_obs": len(values), "count": len(valid),
        "missing_count": int(numeric.isna().sum()), "nonfinite_count": int((numeric.notna() & ~np.isfinite(numeric)).sum()),
        "missing_pct": float(numeric.isna().mean() * 100) if len(values) else 100.0,
        "missing_periods": absent, "expected_periods": len(grid),
        "grid_missing_pct": 100 * missing_grid / len(grid) if len(grid) else 100.0,
        "duplicate_count": int(dates.duplicated().sum()), "missing_timestamp_count": int(dates.isna().sum()),
        "first_date": str(valid.index.min()) if len(valid) else "",
        "last_date": str(valid.index.max()) if len(valid) else "",
        "largest_internal_gap": str(spacing.max()) if len(spacing) else "",
        "dominant_step": str(spacing.mode().iloc[0]) if len(spacing) else "",
        "dominant_step_pct": float((spacing == spacing.mode().iloc[0]).mean() * 100) if len(spacing) else 0,
        "negative_count": int((valid < 0).sum()), "zero_count": int((valid == 0).sum()),
        "min": valid.min(), "max": valid.max(), "mean": valid.mean(), "median": valid.median(),
        "min_date": str(valid.idxmin()) if len(valid) else "", "max_date": str(valid.idxmax()) if len(valid) else "",
        "largest_absolute_jump": jumps.max(), "largest_jump_date": str(jumps.idxmax()) if jumps.notna().any() else "",
    }
    for percentile in [1, 5, 25, 75, 95, 99]:
        result[f"p{percentile:02d}"] = valid.quantile(percentile / 100)
    return result


def forecast_coverage(values, start, end, frequency):
    check_dates(values.index, 'analysis')
    request_bounds('MIN', end)
    if start:
        if pd.Timestamp(start).to_period('M') > VALIDATION_END:
            return 'WITHHELD_BY_POLICY'
        request_bounds(start, end)
    valid = pd.to_numeric(values, errors="coerce")
    valid = valid.where(np.isfinite(valid)).dropna()
    if start and (valid.empty or pd.Timestamp(valid.index.max()).to_period("M") < pd.Timestamp(end).to_period("M")):
        return "false"
    if frequency not in {"monthly", "daily"} or not start:
        return "UNRESOLVED"
    dates = pd.DatetimeIndex(values.index)
    if frequency == "monthly":
        needed = pd.period_range(pd.Timestamp(start), pd.Timestamp(end), freq="M")
        have = pd.Series(values.to_numpy(), index=dates.to_period("M"))
    else:
        needed = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq="D")
        have = values.copy()
    if have.index.has_duplicates:
        return "false"
    supplied = pd.to_numeric(have.reindex(needed), errors="coerce")
    return "true" if np.isfinite(supplied).all() else "false"


def compare_series(left, right):
    """Compare only shared finite observations; report excluded coverage explicitly."""
    check_dates(left.index, 'analysis')
    check_dates(right.index, 'analysis')
    if left.index.has_duplicates or right.index.has_duplicates:
        return {"status": "REVIEW", "issue": "duplicate timestamps prevent unambiguous alignment"}
    pair = pd.concat([left.rename("left"), right.rename("right")], axis=1)
    finite = pair.replace([np.inf, -np.inf], np.nan).dropna()
    residual = finite["left"] - finite["right"]
    return {"overlap_count": len(finite), "left_only_count": int((pair.left.notna() & pair.right.isna()).sum()),
            "right_only_count": int((pair.right.notna() & pair.left.isna()).sum()),
            "exact_equal_count": int((residual == 0).sum()), "min_residual": residual.min(),
            "max_residual": residual.max(), "mean_residual": residual.mean(),
            "max_absolute_residual": residual.abs().max(), "first_overlap": str(finite.index.min()),
            "last_overlap": str(finite.index.max())}


def st_fergus_overlap(left, right):
    result = compare_series(left, right)
    if result.get("status") == "REVIEW":
        return result
    if result["overlap_count"]:
        result["relationship"] = "overlapping_equal" if result["exact_equal_count"] == result["overlap_count"] else "overlapping_different"
    elif left.index.max() < right.index.min() or right.index.max() < left.index.min():
        result["relationship"] = "consecutive_coverage"
    else:
        result["relationship"] = "interleaved_nonoverlap"
    # Different intraday timestamp conventions can hide same-day overlap.
    # These are exploratory sample means, not approved daily gas volumes.
    left_days = left.groupby(pd.DatetimeIndex(left.index).normalize()).mean()
    right_days = right.groupby(pd.DatetimeIndex(right.index).normalize()).mean()
    result["calendar_day_sample_means_exploratory"] = compare_series(left_days, right_days)
    # Coverage/value agreement cannot by itself prove physical definitions.
    result["treatment"] = "REVIEW: physical definitions and gas-day semantics require confirmation"
    return result


def overall_status(retrieval_ok, checks):
    if not retrieval_ok:
        return "TODO"
    return "CONFIRMED" if all(check == "PASS" for check in checks) else "REVIEW"
