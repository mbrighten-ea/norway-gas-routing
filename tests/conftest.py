from pathlib import Path

import pandas as pd
import pytest
import yaml

from norway_gas_routing.data import time_series


@pytest.fixture
def repo_root():
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def config_files(repo_root, tmp_path):
    model = tmp_path / "model.yaml"
    series = tmp_path / "data_series.csv"
    model.write_bytes((repo_root / "config/model.yaml").read_bytes())
    series.write_bytes((repo_root / "config/data_series.csv").read_bytes())
    return model, series


@pytest.fixture
def edit_model(config_files):
    model, series = config_files

    def edit(change):
        raw = yaml.safe_load(model.read_text())
        change(raw)
        model.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        return model, series

    return edit


@pytest.fixture
def monthly():
    def make(key, values, unit="bcm", start="2024-01"):
        index = pd.period_range(start, periods=len(values), freq="M")
        return time_series(key, pd.Series(values, index=index), unit, "monthly")
    return make


@pytest.fixture
def daily():
    def make(value=10.0, key="kollsnes_maint_d", start="2024-01-01", end="2024-01-31"):
        return time_series(key, pd.Series(value, index=pd.date_range(start, end)), "mcm_d", "daily")
    return make
