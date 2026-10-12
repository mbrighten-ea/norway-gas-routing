"""Reproducible 2024 before/after diagnosis using retained inputs only.

The first solve and initial benchmark stay frozen. All comparisons here are
latest-revised reconstructions against EA allocation proxies, not forecasts.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".scratch/cache/matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pulp
import yaml

from norway_gas_routing.config import load_config
from norway_gas_routing.poc import (DESTINATIONS, available_solver, build_month,
                                   solve_month, validate_solution)
from norway_gas_routing.poc_inputs import prepare_inputs, file_hash
import shutil
sys.path.insert(0, str(ROOT / "scripts/run"))
from run_poc import save_csv
from norway_gas_routing.artifacts import (new_experiment, publish_assessment, first_solve_file, verify_first_solve, original_bytes)
from norway_gas_routing.reporting import render_report
from norway_gas_routing.evaluation import check_table, check_dates, reconstruction_evaluation

OUT = ROOT / "outputs/reconstruction/details"
FIRST = ROOT / "archive/20261008-01_first-solve"


def read_months(path):
    frame = pd.read_csv(path, parse_dates=["month"]).set_index("month")
    frame.index = frame.index.to_period("M")
    check_dates(frame.index)
    return frame


def field_trace(settings):
    ledger = pd.read_csv(ROOT / "outputs/benchmark/details/unclassified_field_components.csv")
    ledger["month"] = pd.to_datetime(ledger.month).dt.to_period("M")
    evidence = {r["column"]: r for r in json.loads((ROOT / "evidence/inputs/field_transport_evidence.json").read_text(encoding="utf-8"))}
    mapping = {c: node for node, row in settings["nodes"].items() for c in row.get("workbook_columns", [])}
    ledger["field"] = ledger.column.map(lambda c: evidence.get(c, {}).get("field", c))
    ledger["source_node_after"] = ledger.column.map(mapping).fillna("UNMAPPED")
    ledger["source_url"] = ledger.column.map(lambda c: evidence.get(c, {}).get("url", ""))
    # Distinguish evacuation from the workbook's narrower accounting boundary.
    ledger["legacy_excluded"] = ledger.scope.str.contains("excluded", case=False)
    flags = {"EZ", "DB", "FU", "EH", "EJ", "FV", "EI"}
    sage = {"CG", "FL", "CQ", "EM", "GI", "CK", "FF", "FS", "FD"}
    def route(c, node):
        if c in flags:
            return "FLAGS / St Fergus UK"
        if c in sage:
            return "SAGE / St Fergus UK"
        if c == "DL":
            return "FUKA / SEGAL UK"
        if c == "EB":
            return "Armada / Teesside UK; downstream pipe name unverified here"
        if c == "EQ":
            return "Harald / Tyra / Danish system; final allocation unresolved"
        if c == "ER":
            return "Oseberg sale-gas swap; field net attribution unresolved"
        if c == "CL":
            return "Statpipe; entry and upstream processing unresolved"
        return node.removesuffix("_FEED")
    ledger["evacuation"] = [route(c, n) for c, n in zip(ledger.column, ledger.source_node_after)]
    ledger["classification"] = ledger.source_node_after.map(lambda n:
        "direct UK export proxy" if n == "UK_DIRECT" else
        "unresolved route/accounting; retained unrouted" if n == "UNMAPPED" else "modelled Gassco feed")
    ledger["data_issue"] = ledger.column.map(lambda c:
        "Negative retained May 2024 cell FD436 (-0.000073 bcm); all months withheld, no clipping"
        if c == "FD" else "")
    # Zero-volume columns remain traceable in the original full ledger.
    active = ledger.groupby("column").volume_bcm.apply(lambda v: v.abs().sum()).gt(0)
    ledger = ledger.loc[ledger.column.isin(active.index[active])].copy()
    annual = ledger.groupby(["column", "field", "classification", "source_node_after",
        "evacuation", "legacy_excluded", "source_url"], dropna=False).volume_bcm.sum().reset_index()
    save_csv(ledger, OUT / "unclassified_field_months.csv")
    save_csv(annual.sort_values("volume_bcm", ascending=False), OUT / "unclassified_fields_annual.csv")
    return ledger, annual


def solve_case(network, supply, capacities, preferences, tiebreak):
    results, checks = {}, []
    for month in supply.index:
        source, cap = supply.loc[month].to_dict(), capacities.loc[month].to_dict()
        result = solve_month(build_month(network, source, cap, preferences, str(month)),
                             available_solver("HiGHS")[1], preference_tiebreak=tiebreak)
        checks.append(validate_solution(network, source, cap, result))
        results[month] = result
    return results, checks


def optimal_face(network, supply, capacities, preferences):
    rows = []
    for month in supply.index:
        for destination in ["DK", "PL", "DE"]:
            for direction, sign in [("minimum", 1), ("maximum", -1)]:
                built = build_month(network, supply.loc[month].to_dict(), capacities.loc[month].to_dict(), preferences)
                solved = solve_month(built, available_solver("HiGHS")[1], preference_tiebreak=False)
                built["problem"] += built["deviation"] == solved["minimum_baseline_deviation_bcm"]
                built["problem"].setObjective(sign * built["destinations"][destination])
                stats = built["problem"].solve(available_solver("HiGHS")[1])
                if stats.status != pulp.LpSolveStatus.Optimal:
                    raise RuntimeError("Optimal-face solve failed")
                rows.append({"month": month, "destination": destination, "bound": direction,
                    "volume_bcm": pulp.value(built["destinations"][destination]),
                    "baseline_target_bcm": preferences[destination] * (supply.loc[month].sum() - solved["unrouted"]),
                    "fixed_unrouted_bcm": solved["unrouted"],
                    "fixed_total_absolute_deviation_bcm": solved["minimum_baseline_deviation_bcm"]})
    save_csv(pd.DataFrame(rows), OUT / "first_solve_optimal_face.csv")
    return pd.DataFrame(rows)


def comparison_rows(case, frame, observations):
    rows = []
    groups = {**{d: [d] for d in DESTINATIONS}, "FR+BE": ["FR", "BE"],
              "NL+DE": ["NL", "DE"], "Nybro DK+PL": ["DK", "PL"]}
    for month in frame.index:
        valid_shares = observations.loc[month, list(DESTINATIONS)].notna().all() and observations.loc[month, list(DESTINATIONS)].ge(0).all()
        for group, destinations in groups.items():
            modelled = frame.loc[month, destinations].sum()
            observed_key = {"FR+BE": "FR_BE", "NL+DE": "NL_DE"}.get(group)
            actual = (observations.at[month, observed_key] if observed_key else
                      observations.loc[month, destinations].sum())
            rows.append({"case": case, "month": month, "destination": group,
                         "modelled_bcm": modelled, "observed_bcm": actual,
                         "error_bcm": modelled - actual,
                         "share_error_pp": 100 * (modelled / frame.loc[month, list(DESTINATIONS)].sum() -
                             actual / observations.loc[month, list(DESTINATIONS)].sum()) if valid_shares else None,
                         "share_status": "complete nonnegative basket" if valid_shares else "excluded whole basket: negative or missing destination proxy",
                         "volume_observation_status": "negative net allocation; not a physical delivery target" if actual < 0 else "latest EA allocation proxy",
                         "evaluation": "latest-revised reconstruction against EA proxies"})
    return rows


def metrics(comparisons):
    check_table(comparisons, 'score')
    rows = []
    for (case, destination), frame in comparisons.groupby(["case", "destination"], sort=False):
        rows.append({"case": case, "destination": destination, "months": len(frame),
            "WAPE_pct": 100 * frame.error_bcm.abs().sum() / frame.observed_bcm.abs().sum(),
            "MAE_bcm_month": frame.error_bcm.abs().mean(), "bias_bcm_month": frame.error_bcm.mean(),
            "mean_absolute_share_error_pp": frame.share_error_pp.abs().mean(),
            "share_months": int(frame.share_error_pp.notna().sum()),
            "modelled_annual_bcm": frame.modelled_bcm.sum(), "observed_annual_bcm": frame.observed_bcm.sum()})
    return pd.DataFrame(rows)


def asset_rows(case, network, results, capacities):
    rows = []
    for month, result in results.items():
        for asset, cap in capacities.loc[month].items():
            flow = sum(result["flows"][a["id"]] for a in network["arcs"] if a["asset"] == asset)
            rows.append({"case": case, "month": month, "asset": asset, "flow_bcm": flow,
                         "capacity_bcm": cap, "utilisation_pct": 100 * flow / cap if cap else None,
                         "binding": abs(cap - flow) <= 1e-7})
    return rows


def main():
    global OUT
    candidate = new_experiment(ROOT, "routing-diagnosis")
    shutil.copytree(ROOT / "outputs/reconstruction", candidate, dirs_exist_ok=True)
    OUT = candidate / "details"
    model, registry = load_config(ROOT / "config/model.yaml", ROOT / "config/data_series.csv")
    inputs = prepare_inputs(ROOT, model, registry)
    settings = model["poc"]
    network = yaml.safe_load((ROOT / "outputs/reconstruction/provenance/network_definition.yaml").read_text())
    old_network = yaml.safe_load((first_solve_file(ROOT, "outputs/poc/network_definition.yaml")).read_text())
    original = read_months(first_solve_file(ROOT, "outputs/poc/destination_flows.csv"))
    old_supply = read_months(first_solve_file(ROOT, "outputs/poc/inputs/source_supply.csv"))
    old_supply.columns = old_supply.columns.str.removesuffix("_supply_bcm")
    capacities = inputs["capacities"]
    pd.testing.assert_frame_equal(pd.read_csv(ROOT / "outputs/reconstruction/provenance/inputs/daily_capacities.csv"),
                                  pd.read_csv(first_solve_file(ROOT, "outputs/poc/inputs/daily_capacities.csv")))
    assert (inputs["supply"].sum(axis=1) - old_supply.sum(axis=1)).abs().max() < 1e-7
    preferences = inputs["preferences"]
    ledger, annual = field_trace(settings)
    face = optimal_face(old_network, old_supply, capacities, preferences)
    original_frame = original[[d + "_volume_bcm" for d in DESTINATIONS]].rename(columns=lambda c: c.removesuffix("_volume_bcm"))
    # The original solver's exact chosen point is retained, rather than claiming
    # a rerun of a degenerate objective reproduces that particular allocation.
    old_results = {}
    old_arcs = read_months(first_solve_file(ROOT, "outputs/poc/network_flows.csv"))
    for month in original.index:
        old_results[month] = {"flows": old_arcs.loc[month].set_index("arc_id").flow_bcm.to_dict(),
            "destinations": original_frame.loc[month].to_dict(), "unrouted": original.at[month, "unrouted_supply_bcm"]}
    old_checks = json.loads((first_solve_file(ROOT, "outputs/poc/run_manifest.json")).read_text())["solver_checks"]
    cases = {"first_solve": (old_network, old_supply, old_results, old_checks)}
    for case, net, supply, tie in [("tie_break_only", old_network, old_supply, True),
             ("field_routes_only", network, inputs["supply"], False),
             ("refined_broader_boundary", network, inputs["supply"], True)]:
        results, checks = solve_case(net, supply, capacities, preferences, tie)
        cases[case] = (net, supply, results, checks)
    legacy = inputs["supply"].copy()
    for node in legacy:
        omitted = ledger.loc[ledger.legacy_excluded & ledger.source_node_after.eq(node)].groupby("month").volume_bcm.sum()
        legacy[node] -= omitted.reindex(legacy.index, fill_value=0)
    legacy["UK_DIRECT"] -= old_supply.UK_DIRECT  # Martin Linge exactly once.
    results, checks = solve_case(network, legacy, capacities, preferences, True)
    cases["legacy_formula_boundary"] = (network, legacy, results, checks)
    comparisons, utilisation, totals, baseline = [], [], [], []
    for case, (net, supply, results, checks) in cases.items():
        frame = pd.DataFrame({m: r["destinations"] for m, r in results.items()}).T
        comparisons.extend(comparison_rows(case, frame, inputs["observed"]))
        utilisation.extend(asset_rows(case, net, results, capacities))
        totals.append({"case": case, "supply_bcm": supply.sum().sum(),
            "exports_bcm": frame.sum().sum(), "unclassified_bcm": supply.UNMAPPED.sum(),
            "unrouted_bcm": sum(r["unrouted"] for r in results.values()),
            "max_mass_balance_residual_bcm": max([c["max_mass_balance_residual_bcm"] for c in checks], default=0),
            "max_capacity_violation_bcm": max([c["max_capacity_violation_bcm"] for c in checks], default=0)})
        for month, result in results.items():
            exports = sum(result["destinations"].values())
            for destination in DESTINATIONS:
                target = preferences[destination] * exports
                baseline.append({"case": case, "month": month, "destination": destination,
                    "earlier_share": preferences[destination], "target_bcm": target,
                    "allocated_bcm": result["destinations"][destination],
                    "deviation_bcm": result["destinations"][destination] - target,
                    "second_stage_weight": 1,
                    "fractional_shortfall": max(target - result["destinations"][destination], 0) / target if target else None})
    comparisons = pd.DataFrame(comparisons)
    metric = metrics(comparisons)
    totals = pd.DataFrame(totals)
    utilisation = pd.DataFrame(utilisation)
    save_csv(comparisons, OUT / "monthly_comparisons.csv")
    save_csv(metric, OUT / "metrics.csv")
    save_csv(totals, OUT / "scenario_totals.csv")
    save_csv(utilisation, OUT / "monthly_asset_utilisation.csv")
    save_csv(pd.DataFrame(baseline), OUT / "monthly_baseline_deviations.csv")
    assets = utilisation.groupby(["case", "asset"]).agg(
        flow_bcm=("flow_bcm", "sum"), capacity_bcm=("capacity_bcm", "sum"),
        peak_utilisation_pct=("utilisation_pct", "max"), binding_months=("binding", "sum")).reset_index()
    assets["annual_utilisation_pct"] = assets.flow_bcm / assets.capacity_bcm * 100
    save_csv(assets, OUT / "asset_utilisation_summary.csv")
    trace = ledger.groupby("month").volume_bcm.sum().to_frame("original_residual_field_ledger_bcm")
    trace["original_residual_bcm"] = old_supply.UNMAPPED
    trace["ledger_minus_retained_series_bcm"] = trace.original_residual_field_ledger_bcm - trace.original_residual_bcm
    trace["confirmed_gassco_additions_bcm"] = ledger.loc[ledger.classification.eq("modelled Gassco feed")].groupby("month").volume_bcm.sum()
    trace["confirmed_direct_uk_additions_bcm"] = ledger.loc[ledger.source_node_after.eq("UK_DIRECT")].groupby("month").volume_bcm.sum()
    trace["unresolved_after_bcm"] = inputs["supply"].UNMAPPED
    trace["legacy_excluded_residual_bcm"] = ledger.loc[ledger.legacy_excluded].groupby("month").volume_bcm.sum()
    trace["martin_linge_already_mapped_bcm"] = old_supply.UK_DIRECT
    trace["broader_supply_bcm"] = inputs["supply"].sum(axis=1)
    trace["legacy_compatible_supply_bcm"] = legacy.sum(axis=1)
    save_csv(trace, OUT / "monthly_supply_boundaries.csv", monthly_index=True)
    chart_comparisons(comparisons, metric)
    write_summary(metric, totals, assets, annual, trace, face, inputs["observed"], preferences)
    # Validate preserved files and canonical result agreement independently.
    verify_first_solve(ROOT)
    protected = json.loads((ROOT / "outputs/benchmark/provenance/run_manifest.json").read_text())["protected_sha256"]
    import hashlib
    for relative, digest in protected.items():
        assert hashlib.sha256(original_bytes(ROOT, relative)).hexdigest() == digest, relative
    current = read_months(ROOT / "outputs/reconstruction/results.csv")
    for month, result in cases["refined_broader_boundary"][2].items():
        for destination in DESTINATIONS:
            assert abs(current.at[month, destination + "_volume_bcm"] - result["destinations"][destination]) < 1e-7
        for n in ("exports_bcm", "unrouted_bcm"):
            assert abs(totals.set_index("case").at["tie_break_only", n] - totals.set_index("case").at["first_solve", n]) < 1e-7
        tied = cases["tie_break_only"][2][month]
        ordinary = old_results[month]
        def absolute_deviation(result):
            exports = sum(result["destinations"].values())
            return sum(abs(result["destinations"][d] - preferences[d] * exports) for d in DESTINATIONS)
        assert abs(absolute_deviation(tied) - absolute_deviation(ordinary)) < 1e-7
    assert trace.ledger_minus_retained_series_bcm.abs().max() < 1e-5
    verification = {"run_at_utc": datetime.now(timezone.utc).isoformat(),
        "first_solve_archive_hashes_match": True, "canonical_output_matches": True,
        "initial_benchmark_protected_hashes_match_using_first_solve_archive": True,
        "daily_capacity_and_signed_maintenance_unchanged": True,
        "monthly_supply_boundary_unchanged": True,
        "tie_break_preserves_original_maximum_exports": True,
        "tie_break_preserves_original_L1_penalty": True,
        "solver": "HiGHS", "checks": totals.to_dict("records"),
        "configuration_sha256": file_hash(ROOT / "config/model.yaml"),
        "script_sha256": file_hash(Path(__file__)), "asof": None,
        "analysis": "latest-revised historical reconstruction; scope comparability unresolved"}
    (OUT.parent / "provenance/verification.json").write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    manifest_path = candidate / 'provenance/run_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['parent_run_id'] = manifest['run_id']
    manifest['run_id'] = candidate.name
    manifest['evaluation'] = reconstruction_evaluation(ROOT, inputs, settings, candidate.name)
    manifest['code_sha256'][str(Path(__file__).relative_to(ROOT))] = file_hash(Path(__file__))
    manifest['code_sha256']['src/norway_gas_routing/evaluation.py'] = file_hash(ROOT / 'src/norway_gas_routing/evaluation.py')
    manifest_path.write_text(json.dumps(manifest, default=str, indent=2) + '\n', encoding='utf-8')
    render_report(candidate, "reconstruction")
    publish_assessment(ROOT, candidate, "reconstruction")
    print(totals.to_string(index=False))
    print(metric.loc[metric.destination.isin(DESTINATIONS), ["case", "destination", "WAPE_pct"]].to_string(index=False))


def chart_comparisons(comparisons, metric):
    check_table(comparisons, 'plot')
    cases = ["first_solve", "refined_broader_boundary"]
    fig, axes = plt.subplots(4, 2, figsize=(13, 12), sharex=True)
    for destination, ax in zip(DESTINATIONS, axes.flat):
        rows = comparisons.loc[comparisons.destination.eq(destination)]
        actual = rows.loc[rows.case.eq("first_solve")].copy()
        ax.plot(actual.month.dt.to_timestamp(), actual.observed_bcm, color="#222222", label="EA proxy actual")
        for case, color, label in zip(cases, ["#bb6b30", "#17669b"], ["First solve", "Refined broader boundary"]):
            values = rows.loc[rows.case.eq(case)]
            ax.plot(values.month.dt.to_timestamp(), values.modelled_bcm, color=color, label=label)
        ax.set_title(destination)
        ax.set_ylabel("bcm/month")
        ax.grid(alpha=.2)
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(.93, .13))
    fig.suptitle("2024 reconstruction against EA proxies • supply boundary comparability unresolved")
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(OUT / "monthly_destination_comparison.png", dpi=150)
    plt.close(fig)
    pivot = metric.loc[metric.destination.isin(DESTINATIONS) & metric.case.isin(cases)].pivot(index="destination", columns="case", values="WAPE_pct").reindex(DESTINATIONS)
    ax = pivot.rename(columns={"first_solve": "First solve", "refined_broader_boundary": "Refined broader boundary"}).plot.bar(figsize=(10, 5), color=["#bb6b30", "#17669b"])
    ax.set_ylabel("WAPE (%)")
    ax.set_xlabel("")
    ax.set_title("2024 reconstruction WAPE • EA allocation proxies, not forecast scores")
    ax.tick_params(axis="x", rotation=0)
    ax.figure.tight_layout()
    ax.figure.savefig(OUT / "before_after_wape.png", dpi=150)
    plt.close(ax.figure)


def write_summary(metric, totals, assets, annual, trace, face, observations, preferences):
    t = totals.set_index("case")
    m = metric.set_index(["case", "destination"])
    before, after = t.loc["first_solve"], t.loc["refined_broader_boundary"]
    lines = ["# Targeted diagnosis of the first solved POC", "",
        "2024 latest-revised historical reconstruction. The EA destination observations are allocation proxies with unresolved export-boundary compatibility. These scores are not out-of-sample forecast results.", "",
        "## Changes and results", "",
        "Confirmed omitted net fields extend the existing feeds. Direct UK gas stays on the separate supply-bounded proxy, never entering Kollsnes or Karsto. The total Norway-minus-Snohvit envelope, capacities, signed maintenance and 2023 shares are unchanged. No 2024 actual destinations enter the optimisation.", "",
        "The original equal-weight L1 preference objective has multiple optima. After fixing maximum exports and the minimum L1 penalty, a final LP stage minimises the largest fractional shortfall against positive baseline targets. It introduces no hard country delivery volumes or price term. Zero-share destinations remain physically feasible. The ablation cases isolate this tie-break from source coverage.", "",
        "| Destination | Before WAPE % | Refined broader WAPE % | Legacy-boundary WAPE % |",
        "|---|---:|---:|---:|"]
    for d in DESTINATIONS:
        lines.append(f"| {d} | {m.at[('first_solve', d), 'WAPE_pct']:.2f} | {m.at[('refined_broader_boundary', d), 'WAPE_pct']:.2f} | {m.at[('legacy_formula_boundary', d), 'WAPE_pct']:.2f} |")
    lines += ["", f"Exports: {before.exports_bcm:.6f} → {after.exports_bcm:.6f} bcm. Unrouted: {before.unrouted_bcm:.6f} → {after.unrouted_bcm:.6f} bcm. Unclassified: {before.unclassified_bcm:.6f} → {after.unclassified_bcm:.6f} bcm. The remaining {after.unrouted_bcm - after.unclassified_bcm:.6f} bcm is constrained classified gas under provisional envelopes, not demonstrated real curtailment.",
        f"All months and diagnostic cases solve optimally with HiGHS. Maximum refined balance residual {after.max_mass_balance_residual_bcm:.3g} bcm; capacity violation {after.max_capacity_violation_bcm:.3g} bcm. Graph and LP share exactly the same nodes and arcs.", "",
        "## Supply trace and boundaries", "",
        f"The original residual is January–December 2024 net production: {before.unclassified_bcm:.6f} bcm. The workbook raw field ledger differs by {trace.ledger_minus_retained_series_bcm.sum():.9f} bcm annually; the rounding difference is retained in the residual, not discarded.",
        f"Confirmed additions: {trace.confirmed_gassco_additions_bcm.sum():.6f} bcm into named Gassco feeds, {trace.confirmed_direct_uk_additions_bcm.sum():.6f} bcm through direct UK systems. All month/field cells, routes, source URLs and legacy exclusion flags are in `unclassified_field_months.csv`.",
        f"The workbook legacy boundary removes {trace.legacy_excluded_residual_bcm.sum():.6f} bcm of these residual fields plus already-mapped Martin Linge {trace.martin_linge_already_mapped_bcm.sum():.6f} bcm exactly once. Its corrected annual supply is {t.at['legacy_formula_boundary', 'supply_bcm']:.6f} bcm versus broader {after.supply_bcm:.6f} bcm. The repeated Rev subtraction is corrected only in this diagnostic boundary. These exclusions are not a domestic-use deduction.",
        "The literal legacy boundary is not a clean physical Gassco-only boundary: it excludes Alvheim satellites yet retains other SAGE/FLAGS fields. Broader Norwegian pipeline exports include direct UK gas. Agreement against legacy QA destinations therefore cannot select the intended scope. Snohvit LNG is already excluded and is outside this residual. No residual field is established as genuinely non-exportable solely by the workbook formula.", "",
        "Unresolved field rows:", ""]
    for row in annual.loc[annual.source_node_after.eq("UNMAPPED")].itertuples():
        issue = " May cell FD436 is -0.000073 bcm; all months are withheld rather than clipped." if row.column == "FD" else ""
        lines.append(f"- {row.field}: {row.volume_bcm:.6f} bcm. {row.evacuation}.{issue} [Primary transport description]({row.source_url}).")
    lines += ["", "Heidrun's already-mapped net gas has both Haltenpipe/Tjeldbergodden domestic and Asgard/Karsto paths. The domestic fraction is not retained in these inputs. The plant description gives about 0.7 bcm/year typical Haltenpipe deliveries, not a measured 2024 field-month deduction. No invented subtraction is applied. [Heidrun](https://www.norskpetroleum.no/en/facts/field/heidrun/) and [onshore definitions](https://www.norskpetroleum.no/produksjon-og-eksport/landanlegg/).", "",
        "## Denmark / Poland and routing", "",
        "Nybro is shared North Sea Entry/transit, Faxe is onward Baltic Pipe/Poland delivery, and DK is retained Danish net offtake. The two deliveries are partitioned at Nybro; PL is never counted again as DK. North Sea Entry is 27.4 mcm/d shared by DK+PL; Baltic Pipe is separately 10/365 bcm/day. Both are physical envelope proxies, not commercial bookings or harmonised energy conversions.",
        "The first solve gives DK zero while Nybro/Baltic capacities are slack. Core gas cannot enter Europipe II upstream of Karsto. Europipe I/Norpipe bottlenecks and missing Karsto supply make it costly in total volume terms to match all shares. Within that shortage, sacrificing a bcm of DK/PL instead of DE has the same L1 cost. `first_solve_optimal_face.csv` proves the range of DK/PL allocations at identical maximum exports and L1 score, month by month. The tie-break prevents arbitrary concentration of that shortage; restored Karsto sources address its physical cause.",
        "UK errors are partly omitted FLAGS/SAGE/FUKA supply and partly aggregate route/preferences and target-boundary mismatch. Gas versus oil routes are distinguished: Tommeliten/Valhall/Hod gas enters Norpipe, while oil's Teesside path does not create a UK gas arc. Valemon is routed to Kollsnes for 2024, following its mid-2023 move from Heimdal. Tune is withheld pending sale-gas attribution rather than assuming all transported gas is an additional export. [Valemon](https://www.norskpetroleum.no/en/facts/field/valemon/) and [Tune](https://www.norskpetroleum.no/en/facts/field/tune/).", "",
        "## Capacity utilisation", "",
        "| Asset | Before annual % | After annual % | After peak % | After binding months |",
        "|---|---:|---:|---:|---:|"]
    a = assets.set_index(["case", "asset"])
    for asset in ["KOLLSNES_EXPORT", "KARSTO_PROCESSING", "EUROPIPE_I", "EUROPIPE_II", "NORPIPE", "LANGELED_SOUTH", "NORTH_SEA_ENTRY", "BALTIC_PIPE"]:
        lines.append(f"| {asset} | {a.at[('first_solve',asset),'annual_utilisation_pct']:.1f} | {a.at[('refined_broader_boundary',asset),'annual_utilisation_pct']:.1f} | {a.at[('refined_broader_boundary',asset),'peak_utilisation_pct']:.1f} | {a.at[('refined_broader_boundary',asset),'binding_months']:.0f} |")
    lines += ["", "Kollsnes 143 mcm/d is dry-export capacity; the current primary plant description quotes 146.5 mcm/d rich-processing capacity. The retained signed processing maintenance is still applied provisionally to the dry envelope: negative derates represent retained uplifts, not validated additions to dry nameplate. Karsto 95 mcm/d is rich processing applied to net field gas. These input-basis incompatibilities remain unresolved; no capacity was inflated to fit 2024. Added Fram/Valemon consequently increases modeled Kollsnes disposal. [Plant definitions](https://www.norskpetroleum.no/produksjon-og-eksport/landanlegg/).", "",
        "Monthly capacities enforce monthly feasibility, not intra-month outage scheduling. The pooled core cannot establish exact commercial nominations. DE/NL remain allocation proxies; direct UK route nameplates and 2024 volume-condition compatibility remain unverified. Positive arcs in the diagram are one optimum, not evidence of observed routes.", "",
        "## Remaining decisions", "",
        "Lead modeller decisions remain: the production/target export boundary, measured Heidrun domestic share, Brage Statpipe entry, Tune sale-gas treatment, Trym attribution, matching capacity/maintenance bases and direct route limits. No choice is embedded for unresolved rows. Seasonal preferences and price responsiveness are not added.", "",
        "Files: `metrics.csv` includes WAPE, MAE, bias and destination-share errors; `monthly_comparisons.csv` includes all seven destinations plus legacy pairs and Nybro DK+PL; `scenario_totals.csv` separates source and tie-break effects; `monthly_asset_utilisation.csv` reports every binding month; `monthly_baseline_deviations.csv` exposes targets and equal L1 weights. The updated diagrams are one directory above. The complete first solve and its implementation are preserved in `../../poc_first_solve/`. Initial archived-vintage forecasting benchmarks remain unchanged in `../../benchmark/`.", "",
        "Replay with the approved interpreter: `scripts/run/run_poc.py --solver HiGHS`, then `scripts/verify/diagnose_poc_routing.py`. Route evidence was retrieved once using only the residual fields; no SID discovery, helper edits, legacy edits or package installation.", ""]
    negative_dk = observations.loc[observations.DK.lt(0), "DK"]
    if len(negative_dk):
        at = lines.index("## Denmark / Poland and routing") + 2
        details = ", ".join(f"{month}: {value:.6f} bcm" for month, value in negative_dk.items())
        floor = 100 * negative_dk.abs().sum() / observations.DK.abs().sum()
        lines.insert(at, f"The retained DK proxy is negative in {details}. No nonnegative physical allocation can match it; the corresponding unavoidable DK WAPE contribution is at least {floor:.2f}%. Signed values remain in volume errors, never clipped. Destination-share errors exclude the entire negative basket month; `share_months` records coverage.")
        lines.insert(at + 1, "")
    at = lines.index("## Denmark / Poland and routing") + 2
    shares = ", ".join(f"{d} {100 * preferences[d]:.2f}%" for d in DESTINATIONS)
    lines.insert(at, f"Static earlier shares: {shares}. All second-stage deviations have weight 1 per bcm. No destination-specific penalty was fitted. Training uses complete nonnegative 2023 observations, excluding July/August; 2024 outcomes are not training inputs.")
    lines.insert(at + 1, "")
    january = face.loc[face.month.eq(face.month.min())].set_index(["destination", "bound"])
    lines.insert(at + 2, f"At January's original maximum exports and minimum L1 score, DK's individual feasible range is {january.at[('DK', 'minimum'), 'volume_bcm']:.6f}–{january.at[('DK', 'maximum'), 'volume_bcm']:.6f} bcm and PL's is {january.at[('PL', 'minimum'), 'volume_bcm']:.6f}–{january.at[('PL', 'maximum'), 'volume_bcm']:.6f} bcm. Zero DK was an arbitrary optimal allocation, not a closed Danish route.")
    lines.insert(at + 3, "")
    actual_total = observations.loc[:, list(DESTINATIONS)].sum().sum()
    at = lines.index("## Supply trace and boundaries") + 2
    lines.insert(at, f"The seven EA proxy observations total {actual_total:.6f} bcm, versus legacy-compatible supply {t.at['legacy_formula_boundary', 'supply_bcm']:.6f} bcm. The broader reconstruction's close annual total also contains gas excluded by that legacy formula and offsets it with provisional capacity disposal. Agreement in annual totals alone therefore does not validate either boundary or capacity basis.")
    lines.insert(at + 1, "")
    (OUT / "diagnosis.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
