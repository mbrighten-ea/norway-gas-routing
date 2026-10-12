"""Physical scenario effects and serial point bounds on synthetic supplies."""
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest
import yaml

from norway_gas_routing.capacity.constraints import add_reviewed_point_bounds
from norway_gas_routing.capacity.contract import IDENTITIES
from norway_gas_routing.capacity.inputs import select_capacity_scenario
from norway_gas_routing.routing import (
    DESTINATIONS, available_solver, build_month, network_definition, solve_month, validate_solution)

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    model = yaml.safe_load((ROOT / 'config/model.yaml').read_text(encoding='utf-8'))
    network = network_definition(model['routing'])
    supply = {n: 0. for n,e in network['nodes'].items() if e['kind'] == 'source'}
    capacity = {a: 20. for a in model['routing']['assets']}
    preferences = {d: 0. for d in DESTINATIONS}
    preferences['PL'] = .8
    preferences['DK'] = .2
    return model,network,supply,capacity,preferences,available_solver('HiGHS')[1]


def point(key, value):
    identity = IDENTITIES[key]
    return dict(asset_key=key, operator=identity[0], point=identity[1], direction=identity[2],
        arc=identity[3], status='VERIFIED_COMPATIBLE', optimiser_eligible=True,
        capacity_category='point_technical', coverage_status='complete',
        activation_reference='synthetic-only', conversion_approved=True,
        candidate_bcm=value, maintenance_deductions=0)


def test_serial_faxe_limits_minimum_not_sum_and_dk_unaffected():
    model,network,supply,capacity,prefs,solver = fixture()
    supply['KARSTO_FEED'] = 10.
    capacity['KARSTO_STATPIPE'] = 0.
    capacity['EUROPIPE_II'] = 10.
    built = build_month(network,supply,capacity,prefs)
    built['problem'] += built['destinations']['DE'] == 0
    built['problem'] += built['destinations']['NL'] == 0
    rows = [point('point:north_sea_technical',10.), point('point:faxe_dk_technical',8.), point('point:faxe_pl_technical',5.)]
    add_reviewed_point_bounds(built,rows)
    result=solve_month(built,solver)
    assert result['destinations']['PL'] == pytest.approx(5.)
    assert result['destinations']['DK'] == pytest.approx(5.)
    assert result['unrouted'] == pytest.approx(0.)
    validate_solution(network,supply,capacity,result)
    assert len([c for c in built['problem'].constraints() if c.name.startswith('public_point_')]) == 3


@pytest.mark.parametrize('problem',['duplicate','commercial','numeric_only','derate','identity','missing'])
def test_point_values_cannot_activate_without_all_gates(problem):
    model,network,supply,capacity,prefs,solver = fixture()
    rows=[point('point:faxe_pl_technical',5.)]
    if problem=='duplicate': rows.append(deepcopy(rows[0]))
    if problem=='commercial': rows[0]['capacity_category']='commercial_available'
    if problem=='numeric_only': rows[0]['status']='CONDITIONAL'
    if problem=='derate': rows[0]['maintenance_deductions']=1.
    if problem=='identity': rows[0]['direction']='exit'
    if problem=='missing': rows[0]['candidate_bcm']=None
    with pytest.raises(ValueError): add_reviewed_point_bounds(build_month(network,supply,capacity,prefs),rows)


def test_capacity_correction_reroutes_only_mapped_supply_and_balances():
    model,network,supply,capacity,prefs,solver = fixture()
    supply.update(KOLLSNES_FEED=4.7, UNMAPPED=.5)
    capacity['KOLLSNES_EXPORT']=143.*31/1000
    model['routing']['assets']['KOLLSNES_EXPORT'].pop('maintenance_series')
    month=pd.Period('2024-01','M')
    prepared=dict(months=pd.PeriodIndex([month]),capacities=pd.DataFrame([capacity],index=[month]),
                  supply=pd.DataFrame([supply],index=[month]))
    candidate=select_capacity_scenario(prepared,model,scenario='kollsnes-156')
    baseline=solve_month(build_month(network,supply,capacity,prefs),solver)
    revised_caps=candidate['capacities'].loc[month].to_dict()
    revised=solve_month(build_month(network,supply,revised_caps,prefs),solver)
    assert baseline['unrouted']==pytest.approx(.5+4.7-4.433)
    assert revised['unrouted']==pytest.approx(.5)
    assert revised['flows']['UNMAPPED_UNROUTED']==.5
    validate_solution(network,supply,revised_caps,revised)
    repeated=solve_month(build_month(network,supply,revised_caps,prefs),solver)
    assert repeated['destinations']==pytest.approx(revised['destinations'])


def test_genuine_zero_point_bound_blocks_poland_only():
    model,network,supply,capacity,prefs,solver = fixture()
    supply['KARSTO_FEED']=1.
    built=build_month(network,supply,capacity,prefs)
    add_reviewed_point_bounds(built,[point('point:faxe_pl_technical',0.)])
    result=solve_month(built,solver)
    assert result['destinations']['PL']==pytest.approx(0.)
    assert result['unrouted']==pytest.approx(0.)
    validate_solution(network,supply,capacity,result)


def test_karsto_97_proxy_is_redundant_behind_85_5_outlet_sum():
    model,network,supply,capacity,prefs,solver=fixture()
    supply['KARSTO_FEED']=4.
    capacity.update(KARSTO_PROCESSING=95.*31/1000,KARSTO_STATPIPE=12.*31/1000,EUROPIPE_II=73.5*31/1000)
    baseline=solve_month(build_month(network,supply,capacity,prefs),solver)
    capacity['KARSTO_PROCESSING']=97.*31/1000
    revised=solve_month(build_month(network,supply,capacity,prefs),solver)
    assert revised['unrouted']==pytest.approx(baseline['unrouted'])
    assert sum(revised['destinations'].values())==pytest.approx(85.5*31/1000)
    validate_solution(network,supply,capacity,revised)
