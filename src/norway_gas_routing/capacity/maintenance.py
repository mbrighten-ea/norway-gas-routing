"""Maintenance changes infrastructure capacity, never subtracts from routed flow."""

from ..data import time_series
from ..units import mcm_d_to_monthly_bcm, validate_daily_coverage
from ..validation import ValidationError, check_identifier, check_keys, nonnegative_number


def daily_maintenance_capacity(reference_capacity_mcm_d: float | None,
                               derate: dict, *, asset_name="infrastructure") -> dict:
    """Apply signed maintenance to a supplied baseline; never cap an uplift."""
    if derate["unit"] != "mcm_d" or derate["frequency"] != "daily":
        raise ValidationError("Maintenance derate must be daily mcm_d, not available capacity or a fraction")
    values = validate_daily_coverage(derate["values"])
    if reference_capacity_mcm_d is None:
        raise ValidationError(f"Missing reference capacity for {asset_name}; it remains null")
    reference = nonnegative_number(reference_capacity_mcm_d, "reference_capacity_mcm_d")
    available = reference - values
    if (available < 0).any():
        raise ValidationError(f"Maintenance exceeds reference capacity for {asset_name}; investigate without clipping")
    daily = time_series(derate["key"] + "_available_capacity", available, "mcm_d", "daily")
    return {"daily": daily, "monthly": mcm_d_to_monthly_bcm(daily)}


def capacity_for_asset(model: dict, asset_name: str, derate: dict) -> dict:
    """Use a config from load_config, which already checks maintenance semantics."""
    if asset_name not in model["assets"]:
        raise ValidationError(f"Unknown asset: {asset_name}")
    asset = model["assets"][asset_name]
    if not asset.get("active", True):
        raise ValidationError(f"Inactive asset: {asset_name}")
    if asset.get("maintenance_series") != derate["key"]:
        raise ValidationError(f"Maintenance does not match declared asset/series: {asset_name}")
    return daily_maintenance_capacity(asset["technical_capacity_mcm_d"], derate, asset_name=asset_name)


def validate_maintenance_config(model: dict, series):
    mapped_assets = set()
    for key, entry in model["maintenance_inputs"].items():
        check_identifier(key, "maintenance_inputs", uppercase=True)
        check_keys(entry, key, {"series", "asset", "unit", "semantics", "provisional"}, {"notes"})
        ref, asset = entry["series"], entry["asset"]
        if not isinstance(ref, str) or ref not in series.index:
            raise ValidationError(f"Unknown maintenance series for {key}")
        if not isinstance(asset, str) or asset not in model["assets"] or asset in mapped_assets:
            raise ValidationError(f"Invalid/duplicate maintenance asset for {key}")
        mapped_assets.add(asset)
        row = series.loc[ref]
        if (entry["unit"] != "mcm_d" or entry["semantics"] != "capacity_derate" or
            row["target_unit"] != "mcm_d" or row["raw_unit"] != "mcm_d" or row["source_frequency"] != "daily" or
            row["input_semantics"] != "capacity_derate" or row["asset"] != asset or
            model["assets"][asset].get("maintenance_series") != ref or type(entry["provisional"]) is not bool):
            raise ValidationError(f"Incompatible maintenance declaration for {key}")
    if mapped_assets != {key for key, asset in model["assets"].items() if asset.get("maintenance_series")}:
        raise ValidationError("Maintenance series lacks a declared maintenance input")
    for key, row in series.iterrows():
        if row["asset"] and row["asset"] not in model["assets"]:
            raise ValidationError(f"Unknown CSV asset reference for {key}: {row['asset']}")
