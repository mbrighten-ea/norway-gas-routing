"""Monthly price-off PuLP routing, with one definition for optimisation and plots."""

from collections import defaultdict
from copy import deepcopy
import math

import networkx as nx
import pandas as pd
import pulp

DESTINATIONS = ("UK", "FR", "BE", "NL", "DE", "DK", "PL")


class SolverUnavailable(RuntimeError):
    pass


def network_definition(settings):
    """Copy YAML rows and make disposal arcs explicit in both LP and graph."""
    network = {"nodes": deepcopy(settings["nodes"]), "arcs": deepcopy(settings["arcs"])}
    for node, entry in network["nodes"].items():
        if entry["kind"] == "source":
            network["arcs"].append({"id": node + "_UNROUTED", "from": node,
                                    "to": "UNROUTED", "asset": None, "kind": "accounting"})
    graph = network_graph(network)
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("POC requires an acyclic routing network")
    if {n for n, e in network["nodes"].items() if e["kind"] == "destination"} != set(DESTINATIONS):
        raise ValueError("POC requires exactly seven separate destinations")
    if any(entry["kind"] not in {"source", "junction", "destination", "unrouted"}
           for entry in network["nodes"].values()):
        raise ValueError("Unknown node kind")
    for node, entry in network["nodes"].items():
        if entry["kind"] in {"destination", "unrouted"} and graph.out_degree(node):
            raise ValueError("A destination cannot export onward")
    return network


def network_graph(network):
    graph = nx.MultiDiGraph()
    graph.add_nodes_from((node, dict(entry)) for node, entry in network["nodes"].items())
    identifiers = set()
    for arc in network["arcs"]:
        if arc["id"] in identifiers or arc["from"] == arc["to"]:
            raise ValueError("Duplicate or self-referencing arc")
        if arc["from"] not in network["nodes"] or arc["to"] not in network["nodes"]:
            raise ValueError("Arc references an undefined node")
        identifiers.add(arc["id"])
        graph.add_edge(arc["from"], arc["to"], key=arc["id"], **arc)
    assert set(graph.nodes) == set(network["nodes"])
    assert {key for _, _, key in graph.edges(keys=True)} == identifiers
    return graph


def finite_nonnegative(values, context):
    if any(not math.isfinite(float(v)) or float(v) < 0 for v in values):
        raise ValueError(f"Nonfinite/negative {context}; investigate without clipping")


def monthly_available_capacity(technical, months, derate=None):
    """Dated daily mcm/d nameplate; forward-fill only. Derates must be complete."""
    technical = technical.sort_index()
    if not isinstance(technical.index, pd.DatetimeIndex) or not technical.index.is_unique:
        raise ValueError("Technical capacity requires unique dated updates")
    if technical.index.tz is not None or not technical.index.equals(technical.index.normalize()):
        raise ValueError("Technical capacity timestamps must be naive midnight dates")
    finite_nonnegative(technical, "technical capacity")
    days = pd.date_range(months.min().start_time, months.max().end_time.normalize())
    baseline = technical.reindex(technical.index.union(days)).ffill().reindex(days)
    if baseline.isna().any():
        raise ValueError("Technical capacity missing before first dated record; no backward-fill")
    maintenance = pd.Series(0.0, index=days)
    if derate is not None:
        if not isinstance(derate.index, pd.DatetimeIndex) or not derate.index.is_unique:
            raise ValueError("Maintenance requires unique daily dates")
        maintenance = derate.reindex(days)
        if not all(math.isfinite(float(v)) for v in maintenance):
            raise ValueError("Missing/nonfinite daily maintenance; no filling")
    available = baseline - maintenance
    finite_nonnegative(available, "available capacity")
    daily = pd.DataFrame({"technical_capacity_mcm_d": baseline,
                          "maintenance_derate_mcm_d": maintenance,
                          "available_capacity_mcm_d": available})
    monthly = (daily.groupby(daily.index.to_period("M")).sum() / 1000).rename(columns={
        "technical_capacity_mcm_d": "technical_capacity_bcm",
        "maintenance_derate_mcm_d": "maintenance_derate_bcm",
        "available_capacity_mcm_d": "available_capacity_bcm"})
    return monthly, daily


def historical_preferences(observations):
    """Volume-weighted static shares from development observations only."""
    from .evaluation import check_dates
    check_dates(observations.index, 'fit')
    observations = observations.loc[:, list(DESTINATIONS)]
    good = observations.notna().all(axis=1) & observations.ge(0).all(axis=1)
    training = observations.loc[good]
    if training.empty or training.sum().sum() <= 0:
        raise ValueError("No nonnegative complete earlier observations for preferences")
    shares = training.sum() / training.sum().sum()
    return shares.to_dict(), observations.index[~good].astype(str).tolist()


def build_month(network, supply, capacities, preferences, month="synthetic"):
    sources = {n for n, e in network["nodes"].items() if e["kind"] == "source"}
    if set(supply) != sources or set(preferences) != set(DESTINATIONS):
        raise ValueError("Supply/preference keys do not match the network")
    finite_nonnegative(supply.values(), "supply")
    finite_nonnegative(capacities.values(), "capacity")
    finite_nonnegative(preferences.values(), "preferences")
    if abs(sum(preferences.values()) - 1) > 1e-9:
        raise ValueError("Preferences must sum to one")
    problem = pulp.LpProblem("Norway_" + str(month), pulp.LpMinimize)
    flows = {a["id"]: problem.add_variable("flow_" + a["id"], lowBound=0) for a in network["arcs"]}
    destinations = {d: problem.add_variable("destination_" + d, lowBound=0) for d in DESTINATIONS}
    unrouted = problem.add_variable("unrouted_supply", lowBound=0)
    incoming, outgoing, assets = defaultdict(list), defaultdict(list), defaultdict(list)
    for arc in network["arcs"]:
        variable = flows[arc["id"]]
        outgoing[arc["from"]].append(variable)
        incoming[arc["to"]].append(variable)
        if arc["asset"]:
            assets[arc["asset"]].append(variable)
    if set(capacities) != set(assets):
        raise ValueError("Every constrained asset requires a monthly capacity")
    for node, entry in network["nodes"].items():
        exports = (destinations[node] if entry["kind"] == "destination" else
                   unrouted if entry["kind"] == "unrouted" else 0)
        problem += (float(supply.get(node, 0)) + pulp.lpSum(incoming[node]) ==
                    pulp.lpSum(outgoing[node]) + exports), "balance_" + node
    for asset, variables in assets.items():
        # Sum, rather than separately granting full capacity on each arc.
        problem += pulp.lpSum(variables) <= float(capacities[asset]), "capacity_" + asset
    deviation = {}
    total_supply = sum(supply.values())
    for destination in DESTINATIONS:
        deviation[destination] = problem.add_variable("deviation_" + destination, lowBound=0)
        # Preferences apply to exported gas. Unknown/disposed supply is not an
        # impossible destination target, and cannot justify withholding gas.
        target = preferences[destination] * (total_supply - unrouted)
        problem += deviation[destination] >= destinations[destination] - target
        problem += deviation[destination] >= target - destinations[destination]
    problem.setObjective(unrouted)
    return {"problem": problem, "flows": flows, "destinations": destinations,
            "unrouted": unrouted, "deviation": pulp.lpSum(deviation.values()),
            "preferences": dict(preferences), "total_supply": total_supply}


def available_solver(name=None):
    available = pulp.listSolvers(onlyAvailable=True)
    if name is not None and name not in available:
        raise SolverUnavailable(f"Requested PuLP solver {name!r} unavailable; available={available}")
    if not available:
        raise SolverUnavailable("PuLP is installed, but no LP solver backend is available (available=[]). "
                                "CBC/HiGHS/GLPK executable or API access requires a separately approved remedy.")
    preferred = [s for s in ["HiGHS", "HiGHS_CMD", "COIN_CMD", "GLPK_CMD"] if s in available]
    selected = name or (preferred + available)[0]
    return selected, pulp.getSolver(selected, msg=False)


def solve_month(built, solver, *, preference_tiebreak=True):
    """Maximise exports, minimise L1 deviations, then share tied shortfalls.

    The last stage preserves both earlier optima. It minimises the largest
    fractional shortfall against a positive earlier-share target, so an L1
    tie cannot arbitrarily starve a small destination. Zero-share destinations
    remain feasible, and no destination is given a hard delivery forecast.
    """
    problem = built["problem"]
    first_stats = problem.solve(solver)
    if first_stats.status != pulp.LpSolveStatus.Optimal:
        raise RuntimeError("Maximum-export solve failed: " + first_stats.status_str)
    minimum_unrouted = pulp.value(built["unrouted"])
    problem += built["unrouted"] == minimum_unrouted, "fix_maximum_exports"
    problem.setObjective(built["deviation"])
    second_stats = problem.solve(solver)
    if second_stats.status != pulp.LpSolveStatus.Optimal:
        raise RuntimeError("Baseline-preference solve failed: " + second_stats.status_str)
    minimum_deviation = float(pulp.value(built["deviation"]))
    third_stats = None
    maximum_shortfall = None
    exports = built["total_supply"] - minimum_unrouted
    if preference_tiebreak and exports > 0:
        problem += built["deviation"] == minimum_deviation, "fix_baseline_deviation"
        worst = problem.add_variable("worst_fractional_shortfall", lowBound=0)
        for destination, share in built["preferences"].items():
            if share > 0:
                target = share * exports
                problem += built["destinations"][destination] >= target * (1 - worst)
        problem.setObjective(worst)
        third_stats = problem.solve(solver)
        if third_stats.status != pulp.LpSolveStatus.Optimal:
            raise RuntimeError("Preference tie-break solve failed: " + third_stats.status_str)
        maximum_shortfall = float(pulp.value(worst))
    return {"flows": {k: float(v.varValue) for k, v in built["flows"].items()},
            "destinations": {k: float(v.varValue) for k, v in built["destinations"].items()},
            "unrouted": float(pulp.value(built["unrouted"])),
            "minimum_baseline_deviation_bcm": minimum_deviation,
            "maximum_fractional_shortfall": maximum_shortfall,
            "solve_statistics": {"maximum_exports": first_stats.toDict(),
                                 "baseline_preferences": second_stats.toDict(),
                                 "preference_tiebreak": third_stats.toDict() if third_stats else None}}


def validate_solution(network, supply, capacities, result, tolerance=1e-7):
    """Independent node/asset checks; 5% data tolerance never relaxes LP balance."""
    if set(result["flows"]) != {a["id"] for a in network["arcs"]}:
        raise ValueError("Solution omits network arcs")
    if set(result["destinations"]) != set(DESTINATIONS):
        raise ValueError("Solution omits a destination")
    if any(not math.isfinite(v) or v < -tolerance
           for v in [*result["destinations"].values(), result["unrouted"]]):
        raise ValueError("Invalid solved destination/unrouted values")
    incoming, outgoing, asset_flows = defaultdict(float), defaultdict(float), defaultdict(float)
    for arc in network["arcs"]:
        value = result["flows"][arc["id"]]
        if not math.isfinite(value) or value < -tolerance:
            raise ValueError("Invalid solved flow")
        outgoing[arc["from"]] += value
        incoming[arc["to"]] += value
        if arc["asset"]:
            asset_flows[arc["asset"]] += value
    residuals = {}
    for node, entry in network["nodes"].items():
        sink = result["unrouted"] if entry["kind"] == "unrouted" else result["destinations"].get(node, 0)
        residuals[node] = supply.get(node, 0) + incoming[node] - outgoing[node] - sink
    total_residual = sum(supply.values()) - sum(result["destinations"].values()) - result["unrouted"]
    max_balance = max(abs(total_residual), max(abs(v) for v in residuals.values()))
    max_violation = max([0.0] + [v - capacities[k] for k, v in asset_flows.items()])
    if max_balance > tolerance or max_violation > tolerance:
        raise ValueError(f"Solver validation failed: balance={max_balance}, capacity={max_violation}")
    return {"max_mass_balance_residual_bcm": max_balance,
            "max_capacity_violation_bcm": max_violation}


def draw_network(network, path, *, capacities=None, result=None, title="Physical routing topology"):
    """Render every LP arc, including parallel, zero-flow and accounting arcs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    from matplotlib.transforms import Bbox
    from textwrap import fill

    graph = network_graph(network)
    positions = {n: (e["position"][0] * 1.5, e["position"][1]) for n, e in network["nodes"].items()}
    colors = {"source": "#d9ebf8", "junction": "#e8e8e8", "destination": "#d9f1df", "unrouted": "#fbe2d4"}
    fig, ax = plt.subplots(figsize=(20, 14))
    ax.set_xlim(-1.5, 20)
    ax.set_ylim(-4, 15)
    nx.draw_networkx_nodes(graph, positions, ax=ax, node_size=2700,
                           node_color=[colors[e["kind"]] for e in network["nodes"].values()],
                           edgecolors="#53616b", linewidths=1)
    labels = {n: fill(e.get("label", n), width=17) for n, e in network["nodes"].items()}
    nx.draw_networkx_labels(graph, positions, labels=labels, font_size=8, ax=ax)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    radius = math.sqrt(2700) * fig.dpi / 72 / 2 + 6
    reserved = []
    for position in positions.values():
        px, py = ax.transData.transform(position)
        reserved.append(Bbox.from_bounds(px - radius, py - radius, radius * 2, radius * 2))
    pairs = defaultdict(list)
    for arc in network["arcs"]:
        pairs[(arc["from"], arc["to"])].append(arc)
    asset_totals = defaultdict(float)
    if result:
        for arc in network["arcs"]:
            if arc["asset"]:
                asset_totals[arc["asset"]] += result["flows"][arc["id"]]
    for pair, arcs in pairs.items():
        start, end = positions[pair[0]], positions[pair[1]]
        for i, arc in enumerate(arcs):
            accounting = arc.get("kind") == "accounting"
            rad = (i - (len(arcs) - 1) / 2) * .30
            value = result["flows"][arc["id"]] if result else None
            zero = value is not None and abs(value) < 1e-9
            color = "#c8c8c8" if accounting else "#9ca5ad" if zero else "#315c80"
            width = .6 if accounting else 1 if value is None else 1 + min(value, 3) * 1.3
            patch = FancyArrowPatch(start, end, connectionstyle=f"arc3,rad={rad}",
                                    arrowstyle="-|>", mutation_scale=13, linewidth=width,
                                    linestyle=":" if accounting else "--" if zero else "-",
                                    color=color, shrinkA=29, shrinkB=29, zorder=1)
            ax.add_patch(patch)
            if accounting:
                continue  # All disposal arcs shown; avoid eight overlapping text labels.
            text = fill(arc["id"].replace("_", " ").title(), width=24)
            if capacities is not None:
                cap = capacities.get(arc["asset"])
                text += "\n" + (f"flow {value:.3f} bcm" if value is not None else "")
                if cap is not None:
                    use = asset_totals[arc["asset"]] / cap * 100 if result and cap else 0 if result else None
                    text += f"{' | ' if result else ''}cap {cap:.3f} bcm"
                    if use is not None:
                        text += f" | {use:.0f}%"
                else:
                    text += " | no separate cap" if result else "no separate cap"
            x, y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            dx, dy = end[0] - start[0], end[1] - start[1]
            annotation = ax.text(x, y, text, fontsize=7.5, ha="center", va="center",
                                 bbox=dict(facecolor="white", alpha=.92, edgecolor="none", pad=1), zorder=3)
            # Greedy placement avoids obscuring nodes/earlier arc labels. Geometry
            # depends only on this arc's endpoints, never on a hard-coded edge list.
            length = math.hypot(dx, dy)
            placed = False
            for fraction in [.5, .4, .6, .3, .7]:
                for offset in [.25, -.25, .55, -.55, .85, -.85, 1.15, -1.15]:
                    annotation.set_position((start[0] + fraction * dx + rad * dy / 2 - dy / length * offset,
                                             start[1] + fraction * dy - rad * dx / 2 + dx / length * offset))
                    bounds = annotation.get_window_extent(renderer).expanded(1.03, 1.1)
                    if not any(bounds.overlaps(other) for other in reserved):
                        placed = True
                        break
                if placed:
                    break
            reserved.append(bounds)
    fig.suptitle(title, fontsize=17, y=.97)
    fig.text(.125, .04, "Blue: physical/proxy arcs. Dotted grey: source disposal to unrouted. "
            "Dashed: solved zero flows. DE/NL and direct UK are proxies.\n"
            "No aggregate core capacity. All nodes and arcs come from the PuLP definition; capacities are provisional.",
            fontsize=10)
    ax.axis("off")
    fig.canvas.draw()
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {"nodes": sorted(graph.nodes), "arcs": sorted(k for _, _, k in graph.edges(keys=True))}
