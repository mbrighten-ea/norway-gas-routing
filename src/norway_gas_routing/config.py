"""Load the two canonical files as a YAML dictionary and a metadata DataFrame."""

import csv
import keyword
from pathlib import Path

import pandas as pd
import yaml

from .capacity.maintenance import validate_maintenance_config
from .network import validate_network
from .validation import ValidationError, check_choice, check_identifier, check_keys, validate_controls, validate_transformations


# SafeLoader normally overwrites duplicate keys, hiding configuration errors.
class UniqueKeyLoader(yaml.SafeLoader):
    pass


def unique_yaml_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValidationError(f"Invalid or duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_yaml_mapping)


def load_series(path: str | Path) -> pd.DataFrame:
    required = {"key", "sid", "description", "category", "target_unit", "source_frequency",
                "lifecycle", "model_role", "required_level", "status", "notes"}
    optional = {"source_system", "query_or_transform_hint", "history_required", "forecast_required",
                "raw_unit", "input_semantics", "asset", "display_source", "economic_property",
                "custom_description", "country", "country_iso", "balance_item", "data_item",
                "asset_type", "market_area", "price_type"}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or required - set(headers) or set(headers) - required - optional:
            raise ValidationError("Invalid, missing or duplicate CSV columns")
        rows = list(reader)
    if not rows:
        raise ValidationError("Series registry is empty")
    seen = set()
    for line, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValidationError(f"CSV row {line} has the wrong number of fields")
        key = row["key"]
        check_identifier(key, f"CSV row {line}")
        if keyword.iskeyword(key):
            raise ValidationError(f"Reserved Python keyword: {key}")
        if key in seen:
            raise ValidationError(f"Duplicate series identifier: {key}")
        seen.add(key)
        if 'custom_description' in headers and not row['custom_description'].strip():
            raise ValidationError(f"Missing custom_description for {key}")
        if any(not row[column].strip() for column in required - {"sid", "notes"}):
            raise ValidationError(f"Missing required metadata for {key}")
        # Legacy labels remain loadable while an audited registry is being
        # applied; they do not imply live observations have been validated.
        check_choice(row["status"], {"CONFIRMED", "TODO", "REVIEW", "KNOWN", "PROVISIONAL"}, f"{key}.status")
        if row["status"] in {"CONFIRMED", "KNOWN"} and not row["sid"].strip():
            raise ValidationError(f"{row['status']} series has no SID: {key}")
        check_choice(row["required_level"], {"required", "recommended", "conditional", "optional"}, f"{key}.required_level")
        check_choice(row["target_unit"], {"bcm", "mcm_d", "EUR/MWh", "days", "fraction_or_capacity"}, f"{key}.target_unit")
        check_choice(row["source_frequency"], {"monthly", "daily", "intraday", "daily_to_monthly", "daily_or_monthly", "daily_preferred"}, f"{key}.frequency")
        check_choice(row["lifecycle"], {"actual", "forecast", "forecast_or_actual", "actual_and_forecast", "actual_and_planned"}, f"{key}.lifecycle")
        for column in optional:
            row.setdefault(column, "")
        for column in ("history_required", "forecast_required"):
            check_choice(row[column], {"true", "false", ""}, f"{key}.{column}")
            row[column] = {"true": True, "false": False, "": None}[row[column]]
    return pd.DataFrame(rows).set_index("key")


def load_config(model_path: str | Path, series_path: str | Path) -> tuple[dict, pd.DataFrame]:
    try:
        series = load_series(series_path)
        model = yaml.load(Path(model_path).read_text(encoding="utf-8-sig"), Loader=UniqueKeyLoader)
    except (OSError, yaml.YAMLError, csv.Error) as exc:
        raise ValidationError(f"Cannot read configuration: {exc}") from exc
    sections = {"model", "units", "sources", "junctions", "assets", "arcs", "markets", "derived_series",
                "reconciliation", "solver", "calibration", "scope_notes", "maintenance_inputs", "transformation_status"}
    check_keys(model, "model.yaml", sections, {"routing"})
    if "routing" in model and not isinstance(model["routing"], dict):
        raise ValidationError("routing must be a mapping")
    for section in sections - {"arcs", "reconciliation"}:
        if not isinstance(model[section], dict):
            raise ValidationError(f"{section} must be a mapping")
    validate_controls(model)
    validate_network(model, series)
    validate_transformations(model, series)
    validate_maintenance_config(model, series)
    return model, series
