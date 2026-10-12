"""The explicit diagnostic must preserve signed bcm and normal-input guards."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
from norway_gas_routing.routing_inputs import diagnostic_snohvit_values, prepare_inputs
from norway_gas_routing.evaluation import EvaluationError

MONTHS = pd.period_range('2025-01', '2025-12', freq='M')


def test_signed_monthly_bcm_is_copied_without_conversion_or_clipping():
    values = pd.Series(.3, index=MONTHS)
    values.iloc[4] = -.002
    result = diagnostic_snohvit_values(MONTHS, values, 'official-net-production')
    pd.testing.assert_series_equal(result, values)
    assert result is not values


@pytest.mark.parametrize('scenario', [None, 'actual', 'baseline'])
def test_scenario_must_be_explicit(scenario):
    with pytest.raises(ValueError, match='scenario'):
        diagnostic_snohvit_values(MONTHS, pd.Series(.3, index=MONTHS), scenario)


@pytest.mark.parametrize('values', [None, pd.Series(.3, index=MONTHS[:11]),
    pd.Series(.3, index=MONTHS.to_timestamp()), pd.Series(float('nan'), index=MONTHS),
    pd.Series(float('inf'), index=MONTHS)])
def test_no_missing_nonfinite_or_unindexed_override(values):
    with pytest.raises(ValueError):
        diagnostic_snohvit_values(MONTHS, values, 'selected-series-mixed-vintage')


def test_diagnostic_cannot_cover_training_or_partial_months():
    for months in (pd.period_range('2024-01', '2024-12', freq='M'), MONTHS[:7]):
        with pytest.raises(ValueError, match='full-year 2025'):
            diagnostic_snohvit_values(months, pd.Series(.3, index=months), 'official-net-production')


def test_normal_reader_rejects_override_before_any_io():
    with pytest.raises(ValueError, match='explicit snohvit_sensitivity'):
        prepare_inputs(Path('does-not-exist'), {}, None,
                       diagnostic_snohvit_bcm=pd.Series(.3, index=MONTHS))


def test_holdout_rejected_before_diagnostic_values_or_io():
    model = {'routing': {'start': '2026-01', 'end': '2026-09',
                     'baseline_start': '2023-01', 'baseline_end': '2023-12'}}
    with pytest.raises(EvaluationError):
        prepare_inputs(Path('does-not-exist'), deepcopy(model), None,
                       analysis_mode='snohvit_sensitivity', diagnostic_scenario='official-net-production',
                       diagnostic_snohvit_bcm=pd.Series(.3, index=MONTHS))


def diagnostic_command():
    path = Path(__file__).resolve().parents[2] / 'scripts/run/run_snohvit_sensitivity.py'
    spec = importlib.util.spec_from_file_location('snohvit_command', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_parser_skips_holdout_values_and_keeps_signed_net(tmp_path):
    page = '<caption>Production , saleable</caption><thead>Net gas [bill Sm3]</thead>'
    page += '<tr><td>2025</td></tr>'
    page += ''.join(f'<tr><td>{m}</td><td>oil</td><td>{-.01 if m == 5 else .3}</td></tr>'
                    for m in range(1, 13))
    page += '<tr><td>2026</td></tr><tr><td>1</td><td>oil</td><td>DO NOT PARSE</td></tr></table>'
    path = tmp_path / 'official.html'
    path.write_text(page, encoding='utf-8')
    values = diagnostic_command().official_snohvit(path)
    assert values.index.equals(MONTHS)
    assert values.at[pd.Period('2025-05', freq='M')] == -.01


def test_signed_observations_score_without_denominator_cancellation():
    cells = pd.DataFrame({'scenario': ['synthetic'] * 2, 'level': ['seven_countries'] * 2,
        'destination': ['DK'] * 2, 'month': MONTHS[:2], 'observed_bcm': [-1., 3.],
        'modelled_bcm': [0., 2.], 'error_bcm': [1., -1.], 'share_eligible': [False, True]})
    row = diagnostic_command().score(cells).iloc[0]
    assert row.WAPE_pct == 50
    assert row.MAE_bcm_per_cell == 1
    assert row.signed_bias_total_bcm == 0
    assert row.matched_months == 2
    assert row.share_eligible_months == 1
