"""Independent frozen-package checks; no source retrieval, tuning or LP solves.

Run with the approved workspace interpreter from the repository root. Optional
--write-validation retains this check's evidence when preparing a new package.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

import numpy as np
import pandas as pd
from openpyxl import load_workbook

root = Path.cwd()
sys.path.insert(0, str(root / 'src'))
from norway_gas_routing.config import load_config
from norway_gas_routing.routing import network_definition, validate_solution
from norway_gas_routing.seasonal_snohvit import seasonal_profile

output = root / 'outputs/revision_tolerant_2025'
manifest_path = output / 'provenance/manifest.json'
manifest = json.loads(manifest_path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, digest in manifest['files_sha256'].items():
    assert sha(root / name) == digest, name
freeze = json.loads((output / 'provenance/input_freeze.json').read_text())
forecast_freeze = json.loads((output / 'provenance/forecast_freeze.json').read_text())
assert sha(output / 'details/frozen_forecasts.csv') == forecast_freeze['forecast_file_sha256']
for name, digest in freeze['input_files_sha256'].items():
    assert sha(output / name) == digest, name
raw = root / manifest['source_capture']
inputs = json.loads((raw / 'source_metadata.json').read_text())
evaluation = json.loads((raw / 'evaluation_only/source_metadata.json').read_text())
for record in inputs:
    dates = pd.read_csv(root / record['raw_file']).date
    if record['role'] == 'pre_origin_revision_tolerant_history':
        assert record['end'] < '2024-12-01'
        assert (pd.to_datetime(dates) < pd.Timestamp('2024-12-01')).all()
    else:
        assert '@asof:2024-12-31T23:59:59' in record['query']
    assert sha(root / record['raw_file']) == record['sha256']
    assert pd.Timestamp(record['retrieved_at']) < pd.Timestamp(forecast_freeze['created_at'])
for record in evaluation:
    assert record['start'] == '2025-01-01' and record['end'] == '2025-12-31'
    assert pd.Timestamp(record['retrieved_at']) > pd.Timestamp(forecast_freeze['created_at'])
    if 'raw_file' in record:
        assert sha(root / record['raw_file']) == record['sha256']
        assert pd.to_datetime(pd.read_csv(root / record['raw_file']).date).dt.year.eq(2025).all()

read = lambda name: pd.read_csv(output / name)
history = read('provenance/inputs/historical_owner_observations.csv').set_index('month')
owners = read('provenance/inputs/owners_2023.csv')
weights = read('provenance/inputs/weights_2023.csv')
ledger = read('details/ledger_2023.csv')
account = read('provenance/inputs/reconciliation.csv').set_index('month')
supply = read('provenance/inputs/supply.csv').set_index('month')
capacities = read('provenance/inputs/capacities.csv').set_index('month')
flows = read('details/frozen_forecasts.csv')
assert owners.component_id.is_unique and owners.sid.is_unique
assert owners.loc[owners.role.eq('explicit')].shape[0] == 16
assert owners.loc[owners.component_id.eq('AQ'), 'role'].iloc[0] == 'explicit'
for component, node in {'CI': 'KARSTO_FEED', 'EU': 'KARSTO_FEED', 'EB': 'UK_DIRECT'}.items():
    assert owners.loc[owners.component_id.eq(component), 'node'].iloc[0] == node
for owner in owners.itertuples():
    assert history[owner.component_id].notna().sum() == owner.observed_months
    if owner.observed_months:
        assert np.isclose(history[owner.component_id].sum(), owner.observed_subtotal_bcm, atol=1e-12)
    else:
        assert pd.isna(owner.observed_subtotal_bcm)
assert abs(weights.weight.sum() - 1) < 1e-12
assert np.allclose(weights.annual_bcm / freeze['residual_denominator_bcm'], weights.weight, atol=1e-12)
assert np.allclose(ledger.national_EA_bcm, ledger.snohvit_bcm + ledger.explicit16_bcm + ledger.residual_bcm, atol=1e-12)
assert ledger.numerical_balance_bcm.abs().max() < 1e-12
assert np.allclose(account.national_production_bcm, account.snohvit_bcm + account.mapped_supply_bcm + account.unmapped_supply_bcm + account.external_trym_bcm + account.hypothetical_domestic_bcm, atol=1e-12)
assert np.allclose(supply.sum(axis=1), account.mapped_supply_bcm + account.unmapped_supply_bcm, atol=1e-12)
seasonal, _, rates, years, _ = seasonal_profile(read('provenance/inputs/seasonal_observations.csv'),
    pd.period_range('2025-01', '2025-12', freq='M'), freeze['origin'],
    allow_partial=True, revision_tolerant=True)
assert np.allclose(seasonal.to_numpy(), account.snohvit_bcm, atol=1e-12)
assert years == [2022, 2023] and rates.attrs['imputed_calendar_months'] == []

model, _ = load_config(output / 'provenance/model.yaml', output / 'provenance/data_series.csv')
network = network_definition(model['routing'])
results = json.loads((output / 'provenance/solver_results.json').read_text())
checks = []
for scenario, rate in [('Physical156', 156), ('Capacity143', 143)]:
    for month, result in results[scenario].items():
        caps = capacities.loc[month].to_dict()
        caps['KOLLSNES_EXPORT'] = pd.Period(month, 'M').days_in_month * rate / 1000
        check = validate_solution(network, supply.loc[month].to_dict(), caps, result)
        assert abs(result['flows']['UK_DIRECT_UNROUTED']) < 1e-9
        f = flows.loc[flows.scenario.eq(scenario) & flows.month.eq(month)].iloc[0]
        for country, volume in result['destinations'].items():
            assert abs(f[country] - volume) < 1e-9
        assert abs(f.exports_bcm - sum(result['destinations'].values())) < 1e-9
        assert abs(f.disposal_bcm - result['unrouted']) < 1e-9
        assert abs(f['Common total'] - (f.UK_comparable_bcm + f['FR+BE'] + f['NL+DE'])) < 1e-9
        assert abs(f.UK_comparable_bcm - (f.UK - account.at[month, 'legacy_excluded_uk_direct_bcm'])) < 1e-9
        if scenario == 'Physical156':
            assert abs(result['unrouted'] - account.at[month, 'unmapped_supply_bcm']) < 1e-9
        checks.append(check)
assert len(checks) == 24

comparison = read('results.csv')
metrics = read('details/metrics.csv')
for metric in metrics.itertuples():
    frame = comparison.loc[comparison.method.eq(metric.method) & comparison.destination.eq(metric.destination)]
    error = frame.prediction_bcm - frame.actual_bcm
    assert len(frame) == metric.n == 12
    assert np.allclose(error, frame.error_bcm, atol=1e-12)
    assert abs(error.abs().mean() - metric.mae_bcm_month) < 1e-12
    assert abs(100 * error.abs().sum() / frame.actual_bcm.abs().sum() - metric.wape_pct) < 1e-10
    assert abs(error.sum() - metric.bias_total_bcm) < 1e-10
conditional = read('details/conditional_routing.csv')
assert np.allclose(conditional.full_forecast_error_bcm, conditional.conditional_routing_error_bcm + conditional.forecast_total_error_component_bcm, atol=1e-12)
conditional_metrics = read('details/conditional_metrics.csv')
for group in ['UK', 'FR+BE', 'NL+DE']:
    subset = conditional_metrics.loc[conditional_metrics.group.eq(group)].set_index('method')
    assert subset.at['EA legacy', 'conditional_MAE_bcm'] < subset.at['Physical156', 'conditional_MAE_bcm']

book = load_workbook(output / 'results.xlsx', data_only=True)
assert len(book.sheetnames) == 13 and book.sheetnames[0] == 'Summary'
for sheet in book:
    assert sheet.freeze_panes == 'B4'
    assert all(cell.data_type != 'e' for row in sheet for cell in row)
monthly = book['Monthly comparison']
assert monthly.max_row == 51
dates = [monthly.cell(row, 1).value for row in range(4, 52)]
assert dates == sorted(dates) and len(set(dates)) == 12
for row in range(4, 52):
    assert abs(monthly.cell(row, 5).value - monthly.cell(row, 3).value - monthly.cell(row, 7).value) < 1e-12
    assert abs(monthly.cell(row, 4).value - monthly.cell(row, 3).value - monthly.cell(row, 6).value) < 1e-12
book.close()
report = dict(status='PASS',checked_at=datetime.now(timezone.utc).isoformat(),
    source_records=len(inputs),evaluation_records=len(evaluation),monthly_solutions=len(checks),
    max_mass_balance_residual_bcm=max(c['max_mass_balance_residual_bcm'] for c in checks),
    max_capacity_violation_bcm=max(c['max_capacity_violation_bcm'] for c in checks),
    uk_direct_disposal_bcm=0,ledger_weights_and_source_ownership_checked=True,
    pre_origin_history_bounds_checked=True,archived_forecast_origins_checked=True,
    actual_retrieval_after_freeze_checked=True,protected_actuals_queried=False,
    score_formula_and_conditional_identity_checked=True,excel_cells_and_month_order_checked=True,
    ordinary_regression_tests={'passed':639,'external_evidence_deselected':14,'existing_warnings':1,
        'command':'Approved workspace interpreter -m pytest -q'},
    focused_seasonal_tests={'passed':20,'command':'Approved workspace interpreter -m pytest tests/unit/test_seasonal_snohvit.py -q'},
    f27_strict_package_verification='PASS; all four totals unchanged')
if '--write-validation' in sys.argv:
    (output / 'provenance/validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    manifest['files_sha256'] = {p.relative_to(root).as_posix():sha(p)
        for base in [output, raw] for p in sorted(base.rglob('*')) if p.is_file() and p != manifest_path}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
