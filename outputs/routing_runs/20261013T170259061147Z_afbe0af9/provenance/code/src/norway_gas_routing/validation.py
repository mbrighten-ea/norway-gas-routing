"""Explicit failures and input diagnostics; no repairs or inferred values."""

import re
from math import isfinite
from numbers import Real


class ValidationError(ValueError):
    """An input violates the declared contract."""


def check_keys(value, name, required, optional=()):
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be a mapping")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        raise ValidationError(f"{name}: missing keys {sorted(missing)}; unknown keys {sorted(extra)}")


def check_identifier(value, name, uppercase=False):
    pattern = r"[A-Z][A-Z0-9_]*" if uppercase else r"[a-z][a-z0-9_]*"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValidationError(f"Invalid identifier at {name}: {value!r}")


def check_choice(value, choices, name):
    if not isinstance(value, str) or value not in choices:
        raise ValidationError(f"Invalid {name}: {value!r}")


def check_month(value, name):
    if value is not None and (not isinstance(value, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value)):
        raise ValidationError(f"{name} must be YYYY-MM or null")


def nonnegative_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{label} must be a finite number")
    if not isfinite(value) or value < 0:
        raise ValidationError(f"{label} must be finite and nonnegative")
    return float(value)


def validate_controls(model: dict):
    settings = model["model"]
    check_keys(settings, "model", {"frequency", "forecast_end", "markets", "solve_each_month_independently",
                                   "reference_price_market", "allow_unrouted_volume", "core_has_aggregate_capacity"})
    if settings["frequency"] != "monthly" or settings["forecast_end"] is None:
        raise ValidationError("Model requires monthly frequency and a forecast end month")
    check_month(settings["forecast_end"], "forecast_end")
    markets = settings["markets"]
    if not isinstance(markets, list):
        raise ValidationError("model.markets must be a list")
    for market in markets:
        check_identifier(market, "model.markets", uppercase=True)
    if len(markets) != 6 or set(markets) != {"UK", "GERMANY", "NETHERLANDS", "DENMARK", "BELGIUM", "FRANCE"}:
        raise ValidationError("Model requires the six distinct agreed markets")
    if settings["reference_price_market"] not in markets + [None]:
        raise ValidationError("Unknown reference_price_market")
    for key in ("solve_each_month_independently", "allow_unrouted_volume", "core_has_aggregate_capacity"):
        if type(settings[key]) is not bool:
            raise ValidationError(f"{key} must be a boolean")
    if settings["core_has_aggregate_capacity"]:
        raise ValidationError("CORE has no agreed aggregate capacity")
    check_keys(model["units"], "units", {"flow", "price", "bcm_to_mwh"})
    if model["units"]["flow"] != "bcm/month" or model["units"]["price"] != "EUR/MWh":
        raise ValidationError("Model units must be bcm/month and EUR/MWh")
    if model["units"]["bcm_to_mwh"] is not None:
        nonnegative_number(model["units"]["bcm_to_mwh"], "bcm_to_mwh")
    check_keys(model["solver"], "solver", {"unrouted_volume_penalty", "reconciliation_tolerance_bcm"})
    for key, value in model["solver"].items():
        if value is not None:
            nonnegative_number(value, f"solver.{key}")
    validate_calibration_controls(model["calibration"])


def validate_calibration_controls(calibration: dict):
    check_keys(calibration, "calibration", {"training_start", "training_end", "validation_start", "validation_end",
                                           "initial_global_flexible_fraction", "routing_share_seasonality", "note"})
    for prefix in ("training", "validation"):
        start, end = calibration[f"{prefix}_start"], calibration[f"{prefix}_end"]
        check_month(start, f"{prefix}_start")
        check_month(end, f"{prefix}_end")
        if (start is None) != (end is None) or (start is not None and start > end):
            raise ValidationError(f"Invalid {prefix} period")
    phi = calibration["initial_global_flexible_fraction"]
    if phi is not None and nonnegative_number(phi, "global_flexible_fraction") > 1:
        raise ValidationError("Global flexible fraction must lie in [0, 1]")
    if calibration["routing_share_seasonality"] != "static_initially":
        raise ValidationError("Unrecognised initial routing-share control")


def expression_references(expression) -> set[str]:
    """Check flat sums/differences of series names; never execute the expression."""
    # For example: exit_emden + exit_dornum - flow_nl_actual.
    name = r"[a-z][a-z0-9_]*"
    if not isinstance(expression, str) or not re.fullmatch(name + r"(?:\s*[+-]\s*" + name + r")*", expression.strip()):
        raise ValidationError(f"Unsupported expression: {expression}")
    return set(re.findall(name, expression))


def validate_transformations(model: dict, series):
    derived = model["derived_series"]
    known = set(series.index) | derived.keys()
    dependencies = {}
    expressions = list(derived.items())
    if not isinstance(model["reconciliation"], list):
        raise ValidationError("reconciliation must be a list")
    for rule in model["reconciliation"]:
        check_keys(rule, "reconciliation", {"lhs", "rhs", "severity"})
        check_choice(rule["severity"], {"error", "warning"}, "reconciliation.severity")
        expressions.extend([("reconciliation lhs", rule["lhs"]), ("reconciliation rhs", rule["rhs"])])
    for name, expression in expressions:
        refs = expression_references(expression)
        if refs - known:
            raise ValidationError(f"Unknown expression reference in {name}: {sorted(refs - known)}")
        for ref in refs.intersection(series.index):
            if series.at[ref, "model_role"] == "benchmark_only":
                raise ValidationError(f"Benchmark leakage in {name}: {ref}")
            if series.at[ref, "target_unit"] != "bcm":
                raise ValidationError(f"Incompatible flow units in {name}: {ref}")
        if name in derived:
            check_identifier(name, "derived_series")
            if name in series.index:
                raise ValidationError(f"Derived/raw series collision: {name}")
            dependencies[name] = refs.intersection(derived)
    # Resolve dependencies in order; no progress means the formulas contain a cycle.
    resolved = set()
    while len(resolved) < len(dependencies):
        ready = {key for key, refs in dependencies.items() if key not in resolved and refs <= resolved}
        if not ready:
            raise ValidationError("Cyclic derived-series dependencies")
        resolved.update(ready)
    for key, status in model["transformation_status"].items():
        if key not in derived:
            raise ValidationError(f"Unknown transformation status key: {key}")
        check_choice(status, {"accepted", "decision_required"}, f"{key}.status")
    validate_market_series(model, series, known)


def validate_market_series(model: dict, series, known: set):
    if set(model["markets"]) != set(model["model"]["markets"]):
        raise ValidationError("Market definitions differ from model.markets")
    for market, entry in model["markets"].items():
        check_keys(entry, market, {"price_series", "actual_series"}, {"actual_is_derived", "forecast_price_series"})
        price, actual = entry["price_series"], entry["actual_series"]
        if not isinstance(price, str) or price not in series.index or series.at[price, "category"] != "price":
            raise ValidationError(f"Invalid price series for {market}")
        forecast = entry.get('forecast_price_series')
        if forecast is not None:
            if (not isinstance(forecast, str) or forecast not in series.index
                    or series.at[forecast, 'category'] != 'price'
                    or series.at[forecast, 'lifecycle'] not in {'forecast', 'actual_and_forecast', 'forecast_or_actual'}):
                raise ValidationError(f'Invalid forecast price series for {market}')
            if forecast == price:
                raise ValidationError(f'Historical and forecast prices must be separate for {market}')
        if not isinstance(actual, str) or actual not in known:
            raise ValidationError(f"Unknown actual series for {market}")
        if actual in series.index and series.at[actual, "model_role"] == "benchmark_only":
            raise ValidationError(f"Benchmark calibration leakage for {market}")
        is_derived = actual in model["derived_series"]
        declared = entry.get("actual_is_derived", is_derived)
        if type(declared) is not bool or declared != is_derived or (market == "GERMANY" and not declared):
            raise ValidationError(f"Incorrect actual_is_derived for {market}")
