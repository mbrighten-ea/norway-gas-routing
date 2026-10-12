"""Check scoring and vintage gates independently of live EA services."""
import numpy as np
import pandas as pd
import pytest

from norway_gas_routing import benchmark

def record():
    return {'origin':'2023-12-31','evidence_file':'synthetic.json','metadata':{'forecast_start_date':'2023-12-01',
        'unit':'bcm','lifecycle_stage':'forecast','source_file':'Norwegian flows model.xlsx'}}

def test_forecast_gate_requires_future_month_and_historical_metadata():
    r=record()
    assert benchmark.verified_forecast(r,pd.Period('2024-01','M'),2.)
    assert not benchmark.verified_forecast(r,pd.Period('2023-12','M'),2.)
    assert not benchmark.verified_forecast(r,pd.Period('2024-01','M'),np.nan)
    r['metadata']['lifecycle_stage']='actual'
    assert not benchmark.verified_forecast(r,pd.Period('2024-01','M'),2.)
    r=record();r['metadata'].pop('forecast_start_date')
    assert not benchmark.verified_forecast(r,pd.Period('2024-01','M'),2.)

def test_metrics_and_share_exclusion(tmp_path,monkeypatch):
    monkeypatch.setattr(benchmark,'OUT',tmp_path)
    rows=[]
    for month in ['2024-01','2024-02']:
        for name in benchmark.GROUPS:
            rows.append({'method':'legacy_asof','origin':'2023-12-31','target_month':month,
                'level':'five_groups','destination':name,'prediction_bcm':3.,'actual_bcm':2.})
    # One negative net allocation invalidates all shares for that month, while
    # signed volume errors remain scored using absolute actual WAPE denominator.
    rows[-1]['actual_bcm']=-1.
    frame,metrics=benchmark.scores(rows)
    uk=metrics.loc[metrics.destination.eq('UK')].iloc[0]
    assert uk.wape_pct==pytest.approx(50)
    assert uk.mae_bcm_month==pytest.approx(1)
    assert uk.bias_total_bcm==pytest.approx(2)
    assert uk.share_n==1
    assert frame.loc[frame.target_month.eq('2024-02'),'share_error_pp'].isna().all()

def test_seasonal_does_not_train_on_forecasts_or_future_actuals(tmp_path,monkeypatch):
    monkeypatch.setattr(benchmark,'OUT',tmp_path)
    months=pd.period_range('2022-01','2024-12',freq='M')
    historical=pd.Series(2.,index=months)
    historical.loc['2023-12':]=999.
    snapshots={'2023-12-31':{name:(historical.copy(),record()) for name in benchmark.SUFFIX}}
    rows=benchmark.forecast_rows({name:historical.copy() for name in benchmark.SUFFIX},snapshots)
    training=pd.read_csv(tmp_path/'seasonal_training_vintages.csv')
    assert training.month.max()=='2023-11'
    seasonal=[r for r in rows if r['method']=='seasonal_asof' and r['destination']=='UK' and r['target_month']=='2024-01']
    assert seasonal[0]['prediction_bcm']==pytest.approx(2.)

def test_duplicate_months_are_not_silently_aggregated():
    with pytest.raises(ValueError,match='Duplicate monthly'):
        benchmark.monthly(pd.Series([1.,2.],index=pd.to_datetime(['2024-01-01','2024-01-02'])))
