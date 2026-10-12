"""Synthetic physical envelopes: export preservation and independent extrema."""
import importlib.util
from pathlib import Path

import pulp
import pytest
from norway_gas_routing.poc import DESTINATIONS, available_solver, build_month, network_definition, validate_solution

path = Path(__file__).resolve().parents[2] / 'scripts/run/run_routing_flexibility.py'
spec = importlib.util.spec_from_file_location('routing_flexibility', path)
flexibility = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flexibility)


@pytest.fixture
def physical_case():
    nodes = {n: {'kind': 'source'} for n in ('SRC', 'UK_DIRECT', 'UNMAPPED')}
    nodes.update({n: {'kind': 'junction'} for n in ('CORE', 'POOL', 'SPLIT')})
    nodes.update({d: {'kind': 'destination'} for d in DESTINATIONS})
    nodes['UNROUTED'] = {'kind': 'unrouted'}
    edges = [('SRC', 'CORE', None), ('CORE', 'POOL', 'POOL_CAP'), ('POOL', 'DE', None),
        ('POOL', 'NL', None), ('CORE', 'FR', 'FR_CAP'), ('CORE', 'BE', 'BE_CAP'),
        ('CORE', 'UK', 'UK_CAP'), ('CORE', 'SPLIT', 'NSE_CAP'), ('SPLIT', 'DK', None),
        ('SPLIT', 'PL', 'PL_CAP'), ('UK_DIRECT', 'UK', None)]
    arcs = [{'id': f'arc_{i}', 'from': a, 'to': b, 'asset': cap} for i, (a, b, cap) in enumerate(edges)]
    network = network_definition({'nodes': nodes, 'arcs': arcs})
    supply = {'SRC': 10., 'UK_DIRECT': 2., 'UNMAPPED': 1.}
    capacities = {'POOL_CAP': 5., 'FR_CAP': 3., 'BE_CAP': 4., 'UK_CAP': 4., 'NSE_CAP': 2., 'PL_CAP': 1.}
    return network, supply, capacities


def test_stage1_matches_existing_equations_without_preference_rows(physical_case):
    network, supply, capacities = physical_case
    _, solver = available_solver('HiGHS')
    physical = flexibility.physical_problem(network, supply, capacities)
    stage1 = flexibility.solved_values(physical, solver)
    existing = build_month(network, supply, capacities, {d: 1 / 7 for d in DESTINATIONS})
    existing['problem'].solve(solver)
    assert stage1['unrouted'] == pytest.approx(pulp.value(existing['unrouted']))
    assert stage1['unrouted'] == pytest.approx(1)
    assert all(c.name.startswith(('balance_', 'capacity_')) for c in physical['problem'].constraints())
    assert 'preferences' not in physical and 'deviation' not in physical


def test_extrema_keep_total_exports_and_shared_capacities(physical_case):
    network, supply, capacities = physical_case
    stage1, endpoints = flexibility.envelopes(network, supply, capacities, available_solver('HiGHS')[1])
    assert len(endpoints) == 14
    for result, checks, _ in endpoints.values():
        assert sum(result['destinations'].values()) == pytest.approx(12)
        assert result['unrouted'] == pytest.approx(stage1['unrouted'])
        assert result['destinations']['DE'] + result['destinations']['NL'] <= 5 + 1e-9
        assert result['destinations']['DK'] + result['destinations']['PL'] <= 2 + 1e-9
        assert result['flows']['UNMAPPED_UNROUTED'] == pytest.approx(1)
        assert validate_solution(network, supply, capacities, result) == checks
    assert endpoints['DE', 'maximum'][0]['destinations']['DE'] == pytest.approx(5)
    assert endpoints['NL', 'maximum'][0]['destinations']['NL'] == pytest.approx(5)
    # The separately attainable maxima cannot be added into a joint allocation.
    assert endpoints['DE', 'maximum'][0]['destinations']['DE'] + endpoints['NL', 'maximum'][0]['destinations']['NL'] > 5
    assert endpoints['UK', 'minimum'][0]['destinations']['UK'] == pytest.approx(2)
    assert endpoints['UK', 'maximum'][0]['destinations']['UK'] == pytest.approx(6)
    assert endpoints['PL', 'maximum'][0]['destinations']['PL'] == pytest.approx(1)
    assert endpoints['FR', 'maximum'][0]['destinations']['FR'] == pytest.approx(3)


def test_constraint_dual_identifies_a_direct_capacity_ceiling(physical_case):
    network, supply, capacities = physical_case
    _, endpoints = flexibility.envelopes(network, supply, capacities, available_solver('HiGHS')[1])
    assert -endpoints['FR', 'maximum'][2]['FR_CAP'] == pytest.approx(1)


@pytest.mark.parametrize('invalid', ['negative_supply', 'missing_asset'])
def test_bad_physical_inputs_are_not_filled(physical_case, invalid):
    network, supply, capacities = physical_case
    if invalid == 'negative_supply':
        supply['SRC'] = -1
    else:
        capacities.pop('POOL_CAP')
    with pytest.raises(ValueError):
        flexibility.physical_problem(network, supply, capacities)
