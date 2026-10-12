"""Wrapper contracts tested without importing or contacting the live service."""
from unittest.mock import Mock

import pandas as pd
import pytest

from norway_gas_routing import data_functions as data


def test_connection_uses_existing_helper(monkeypatch):
    helper = Mock()
    monkeypatch.setitem(__import__('sys').modules, 'helper_functions_ea', helper)
    assert data.connect_shooju() is helper.ShoojuTools.return_value
    helper.check_env.assert_called_once_with()
    helper.ShoojuTools.assert_called_once_with(silence_alerts=True)


def test_series_passes_dates_and_preserves_values():
    client = Mock()
    values = pd.Series([-2.0, float('nan'), 0.0], index=pd.date_range('2025-01-01', periods=3, tz='UTC'))
    client.get_points_from_sid_into_series.return_value = values
    assert data.get_series('some_sid', '2025-01-01', 'MAX', max_points=10, client=client) is values
    client.get_points_from_sid_into_series.assert_called_once_with('some_sid', '2025-01-01', '2025-12-31', 10)


def test_metadata_and_discovery_fields():
    client = Mock()
    client.get_fields_from_sid.return_value = {'unit': 'kWh_d'}
    assert data.get_metadata('some_sid', client=client) == {'unit': 'kWh_d'}
    client.get_fields_from_sid.assert_called_once_with('some_sid', fields=['*'])
    client.get_fields_from_query.return_value = pd.DataFrame({'series_id': ['some_sid'], 'unit': ['kWh_d']}, index=['some_sid'])
    found = data.find_series('sid:container', ['unit', 'series_id'], client=client)
    client.get_fields_from_query.assert_called_once_with('sid:container', fields=['series_id', 'unit'])
    assert found.index.tolist() == [0]
    assert found.series_id.tolist() == ['some_sid']
    with pytest.raises(ValueError, match='explicitly'):
        data.find_series('sid:container', ['*'], client=client)


def test_frame_aligns_by_dates_without_filling_or_conversion():
    client = Mock()
    client.get_points_from_sid_into_series.side_effect = [
        pd.Series([-3.0, 0.0], index=pd.to_datetime(['2025-01-01', '2025-01-03'])),
        pd.Series([7.0], index=pd.to_datetime(['2025-01-02']))]
    frame = data.get_series_frame({'maintenance': 'sid_a', 'flow': 'sid_b'}, client=client)
    assert frame.columns.tolist() == ['maintenance', 'flow']
    assert len(frame) == 3
    assert frame.loc['2025-01-01', 'maintenance'] == -3
    assert frame.loc['2025-01-03', 'maintenance'] == 0
    assert pd.isna(frame.loc['2025-01-02', 'maintenance'])
    assert frame.loc['2025-01-02', 'flow'] == 7


def test_frame_rejects_duplicate_dates_and_service_errors_propagate():
    client = Mock()
    client.get_points_from_sid_into_series.return_value = pd.Series([1, 2], index=[pd.Timestamp('2025-01-01')] * 2)
    with pytest.raises(ValueError, match='Duplicate timestamps'):
        data.get_series_frame({'flow': 'sid_a'}, client=client)
    client.get_points_from_sid_into_series.side_effect = RuntimeError('unavailable')
    with pytest.raises(RuntimeError, match='unavailable'):
        data.get_series_frame({'flow': 'sid_a'}, client=client)


@pytest.mark.parametrize('cap', [0, -2, True, 1.5])
def test_invalid_point_caps_fail_before_retrieval(cap):
    client = Mock()
    with pytest.raises(ValueError, match='max_points'):
        data.get_series('some_sid', max_points=cap, client=client)
    client.get_points_from_sid_into_series.assert_not_called()


def test_empty_requests_fail_before_connection(monkeypatch):
    connect = Mock()
    monkeypatch.setattr(data, 'connect_shooju', connect)
    for call in [lambda: data.get_series(''), lambda: data.find_series(' '), lambda: data.get_series_frame({})]:
        with pytest.raises(ValueError):
            call()
    connect.assert_not_called()
