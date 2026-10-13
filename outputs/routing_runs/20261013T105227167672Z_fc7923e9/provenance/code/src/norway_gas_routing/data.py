"""Monthly observations and the agreed physical destination calculations."""

import pandas as pd

from .validation import ValidationError, nonnegative_number
from .evaluation import read_parquet


def validate_values(values: pd.Series, frequency: str):
    if not isinstance(values, pd.Series) or values.empty:
        raise ValidationError("Time series must be a nonempty pandas Series")
    if values.index.has_duplicates:
        raise ValidationError("Duplicate observation dates")
    if values.index.hasnans:
        raise ValidationError("Missing observation dates")
    if frequency == "monthly":
        if not isinstance(values.index, pd.PeriodIndex) or values.index.freqstr != "M":
            raise ValidationError("Monthly observations require a monthly PeriodIndex")
    elif frequency == "daily":
        if (not isinstance(values.index, pd.DatetimeIndex) or values.index.tz is not None or
            not values.index.equals(values.index.normalize())):
            raise ValidationError("Daily observations require timezone-free midnight calendar dates")
    else:
        raise ValidationError(f"Unsupported frequency: {frequency}")
    if values.isna().any():
        raise ValidationError("Missing observation values")
    if (not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values) or
        pd.api.types.is_complex_dtype(values)):
        raise ValidationError("Observations must be real numeric values")
    if values.isin([float("inf"), -float("inf")]).any():
        raise ValidationError("Observations must be finite")


def time_series(key: str, values: pd.Series, unit: str, frequency: str) -> dict:
    """Make a plain dictionary; keep units explicit rather than infer them."""
    validate_values(values, frequency)
    if unit not in {"bcm", "mcm_d"}:
        raise ValidationError(f"Unsupported flow/capacity unit: {unit}")
    return {"key": key, "values": values.astype(float).sort_index().copy(),
            "unit": unit, "frequency": frequency}


def align_monthly(components: dict) -> pd.DataFrame:
    """Check units and matching months before adding physical observations."""
    if not components:
        raise ValidationError("No components supplied")
    values = {}
    index = None
    for name, component in components.items():
        if component is None:
            raise ValidationError(f"Missing component: {name}")
        if not isinstance(component, dict):
            raise ValidationError(f"{name} must be a series dictionary")
        if component["unit"] != "bcm" or component["frequency"] != "monthly":
            raise ValidationError(f"{name}: expected monthly bcm")
        validate_values(component["values"], "monthly")
        ordered = component["values"].sort_index()
        if (ordered < 0).any():
            raise ValidationError(f"Negative physical flow component: {name}")
        if index is not None and not ordered.index.equals(index):
            raise ValidationError(f"Missing or mismatched months in component: {name}")
        index = ordered.index
        values[name] = ordered
    return pd.DataFrame(values, index=index)


def derive_de_nl(emden: dict, dornum: dict, netherlands: dict) -> pd.DataFrame:
    """Germany is residual Norwegian flow after subtracting Dutch TSO receipts."""
    inputs = align_monthly({"Emden": emden, "Dornum": dornum, "NL": netherlands})
    result = pd.DataFrame(index=inputs.index)
    result["DE_NL_total"] = inputs["Emden"] + inputs["Dornum"]
    result["NL"] = inputs["NL"]
    result["DE"] = result["DE_NL_total"] - result["NL"]
    if (result["DE"] < 0).any():
        negative = result.loc[result["DE"] < 0].to_dict(orient="index")
        raise ValidationError(f"Negative German residual; investigate units/coverage/semantics: {negative}")
    return result


def reconcile_de_nl(derived: pd.DataFrame, emden: dict, dornum: dict,
                    netherlands: dict, *, tolerance_bcm: float) -> pd.DataFrame:
    expected = derive_de_nl(emden, dornum, netherlands)
    tolerance = nonnegative_number(tolerance_bcm, "tolerance_bcm")
    if not isinstance(derived, pd.DataFrame) or set(derived.columns) != set(expected.columns):
        raise ValidationError("DE/NL reconciliation needs DE_NL_total, NL and DE columns")
    actual = derived.sort_index()
    for column in expected.columns:
        validate_values(actual[column], "monthly")
        if (actual[column] < 0).any():
            raise ValidationError(f"Negative physical flow component: {column}")
    if not actual.index.equals(expected.index):
        raise ValidationError("DE/NL reconciliation months differ")
    residuals = actual[expected.columns].astype(float) - expected
    if (residuals.abs() > tolerance).any().any():
        raise ValidationError(f"DE/NL reconciliation failure: {residuals.to_dict()}")
    return residuals


def derive_other_destinations(*, easington: dict, segal: dict, st_fergus: dict,
                              nybro: dict, zeebrugge: dict, dunkerque: dict) -> pd.DataFrame:
    """St Fergus must already be resolved; never add the two raw aliases here."""
    values = align_monthly({"Easington": easington, "SEGAL": segal, "St Fergus": st_fergus,
                            "Nybro": nybro, "Zeebrugge": zeebrugge, "Dunkerque": dunkerque})
    return pd.DataFrame({"UK": values["Easington"] + values["SEGAL"] + values["St Fergus"],
                         "DENMARK": values["Nybro"], "BELGIUM": values["Zeebrugge"],
                         "FRANCE": values["Dunkerque"]}, index=values.index)


def reconcile_destinations(destinations: dict, physical_exits: dict,
                           *, tolerance_bcm: float) -> pd.Series:
    destination_names = {"UK", "GERMANY", "NETHERLANDS", "DENMARK", "BELGIUM", "FRANCE"}
    exit_names = {"Emden", "Dornum", "Easington", "SEGAL", "St Fergus", "Nybro", "Zeebrugge", "Dunkerque"}
    if set(destinations) != destination_names or set(physical_exits) != exit_names:
        raise ValidationError("Reconciliation needs all six destinations and eight distinct physical exits")
    markets = align_monthly(destinations)
    exits = align_monthly(physical_exits)
    if not markets.index.equals(exits.index):
        raise ValidationError("Destination and physical exit months differ")
    tolerance = nonnegative_number(tolerance_bcm, "tolerance_bcm")
    residual = markets.sum(axis=1) - exits.sum(axis=1)
    residual.name = "destination_minus_physical_bcm"
    if (residual.abs() > tolerance).any():
        raise ValidationError(f"Destination reconciliation failure: {residual.to_dict()}")
    return residual


def read_parquet_series(path: str, *, key: str, unit: str, frequency: str) -> dict:
    """Read the normalised one-column format without provider-specific conversions."""
    import pyarrow.parquet as pq
    if 'value' not in pq.read_schema(path).names:
        raise ValidationError("Parquet series must contain exactly one 'value' column")
    frame = read_parquet(path)
    if list(frame.columns) != ["value"]:
        raise ValidationError("Parquet series must contain exactly one 'value' column")
    return time_series(key, frame["value"], unit, frequency)
