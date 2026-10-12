"""Synthetic physical-network checks; live data and services are never required."""

from copy import deepcopy

import pandas as pd
import pulp
import pytest
import yaml

from norway_gas_routing.poc import (DESTINATIONS, SolverUnavailable, available_solver,
    build_month, historical_preferences, monthly_available_capacity, network_definition,
    network_graph, solve_month, validate_solution)


@pytest.fixture
def network(repo_root):
    settings = yaml.safe_load((repo_root / "config/model.yaml").read_text())["poc"]
    return network_definition(settings)


def fixture_values(network):
    supply = {n: 0.0 for n, e in network["nodes"].items() if e["kind"] == "source"}
    capacities = {a["asset"]: 100.0 for a in network["arcs"] if a["asset"]}
    result = {"flows": {a["id"]: 0.0 for a in network["arcs"]},
              "destinations": {d: 0.0 for d in DESTINATIONS}, "unrouted": 0.0}
    return supply, capacities, result


def karsto_candidate(network):
    supply, capacities, result = fixture_values(network)
    supply["KARSTO_FEED"] = 10
    capacities.update(KARSTO_PROCESSING=6, EUROPIPE_II=4, NORTH_SEA_ENTRY=3, BALTIC_PIPE=2)
    result["flows"].update(KARSTO_PROCESSING=6, KARSTO_STATPIPE=2, EUROPIPE_II=4,
        EUROPIPE_II_DORNUM=1, NORTH_SEA_ENTRY=3, BALTIC_PIPE=2, DK_OFFTAKE=1,
        PL_DELIVERY=2, DE_ALLOCATION_PROXY=1, LANGELED_SOUTH=2, KARSTO_FEED_UNROUTED=4)
    result["destinations"].update(UK=2, DE=1, DK=1, PL=2)
    result["unrouted"] = 4
    return supply, capacities, result


def test_graph_contains_all_lp_nodes_parallel_arcs_and_disposal(network):
    supply, capacities, _ = fixture_values(network)
    built = build_month(network, supply, capacities, {d: 1 / 7 for d in DESTINATIONS})
    graph = network_graph(network)
    assert set(graph.nodes) == set(network["nodes"])
    assert {k for _, _, k in graph.edges(keys=True)} == set(built["flows"])
    assert set(graph.nodes) == {c.name.removeprefix("balance_") for c in built["problem"].constraints()
                                if c.name.startswith("balance_")}
    assert graph.number_of_edges("KOLLSNES", "CORE") == 2
    assert graph.number_of_edges("UNMAPPED", "UNROUTED") == 1
    assert set(built["destinations"]) == set(DESTINATIONS)


def test_shared_processing_transit_and_epii_candidate_balances(network):
    supply, capacities, result = karsto_candidate(network)
    checks = validate_solution(network, supply, capacities, result)
    assert checks == {"max_mass_balance_residual_bcm": 0, "max_capacity_violation_bcm": 0}


@pytest.mark.parametrize("asset", ["KARSTO_PROCESSING", "EUROPIPE_II", "NORTH_SEA_ENTRY", "BALTIC_PIPE"])
def test_shared_bottlenecks_reject_individually_valid_branch_totals(network, asset):
    supply, capacities, result = karsto_candidate(network)
    capacities[asset] -= .1
    with pytest.raises(ValueError, match="capacity"):
        validate_solution(network, supply, capacities, result)


def test_ogt_is_before_both_heimdal_routes(network):
    supply, capacities, result = fixture_values(network)
    supply["OSEBERG"] = 2
    capacities["OGT"] = 2
    result["flows"].update(OGT=2, VESTERLED=1, HEIMDAL_STATPIPE=1, ZEEPIPE_EXPORT=1)
    result["destinations"].update(UK=1, BE=1)
    validate_solution(network, supply, capacities, result)
    capacities["OGT"] = 1.5
    with pytest.raises(ValueError, match="capacity"):
        validate_solution(network, supply, capacities, result)


def test_rerouting_around_vesterled_outage_is_physically_feasible(network):
    supply, capacities, result = fixture_values(network)
    supply["OSEBERG"] = 2
    capacities["VESTERLED"] = 0
    result["flows"].update(OGT=2, HEIMDAL_STATPIPE=2, LANGELED_SOUTH=2)
    result["destinations"]["UK"] = 2
    validate_solution(network, supply, capacities, result)


def test_exact_node_balance_not_five_percent(network):
    supply, capacities, result = karsto_candidate(network)
    result["destinations"]["DK"] += .001
    with pytest.raises(ValueError, match="balance"):
        validate_solution(network, supply, capacities, result)


def test_unclassified_production_cannot_enter_core(network):
    assert [a["to"] for a in network["arcs"] if a["from"] == "UNMAPPED"] == ["UNROUTED"]
    supply, capacities, result = fixture_values(network)
    supply["UNMAPPED"] = 1
    result["flows"]["UNMAPPED_UNROUTED"] = result["unrouted"] = 1
    validate_solution(network, supply, capacities, result)


def test_dated_capacity_forward_fill_signed_maintenance_and_leap_month():
    months = pd.period_range("2024-01", "2024-02", freq="M")
    technical = pd.Series([5., 10.], index=pd.to_datetime(["2024-01-01", "2024-01-16"]))
    maintenance = pd.Series(2., index=pd.date_range("2024-01-01", "2024-02-29"))
    maintenance.loc["2024-02-01"] = -2  # Signed uplift retained, not clipped.
    monthly, daily = monthly_available_capacity(technical, months, maintenance)
    assert monthly.loc[pd.Period("2024-01"), "available_capacity_bcm"] == pytest.approx(.173)
    assert monthly.loc[pd.Period("2024-02"), "available_capacity_bcm"] == pytest.approx(.236)
    assert daily.loc["2024-02-01", "available_capacity_mcm_d"] == 12
    assert monthly.technical_capacity_bcm.sum() - monthly.maintenance_derate_bcm.sum() == pytest.approx(
        monthly.available_capacity_bcm.sum())


@pytest.mark.parametrize("failure", ["early", "missing_derate", "excess_derate"])
def test_no_capacity_backfill_or_missing_outage_fill(failure):
    months = pd.period_range("2024-01", periods=1, freq="M")
    technical = pd.Series([10.], index=pd.to_datetime(["2024-01-02" if failure == "early" else "2024-01-01"]))
    maintenance = pd.Series(11. if failure == "excess_derate" else 2., index=pd.date_range("2024-01-01", "2024-01-31"))
    if failure == "missing_derate":
        maintenance = maintenance.iloc[1:]
    with pytest.raises(ValueError):
        monthly_available_capacity(technical, months, maintenance)


def test_negative_net_allocations_are_excluded_from_preferences_not_clipped():
    observations = pd.DataFrame(1., index=pd.period_range("2023-01", periods=2, freq="M"), columns=DESTINATIONS)
    observations.loc[pd.Period("2023-02"), "DK"] = -1
    original = observations.copy()
    shares, excluded = historical_preferences(observations)
    assert excluded == ["2023-02"]
    assert shares["DK"] == pytest.approx(1 / 7)
    pd.testing.assert_frame_equal(observations, original)


def test_shared_asset_capacity_is_one_sum_constraint(network):
    network = deepcopy(network)
    for arc in network["arcs"]:
        if arc["id"] in {"ZEEPIPE_IIA", "ZEEPIPE_IIB"}:
            arc["asset"] = "SHARED_TEST"
    supply, capacities, _ = fixture_values(network)
    built = build_month(network, supply, capacities, {d: 1 / 7 for d in DESTINATIONS})
    constraint = str(built["problem"].get_constraint_by_name("capacity_SHARED_TEST"))
    assert "flow_ZEEPIPE_IIA" in constraint and "flow_ZEEPIPE_IIB" in constraint


def test_native_pulp4_nonoptimal_solve_response_is_rejected(network, monkeypatch):
    supply, capacities, _ = fixture_values(network)
    built = build_month(network, supply, capacities, {d: 1 / 7 for d in DESTINATIONS})
    response = pulp.LpSolveStats(status=pulp.LpSolveStatus.Infeasible)
    monkeypatch.setattr(built["problem"], "solve", lambda solver: response)
    with pytest.raises(RuntimeError, match="Infeasible"):
        solve_month(built, object())


@pytest.fixture
def solver():
    try:
        return available_solver()[1]
    except SolverUnavailable as error:
        pytest.skip(str(error))


def test_solver_routes_maximum_before_preferences(network, solver):
    supply, capacities, _ = karsto_candidate(network)
    capacities["KARSTO_STATPIPE"] = 2
    preferences = {d: 0. for d in DESTINATIONS}
    preferences.update(UK=.2, FR=.1, DE=.2, DK=.1, PL=.4)
    built = build_month(network, supply, capacities, preferences)
    result = solve_month(built, solver)
    validate_solution(network, supply, capacities, result)
    assert result["unrouted"] == pytest.approx(4)
    assert sum(result["destinations"].values()) == pytest.approx(6)


def test_solver_reroutes_outage_without_reducing_field_supply(network, solver):
    supply, capacities, _ = fixture_values(network)
    supply["OSEBERG"] = 2
    capacities["VESTERLED"] = 0
    preferences = {d: 0. for d in DESTINATIONS}
    preferences["UK"] = 1
    result = solve_month(build_month(network, supply, capacities, preferences), solver)
    validate_solution(network, supply, capacities, result)
    assert result["unrouted"] == pytest.approx(0)
    assert result["flows"]["VESTERLED"] == pytest.approx(0)
    assert result["flows"]["LANGELED_SOUTH"] == pytest.approx(2)


def test_tiebreak_shares_shortfall_without_changing_exports_or_l1(network, solver):
    # UK-only gas forces an overshoot. Karsto's scarce remaining gas can go
    # to DE, DK or PL at an identical L1 score; no destination should starve.
    supply, capacities, _ = fixture_values(network)
    supply.update(UK_DIRECT=8, KARSTO_FEED=2)
    preferences = {d: 0. for d in DESTINATIONS}
    preferences.update(UK=.5, DE=.3, DK=.05, PL=.15)
    ordinary = solve_month(build_month(network, supply, capacities, preferences), solver,
                           preference_tiebreak=False)
    fair = solve_month(build_month(network, supply, capacities, preferences), solver)
    validate_solution(network, supply, capacities, fair)
    assert fair["unrouted"] == pytest.approx(ordinary["unrouted"])
    assert fair["minimum_baseline_deviation_bcm"] == pytest.approx(ordinary["minimum_baseline_deviation_bcm"])
    assert fair["destinations"]["UK"] == pytest.approx(8)
    for destination in ("DE", "DK", "PL"):
        assert fair["destinations"][destination] == pytest.approx(4 * preferences[destination])
    assert fair["maximum_fractional_shortfall"] == pytest.approx(.6)


def test_tiebreak_zero_export_and_zero_preference_are_feasible(network, solver):
    supply, capacities, _ = fixture_values(network)
    preferences = {d: 0. for d in DESTINATIONS}
    preferences["DE"] = 1
    empty = solve_month(build_month(network, supply, capacities, preferences), solver)
    assert empty["unrouted"] == 0
    assert empty["maximum_fractional_shortfall"] is None
    # Physical UK gas cannot be blocked by its zero historical preference.
    supply["UK_DIRECT"] = 1
    result = solve_month(build_month(network, supply, capacities, preferences), solver)
    validate_solution(network, supply, capacities, result)
    assert result["destinations"]["UK"] == pytest.approx(1)
    assert result["maximum_fractional_shortfall"] == pytest.approx(1)


def test_workbook_additions_reject_double_counted_fields():
    from norway_gas_routing.poc_inputs import workbook_source_columns
    assert workbook_source_columns({"a": {"workbook_columns": ["ES", "FO"]}}, ["asgard_prod"]) == ["ES", "FO"]
    with pytest.raises(ValueError, match="multiple"):
        workbook_source_columns({"a": {"workbook_columns": ["AF"]}}, ["asgard_prod"])
    with pytest.raises(ValueError, match="multiple"):
        workbook_source_columns({"a": {"workbook_columns": ["ES"]},
                                 "b": {"workbook_columns": ["ES"]}}, [])
