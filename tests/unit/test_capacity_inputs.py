"""Synthetic capacity selection and conversion safeguards; no EA data calls."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from norway_gas_routing.capacity.conversion import (
    REQUIREMENTS, aggregate_converted_month, convert_gas_day_quantities)
from norway_gas_routing.capacity.inputs import (
    SCENARIOS, baseline_rate, database_candidates, dated_daily_rates, select_capacity_scenario)
from norway_gas_routing.capacity.public import gas_boundary
from norway_gas_routing.evaluation import EvaluationError
from norway_gas_routing.routing import monthly_available_capacity

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def prepared():
    model = yaml.safe_load((ROOT / 'config/model.yaml').read_text(encoding='utf-8'))
    months = pd.period_range('2024-01', '2024-02', freq='M')
    capacities, daily, monthly = {}, [], []
    for asset, entry in model['routing']['assets'].items():
        rate = entry.get('mcm_d', entry.get('annual_bcm', 0) * 1000 / 365)
        derate = pd.Series(2., index=pd.date_range('2024-01-01', '2024-02-29')) if entry.get('maintenance_series') else None
        if derate is not None:
            derate.iloc[0] = -2.
        m, d = monthly_available_capacity(pd.Series([rate], index=pd.to_datetime(['2024-01-01'])), months, derate)
        capacities[asset] = m.available_capacity_bcm
        daily.append(d.rename_axis('date').reset_index().assign(asset=asset))
        monthly.append(m.rename_axis('month').reset_index().assign(asset=asset))
    return model, dict(months=months, capacities=pd.DataFrame(capacities),
        capacity_daily=pd.concat(daily), capacity_monthly=pd.concat(monthly),
        supply=pd.DataFrame({'UNMAPPED': [1., 2.]}, index=months), preferences={'UK': 1.})


def test_default_isolated_unchanged_without_database(prepared):
    model, inputs = prepared
    selected = select_capacity_scenario(inputs, model)
    for key in ('capacities', 'capacity_daily', 'capacity_monthly', 'supply'):
        pd.testing.assert_frame_equal(selected[key], inputs[key])
    assert selected['selected_capacity_inputs'].fallback.all()
    selected['capacities'].iloc[0, 0] = 0
    assert inputs['capacities'].iloc[0, 0] > 0


def test_evidence_mode_retains_all_ineligible_baselines(prepared):
    model, inputs = prepared
    observations = database_candidates(ROOT, model, inputs['months'])
    assert not observations.optimiser_eligible.any()
    assert observations.candidate_bcm.isna().all()
    assert set(observations.operator.dropna()) == {'DK-TSO-0001', 'PL-TSO-0002'}
    assert len(observations.loc[observations.asset_key.eq('point:faxe_dk_technical')]) == 2
    selected = select_capacity_scenario(inputs, model, scenario='evidence-backed', candidates=observations)
    pd.testing.assert_frame_equal(selected['capacities'], inputs['capacities'])
    pd.testing.assert_frame_equal(observations, database_candidates(ROOT, model, inputs['months']))


@pytest.mark.parametrize('scenario', list(SCENARIOS)[2:])
def test_assumptions_are_not_verified_and_preserve_other_inputs(prepared, scenario):
    model, inputs = prepared
    result = select_capacity_scenario(inputs, model, scenario=scenario)
    pd.testing.assert_frame_equal(result['supply'], inputs['supply'])
    assert result['preferences'] == inputs['preferences']
    assert not result['selected_capacity_inputs'].public_candidate_eligible.any()
    for asset in inputs['capacities']:
        if asset not in SCENARIOS[scenario]:
            pd.testing.assert_series_equal(result['capacities'][asset], inputs['capacities'][asset])
    pd.testing.assert_series_equal(result['capacity_daily'].maintenance_derate_mcm_d,
                                   inputs['capacity_daily'].maintenance_derate_mcm_d)


def test_kollsnes_156_leap_and_signed_maintenance_once(prepared):
    model, inputs = prepared
    selected = select_capacity_scenario(inputs, model, scenario='kollsnes-156')
    delta = selected['capacities'].KOLLSNES_EXPORT - inputs['capacities'].KOLLSNES_EXPORT
    assert delta.tolist() == pytest.approx([13 * 31 / 1000, 13 * 29 / 1000])
    daily = selected['capacity_daily'].query("asset == 'KOLLSNES_EXPORT'")
    assert daily.iloc[0].available_capacity_mcm_d == 158.
    assert daily.available_capacity_mcm_d.sum() / 1000 == pytest.approx(selected['capacities'].KOLLSNES_EXPORT.sum())
    monthly = selected['capacity_monthly'].query("asset == 'KOLLSNES_EXPORT'")
    assert monthly.available_capacity_bcm.sum() == pytest.approx(selected['capacities'].KOLLSNES_EXPORT.sum())


@pytest.mark.parametrize('problem', ['missing', 'overlap', 'forward', 'negative'])
def test_dated_schedule_fails_closed(problem):
    intervals = [('2024-01-01', '2024-02-01', 156.)]
    if problem == 'missing': intervals[0] = ('2024-01-02', '2024-02-01', 156.)
    if problem == 'overlap': intervals.append(('2024-01-15', '2024-02-01', 144.5))
    if problem == 'negative': intervals[0] = ('2024-01-01', '2024-02-01', -1.)
    months = pd.period_range('2024-01', '2024-02' if problem == 'forward' else '2024-01', freq='M')
    with pytest.raises(ValueError): dated_daily_rates(intervals, months)


def test_half_open_sensitivity_dates_are_not_historical_actual():
    months = pd.period_range('2023-08', '2023-12', freq='M')
    early = dated_daily_rates(SCENARIOS['kollsnes-autumn-early']['KOLLSNES_EXPORT'], months)
    late = dated_daily_rates(SCENARIOS['kollsnes-autumn-late']['KOLLSNES_EXPORT'], months)
    assert early.loc['2023-08-31'] == 144.5
    assert early.loc['2023-09-01'] == 156
    assert late.loc['2023-11-30'] == 144.5
    assert late.loc['2023-12-01'] == 156


@pytest.mark.parametrize('problem', ['name', 'no_candidates', 'eligible', 'no_maintenance', 'changed_rating'])
def test_no_silent_activation_or_maintenance_overlap(prepared, problem):
    model, inputs = prepared
    kwargs = dict(scenario='kollsnes-156')
    if problem == 'name': kwargs['scenario'] = 'automatic'
    if problem == 'no_candidates': kwargs['scenario'] = 'evidence-backed'
    if problem == 'eligible': kwargs['candidates'] = pd.DataFrame({'optimiser_eligible': [True]})
    if problem == 'no_maintenance': inputs.pop('capacity_daily')
    if problem == 'changed_rating': inputs['capacity_daily'].loc[inputs['capacity_daily'].asset.eq('KOLLSNES_EXPORT'), 'technical_capacity_mcm_d'] = 156
    with pytest.raises(ValueError): select_capacity_scenario(inputs, model, **kwargs)


def conversion_fixture():
    contract = dict(identity=['DK-TSO-0001', 'ITP-00630', 'entry'],
        source_url='synthetic-fixture', source_sha256='synthetic', approval_reference='synthetic-only',
        monthly_basis='gas_day_start_label', factor_kind='capacity_basis_kwh_per_model_m3',
        factor_intervals=[dict(start='2024-01-01T06:00:00+01:00', end='2025-01-01T06:00:00+01:00', kwh_per_model_m3=10.)],
        **{key: True for key in REQUIREMENTS})
    days = []
    for day in pd.date_range('2024-01-01', '2024-12-31'):
        start, end = gas_boundary(day.date()), gas_boundary(day.date() + timedelta(days=1))
        hours = (pd.Timestamp(end).tz_convert('UTC') - pd.Timestamp(start).tz_convert('UTC')).total_seconds() / 3600
        days.append(dict(gas_day=day.strftime('%Y-%m-%d'), gas_day_start=start.isoformat(),
            gas_day_end=end.isoformat(), technical_kwh_per_gas_day=hours * 10e6, quality='complete'))
    return pd.DataFrame(days), contract


def test_conversion_quantities_not_rates_dst_leap_and_zero():
    days, contract = conversion_fixture()
    days.loc[0, ['technical_kwh_per_gas_day', 'quality']] = [0., 'reported_zero']
    converted = convert_gas_day_quantities(days, contract, asset_key='point:north_sea_technical')
    assert converted.iloc[0].candidate_bcm == 0
    assert converted.loc[converted.gas_day.eq('2024-03-30'), 'candidate_bcm'].iloc[0] == .023
    assert converted.loc[converted.gas_day.eq('2024-10-26'), 'candidate_bcm'].iloc[0] == .025
    assert aggregate_converted_month(converted, '2024-02')['candidate_bcm'] == pytest.approx(29 * .024)
    converted.loc[1, 'candidate_bcm'] = float('nan')
    assert aggregate_converted_month(converted, '2024-01')['candidate_bcm'] is None


@pytest.mark.parametrize('requirement', REQUIREMENTS)
def test_unsupported_conversion_rejected(requirement):
    days, contract = conversion_fixture()
    contract[requirement] = False
    with pytest.raises(ValueError): convert_gas_day_quantities(days, contract, asset_key='point:north_sea_technical')


@pytest.mark.parametrize('problem', ['identity', 'factor', 'basis', 'overlap', 'boundary', 'expired', 'split'])
def test_conversion_identity_reference_dates_and_temporal_controls(problem):
    days, contract = conversion_fixture()
    if problem == 'identity': contract['identity'][0] = 'PL-TSO-0002'
    if problem == 'factor': contract['factor_kind'] = 'measured_flow_gcv'
    if problem == 'basis': contract['monthly_basis'] = 'calendar'
    if problem == 'overlap': contract['factor_intervals'].append(deepcopy(contract['factor_intervals'][0]))
    if problem == 'boundary': days.loc[0, 'gas_day_start'] = '2024-01-01T00:00:00+01:00'
    if problem == 'expired': contract['factor_intervals'][0]['end'] = '2024-02-01T06:00:00+01:00'
    if problem == 'split': contract['factor_intervals'][0]['start'] = '2024-01-01T12:00:00+01:00'
    with pytest.raises(ValueError): convert_gas_day_quantities(days, contract, asset_key='point:north_sea_technical')


def test_holdout_rejected_before_database_values(prepared):
    model, inputs = prepared
    with pytest.raises(EvaluationError): database_candidates(ROOT, model, pd.period_range('2026-01', '2026-09', freq='M'))
    inputs['months'] = pd.period_range('2026-01', periods=1, freq='M')
    with pytest.raises(EvaluationError): select_capacity_scenario(inputs, model)
    days, contract = conversion_fixture()
    days.loc[0, 'gas_day'] = '2026-01-01'
    with pytest.raises(EvaluationError): convert_gas_day_quantities(days, contract, asset_key='point:north_sea_technical')


@pytest.mark.parametrize('column,value',[('asset_key','point:faxe_pl_technical'),('capacity_category','commercial_available'),('original_unit','kWh/h')])
def test_conversion_rejects_incompatible_source_rows(column,value):
    days,contract=conversion_fixture()
    days[column]=value
    with pytest.raises(ValueError): convert_gas_day_quantities(days,contract,asset_key='point:north_sea_technical')


def test_unknown_baseline_never_becomes_zero():
    assert baseline_rate({'mcm_d':0.})==0.
    for entry in ({},{'mcm_d':None},{'mcm_d':float('nan')}):
        with pytest.raises(ValueError): baseline_rate(entry)
