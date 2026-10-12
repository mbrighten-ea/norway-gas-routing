"""Optional empirical incentives preserve lexicographic physical safeguards."""
import math
from pathlib import Path
import pytest
import yaml
from norway_gas_routing.routing import (DESTINATIONS, available_solver, build_month,
                                       network_definition, solve_month, validate_solution)


def fixture():
    root = Path(__file__).resolve().parents[2]
    model = yaml.safe_load((root/'config/model.yaml').read_text(encoding='utf-8'))
    network = network_definition(model['routing'])
    supply = {n: 0. for n, e in network['nodes'].items() if e['kind'] == 'source'}
    supply.update(KOLLSNES_FEED=5., KARSTO_FEED=3., UNMAPPED=.5)
    caps = {a: 20. for a in model['routing']['assets']}
    caps.update(KOLLSNES_EXPORT=4., EUROPIPE_II=2., NORTH_SEA_ENTRY=1., BALTIC_PIPE=.5)
    prefs = dict(zip(DESTINATIONS, [.3, .2, .1, .1, .2, .05, .05]))
    return network, supply, caps, prefs, available_solver('HiGHS')[1]


@pytest.mark.parametrize('cap', [4., 5.])
def test_zero_is_identical_and_input_isolation(cap):
    network, supply, caps, prefs, solver = fixture()
    caps['KOLLSNES_EXPORT'] = cap
    old = solve_month(build_month(network, supply, caps, prefs), solver)
    zero = solve_month(build_month(network, supply, caps, prefs), solver,
                       responsiveness=0., price_spreads={'UK': 100., 'FR': -100., 'DE_NL': 50.})
    assert zero['destinations'] == pytest.approx(old['destinations'], abs=1e-9)
    assert zero['unrouted'] == pytest.approx(old['unrouted'], abs=1e-9)
    assert prefs['UK'] == .3 and caps['KOLLSNES_EXPORT'] == cap


@pytest.mark.parametrize('market', ['UK', 'FR', 'DE_NL'])
def test_positive_shock_responds_without_losing_exports(market):
    network, supply, caps, prefs, solver = fixture()
    old = solve_month(build_month(network, supply, caps, prefs), solver)
    spreads = dict(UK=0., FR=0., DE_NL=0.)
    spreads[market] = 50.
    built = build_month(network, supply, caps, prefs)
    result = solve_month(built, solver, responsiveness=4., price_spreads=spreads)
    names = ['DE', 'NL'] if market == 'DE_NL' else [market]
    assert sum(result['destinations'][d] for d in names) > sum(old['destinations'][d] for d in names)
    assert result['unrouted'] == pytest.approx(old['unrouted'], abs=1e-9)
    assert result['stage2_final_bcm_equivalent'] == pytest.approx(result['stage2_optimum_bcm_equivalent'], abs=1e-8)
    assert 'fix_combined_stage2' in {c.name for c in built['problem'].constraints()}
    assert 'fix_baseline_deviation' not in {c.name for c in built['problem'].constraints()}
    validate_solution(network, supply, caps, result, tolerance=1e-8)


@pytest.mark.parametrize('bad', [-1., math.inf, math.nan, True])
def test_invalid_strength_fails(bad):
    network, supply, caps, prefs, solver = fixture()
    with pytest.raises(ValueError):
        solve_month(build_month(network, supply, caps, prefs), solver, responsiveness=bad)


@pytest.mark.parametrize('spreads', [None, {'UK': 1.}, {'UK': 1., 'FR': 0., 'DE_NL': 0., 'BE': 1.},
                                    {'UK': math.nan, 'FR': 0., 'DE_NL': 0.}])
def test_unapproved_markets_and_missing_spreads_fail(spreads):
    network, supply, caps, prefs, solver = fixture()
    with pytest.raises(ValueError):
        solve_month(build_month(network, supply, caps, prefs), solver,
                    responsiveness=1., price_spreads=spreads)


def test_strength_increases_incentive_score_and_relaxes_old_l1_optimum():
    network, supply, caps, prefs, solver = fixture()
    results = [solve_month(build_month(network, supply, caps, prefs), solver,
                          responsiveness=strength, price_spreads={'UK': 20., 'FR': 0., 'DE_NL': 0.})
               for strength in [0., .25, 1., 4.]]
    uk = [r['destinations']['UK'] for r in results]
    assert all(b >= a-1e-9 for a, b in zip(uk, uk[1:]))
    assert uk[-1] > uk[0]
    assert results[-1]['minimum_baseline_deviation_bcm'] > results[0]['minimum_baseline_deviation_bcm']


def test_negative_shock_discourages_market_but_never_withholds_exports():
    network, supply, caps, prefs, solver = fixture()
    baseline = solve_month(build_month(network, supply, caps, prefs), solver)
    shocked = solve_month(build_month(network, supply, caps, prefs), solver,
                          responsiveness=4., price_spreads={'UK': -50., 'FR': 0., 'DE_NL': 0.})
    assert shocked['destinations']['UK'] < baseline['destinations']['UK']
    assert shocked['unrouted'] == pytest.approx(baseline['unrouted'], abs=1e-9)
    validate_solution(network, supply, caps, shocked)
