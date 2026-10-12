"""Reference discovery must not activate production or change physical equations."""
import csv

import pandas as pd

from norway_gas_routing.config import load_config
from norway_gas_routing.routing import network_definition


FIELDS = ('balder', 'brage', 'halten_ost', 'trym', 'tune', 'urd')


def test_verified_field_history_references_are_not_selected_supply(repo_root):
    model, registry = load_config(repo_root / 'config/model.yaml', repo_root / 'config/data_series.csv')
    selected = {key for entry in model['sources'].values() for key in entry['series']}
    for field in FIELDS:
        row = registry.loc[field + '_net_actual']
        assert row.sid == f'NPD\\monthly_by_field\\marketed_production\\{field}\\gas-saleable'
        assert row.model_role == 'reference_only' and row.required_level == 'optional'
        assert row.lifecycle == 'actual' and row.forecast_required is False
        assert row.raw_unit == row.target_unit == 'bcm'
        assert row.name not in selected
        assert registry.sid.str.casefold().eq(row.sid.casefold()).sum() == 1
    total = registry.loc['norway_net_actual']
    assert total.sid == 'NPD\\monthly_total\\Gas - saleable'
    assert total.model_role == 'reference_only' and total.required_level == 'optional'
    assert total.name not in selected and total.forecast_required is False


def test_appending_a_synthetic_production_reference_preserves_selection_and_network(config_files):
    model_path, registry_path = config_files
    model, before = load_config(model_path, registry_path)
    old_network = network_definition(model['routing'])
    selected = {key for source in model['sources'].values() for key in source['series']}
    with registry_path.open(encoding='utf-8-sig', newline='') as stream:
        header = next(csv.reader(stream))
    row = {key: '' for key in header}
    row.update(key='synthetic_reference', sid='synthetic\\reference', description='Synthetic field history',
               custom_description='Synthetic field history; inactive reference.', category='production',
               raw_unit='bcm', target_unit='bcm', source_frequency='monthly', lifecycle='actual',
               model_role='reference_only', required_level='optional', status='CONFIRMED', forecast_required='false')
    with registry_path.open('a', encoding='utf-8', newline='') as stream:
        csv.DictWriter(stream, fieldnames=header).writerow(row)
    after_model, after = load_config(model_path, registry_path)
    assert after_model == model
    assert network_definition(after_model['routing']) == old_network
    pd.testing.assert_frame_equal(before.loc[list(selected)], after.loc[list(selected)])
    assert 'synthetic_reference' not in selected
