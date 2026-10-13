"""Deterministic public-only command output and explicit unknown availability."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from norway_gas_routing.capacity.public import sha256

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.retained_evidence
def test_public_export_deterministic_and_not_solver_ready(tmp_path):
    spec=importlib.util.spec_from_file_location('capacity_candidate_export',ROOT/'scripts/audit/build_capacity_candidates.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first,second=tmp_path/'first',tmp_path/'second'
    module.export_candidates(first)
    module.export_candidates(second)
    assert {p.name:sha256(p) for p in first.iterdir()} == {p.name:sha256(p) for p in second.iterdir()}
    table=pd.read_csv(first/'monthly_capacity_preparation.csv')
    assert len(table)==8*24*19
    assert table.loc[table.asset.eq('KOLLSNES_EXPORT'),'candidate_available_bcm'].isna().all()
    assert not table.public_candidate_eligible.any()
    assert not table.solver_ready_without_production.any()
    observations=pd.read_csv(first/'database_candidates.csv')
    assert observations.candidate_bcm.isna().all()
    assert set(observations.loc[observations.month.str.startswith('2021') & observations.asset_key.str.startswith('point:'),'status']) == {'MISSING_DATA'}
