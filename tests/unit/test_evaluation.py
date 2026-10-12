"""Chronological gates use synthetic data, including inaccessible canary values."""
from copy import deepcopy
import json

import pandas as pd
import pytest

from norway_gas_routing.evaluation import (EvaluationError, check_dates, load_policy,
    read_parquet, request_bounds, validate_forecast_inputs, validate_manifest,
    reconstruction_evaluation)
from norway_gas_routing.poc import DESTINATIONS, historical_preferences
from norway_gas_routing import benchmark, project_data, reporting
from norway_gas_routing.poc_inputs import prepare_inputs, technical_capacity_points
from norway_gas_routing.series_audit import profile, compare_series
from norway_gas_routing.series_audit import forecast_coverage


@pytest.mark.parametrize('purpose', ['analysis', 'read', 'plot', 'score', 'selection', 'fit'])
@pytest.mark.parametrize('month', ['2026-01', '2026-09', '2026-12', '2030-01'])
def test_holdout_and_later_targets_rejected(purpose, month):
    with pytest.raises(EvaluationError, match='locked'):
        check_dates([month], purpose)


def test_validation_comparison_allowed_but_fitting_rejected():
    check_dates(['2025-01', '2025-12'], 'selection')
    with pytest.raises(EvaluationError):
        historical_preferences(pd.DataFrame(1., index=pd.period_range('2024-12', '2025-01', freq='M'), columns=DESTINATIONS))


def test_scores_do_not_blend_development_and_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark, 'OUT', tmp_path)
    rows = [{'method': 'legacy_asof', 'origin': '2024-06-30', 'level': 'five_groups',
             'destination': d, 'target_month': month, 'prediction_bcm': prediction, 'actual_bcm': 2.}
            for month, prediction in [('2024-12', 2.), ('2025-01', 4.)] for d in benchmark.GROUPS]
    _, metrics = benchmark.scores(rows)
    uk = metrics.loc[metrics.destination.eq('UK')].set_index('split')
    assert uk.at['development', 'wape_pct'] == 0
    assert uk.at['validation', 'wape_pct'] == 100
    assert uk.n.tolist() == [1, 1]


def test_seasonal_validation_predictions_ignore_validation_outcomes(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark, 'OUT', tmp_path)
    months = pd.period_range('2023-01', '2025-12', freq='M')
    history = pd.Series(2., index=months)
    origin = '2024-12-31'
    record = {'origin': origin, 'evidence_file': 'synthetic.json', 'metadata': {
        'forecast_start_date': '2024-12-01', 'unit': 'bcm', 'lifecycle_stage': 'forecast',
        'source_file': 'Norwegian flows model.xlsx'}}
    snapshot = {name: (history.copy(), record) for name in benchmark.SUFFIX}
    first = benchmark.forecast_rows({name: history.copy() for name in benchmark.SUFFIX}, {origin: snapshot})
    altered = history.copy(); altered.loc['2025'] = 999.
    snapshot = {name: (altered.copy(), record) for name in benchmark.SUFFIX}
    second = benchmark.forecast_rows({name: altered.copy() for name in benchmark.SUFFIX}, {origin: snapshot})
    assert [r['prediction_bcm'] for r in first if r['method'] == 'seasonal_asof'] == [
        r['prediction_bcm'] for r in second if r['method'] == 'seasonal_asof']
    assert pd.read_csv(tmp_path / 'seasonal_training_vintages.csv').month.max() < '2025-01'


def test_forecast_horizon_cannot_cross_holdout(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark, 'OUT', tmp_path / 'not-created')
    with pytest.raises(EvaluationError, match='locked'):
        benchmark.forecast_rows({}, {'2025-06-30': {}})
    assert not (tmp_path / 'not-created').exists()


def test_relative_requests_and_generic_holdout_reads_fail_before_connection(monkeypatch):
    from norway_gas_routing import data_functions
    with pytest.raises(EvaluationError, match='absolute'):
        request_bounds('-1yb', 'MAX')
    monkeypatch.setattr(data_functions, '_client', lambda *a: pytest.fail('Connection attempted'))
    with pytest.raises(EvaluationError, match='locked'):
        data_functions.get_series_frame({'x': 'synthetic'}, end='2026-01-01')


def test_fixed_policy_cannot_be_unlocked(tmp_path):
    policy = load_policy(); policy.pop('config_sha256'); policy['holdout']['locked'] = False
    path = tmp_path / 'evaluation.yaml'; path.write_text(json.dumps(policy))
    with pytest.raises(EvaluationError, match='unlock'):
        load_policy(path)


@pytest.mark.parametrize('period_index', [False, True])
def test_cached_reads_filter_reserved_values_before_pandas_load(tmp_path, monkeypatch, period_index):
    dates = pd.period_range('2024-12', '2026-09', freq='M')
    index = dates if period_index else dates.to_timestamp()
    path = tmp_path / 'raw.parquet'
    frame = pd.DataFrame({'value': range(len(index))}, index=index)
    frame.to_parquet(path)
    original = pd.read_parquet
    calls = []
    def bounded(*args, **kwargs):
        assert kwargs.get('filters') is not None, 'Unbounded read attempted'
        calls.append(kwargs['filters'])
        return original(*args, **kwargs)
    monkeypatch.setattr(pd, 'read_parquet', bounded)
    if period_index:
        with pytest.raises(EvaluationError, match='crosses requested boundary'):
            read_parquet(path)
        assert not calls  # Only dates were inspected; no values loaded.
        return
    loaded = read_parquet(path)
    assert len(loaded) == 13 and loaded.index.max() == index[12]
    assert len(read_parquet(path, purpose='fit')) == 1
    with pytest.raises(EvaluationError):
        read_parquet(path, end='2026-01-01')
    assert len(calls) == 2


def test_cached_daily_date_column(tmp_path):
    path = tmp_path / 'days.parquet'
    pd.DataFrame({'calendar_date': pd.to_datetime(['2025-12-31', '2026-01-01']), 'value': [1, 999]}).to_parquet(path)
    assert read_parquet(path, date_column='calendar_date').value.tolist() == [1]


def test_technical_csv_rejects_reserved_dates_before_loading_values(tmp_path, monkeypatch):
    path = tmp_path / 'capacity.csv'
    path.write_text('date,technical_capacity_mcm_d\n2025-12-31,10\n2026-01-01,999\n')
    original = pd.read_csv
    def date_only(*args, **kwargs):
        assert kwargs.get('usecols') == ['date'], 'Capacity values were loaded before checking dates'
        return original(*args, **kwargs)
    monkeypatch.setattr(pd, 'read_csv', date_only)
    with pytest.raises(EvaluationError, match='locked'):
        technical_capacity_points(path)


def test_permitted_technical_csv_retains_signed_or_zero_values(tmp_path):
    path = tmp_path / 'capacity.csv'
    path.write_text('date,technical_capacity_mcm_d\n2024-01-01,0\n2024-02-01,10\n')
    assert technical_capacity_points(path).tolist() == [0, 10]


def test_raw_requests_block_before_connection(monkeypatch):
    monkeypatch.setattr(project_data, 'series_info', lambda *a, **k: {'key': 'x', 'sid': 'synthetic', 'status': 'REVIEW'})
    def forbidden(*args):
        pytest.fail('Connection attempted before checking dates')
    monkeypatch.setattr(project_data.sj, '_client', forbidden)
    with pytest.raises(EvaluationError):
        project_data.get_registered_series('x', end='2026-01-01')
    assert request_bounds() == ('MIN', '2025-12-31')


def bundle():
    records = []
    for category in ('production', 'maintenance', 'technical_capacity', 'historical_flows', 'prices'):
        origin = '2024-12-31T23:59:59Z'
        records.append({'key': category, 'category': category, 'sha256': 'synthetic',
            'evidence_file': 'synthetic.json', 'query': 'sid=synthetic@asof:' + origin,
            'asof': origin, 'available_at': '2024-12-30T00:00:00Z',
            'availability_verified': True, 'archive_verified': True,
            'kind': 'actual' if category == 'historical_flows' else 'forecast',
            'target_months': ['2024-11'] if category == 'historical_flows' else ['2025-01'],
            'forecast_start': '2025-01', 'effective_at': '2025-01-01'})
    return records


def test_valid_origin_bundle_including_known_future_maintenance():
    records = bundle()
    records[1]['kind'] = 'known_plan'
    records[2]['kind'] = 'technical_schedule'
    assert validate_forecast_inputs(records, '2024-12-31T23:59:59Z', price_enabled=True)


@pytest.mark.parametrize('category', ['production', 'maintenance', 'technical_capacity', 'historical_flows', 'prices'])
@pytest.mark.parametrize('change', [
    {'available_at': '2025-01-01T00:00:00Z'},
    {'asof': '2025-01-01T00:00:00Z'},
    {'availability_verified': False}, {'archive_verified': False},
    {'sha256': None}, {'query': 'sid=synthetic'}, {'target_months': []}])
def test_future_or_unproven_input_cannot_be_forecast(category, change):
    records = bundle()
    next(r for r in records if r['category'] == category).update(change)
    with pytest.raises(EvaluationError):
        validate_forecast_inputs(records, '2024-12-31T23:59:59Z', price_enabled=True)


def test_validation_vintage_cannot_refit_training():
    records = bundle()
    for r in records:
        if r['category'] != 'historical_flows':
            r['target_months'] = ['2025-02']
    records[-2].update(asof='2025-01-31T23:59:59Z', available_at='2025-01-30T00:00:00Z',
        query='sid=synthetic@asof:2025-01-31T23:59:59Z')
    with pytest.raises(EvaluationError, match='training information cutoff'):
        validate_forecast_inputs(records, '2025-01-31T23:59:59Z')


def test_future_actuals_and_undated_capacity_rejected():
    records = bundle(); records[0]['kind'] = 'actual'
    with pytest.raises(EvaluationError, match='Future realised'):
        validate_forecast_inputs(records, '2024-12-31T23:59:59Z')
    records = bundle(); records[2].pop('effective_at')
    with pytest.raises(EvaluationError, match='effectiveness'):
        validate_forecast_inputs(records, '2024-12-31T23:59:59Z')
    with pytest.raises(EvaluationError, match='missing input categories'):
        validate_forecast_inputs(records[:1], '2024-12-31T23:59:59Z')


@pytest.mark.parametrize('field', ['asof', 'available_at', 'effective_at'])
def test_missing_parsed_vintage_dates_fail_closed(field):
    records = bundle()
    record = records[2]
    record[field] = 'NaT'
    record['query'] = 'sid=synthetic@asof:' + record['asof']
    with pytest.raises(EvaluationError):
        validate_forecast_inputs(records, '2024-12-31T23:59:59Z')


def test_capacity_cannot_be_backfilled_before_effective_date():
    records = bundle(); records[2]['effective_at'] = '2025-01-02'
    with pytest.raises(EvaluationError, match='effective throughout'):
        validate_forecast_inputs(records, '2024-12-31T23:59:59Z')


def test_future_forecast_start_is_withheld_without_inspecting_values():
    values = pd.Series(['unreadable canary'], index=pd.to_datetime(['2025-12-01']))
    assert forecast_coverage(values, '2026-01-01', '2025-12-31', 'monthly') == 'WITHHELD_BY_POLICY'
    with pytest.raises(EvaluationError, match='locked'):
        forecast_coverage(values, '', '2026-01-01', 'monthly')


def test_holdout_cannot_be_scored_profiled_or_plotted(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark, 'OUT', tmp_path / 'scores')
    rows = [{'target_month': '2026-01', 'actual_bcm': 999, 'prediction_bcm': 1}]
    with pytest.raises(EvaluationError):
        benchmark.scores(rows)
    assert not (tmp_path / 'scores').exists()
    future = pd.Series([999.], index=pd.to_datetime(['2026-01-01']))
    with pytest.raises(EvaluationError):
        profile(future)
    with pytest.raises(EvaluationError):
        compare_series(future, future)
    pd.DataFrame(rows).to_csv(tmp_path / 'results.csv', index=False)
    with pytest.raises(EvaluationError):
        reporting.forecast_charts(tmp_path)
    assert not (tmp_path / 'details').exists()


def test_poc_rejects_future_or_forecast_before_input_io():
    with pytest.raises(EvaluationError, match='reconstruction only'):
        prepare_inputs(None, {}, None, analysis_mode='retrospective_forecast')
    with pytest.raises(EvaluationError, match='locked'):
        prepare_inputs(None, {'poc': {'start': '2026-01', 'end': '2026-09',
            'baseline_start': '2023-01', 'baseline_end': '2023-12'}}, None)


def test_validation_manifest_keeps_development_parameters_and_reconstruction_label():
    inputs = {'months': pd.period_range('2025-01', '2025-12', freq='M'),
              'training_observations': pd.DataFrame(index=pd.period_range('2023-01', '2023-12', freq='M')),
              'preferences': {'UK': 1.}, 'provenance': []}
    evaluation = reconstruction_evaluation(None, inputs, {'baseline_start': '2023-01', 'baseline_end': '2023-12'}, 'synthetic')
    manifest = {'run_id': 'synthetic', 'evaluation': evaluation}
    validate_manifest(manifest)
    assert evaluation['period_role'] == 'validation comparison only'
    assert not evaluation['complete_origin_vintages']
    altered = deepcopy(manifest); altered['evaluation']['target_end'] = '2026-01'
    with pytest.raises(EvaluationError):
        validate_manifest(altered)
    altered = deepcopy(manifest); altered['evaluation']['model_parameters']['historical_routing_shares']['UK'] = .5
    with pytest.raises(EvaluationError, match='identity mismatch'):
        validate_manifest(altered)
