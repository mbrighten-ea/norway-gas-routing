"""Future workflow fixtures are explicit demonstrations, never EA forecasts."""
import hashlib
import json
from unittest.mock import Mock

from openpyxl import load_workbook
import pandas as pd
import pytest
import yaml

from norway_gas_routing import operational as op, forecast_inputs as forecast
from norway_gas_routing import project_data
from norway_gas_routing.evaluation import check_dates, EvaluationError
from test_operational import workspace


def configure(root,source='synthetic_demo',**changes):
    path=root/'config/run.yaml'
    request=yaml.safe_load(path.read_text())
    request.update(mode='current_forecast',start=None,end=None,origin=None,horizon_months=12,
        input_source=source,capacity_scenario='synthetic_fixture' if source=='synthetic_demo' else 'baseline_prospective')
    request.update(changes)
    path.write_text(yaml.safe_dump(request))


def verify_hashes(output,manifest):
    for path,digest in manifest['files_sha256'].items():
        assert hashlib.sha256((output/path).read_bytes()).hexdigest()==digest


def test_rolling_12_month_solve_excel_balances_and_nonoverwrite(workspace,monkeypatch):
    configure(workspace)
    output,code=op.execute_run(workspace)
    assert code==0
    manifest=json.loads((output/'provenance/run_manifest.json').read_text())
    assert manifest['status']=='OPTIMAL' and 'SYNTHETIC' in manifest['analysis_type']
    origin,months=forecast.forecast_window(manifest['settings']['origin'])
    assert len(months)==12 and months.min()==pd.Timestamp.now().to_period('M')+1
    assert manifest['evaluation']['analysis_mode']=='current_forecast'
    assert manifest['evaluation']['holdout_loaded'] is False and manifest['evaluation']['holdout_scored'] is False
    frame=pd.read_csv(output/'results.csv')
    assert len(frame)==12 and frame.forecast_origin.eq(origin).all()
    assert (frame.total_exports_bcm+frame.unrouted_supply_bcm-frame.pipeline_supply_proxy_bcm).abs().max()<1e-7
    checks=pd.read_csv(output/'details/solver_checks.csv')
    assert checks.max_mass_balance_residual_bcm.max()<1e-7 and checks.max_capacity_violation_bcm.max()<1e-7
    reconciliation=pd.read_csv(output/'provenance/inputs/reconciliation.csv')
    assert (reconciliation.national_production_bcm-reconciliation.snohvit_bcm-reconciliation.pipeline_supply_bcm).abs().max()<1e-9
    book=load_workbook(output/'results.xlsx')
    assert len(book.sheetnames)==9 and len(book['Monthly flows']._charts)==1
    assert 'SYNTHETIC' in book['Read me']['A1'].value
    assert book['Comparisons']['E4'].value=='Unavailable'
    assert (output/'report.html').is_file() and (output/'details/monthly_flows.png').is_file()
    verify_hashes(output,manifest)
    first=hashlib.sha256((output/'results.xlsx').read_bytes()).hexdigest()
    monkeypatch.setattr(op,'optimise',lambda *a,**k:pytest.fail('Validation-only constructed an LP'))
    second,code=op.execute_run(workspace,validate_only=True)
    assert code==0 and output!=second
    assert hashlib.sha256((output/'results.xlsx').read_bytes()).hexdigest()==first
    assert json.loads((second/'provenance/solver_results.json').read_text())=={}


@pytest.mark.parametrize('changes,message',[
    ({'horizon_months':True},'integer'),({'horizon_months':0},'integer'),
    ({'horizon_months':60},'December 2030'),({'origin':'2026-05-31'},'historical replay'),
    ({'origin':True},'quoted UTC timestamp'),({'capacity_scenario':[]},'named string'),
    ({'origin':'2030-01-01'},'no later than now'),({'start':'2026-01'},'derive'),
    ({'capacity_scenario':'baseline_prospective'},'never mix')])
def test_bad_current_request_rejected_before_io(workspace,changes,message):
    configure(workspace,**changes)
    with pytest.raises(ValueError,match=message): op.execute_run(workspace)
    assert not (workspace/'outputs').exists()


def fake_forecast(contract,change=None):
    def retrieve(key,start,end,**kwargs):
        spec=contract['sources'][key]
        frequency=spec['frequency']
        dates=pd.date_range(start,end,freq='D' if frequency=='daily' else 'MS',tz='UTC')
        response=dict(registry=dict(key=key,sid=spec['sid']),asof=kwargs['origin'],
            query='sid="'+spec['sid']+'"@asof:'+pd.Timestamp(kwargs['origin']).strftime('%Y-%m-%dT%H:%M:%S'),
            values=pd.Series(1.,index=dates),metadata=dict(series_id=spec['sid'],source_file=spec['source_file'],
                unit=spec['metadata_unit'],frequency=frequency,lifecycle_stage='forecast',
                forecast_start_date='2026-10-01',_mock_sid_response=True))
        if change: change(key,response)
        return response
    return retrieve


def test_complete_available_sid_coverage_still_blocks_unapproved_supply(workspace,monkeypatch):
    configure(workspace,'fresh_sid')
    contract=json.loads((workspace/'evidence/inputs/routing_sources_b1/verified_sources.json').read_text())
    monkeypatch.setattr(forecast,'connect_shooju',lambda:object())
    monkeypatch.setattr(forecast,'get_prospective_forecast',fake_forecast(contract))
    monkeypatch.setattr(op,'optimise',lambda *a,**k:pytest.fail('Unapproved partial supply entered solver'))
    output,code=op.execute_run(workspace,validate_only=True)
    assert code==2
    manifest=json.loads((output/'provenance/run_manifest.json').read_text())
    assert 'Complete 2024 production ledger failed' in manifest['blocker']
    assert '41 components' in manifest['blocker'] and 'TRYM' in manifest['blocker']
    assert (output/'provenance/production_population.csv').is_file()
    assert (output/'provenance/provisional_capacity_monthly.csv').is_file()
    inventory=pd.read_csv(output/'input_sources.csv')
    assert inventory.classification.eq('essential_population').sum()==69
    assert inventory.loc[inventory.classification.eq('essential_population'),'start'].eq('2024-01').all()
    assert len(manifest['inputs'])==19 and all(r['sha256'] for r in manifest['inputs'])
    assert not (output/'provenance/inputs/supply.csv').exists()
    assert pd.read_csv(output/'results.csv').total_exports_bcm.isna().all()
    verify_hashes(output,manifest)


@pytest.mark.parametrize('case,message',[('gap','coverage'),('unit','units'),('actual','genuine forecast'),
    ('origin','origin mismatch'),('negative','negative production'),('nan','nonfinite')])
def test_source_failure_keeps_raw_and_blocks_optimisation(workspace,monkeypatch,case,message):
    configure(workspace,'fresh_sid',horizon_months=1)
    contract=json.loads((workspace/'evidence/inputs/routing_sources_b1/verified_sources.json').read_text())
    def change(key,response):
        if key!='troll_prod': return
        if case=='gap': response['values']=response['values'].iloc[:0]
        if case=='unit': response['metadata']['unit']='mcm_d'
        if case=='actual': response['metadata']['lifecycle_stage']='actual'
        if case=='origin': response['asof']='2026-10-01T00:00:00Z'
        if case=='negative': response['values'].iloc[0]=-1.
        if case=='nan': response['values'].iloc[0]=float('nan')
    monkeypatch.setattr(forecast,'connect_shooju',lambda:object())
    monkeypatch.setattr(forecast,'get_prospective_forecast',fake_forecast(contract,change))
    monkeypatch.setattr(op,'optimise',lambda *a,**k:pytest.fail('Bad forecast entered optimiser'))
    output,code=op.execute_run(workspace)
    assert code==2
    manifest=json.loads((output/'provenance/run_manifest.json').read_text())
    assert message in manifest['blocker']
    record=next(r for r in manifest['inputs'] if r['key']=='troll_prod')
    assert record['status']=='REJECTED' and (output/record['raw_file']).is_file()


def test_current_archive_query_is_exact_without_unlocking_actuals():
    client=Mock()
    origin,months=forecast.forecast_window(horizon_months=1)
    registry=pd.DataFrame([dict(key='forecast',sid='exact_sid',query_or_transform_hint='')]).set_index('key')
    client.get_fields_from_sid.return_value=dict(lifecycle_stage='forecast',forecast_start_date='2026-10-01')
    client.sj.get_df.return_value=pd.DataFrame(dict(dt=[months.min().start_time],val=[1.]))
    response=project_data.get_prospective_forecast('forecast',str(months.min().start_time.date()),
        str(months.max().end_time.date()),origin=origin,registry=registry,client=client)
    assert '@asof:' in response['query'] and response['asof']==origin
    assert client.sj.get_df.call_args.kwargs['df']>= '2026-10-01'
    client.get_points_from_sid_into_series.assert_not_called()
    client.sj.get_df.return_value=pd.DataFrame(columns=['dt','val'])
    with pytest.raises(ValueError,match='no latest fallback'):
        project_data.get_prospective_forecast('forecast',str(months.min().start_time.date()),
            str(months.max().end_time.date()),origin=origin,registry=registry,client=client)
    client.get_points_from_sid_into_series.assert_not_called()
    with pytest.raises(EvaluationError): check_dates(['2026-01','2026-09'],'read')


def test_prospective_export_cannot_export_locked_or_undeclared_dates(workspace):
    configure(workspace)
    request,_,_,_=op.load_run_config(workspace,'config/run.yaml')
    frame=pd.DataFrame(dict(month=['2026-01-01'],value=[1.]))
    with pytest.raises(ValueError,match='outside its delivery contract'):
        op.save_current_forecast_table(frame,workspace/'unsafe.csv',request)
    assert not (workspace/'unsafe.csv').exists()
    frame.month=request['start']+'-01'
    with pytest.raises(EvaluationError): op.save_csv(frame,workspace/'historical.csv')
    assert not (workspace/'historical.csv').exists()
