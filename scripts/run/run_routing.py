"""Run the retained-data routing model; leave clearly labelled preparation if no solver exists."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".scratch/cache/matplotlib"))

import pandas as pd
import pulp
import yaml

from norway_gas_routing.artifacts import new_experiment, publish_assessment
from norway_gas_routing.reporting.assessment import render_report
from norway_gas_routing.evaluation import reconstruction_evaluation, check_table
from norway_gas_routing.config import load_config
from norway_gas_routing.routing import (DESTINATIONS, SolverUnavailable, available_solver,
    build_month, draw_network, network_definition, solve_month, validate_solution)
from norway_gas_routing.routing_inputs import file_hash, prepare_inputs


def save_csv(frame, path, *, monthly_index=False):
    frame = frame.copy()
    if monthly_index:
        frame.index = frame.index.to_timestamp()
        frame = frame.rename_axis("month").reset_index()
    if "month" in frame and isinstance(frame.month.dtype, pd.PeriodDtype):
        frame["month"] = frame.month.dt.to_timestamp()
    check_table(frame)
    frame.to_csv(path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d", float_format="%.9f")


def output_tables(network, inputs, results, status):
    destinations, comparisons, arcs = [], [], []
    groups = {"UK": ("UK",), "FR+BE": ("FR", "BE"), "NL+DE": ("NL", "DE"),
              "Baltic Pipe": ("PL",), "DK": ("DK",)}
    observation_keys = {"UK": "UK", "FR+BE": "FR_BE", "NL+DE": "NL_DE", "Baltic Pipe": "PL", "DK": "DK"}
    tolerance = inputs["settings"]["reconciliation_relative_tolerance"]
    for month in inputs["months"]:
        result = results.get(month)
        day = month.start_time
        row = {"month": day, **{d + "_volume_bcm": result["destinations"][d] if result else None for d in DESTINATIONS},
               "total_exports_bcm": sum(result["destinations"].values()) if result else None,
               "unrouted_supply_bcm": result["unrouted"] if result else None,
               "pipeline_supply_proxy_bcm": float(inputs["supply"].loc[month].sum()),
               "unclassified_supply_bcm": float(inputs["supply"].at[month, "UNMAPPED"]), "solver_status": status}
        destinations.append(row)
        for group, markets in groups.items():
            observed = float(inputs["observed"].at[month, observation_keys[group]])
            modelled = sum(result["destinations"][d] for d in markets) if result else None
            error = modelled - observed if result else None
            pct = error / abs(observed) * 100 if result and observed > 0 else None
            comparisons.append({"month": day, "benchmark_group": group, "modelled_volume_bcm": modelled,
                "observed_volume_bcm": observed, "error_bcm": error, "relative_error_pct": pct,
                "within_5pct_tolerance": abs(error) <= tolerance * observed if result and observed > 0 else None,
                "observation_status": "negative net allocation; not a nonnegative physical target" if observed < 0 else
                                      "EA legacy monthly proxy; latest revised", "solver_status": status})
        asset_totals = {}
        if result:
            for arc in network["arcs"]:
                if arc["asset"]:
                    asset_totals[arc["asset"]] = asset_totals.get(arc["asset"], 0) + result["flows"][arc["id"]]
        for arc in network["arcs"]:
            cap = float(inputs["capacities"].at[month, arc["asset"]]) if arc["asset"] else None
            flow = result["flows"][arc["id"]] if result else None
            asset_total = asset_totals.get(arc["asset"]) if result and arc["asset"] else None
            arcs.append({"month": day, "arc_id": arc["id"], "from_node": arc["from"], "to_node": arc["to"],
                         "asset": arc["asset"], "arc_type": arc.get("kind", "physical_or_allocation_proxy"),
                         "flow_bcm": flow, "available_capacity_bcm": cap, "asset_total_flow_bcm": asset_total,
                         "asset_utilisation_pct": asset_total / cap * 100 if asset_total is not None and cap else None,
                         "capacity_status": "provisional sourced envelope" if cap is not None else "no separately sourced capacity",
                         "solver_status": status})
    return pd.DataFrame(destinations), pd.DataFrame(comparisons), pd.DataFrame(arcs)


def summary(inputs, status, blocker, destination_table, comparison_table, checks):
    settings, recon = inputs["settings"], inputs["reconciliation"]
    source_checks = inputs["source_capacity_checks"]
    source_exceptions = source_checks.loc[source_checks.source_supply_above_capacity_bcm.gt(1e-7)]
    exceptions = recon.index[~recon.within_5pct_legacy_reconciliation].astype(str).tolist()
    source = inputs["supply"]
    lines = ["# Seven-destination routing routing model", "", f"Run status: **{status}**.", ""]
    if blocker:
        lines += [blocker, "Solved flows, utilisation and model-versus-observed errors are blank, not zero. "
                  "`network_flows.png` is a capacity/preparation view explicitly marked unsolved. "
                  "`representative_month.lp` contains the real-data first-stage model.", ""]
    lines += [f"Period: {settings['start']}–{settings['end']}; static soft preferences from "
              f"{settings['baseline_start']}–{settings['baseline_end']}. "
              f"Excluded negative/incomplete training months: {', '.join(inputs['excluded_training_months']) or 'none'}.", "",
              f"Actual retained EA production gives {source.sum().sum():.3f} bcm net pipeline-supply proxy, "
              f"including {source.UNMAPPED.sum():.3f} bcm unclassified production held unrouted. "
              "No residual is assigned to an unevidenced route. This is partial source reconstruction of the full supply envelope.", "",
              "## Accounting and constraints", "",
              "- Total EA production includes Snøhvit; subtract its validated historical net rate × days / 1000 once. "
              "Do not add total/non-flexible production to component fields or use the stale 2022 exclusion forecast.",
              "- Production workbook `Production mcm_d!HN432` deducts Rev (`EB432`) twice; the diagnostic column adds one deduction back. "
              "`gassco_total` also excludes non-Gassco fields and is a comparison series, not supply. No other field deduction is repeated.",
              "- Karsto processing precedes both Statpipe and Europipe II; OGT precedes both Vesterled and Heimdal Statpipe. "
              "Germany plus Danish transit share Europipe II. DK and PL share North Sea Entry; Poland also crosses the Baltic Pipe envelope. "
              "Norpipe has an Ekofisk junction, with the mapped Statpipe connection from the core.",
              "- Kollsnes uses a provisional 143 mcm/d dry-export baseline with the existing signed processing derate. "
              "Other capacities use sourced envelopes. No field maintenance is subtracted from production; no unsupported terminal/plant derates are applied.",
              "- PuLP first minimises unrouted supply, then fixes that total and minimises absolute deviations from earlier shares of solved exports. "
              "A third stage preserves both optima and minimises the largest fractional shortfall to resolve allocation ties. "
              "No sequential residual allocation, aggregate core ceiling, manual adjustment or price objective.",
              "- Exact equality constraints enforce source/junction mass balance. Independent checks use 1e-7 bcm numerical tolerance; "
              "the 5% data reconciliation tolerance does not relax the optimiser.", "", "## Reconciliation", "",
              f"Seven retained destination benchmarks versus legacy total: maximum absolute relative difference "
              f"{recon.observed_sum_vs_legacy_total_error_pct.abs().max():.2f}%; outside 5%: {', '.join(exceptions) or 'none'}. "
              f"Against the broader full pipeline-supply proxy, the maximum difference is "
              f"{recon.observed_sum_vs_pipeline_supply_error_pct.abs().max():.2f}%. "
              f"Negative destination observation months in this run: {int(recon.negative_destination_observation.sum())}. "
              "These are EA workbook physical/net-allocation proxies, not independent commercial validation."]
    if len(source_exceptions):
        lines += [f"Source production exceeds its first provisional asset envelope in {len(source_exceptions)} source-months "
                  f"({', '.join(sorted(source_exceptions.source_node.unique()))}); maximum excess "
                  f"{source_exceptions.source_supply_above_capacity_bcm.max():.3f} bcm. "
                  "See `inputs/source_capacity_checks.csv`; baseline/derate compatibility requires review before treating this as real curtailment."]
    if status == "OPTIMAL":
        failed = comparison_table.loc[comparison_table.within_5pct_tolerance.eq(False)]
        lines += [f"Solved exports: {destination_table.total_exports_bcm.sum():.3f} bcm; "
                  f"unrouted: {destination_table.unrouted_supply_bcm.sum():.3f} bcm. "
                  f"Benchmark comparisons outside 5%: {len(failed)}; inspect `legacy_comparison.csv`.",
                  f"Maximum node mass-balance residual: {max(c['max_mass_balance_residual_bcm'] for c in checks):.3g} bcm; "
                  f"maximum capacity violation: {max(c['max_capacity_violation_bcm'] for c in checks):.3g} bcm."]
    lines += ["", "## Material limits", "",
              "- Unclassified fields/domestic allocations remain unresolved. Heidrun's existing Karsto mapping may include domestic gas. "
              "Direct UK net fields use a separate supply-bounded FLAGS/SAGE/FUKA/Armada aggregate, without verified route nameplates. "
              "The existing Norway-minus-Snohvit boundary is retained; the legacy exclusions are compared separately in diagnosis.md.",
              "- Karsto's 95 mcm/d envelope is a rich-gas processing figure applied provisionally to net gas. "
              "Plant/pipe effective dates and common standard-volume conditions are unverified. Monthly capacity cannot capture within-month outage timing.",
              "- DE/NL shares are landing-pool allocation proxies. Nybro is entry plus transit, not Denmark-only consumption. "
              "Negative historical DK net allocations cannot be nonnegative physical delivery targets. "
              "Faxe kWh histories are not converted using an invented calorific value.",
              "- St Fergus collection regimes represent one underlying flow. The legacy workbook sums both; this routing model does not ingest/stitch them. "
              "The selected 2023/2024 windows avoid their 2020 overlap, but legacy monthly-proxy provenance remains limited.",
              "- This is latest-revised historical reconstruction, not out-of-sample forecasting or a vintage-correct backtest. "
              "Shooju @asof supports revisions, but a full contemporaneous input bundle is not prepared. "
              "Arc allocations can be non-unique under a price-off objective; solved routes are not observed commercial nominations.", "",
              "Inputs/settings/file hashes and retained retrieval metadata: `run_manifest.json`. "
              "Capacity/maintenance, source supply and data reconciliation: `inputs/`. "
              "Workbook review: `../../evidence/legacy/legacy_poc_review.md`. CSV dates are ISO and all volumes bcm; UTF-8 BOM supports Excel.", "",
              "Run from this repository with the approved interpreter: "
              "`& '../.envs/env1.0/python.exe' scripts/run/run_routing.py` (exit 2 means no solver backend).", ""]
    return "\n".join(lines)


def run(solver_name=None):
    model, registry = load_config(ROOT / "config/model.yaml", ROOT / "config/data_series.csv")
    settings = model["routing"]
    network = network_definition(settings)
    inputs = prepare_inputs(ROOT, model, registry)
    inputs["settings"] = settings
    output = new_experiment(ROOT, "baseline-routing")
    (output / "details").mkdir()
    (output / "provenance").mkdir()
    prepared = output / "provenance/inputs"
    prepared.mkdir(parents=True, exist_ok=True)
    save_csv(inputs["supply"].add_suffix("_supply_bcm"), prepared / "source_supply.csv", monthly_index=True)
    save_csv(inputs["capacity_daily"].sort_values(["date", "asset"]), prepared / "daily_capacities.csv")
    save_csv(inputs["capacity_monthly"].sort_values(["month", "asset"]), prepared / "monthly_capacities.csv")
    save_csv(inputs["selected_capacity_inputs"], prepared / "selected_capacity_inputs.csv")
    save_csv(inputs["reconciliation"], prepared / "input_reconciliation.csv", monthly_index=True)
    save_csv(inputs["training_observations"], prepared / "baseline_observations.csv", monthly_index=True)
    source_checks = []
    for month in inputs["months"]:
        for node, entry in network["nodes"].items():
            if entry["kind"] != "source":
                continue
            first_arcs = [a for a in network["arcs"] if a["from"] == node and a.get("kind") != "accounting"]
            # These checks are conservative diagnostics of directly constrained
            # source exits; full network feasibility is checked by the LP.
            asset = first_arcs[0]["asset"] if len(first_arcs) == 1 else None
            cap = float(inputs["capacities"].at[month, asset]) if asset else None
            volume = float(inputs["supply"].at[month, node])
            source_checks.append({"month": month.start_time, "source_node": node, "source_supply_bcm": volume,
                                  "first_asset": asset, "available_capacity_bcm": cap,
                                  "source_supply_above_capacity_bcm": max(volume - cap, 0) if cap is not None else None})
    inputs["source_capacity_checks"] = pd.DataFrame(source_checks)
    save_csv(inputs["source_capacity_checks"], prepared / "source_capacity_checks.csv")
    save_csv(pd.DataFrame([{"destination": d, "baseline_share": inputs["preferences"][d]} for d in DESTINATIONS]),
             prepared / "baseline_preferences.csv")
    (output / "provenance/network_definition.yaml").write_text(yaml.safe_dump(network, sort_keys=False), encoding="utf-8")
    built = {month: build_month(network, inputs["supply"].loc[month].to_dict(),
             inputs["capacities"].loc[month].to_dict(), inputs["preferences"], str(month)) for month in inputs["months"]}
    first = inputs["months"][0]
    built[first]["problem"].writeLP(str(output / "details/representative_month.lp"))
    results, checks, blocker, selected = {}, [], None, None
    try:
        selected, solver = available_solver(solver_name)
        for month in inputs["months"]:
            result = solve_month(built[month], solver)
            check = validate_solution(network, inputs["supply"].loc[month].to_dict(),
                         inputs["capacities"].loc[month].to_dict(), result,
                         settings["solver_numerical_tolerance_bcm"])
            checks.append({**check, "month": str(month), "solve_statistics": result["solve_statistics"],
                           "minimum_baseline_deviation_bcm": result["minimum_baseline_deviation_bcm"],
                           "maximum_fractional_shortfall": result["maximum_fractional_shortfall"]})
            results[month] = result
        status = "OPTIMAL"
    except SolverUnavailable as error:
        status, blocker = "BLOCKED_NO_SOLVER", str(error)
    destinations, comparisons, arcs = output_tables(network, inputs, results, status)
    save_csv(destinations, output / "results.csv")
    save_csv(comparisons, output / "details/legacy_comparison.csv")
    save_csv(arcs, output / "details/network_flows.csv")
    topology_check = draw_network(network, output / "details/network_topology.png")
    plot_check = draw_network(network, output / "details/network_flows.png", capacities=inputs["capacities"].loc[first].to_dict(),
                 result=results.get(first), title=f"{first} — solved monthly flows (bcm)" if results else
                 f"{first} — SOLVER UNAVAILABLE: capacity view only; no solved flows")
    assert topology_check == plot_check
    assert set(topology_check["arcs"]) == set(built[first]["flows"])
    assert set(topology_check["nodes"]) == {
        constraint.name.removeprefix("balance_") for constraint in built[first]["problem"].constraints()
        if constraint.name.startswith("balance_")}
    manifest = {"run_id": output.name, "run_at_utc": datetime.now(timezone.utc).isoformat(), "status": status, "blocker": blocker,
        "interpreter": sys.executable, "pulp_version": pulp.__version__, "solver": selected,
        "available_solvers": pulp.listSolvers(onlyAvailable=True), "asof": None,
        "analysis_type": "latest-revised historical reconstruction; partial classified supply",
        "config_sha256": file_hash(ROOT / "config/model.yaml"),
        "registry_sha256": file_hash(ROOT / "config/data_series.csv"),
        "code_sha256": {str(path.relative_to(ROOT)): file_hash(path) for path in
            [Path(__file__), *[ROOT / 'src/norway_gas_routing' / name for name in
                ('routing.py', 'routing_inputs.py', 'config.py', 'artifacts.py', 'reporting/assessment.py')]]},
        "package_versions": {name: version(name) for name in ["pulp", "pandas", "networkx", "matplotlib", "openpyxl", "pyarrow", "PyYAML"]},
        "settings": settings,
        "network": network, "graph_lp_match": topology_check, "inputs": inputs["provenance"],
        "baseline_preferences": inputs["preferences"], "excluded_training_months": inputs["excluded_training_months"],
        "solver_checks": checks, "unit": "bcm/month",
        "evaluation": reconstruction_evaluation(ROOT, inputs, settings, output.name)}
    manifest['code_sha256']['src/norway_gas_routing/evaluation.py'] = file_hash(ROOT / 'src/norway_gas_routing/evaluation.py')
    (output / "provenance/run_manifest.json").write_text(json.dumps(manifest, default=str, indent=2) + "\n", encoding="utf-8")
    (output / "details/run_summary.md").write_text(summary(inputs, status, blocker, destinations, comparisons, checks) +
        "\nTargeted before/after diagnosis: [diagnosis.md](diagnosis.md). "
        "First-solve outputs and implementation: `../../../archive/20261008-01_first-solve/`.\n", encoding="utf-8")
    render_report(output, "reconstruction")
    if not blocker:
        output = publish_assessment(ROOT, output, "reconstruction")
    print(status, "—", output)
    if blocker:
        print(blocker)
    return 2 if blocker else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", help="Name of an already installed PuLP solver")
    sys.exit(run(parser.parse_args().solver))
