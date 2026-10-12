import csv
import json

import pytest

from norway_gas_routing.config import load_config, load_series
from norway_gas_routing.diagnostics import configuration_report
from norway_gas_routing.network import reachable_markets
from norway_gas_routing.validation import ValidationError


def test_repository_config_is_loadable_and_explicit(config_files):
    model, series = load_config(*config_files)
    assert len(model["markets"]) == 6
    assert len(model["sources"]) == 8
    assert reachable_markets(model, "UK_DIRECT") == ("UK",)
    assert reachable_markets(model, "DE_DIRECT") == ()
    assert "DENMARK" in reachable_markets(model, "KARSTO")
    assert not model["model"]["core_has_aggregate_capacity"]
    assert model["junctions"]["CORE"]["aggregate_capacity"] is None
    assert all(asset["technical_capacity_mcm_d"] is None for asset in model["assets"].values())
    assert model["calibration"]["initial_global_flexible_fraction"] is None
    maintenance = model["maintenance_inputs"]["KOLLSNES_PROCESSING"]
    row = series.loc[maintenance["series"]]
    assert maintenance["provisional"] and maintenance["semantics"] == "capacity_derate"
    assert row["sid"].endswith(r"daily_NO\NO_maintenance_Kollsnes")
    assert (row["target_unit"], row["source_frequency"], row["display_source"], row["economic_property"]) == (
        "mcm_d", "daily", "Gassco", "outages")
    assert row["history_required"] is None and row["forecast_required"] is True
    upstream = series[series["sid"].str.contains("upstream_maintenance")]
    assert (upstream["model_role"] == "reference_only").all()
    assert not set(upstream.index) & {entry["series"] for entry in model["maintenance_inputs"].values()}


def test_dashboard_prices_are_separate_from_ea_forecasts(config_files):
    model, series = load_config(*config_files)
    for market in ['UK', 'GERMANY', 'NETHERLANDS', 'BELGIUM', 'FRANCE']:
        entry = model['markets'][market]
        actual = series.loc[entry['price_series']]
        forecast = series.loc[entry['forecast_price_series']]
        assert actual.sid.startswith('teams\\external_data\\reuters\\ng_cash_price\\')
        assert actual.lifecycle == 'actual' and actual.status == 'REVIEW'
        assert forecast.lifecycle == 'forecast' and forecast.price_type == 'forecast'
        assert actual.name != forecast.name
    uk = series.loc[model['markets']['UK']['price_series']]
    assert uk.raw_unit == 'p_therm' and uk.target_unit == 'EUR/MWh'
    assert not series.loc[model['markets']['DENMARK']['price_series'], 'sid']


@pytest.mark.parametrize('forecast', ['unknown_price', 'the_day_ahead', 'troll_prod'])
def test_invalid_forecast_price_references_are_rejected(edit_model, forecast):
    paths = edit_model(lambda model: model['markets']['GERMANY'].update(forecast_price_series=forecast))
    with pytest.raises(ValidationError, match='forecast price'):
        load_config(*paths)


@pytest.mark.parametrize("change", [
    lambda c: c.pop("assets"),
    lambda c: c.update(unknown_section={}),
    lambda c: c["model"].update(frequency="daily"),
    lambda c: c["model"].update(forecast_end="2030-13"),
    lambda c: c["model"].update(allow_unrouted_volume="true"),
    lambda c: c["model"].update(core_has_aggregate_capacity=True),
    lambda c: c["junctions"]["CORE"].update(aggregate_capacity=10),
    lambda c: c["model"]["markets"].append("UK"),
    lambda c: c["assets"]["NORPIPE"].update(technical_capacity_mcm_d=-1),
    lambda c: c["assets"]["NORPIPE"].update(technical_capacity_mcm_d=True),
    lambda c: c["assets"]["NORPIPE"].update(technical_capacity_mcm_d=float("nan")),
    lambda c: c["arcs"][0].update(id="bad-id"),
    lambda c: c["arcs"].append(c["arcs"][0].copy()),
    lambda c: c["arcs"][0].update(to="NONEXISTENT"),
    lambda c: c["arcs"][0].update(to=[]),
    lambda c: c["arcs"][0].update(asset="NONEXISTENT"),
    lambda c: c["arcs"][0].update(to="NYHAMNA"),
    lambda c: c["arcs"][0].update(to="DE_DIRECT"),
    lambda c: c["sources"]["KARSTO"]["series"].append("troll_prod"),
    lambda c: c["sources"]["KARSTO"]["series"].append("norway_prod"),
    lambda c: c["sources"]["OTHER_RESIDUAL"].update(active=True),
    lambda c: c["sources"]["DE_DIRECT"].update(active=True),
    lambda c: c["junctions"].update(UK={"description": "duplicate"}),
    lambda c: c["sources"]["KOLLSNES"].update(series=["missing_production"]),
    lambda c: c["derived_series"].update(flow_de_actual="de_flow_qa"),
    lambda c: c["derived_series"].update(flow_de_actual="unknown_flow"),
    lambda c: c["derived_series"].update(flow_de_actual="flow_de_actual"),
    lambda c: c["derived_series"].update(flow_de_actual="emden_flow * 2"),
    lambda c: c["derived_series"].update(flow_de_actual="__import__('os')"),
    lambda c: c["derived_series"].update(flow_de_actual="the_forecast + dornum_flow"),
    lambda c: c["markets"]["GERMANY"].update(actual_series="de_flow_qa"),
    lambda c: c["markets"]["GERMANY"].update(actual_series=[]),
    lambda c: c["markets"]["GERMANY"].update(actual_is_derived=False),
    lambda c: c["maintenance_inputs"]["KOLLSNES_PROCESSING"].update(semantics="available_capacity"),
    lambda c: c["maintenance_inputs"]["KOLLSNES_PROCESSING"].update(unit="bcm"),
    lambda c: c["maintenance_inputs"]["KOLLSNES_PROCESSING"].update(asset="NOT_AN_ASSET"),
    lambda c: c["assets"]["KOLLSNES_INJECTION"].update(availability_series="nyhamna_avail_cap"),
    lambda c: c["calibration"].update(initial_global_flexible_fraction=1.1),
    lambda c: c["solver"].update(reconciliation_tolerance_bcm=-0.1),
    lambda c: c["calibration"].update(training_start="2024-02", training_end="2024-01"),
    lambda c: c.update(sources=[]),
])
def test_schema_failures(edit_model, change):
    with pytest.raises(ValidationError):
        load_config(*edit_model(change))


def test_duplicate_yaml_keys(config_files):
    model, series = config_files
    with model.open("a") as stream:
        stream.write("\nmodel: {}\n")
    with pytest.raises(ValidationError, match="duplicate YAML"):
        load_config(model, series)


def test_duplicate_csv_headers(config_files):
    _, series = config_files
    text = series.read_text(encoding="utf-8")
    series.write_text(text.replace("key,sid,", "key,key,", 1), encoding="utf-8")
    with pytest.raises(ValidationError, match="duplicate CSV columns"):
        load_series(series)


@pytest.mark.parametrize("failure", ["duplicate", "invalid_id", "missing_column", "bad_unit", "missing_sid", "extra_field", "bad_boolean"])
def test_series_schema(config_files, failure):
    _, path = config_files
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    if failure == "duplicate":
        rows.append(rows[0].copy())
    elif failure == "invalid_id":
        rows[0]["key"] = "invalid-key"
    elif failure == "missing_column":
        fields.remove("sid")
        for row in rows:
            row.pop("sid")
    elif failure == "bad_unit":
        rows[0]["target_unit"] = "unrecognised"
    elif failure == "missing_sid":
        rows[0]["sid"] = ""
        rows[0]["status"] = "CONFIRMED"
    elif failure == "bad_boolean":
        rows[0]["history_required"] = "yes"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        if failure == "extra_field":
            stream.write(",".join(["extra"] * (len(fields) + 1)) + "\n")
    with pytest.raises(ValidationError):
        load_series(path)


def test_deterministic_diagnostics_and_explicit_missing_inputs(config_files):
    first = configuration_report(*load_config(*config_files))
    second = configuration_report(*load_config(*config_files))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["schema_valid"] and not first["production_ready"]
    issues = {(issue["code"], issue["location"]) for issue in first["issues"]}
    assert ("missing_technical_capacity", "assets.KOLLSNES_INJECTION") in issues
    assert ("decision_required", "derived_series.exit_st_fergus") in issues
    assert ("missing_sid", "series.denmark_price") in issues
