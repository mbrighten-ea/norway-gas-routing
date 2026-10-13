"""Operational opt-in and validation-only guards; explicitly manufactured data."""
import json
import pandas as pd
import pytest
import yaml

from norway_gas_routing import operational as op
from test_operational import workspace


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    now=pd.Timestamp('2026-10-13T12:00:00Z')
    monkeypatch.setattr(pd.Timestamp,'now',lambda tz=None:now.tz_convert(tz) if tz else now.tz_localize(None))


def configuration(root,**changes):
    p=root/'config/run.yaml'; c=yaml.safe_load(p.read_text())
    c.update(mode='current_forecast',input_source='fresh_sid',start=None,end=None,origin=None,
        horizon_months=12,forecast_end_month='2029-12',physical_input_contract='core_f24',
        heidrun_treatment='export_eligible',capacity_scenario='core_f24_156',price_enabled=False)
    c.update(changes); p.write_text(yaml.safe_dump(c)); return c


@pytest.mark.parametrize('changes',[{'heidrun_treatment':None},{'physical_input_contract':None},
    {'capacity_scenario':'provisional_kollsnes_143'},{'mode':'historical_reconstruction'},
    {'input_source':'synthetic_demo'},{'price_enabled':True}])
def test_incompatible_optins_cannot_bypass_guards(workspace,changes):
    configuration(workspace,**changes)
    with pytest.raises(ValueError): op.load_run_config(workspace,'config/run.yaml')


def test_38_month_validate_only_never_optimises(workspace,monkeypatch):
    configuration(workspace)
    def prepare(root,model,registry,request):
        inputs=op.synthetic_inputs(model)
        inputs['approved_contract']='core_f24'
        inputs['provenance']=[dict(key='mock',metadata={'_mock_sid_response':True},
            kind='mock_forward_fixture',transformation='Manufactured values for validation-only test')]
        inputs['reconciliation']=pd.DataFrame({'national_production_bcm':inputs['supply'].sum(axis=1)+.2},index=inputs['months'])
        return inputs
    monkeypatch.setattr(op,'prepare_run_inputs',prepare)
    monkeypatch.setattr(op,'optimise',lambda *a:pytest.fail('validate-only constructed LP'))
    output,code=op.execute_run(workspace,validate_only=True)
    manifest=json.loads((output/'provenance/run_manifest.json').read_text())
    assert code==0 and manifest['status']=='VALIDATED_ONLY'
    assert manifest['settings']['horizon_months']==38
    assert 'MOCK' in manifest['analysis_type'] and manifest['holdout_scored'] is False
    assert manifest['operational_forecast_available'] is False
    assert json.loads((output/'provenance/solver_results.json').read_text())=={}
