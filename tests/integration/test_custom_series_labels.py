import csv

import pytest

from norway_gas_routing.config import load_series
from norway_gas_routing.validation import ValidationError


def rewrite_registry(path, change):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        columns, rows = reader.fieldnames, list(reader)
    change(columns, rows)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_analyst_lookup_and_distinct_st_fergus_regimes(config_files):
    series = load_series(config_files[1])
    by_id = series
    assert by_id.loc['nyhamna_maint_d', 'sid'].endswith('NO_maintenance_Nyhamna')
    assert by_id.loc['st_fergus_flow_compact', 'sid'] == r'gassco\StFergus'
    assert by_id.loc['st_fergus_flow_snake', 'sid'] == r'gassco\St_Fergus'


@pytest.mark.parametrize('invalid', ['NyhamnaFlow', 'nyhamna-flow', 'ø_flow', 'class', ''])
def test_invalid_keys_rejected(config_files, invalid):
    path = config_files[1]
    rewrite_registry(path, lambda columns, rows: rows[0].update(key=invalid))
    with pytest.raises(ValidationError):
        load_series(path)


def test_duplicate_keys_rejected(config_files):
    path = config_files[1]
    rewrite_registry(path, lambda columns, rows: rows[1].update(key=rows[0]['key']))
    with pytest.raises(ValidationError, match='Duplicate series identifier'):
        load_series(path)


def test_blank_custom_description_rejected(config_files):
    path = config_files[1]
    rewrite_registry(path, lambda columns, rows: rows[0].update(custom_description='  '))
    with pytest.raises(ValidationError, match='custom_description'):
        load_series(path)


def test_retained_registry_without_custom_columns_still_loads(config_files):
    path = config_files[1]

    def remove_custom_columns(columns, rows):
        for column in ['custom_description']:
            columns.remove(column)
            for row in rows:
                row.pop(column)

    rewrite_registry(path, remove_custom_columns)
    assert load_series(path).custom_description.eq('').all()


def test_key_migration_preserves_all_source_metadata(repo_root):
    def rows(path):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))

    before = rows(repo_root / 'data/raw/registry_before_key_migration.csv')
    after = rows(repo_root / 'config/data_series.csv')
    crosswalk = rows(repo_root / 'evidence/inputs/series_key_migration.csv')
    price_mapping = {row['old_key']: row['key'] for row in rows(repo_root / 'evidence/inputs/price_key_migration.csv')}
    series_mapping = {row['old_key']: row['key'] for row in rows(repo_root / 'evidence/inputs/series_key_shortening.csv')}
    def current_key(key):
        return series_mapping.get(key, price_mapping.get(key, key))
    # The migration snapshot is frozen; later source discoveries may append
    # inactive references without changing any migrated row or its order.
    assert len(before) == len(crosswalk) <= len(after)
    for appended in after[len(before):]:
        assert appended['model_role'] == 'reference_only'
        assert appended['required_level'] == 'optional'
    assert 'custom_id' not in after[0]
    for old, new, link in zip(before, after, crosswalk):
        assert new['key'] == current_key(old['custom_id']) == link['key']
        assert old['key'] == link['old_key']
        # Later analyst-directed edits changed descriptions and price roles.
        unchanged = set(old) - {'key', 'custom_id', 'notes', 'custom_description', 'model_role', 'required_level'}
        assert {k: old[k] for k in unchanged} == {k: new[k] for k in unchanged}
    # Notes were subsequently shortened; their full text is retained separately.
    archive = rows(repo_root / 'evidence/inputs/data_series_notes_detail.csv')
    assert {row['key']: row['notes'] for row in archive} == {
        current_key(row['custom_id']): row['notes'] for row in before}


def test_price_keys_are_short_and_still_distinguish_sources(repo_root):
    series = load_series(repo_root / 'config/data_series.csv')
    prices = series.loc[series.category == 'price']
    assert len(prices) == 34 and max(map(len, prices.index)) <= 22
    assert prices.loc['ttf_day_ahead', 'sid'].endswith('trnlttfd1')
    assert prices.loc['ttf_eex_last', 'sid'].endswith('ttf\\last_price')
    assert prices.loc['ttf_futures_settle', 'query_or_transform_hint'].startswith('contract_obj.id=')
    assert prices.loc['nbp_forecast_eur', 'raw_unit'] == 'eur_MWh'
    assert prices.loc['nbp_forecast', 'raw_unit'] == 'p_therm'


def test_short_keys_preserve_frequency_and_source_variants(repo_root):
    series = load_series(repo_root / 'config/data_series.csv')
    assert series.loc['troll_prod', 'sid'].endswith('NO_production_Troll_field')
    assert series.loc['nyhamna_maint_d', 'source_frequency'] == 'daily'
    assert series.loc['nyhamna_maint_m', 'source_frequency'] == 'monthly'
    assert series.loc['karsto_maint_m_native', 'sid'] != series.loc['karsto_maint_m_snake', 'sid']
    assert series.loc['emden_ept1_in_tech_cap', 'data_item'] == 'firm_technical_capacity'
    assert series.loc['nyhamna_avail_cap', 'data_item'] == 'available_capacity'
    assert series.loc['de_flow_qa', 'model_role'] == 'benchmark_only'
