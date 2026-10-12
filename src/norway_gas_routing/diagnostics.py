"""Report unresolved inputs separately from configuration schema errors."""

import argparse
import json
from pathlib import Path

from .config import load_config


def configuration_report(model: dict, series) -> dict:
    """Summarise a config loaded by load_config and list its unresolved inputs."""
    issues = []

    def report(code, location, message):
        issues.append({"code": code, "location": location, "message": message})

    for key, row in series.iterrows():
        if not row["sid"]:
            report("missing_sid", f"series.{key}", f"{row['required_level']} series has no SID")
        if row["target_unit"] == "fraction_or_capacity":
            report("unresolved_capacity_semantics", f"series.{key}", "Unit and availability/derate semantics are unresolved")
        if row["category"] in {"physical_exit_flow", "country_flow"} and not row["raw_unit"]:
            report("unresolved_raw_unit", f"series.{key}", "Raw units and retrieval conversion need verification; hints are not executable")
    for key, asset in model["assets"].items():
        if asset["technical_capacity_mcm_d"] is None:
            report("missing_technical_capacity", f"assets.{key}", "Technical capacity remains null; no capacity/effective limit is inferred")
    for key, source in model["sources"].items():
        if not source.get("active", True):
            report("inactive_unresolved_source", f"sources.{key}", "Excluded until identified/reconciled")
    for key, status in model["transformation_status"].items():
        if status == "decision_required":
            report("decision_required", f"derived_series.{key}", "Retained proposed formula is not implemented")
    for section in ("solver", "calibration"):
        for key, value in model[section].items():
            if value is None:
                report("unresolved_control", f"{section}.{key}", "No default is supplied")
    if model["units"]["bcm_to_mwh"] is None:
        report("unresolved_energy_conversion", "units.bcm_to_mwh", "No gas energy conversion is supplied")
    if model["model"]["reference_price_market"] == "NETHERLANDS":
        report("decision_required", "model.reference_price_market", "Existing NL reference differs from conceptual DE reference; commercial logic is unimplemented")
    return {
        "schema_valid": True,
        "production_ready": False,
        "data_availability": "not assessed by schema diagnostics; consult evidence/inputs/data_series_audit.csv for live retrieval evidence",
        "counts": {"series": len(series), "sources": len(model["sources"]),
                   "nodes": len(model["sources"]) + len(model["junctions"]) + len(model["markets"]),
                   "arcs": len(model["arcs"]), "assets": len(model["assets"]),
                   "markets": len(model["markets"]), "maintenance_inputs": len(model["maintenance_inputs"])},
        "issues": sorted(issues, key=lambda issue: (issue["location"], issue["code"])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    args = parser.parse_args()
    model, series = load_config(args.config_dir / "model.yaml", args.config_dir / "data_series.csv")
    print(json.dumps(configuration_report(model, series), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
