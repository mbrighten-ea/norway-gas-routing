"""Synthetic fresh-SID references, actual boundaries and forecast-error preparation."""
from unittest.mock import Mock
import numpy as np
import pandas as pd
import pytest

from norway_gas_routing import visual_sids as sources
from norway_gas_routing.visual_data import comparison, actual_error_summary
from norway_gas_routing.visual_report import build_package


def response(months=('2025-01','2025-02'), values=(2.,3.), boundary='2026-10-01'):
    return {'metadata': {'unit':'bcm', 'frequency':'monthly', 'lifecycle_stage':'forecast',
        'source_file':'Norwegian flows model.xlsx', 'forecast_start_date':boundary},
        'values': pd.Series(values,index=pd.to_datetime([m+'-01' for m in months],utc=True)),
        'query':None}


def test_historical_boundary_rejects_forecast_values_as_actuals():
    with pytest.raises(ValueError, match='cross its forecast-start'):
        sources.monthly_reference(response(boundary='2025-02-01'), ['2025-01','2025-02'])


def test_monthly_units_are_checked_and_missing_months_stay_missing():
    r=response(months=('2025-01',),values=(2.,))
    values=sources.monthly_reference(r,['2025-01','2025-02'])
    assert values.iloc[0]==2. and np.isnan(values.iloc[1])
    r['metadata']['unit']='mcm_d'
    with pytest.raises(ValueError,match='monthly bcm'):sources.monthly_reference(r,['2025-01'])


def test_origin_must_precede_targets_and_forecast_boundary():
    with pytest.raises(ValueError,match='future-forecast'):
        sources.monthly_reference(response(boundary='2025-02-01'),['2025-01'],'2024-12-31')


def test_fresh_sid_sources_preserve_original_groups_and_query_origin(monkeypatch):
    registry=pd.DataFrame({'sid':[f'teams\\{k}' for k in sources.KEYS.values()]},index=list(sources.KEYS.values()))
    calls=[]
    def retrieve(key,start,end,**kwargs):
        calls.append((key,kwargs.get('asof')))
        return response(values=(99.,100.) if key=='fr_be_flow_qa' else (2.,3.),boundary='2024-12-01')
    monkeypatch.setattr(sources,'get_registered_series',retrieve)
    for _ in range(2):
        result=sources.load_sid_reference(['2025-01','2025-02'],'2024-12-31',registry=registry)
        assert result['data'].query("destination == 'FR+BE'").value_bcm.tolist()==[99.,100.]
        assert not result['data'].destination.isin(['FR','BE','NL','DE']).any()
        assert len(result['responses'])==6
        assert result['ledger'].response_sha256.str.len().eq(64).all()
    assert len(calls)==12 and all(origin=='2024-12-31T23:59:59Z' for _,origin in calls)


def test_holdout_origin_is_rejected_before_service_calls(monkeypatch):
    retrieve=Mock();monkeypatch.setattr(sources,'get_registered_series',retrieve)
    with pytest.raises(ValueError,match='holdout'):
        sources.load_sid_reference(['2025-01'],'2026-01-01')
    retrieve.assert_not_called()


def test_error_tables_score_legacy_and_do_not_rank_reconstructions():
    run={'id':'synthetic','scenario':'test','title':'Historical reconstruction',
        'monthly':pd.DataFrame([{'month':'2025-01',**{c:1. for c in sources.COUNTRIES}}])}
    legacy={'kind':'forecast','vintage':'2024-12-31','data':pd.DataFrame([
        {'month':'2025-01','level':'countries','destination':'UK','value_bcm':1.5,'compatible':True,'status':'forecast','cell':''}])}
    actuals={'data':pd.DataFrame([
        {'month':'2025-01','level':'countries','destination':'UK','value_bcm':2.,'compatible':True,'status':'EA actual'},
        {'month':'2025-01','level':'countries','destination':'DK','value_bcm':-.1,'compatible':False,'status':'signed net'}])}
    prepared=comparison(run,legacy,actuals)
    uk=prepared.query("level == 'countries' and destination == 'UK'").iloc[0]
    assert uk.legacy_error_bcm==-.5 and uk.reconstruction_residual_bcm==-1.
    assert np.isnan(uk.routing_forecast_error_bcm)
    dk=prepared.query("level == 'countries' and destination == 'DK'").iloc[0]
    assert dk.ea_actual_bcm==-.1 and dk.ea_net_context_bcm==-.1
    assert np.isnan(dk.actual_chart_bcm) and np.isnan(dk.legacy_error_bcm)
    summary=actual_error_summary(prepared)
    assert summary.query("level == 'countries' and destination == 'UK'").iloc[0].legacy_mae_bcm_month==.5
    assert summary.routing_forecast_mae_bcm_month.isna().all()


@pytest.mark.parametrize('source',['workbook','retained:2024-06-30'])
def test_cached_numerical_report_sources_are_rejected_before_loading(tmp_path,source):
    with pytest.raises(ValueError,match='SID-only'):
        build_package(tmp_path,[],tmp_path/'outputs/graphics',[source])
