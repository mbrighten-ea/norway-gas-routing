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


def test_seasonal_optin_and_unchanged_sid_default(workspace):
    configuration(workspace)
    assert op.load_run_config(workspace,'config/run.yaml')[0]['snohvit_method']=='sid_forecast'
    configuration(workspace,snohvit_method='seasonal_two_year')
    assert op.load_run_config(workspace,'config/run.yaml')[0]['snohvit_method']=='seasonal_two_year'
    configuration(workspace,snohvit_method='flat')
    with pytest.raises(ValueError,match='snohvit_method'):op.load_run_config(workspace,'config/run.yaml')


@pytest.mark.parametrize('method',['sid_forecast','seasonal_two_year'])
def test_preparation_consumes_only_explicit_snohvit_method(workspace,monkeypatch,tmp_path,method):
    from norway_gas_routing import forecast_inputs as fi,forward_supply as fs,seasonal_snohvit as sn
    configuration(workspace,snohvit_method=method)
    request,model,registry,_=op.load_run_config(workspace,'config/run.yaml')
    output=tmp_path/'capture';output.mkdir();request['_provenance_dir']=output
    calls=[]
    monkeypatch.setattr(fi,'connect_shooju',lambda:object())
    def inspect(root,key,dates,registry,contract,records,output,origin,client):
        calls.append(key);return pd.Series(.1,index=dates)
    monkeypatch.setattr(fi,'inspect_forecast_source',inspect)
    def seasonal(months,origin,records,output,client):
        calls.append('seasonal');return pd.Series(.3,index=months)
    monkeypatch.setattr(sn,'retrieve_seasonal_snohvit',seasonal)
    monkeypatch.setattr(fs,'prepare_approved_inputs',lambda root,model,registry,request,candidates,*a:candidates)
    candidates=fi.prepare_current_inputs(workspace,model,registry,request)
    if method=='seasonal_two_year':
        assert 'snohvit_net_prod' not in calls and 'seasonal' in calls
        assert candidates['snohvit_seasonal_bcm'].iloc[0]==.3
    else:
        assert 'snohvit_net_prod' in calls and 'seasonal' not in calls
        assert 'snohvit_seasonal_bcm' not in candidates


def test_seasonal_gap_keeps_core_input_blocker(workspace,monkeypatch,tmp_path):
    from norway_gas_routing import forecast_inputs as fi,forward_supply as fs,seasonal_snohvit as sn
    configuration(workspace,snohvit_method='seasonal_two_year')
    request,model,registry,_=op.load_run_config(workspace,'config/run.yaml')
    output=tmp_path/'capture';output.mkdir();request['_provenance_dir']=output
    monkeypatch.setattr(fi,'connect_shooju',lambda:object())
    monkeypatch.setattr(fi,'inspect_forecast_source',lambda root,key,dates,*a:pd.Series(.1,index=dates))
    def unavailable(*a):raise ValueError('two complete origin-eligible years unavailable')
    monkeypatch.setattr(sn,'retrieve_seasonal_snohvit',unavailable)
    monkeypatch.setattr(fs,'prepare_approved_inputs',lambda *a:pytest.fail('Failed baseline reached allocation'))
    with pytest.raises(ValueError,match='essential source coverage failed'):
        fi.prepare_current_inputs(workspace,model,registry,request)
