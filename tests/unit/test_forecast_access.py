from unittest.mock import Mock

import pandas as pd
import pytest

from norway_gas_routing import project_data as data
from norway_gas_routing.evaluation import EvaluationError


def request(client,start='2030-01-01',end='2030-01-31'):
    registry=pd.DataFrame([dict(key='forecast',sid='exact_sid',query_or_transform_hint='')]).set_index('key')
    return data.get_prospective_forecast('forecast',start,end,registry=registry,client=client)


def test_forecast_access_is_separate_from_historical_guard():
    client=Mock()
    client.get_fields_from_sid.return_value=dict(lifecycle_stage='forecast',forecast_start_date='2026-10-01')
    client.get_points_from_sid_into_series.return_value=pd.Series([1.],index=pd.to_datetime(['2030-01-01']))
    result=request(client)
    assert result['access_mode']=='prospective_forecast_inspection'
    assert result['values'].iloc[0]==1.
    registry=pd.DataFrame([dict(key='forecast',sid='exact_sid',query_or_transform_hint='')]).set_index('key')
    with pytest.raises(EvaluationError):
        data.get_registered_series('forecast','2030-01-01','2030-01-31',registry=registry,client=client)


@pytest.mark.parametrize('start,end',[('2026-01-01','2026-09-30'),('2025-01-01','2025-12-31'),
    ('2031-01-01','2031-02-01'),('2030-02-01','2030-01-01')])
def test_prospective_bounds_reject_before_metadata_or_points(start,end):
    client=Mock()
    with pytest.raises(ValueError,match='Prospective'): request(client,start,end)
    client.get_fields_from_sid.assert_not_called()
    client.get_points_from_sid_into_series.assert_not_called()


@pytest.mark.parametrize('meta',[dict(lifecycle_stage='actual',forecast_start_date='2025-01-01'),
    dict(lifecycle_stage='forecast'),dict(lifecycle_stage='forecast',forecast_start_date='2030-02-01')])
def test_forecast_metadata_rejects_actuals_and_unverified_segment(meta):
    client=Mock()
    client.get_fields_from_sid.return_value=meta
    with pytest.raises(ValueError,match='forecast segment'): request(client)
    client.get_points_from_sid_into_series.assert_not_called()


def test_out_of_bounds_provider_response_is_never_returned():
    client=Mock()
    client.get_fields_from_sid.return_value=dict(lifecycle_stage='forecast',forecast_start_date='2025-01-01')
    client.get_points_from_sid_into_series.return_value=pd.Series([1.],index=pd.to_datetime(['2026-03-01']))
    with pytest.raises(ValueError,match='out-of-bounds'): request(client)
