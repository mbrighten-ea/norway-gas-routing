from unittest.mock import Mock

import pandas as pd
import pytest

from norway_gas_routing import project_data as data


@pytest.fixture
def registry():
    return pd.DataFrame([
        {'key': 'nyhamna_maint_d',
         'sid': 'maintenance_sid', 'category': 'maintenance', 'asset': 'nyhamna',
         'status': 'REVIEW', 'model_role': 'capacity', 'notes': 'Retain negatives',
         'raw_unit': 'mcm_d', 'query_or_transform_hint': ''},
        {'key': 'missing_price', 'sid': '',
         'category': 'price', 'asset': '', 'status': 'TODO', 'model_role': 'price',
         'notes': '', 'raw_unit': '', 'query_or_transform_hint': ''},
        {'key': 'contract_price', 'sid': 'contract_id',
         'category': 'price', 'asset': '', 'status': 'REVIEW', 'model_role': 'reference_only',
         'notes': '', 'raw_unit': 'EUR/MWh', 'query_or_transform_hint': 'contract_obj.id="contract_id"'},
    ]).set_index('key')


def test_readable_key_resolves_info(registry):
    info = data.series_info('nyhamna_maint_d', registry=registry)
    assert info['key'] == 'nyhamna_maint_d'
    assert info['notes'] == 'Retain negatives'
    with pytest.raises(KeyError):
        data.series_info('unknown', registry=registry)


def test_filters_keep_review_and_todo_visible(registry):
    assert len(data.select_series(registry=registry)) == 3
    selected = data.select_series(category='maintenance', asset='nyhamna', registry=registry)
    assert selected.index.tolist() == ['nyhamna_maint_d']
    assert data.select_series(status='CONFIRMED', registry=registry).empty


def test_retrieval_keeps_status_notes_and_negative_values(registry):
    client = Mock()
    values = pd.Series([-1.0, 0.0, 5.0], index=pd.date_range('2025-01-01', periods=3))
    client.get_points_from_sid_into_series.return_value = values
    client.get_fields_from_sid.return_value = {'unit': 'mcm_d'}
    result = data.get_registered_series('nyhamna_maint_d', '2025-01-01', '2025-01-03', registry=registry, client=client)
    assert result['values'] is values
    assert result['registry']['status'] == 'REVIEW'
    assert result['metadata'] == {'unit': 'mcm_d'}
    assert result['evidence/inputs']['negative_count'] == 1
    client.get_points_from_sid_into_series.assert_called_once_with('maintenance_sid', '2025-01-01', '2025-01-03', -1)


@pytest.mark.parametrize('identifier, issue', [('missing_price', 'no SID'), ('contract_price', 'contract identifier')])
def test_unretrievable_rows_fail_before_connecting(registry, monkeypatch, identifier, issue):
    connect = Mock()
    monkeypatch.setattr(data.sj, 'connect_shooju', connect)
    with pytest.raises(ValueError, match=issue):
        data.get_registered_series(identifier, registry=registry)
    with pytest.raises(ValueError, match=issue):
        data.get_registered_frame(['nyhamna_maint_d', identifier], registry=registry)
    connect.assert_not_called()


def test_group_returns_labels_and_registry_metadata(registry):
    client = Mock()
    client.get_points_from_sid_into_series.return_value = pd.Series([2.0], index=pd.to_datetime(['2025-01-01']))
    name = 'nyhamna_maint_d'
    values, metadata = data.get_registered_frame([name], registry=registry, client=client)
    assert values.columns.tolist() == [name]
    assert metadata.loc[name, 'key'] == name
    assert metadata.loc[name, 'raw_unit'] == 'mcm_d'
    with pytest.raises(ValueError, match='distinct'):
        data.get_registered_frame([name, name], registry=registry, client=client)


def test_duplicate_registry_keys_are_rejected(registry):
    registry.index = ['nyhamna_maint_d'] * len(registry)
    with pytest.raises(ValueError, match='Ambiguous'):
        data.series_info('nyhamna_maint_d', registry=registry)


def test_current_registry_loads_and_contract_candidates_are_flagged():
    registry = data.load_registry()
    assert data.series_info('nyhamna_maint_d', registry=registry)['sid']
    contracts = registry.loc[registry.query_or_transform_hint.str.contains('contract_obj.id=', regex=False)]
    for key in contracts.index:
        with pytest.raises(ValueError, match='contract identifier'):
            data.get_registered_series(key, registry=registry)


def test_country_filter_matches_composite_scope(registry):
    registry['country_iso'] = ['NL;DE', 'DK', 'GB']
    registry['balance_item'] = ['pipeline_exports', 'not_applicable', 'not_applicable']
    selected = data.select_series(country_iso='DE', balance_item='pipeline_exports', registry=registry)
    assert selected.index.tolist() == ['nyhamna_maint_d']
    assert data.select_series(country_iso='NO', registry=registry).empty


def test_asof_queries_exact_sid_and_metadata_afresh_each_call(registry):
    client = Mock()
    client.sj.get_df.return_value = pd.DataFrame({'dt': ['2025-01-01', '2025-02-01'], 'val': [-1., 2.]})
    client.get_fields_from_sid.return_value = {'unit': 'mcm_d'}
    for _ in range(2):
        result = data.get_registered_series('nyhamna_maint_d', '2025-01-01', '2025-02-28',
            registry=registry, client=client, asof='2024-12-31T23:59:59Z')
        assert result['values'].tolist() == [-1., 2.]
        assert result['query'] == 'sid="maintenance_sid"@asof:2024-12-31T23:59:59'
    assert client.sj.get_df.call_count == 2
    assert client.get_fields_from_sid.call_count == 2
    client.get_points_from_sid_into_series.assert_not_called()


def test_empty_archive_is_blocker_without_cached_fallback(registry):
    client = Mock()
    client.sj.get_df.return_value = pd.DataFrame()
    with pytest.raises(ValueError, match='no SID values'):
        data.get_registered_series('nyhamna_maint_d', '2025-01-01', '2025-12-31',
            registry=registry, client=client, asof='2024-12-31T23:59:59Z')
    client.get_points_from_sid_into_series.assert_not_called()


def test_reserved_origin_is_rejected_before_query(registry):
    client = Mock()
    with pytest.raises(ValueError, match='holdout'):
        data.get_registered_series('nyhamna_maint_d', '2025-01-01', '2025-12-31',
            registry=registry, client=client, asof='2026-01-01')
    client.sj.get_df.assert_not_called()


def test_duplicate_archived_dates_are_not_silently_aggregated(registry):
    client = Mock()
    client.sj.get_df.return_value = pd.DataFrame({'dt': ['2025-01-01', '2025-01-01'], 'val': [1., 2.]})
    with pytest.raises(ValueError, match='duplicate'):
        data.get_registered_series('nyhamna_maint_d', '2025-01-01', '2025-12-31',
            registry=registry, client=client, asof='2024-12-31T23:59:59Z')


def test_sorting_scope_and_important_caveats_are_retained():
    registry = data.load_registry()
    assert registry.loc['easington_flow', 'country_iso'] == 'GB'
    assert registry.loc['emden_ept1_in_flow', 'country_iso'] == 'NL'
    assert registry.loc['snohvit_net_prod', 'balance_item'] == 'production'
    assert registry.loc['kollsnes_upstream_maint_d', 'asset_type'] == 'upstream_group'
    assert 'intraday' in registry.loc['kollsnes_upstream_maint_d', 'notes']
    assert '47-day overlap' in registry.loc['st_fergus_flow_compact', 'notes']
    assert registry.columns[-1] == 'notes'
    assert registry.columns[0] == 'sid'  # key is the DataFrame index.
    assert registry.notes.str.len().max() <= 250
