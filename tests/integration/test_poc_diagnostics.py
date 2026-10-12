"""Synthetic scoring check for negative Danish net allocation observations."""
import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("poc_diagnostics", ROOT / "scripts/verify/diagnose_poc_routing.py")
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


def test_negative_net_allocation_is_scored_but_excludes_entire_share_basket():
    months = pd.period_range("2024-01", periods=2, freq="M")
    observations = pd.DataFrame(2., index=months, columns=list(diagnostics.DESTINATIONS))
    observations.loc[months[1], "DK"] = -1
    observations["FR_BE"] = 4.
    observations["NL_DE"] = 4.
    allocations = pd.DataFrame(1., index=months, columns=list(diagnostics.DESTINATIONS))
    comparisons = pd.DataFrame(diagnostics.comparison_rows("synthetic", allocations, observations))
    assert comparisons.loc[comparisons.month.eq(months[1]), "share_error_pp"].isna().all()
    scores = diagnostics.metrics(comparisons).set_index("destination")
    assert scores.at["DK", "WAPE_pct"] == pytest.approx(100)
    assert scores.at["DK", "MAE_bcm_month"] == pytest.approx(1.5)
    assert scores.at["DK", "bias_bcm_month"] == pytest.approx(.5)
    assert scores.at["UK", "share_months"] == 1
    assert observations.at[months[1], "DK"] == -1
