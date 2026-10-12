import pandas as pd
import pytest

from norway_gas_routing.data import (
    time_series, derive_de_nl, derive_other_destinations, read_parquet_series,
    reconcile_de_nl, reconcile_destinations,
)
from norway_gas_routing.validation import ValidationError


def test_de_nl_identities_and_determinism(monthly):
    emden, dornum, nl = [monthly(key, values) for key, values in
                        (("Emden", [2, 3]), ("Dornum", [4, 5]), ("NL", [1, 2]))]
    expected = pd.DataFrame({"DE_NL_total": [6., 8.], "NL": [1., 2.], "DE": [5., 6.]}, index=emden["values"].index)
    pd.testing.assert_frame_equal(derive_de_nl(emden, dornum, nl), expected)
    pd.testing.assert_frame_equal(derive_de_nl(emden, dornum, nl), derive_de_nl(emden, dornum, nl))
    assert reconcile_de_nl(expected, emden, dornum, nl, tolerance_bcm=0).eq(0).all().all()


@pytest.mark.parametrize("missing", [0, 1, 2])
def test_missing_de_nl_components(monthly, missing):
    components = [monthly(key, [1]) for key in ("Emden", "Dornum", "NL")]
    components[missing] = None
    with pytest.raises(ValidationError, match="Missing component"):
        derive_de_nl(*components)


def test_de_nl_incompatible_units(monthly):
    with pytest.raises(ValidationError, match="expected monthly bcm"):
        derive_de_nl(monthly("Emden", [1], "mcm_d"), monthly("Dornum", [1]), monthly("NL", [1]))


@pytest.mark.parametrize("nl", [3.0, 2.00000001])
def test_negative_german_residual_is_flagged_without_clipping(monthly, nl):
    with pytest.raises(ValidationError, match="Negative German residual"):
        derive_de_nl(monthly("Emden", [1]), monthly("Dornum", [1]), monthly("NL", [nl]))


def test_zero_german_residual_allowed(monthly):
    assert derive_de_nl(monthly("Emden", [1]), monthly("Dornum", [1]), monthly("NL", [2]))["DE"].iloc[0] == 0


def test_missing_months_not_silently_aligned(monthly):
    with pytest.raises(ValidationError, match="months"):
        derive_de_nl(monthly("Emden", [1, 1]), monthly("Dornum", [1]), monthly("NL", [1, 1]))


@pytest.mark.parametrize("column", ["DE_NL_total", "DE", "NL"])
def test_de_nl_reconciliation_detects_each_changed_target(monthly, column):
    emden, dornum, nl = [monthly(key, [1]) for key in ("Emden", "Dornum", "NL")]
    frame = derive_de_nl(emden, dornum, nl)
    frame[column] += .2
    with pytest.raises(ValidationError, match="reconciliation failure"):
        reconcile_de_nl(frame, emden, dornum, nl, tolerance_bcm=.01)


def test_reconciliation_missing_column_and_tolerance(monthly):
    components = [monthly(key, [1]) for key in ("Emden", "Dornum", "NL")]
    frame = derive_de_nl(*components)
    with pytest.raises(ValidationError):
        reconcile_de_nl(frame.drop(columns="DE"), *components, tolerance_bcm=0)
    with pytest.raises(ValidationError):
        reconcile_de_nl(frame, *components, tolerance_bcm=-1)


def test_other_destinations_and_total_reconciliation(monthly):
    exits = {key: monthly(key, [value, value * 2]) for value, key in enumerate(
        ("Emden", "Dornum", "Easington", "SEGAL", "St Fergus", "Nybro", "Zeebrugge", "Dunkerque"), start=1)}
    de_nl = derive_de_nl(exits["Emden"], exits["Dornum"], monthly("NL", [1, 2]))
    other = derive_other_destinations(easington=exits["Easington"], segal=exits["SEGAL"],
                                      st_fergus=exits["St Fergus"], nybro=exits["Nybro"],
                                      zeebrugge=exits["Zeebrugge"], dunkerque=exits["Dunkerque"])
    assert other["UK"].tolist() == [12., 24.]
    assert other["DENMARK"].tolist() == [6., 12.]
    assert other["BELGIUM"].tolist() == [7., 14.]
    assert other["FRANCE"].tolist() == [8., 16.]
    destinations = {key: time_series(key, other[key], "bcm", "monthly") for key in other}
    destinations.update(GERMANY=time_series("DE", de_nl["DE"], "bcm", "monthly"),
                        NETHERLANDS=time_series("NL", de_nl["NL"], "bcm", "monthly"))
    assert reconcile_destinations(destinations, exits, tolerance_bcm=0).eq(0).all()
    destinations["UK"] = monthly("UK", [13, 24])
    with pytest.raises(ValidationError, match="Destination reconciliation failure"):
        reconcile_destinations(destinations, exits, tolerance_bcm=.001)
    with pytest.raises(ValidationError):
        reconcile_destinations(destinations, {key: value for key, value in exits.items() if key != "St Fergus"}, tolerance_bcm=0)


@pytest.mark.parametrize("values", [[None], [float("nan")], [float("inf")], [True], ["1"], [-float("inf")]])
def test_invalid_observations(monthly, values):
    with pytest.raises(ValidationError):
        monthly("Emden", values)


def test_duplicate_and_invalid_dates():
    with pytest.raises(ValidationError, match="Duplicate"):
        time_series("x", pd.Series([1, 2], index=pd.PeriodIndex(["2024-01", "2024-01"], freq="M")), "bcm", "monthly")
    with pytest.raises(ValidationError, match="PeriodIndex"):
        time_series("x", pd.Series([1], index=pd.date_range("2024-01-01", periods=1)), "bcm", "monthly")
    with pytest.raises(ValidationError, match="Missing observation dates"):
        time_series("x", pd.Series([1], index=pd.PeriodIndex([pd.NaT], freq="M")), "bcm", "monthly")


def test_negative_physical_component(monthly):
    with pytest.raises(ValidationError, match="Negative physical flow"):
        derive_de_nl(monthly("Emden", [-1]), monthly("Dornum", [1]), monthly("NL", [0]))


def test_parquet_loader_requires_explicit_units_and_schema(tmp_path, monthly):
    original = monthly("Emden", [1, 2])
    path = tmp_path / "series.parquet"
    original["values"].rename("value").to_frame().to_parquet(path)
    loaded = read_parquet_series(path, key="Emden", unit="bcm", frequency="monthly")
    pd.testing.assert_series_equal(loaded["values"], original["values"], check_names=False)
    pd.DataFrame({"wrong_column": [1]}).to_parquet(path)
    with pytest.raises(ValidationError, match="value"):
        read_parquet_series(path, key="Emden", unit="bcm", frequency="monthly")
