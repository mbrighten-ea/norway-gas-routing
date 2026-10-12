"""Profile retained Shooju evidence. Does not change the sourcing registry."""

import json
import math
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from norway_gas_routing.series_audit import (compare_series, forecast_coverage,
                                            overall_status, profile, st_fergus_overlap)
from retrieve_series_audit import evidence_name
from norway_gas_routing.evaluation import read_parquet, ROUTINE_END


def main():
    raw = ROOT / "data/raw/series_audit"
    snapshot = raw / "registry_before_audit.csv"
    if not snapshot.exists():
        snapshot.write_bytes((ROOT / "config/data_series.csv").read_bytes())
    registry = pd.read_csv(snapshot, keep_default_na=False)
    model = yaml.safe_load((ROOT / "config/model.yaml").read_text())
    horizon = pd.Timestamp(ROUTINE_END)
    candidates = pd.read_csv(ROOT / "evidence/inputs/audit_candidates.csv", keep_default_na=False).to_dict("records")
    candidates += [{"key": r["key"], "sid": "", "intended_role": r["model_role"], "category": r["category"]}
                   for r in registry.to_dict("records") if not r["sid"]]
    rows, observations, metadata, flagged = [], {}, {}, []
    for item in candidates:
        row = dict(item)
        sid = item["sid"]
        name = evidence_name(sid)
        file = raw / (name + ".json")
        evidence = json.loads(file.read_text()) if sid and file.exists() else {}
        meta = evidence.get("metadata", {})
        row.update({"retrieval_ok": evidence.get("retrieval_ok", False), "metadata_description": meta.get("description", ""),
                    "metadata_client_description": meta.get("ea_client_description", ""),
                    "metadata_name": meta.get("series_id_name", ""), "geography": meta.get("country", ""),
                    "source": meta.get("source", ""), "display_source": meta.get("display_source", ""),
                    "lifecycle_stage": meta.get("lifecycle_stage", ""), "economic_property": meta.get("economic_property", ""),
                    "metadata_unit": meta.get("unit", ""), "validated_unit": "", "metadata_frequency": meta.get("frequency", ""),
                    "forecast_start_date": meta.get("forecast_start_date", ""),
                    "history_sufficient": "UNRESOLVED: calibration/backtest dates not specified",
                    "forecast_sufficient": "UNRESOLVED", "semantic_status": "REVIEW", "unit_status": "REVIEW",
                    "frequency_status": "REVIEW", "value_status": "REVIEW",
                    "raw_file": str((raw / (name + ".parquet")).relative_to(ROOT)) if evidence.get("retrieval_ok") else "",
                    "metadata_file": str(file.relative_to(ROOT)) if evidence else ""})
        notes = []
        if not row["retrieval_ok"]:
            row["overall_status"] = "TODO"
            row["notes"] = ("No SID identified in scoped catalogue" if not sid else
                            "Established helper retrieval failed: " + evidence.get("error_type", "not attempted"))
            rows.append(row)
            continue
        values = read_parquet(raw / (name + ".parquet"))["value"]
        observations[sid] = values
        metadata[sid] = meta
        row.update(profile(values))
        interesting = (values < 0) | (values == values.min()) | (values == values.max())
        if values.diff().abs().notna().any():
            interesting |= values.index.isin(values.diff().abs().nlargest(3).index)
        subset = values[interesting].rename("value").to_frame().reset_index()
        subset.columns = ["timestamp", "value"]
        subset["sid"] = sid
        subset["key"] = item["key"]
        flagged.append(subset)
        frequency = row["observed_frequency"]
        row["forecast_sufficient"] = forecast_coverage(values, meta.get("forecast_start_date"), horizon, frequency)
        unit = meta.get("unit", "")
        if unit in {"bcm", "mcm_d", "kWh_d"}:
            row["unit_status"] = "PASS"
            row["validated_unit"] = unit
        if frequency == meta.get("frequency") and not row["duplicate_count"] and not row["missing_timestamp_count"]:
            row["frequency_status"] = "PASS"
        else:
            notes.append(f"Reported frequency {meta.get('frequency', 'absent')}; observed {frequency}; dominant interval {row['dominant_step']} ({row['dominant_step_pct']:.2f}%)")
        data_issues = ["negative_count", "missing_count", "nonfinite_count", "missing_periods", "duplicate_count", "missing_timestamp_count"]
        if "maintenance" in sid.lower() and unit == "mcm_d":
            # Analyst-approved 2026-10-08: signed adjustment to a baseline.
            # Negative observations remain counted, but are not a data blocker.
            data_issues.remove("negative_count")
            if row["negative_count"]:
                notes.append(f"negative_count={row['negative_count']}; approved signed maintenance: negative values increase available capacity relative to the reference baseline; no clipping")
        row["value_status"] = "PASS" if row["count"] and not any(row[k] for k in data_issues) else "REVIEW"
        for key in data_issues:
            if row[key]:
                notes.append(f"{key}={row[key]}")
        if row["count"] == row["zero_count"]:
            row["value_status"] = "REVIEW"
            notes.append("Entire returned series is zero; absence of activity/outage cannot be established")
        if item["category"] == "production":
            if meta.get("description") == "Norway natural gas supply to UK":
                notes.append("Generic description says UK supply; client description/name says field or Norway production; provider identity correction required")
            else:
                notes.append("Production/reconciliation definition requires review against Norway total and LNG exclusion")
            if "snohvit_field" in sid.lower() or "gas_production" in sid.lower():
                row["unit_status"] = "REVIEW"
                row["validated_unit"] = ""
                notes.append("Observed LNG-production magnitude/negative values require unit and formula verification; bcm label alone is insufficient")
        elif sid.startswith("gassco\\"):
            notes.append("Intraday observations labelled mcm with daily-rate descriptions; gas-day, sampling and rate/volume meaning unresolved; no hourly sum or inferred conversion")
            row["unit_status"] = "REVIEW"
        elif sid.startswith("ENTSOG\\"):
            notes.append("Energy flow kWh_d; no approved energy-to-volume factor; cannot use for bcm calibration yet")
        elif "maintenance" in sid.lower():
            if item["intended_role"] == "REFERENCE ONLY":
                row["semantic_status"] = "PASS" if meta.get("description") and unit == "mcm_d" else "REVIEW"
            notes.append("Under the approved convention zero means no adjustment to the reference baseline; additional infrastructure constraints are not promoted to model input")
            if "upstream_maintenance" in sid.lower() or "adjusted" in sid.lower():
                notes.append("Reference/QA only: overlap with exogenous field forecasts unresolved; do not add a supply/plant constraint")
            if item["key"] == "maintenance_kollsnes":
                row["semantic_status"] = "PASS"
                notes.append("Accepted provisional processing adjustment; available_capacity = reference_capacity - maintenance; negative values are an uplift; reference/technical capacity remains unsourced")
        elif item["category"] == "calendar":
            if (values.to_numpy() == pd.DatetimeIndex(values.index).days_in_month).all():
                row.update(semantic_status="PASS", unit_status="PASS", frequency_status="PASS", validated_unit="days")
                notes.append("Every value verified against calendar days in its timestamp month")
        elif unit == "bcm" and meta.get("description") and meta.get("country"):
            row["semantic_status"] = "PASS"
            notes.append("QA/benchmark only; not an independent raw flow or calibration target")
        else:
            notes.append("Identity/model relevance or conversion has not been established")
        if row["forecast_sufficient"] == "WITHHELD_BY_POLICY":
            notes.append("Forecast start is beyond the permitted horizon; reserved values were not inspected")
            if item["intended_role"] in {"supply", "capacity_constraint"}:
                row["value_status"] = "REVIEW"
        if row["forecast_sufficient"] == "false":
            notes.append("Finite observations do not cover the permitted evaluation horizon through 2025-12; later values are withheld by policy")
            if item["intended_role"] in {"supply", "capacity_constraint"}:
                row["value_status"] = "REVIEW"
        if unit == "bcm" and item["category"] == "production":
            total_sid = r"teams\natural_gas\EUR\NO_production"
            total_file = raw / (evidence_name(total_sid) + ".parquet")
            if total_file.exists():
                total = read_parquet(total_file).value
                pair = pd.concat([values.rename("field"), total.rename("total")], axis=1).dropna()
                above = pair.field > pair.total
                row["above_norway_total_count"] = int(above.sum())
                if above.any():
                    row.update(unit_status="REVIEW", value_status="REVIEW", validated_unit="")
                    notes.append(f"Exceeds Norway total in {int(above.sum())} shared months; maximum excess={(pair.field-pair.total).max():.6g} bcm")
        row["overall_status"] = overall_status(True, [row[k] for k in ["semantic_status", "unit_status", "frequency_status", "value_status"]])
        row["notes"] = "; ".join(notes)
        rows.append(row)
    audit = pd.DataFrame(rows)
    pd.concat(flagged, ignore_index=True).to_parquet(ROOT / "evidence/inputs/review_observations.parquet", index=False)
    cross = {}
    def compare(label, left, right):
        if left is not None and right is not None:
            cross[label] = compare_series(left, right)
    def get(suffix):
        return observations.get("teams\\natural_gas\\EUR\\" + suffix)
    total = get("NO_production")
    excl = get("NO_production_excl_Snohvit")
    snohvit = get("NO_production_Snohvit_field")
    compare("total_minus_excl_vs_snohvit", total - excl, snohvit)
    compare("nonflex_plus_troll_plus_oseberg_vs_total", get("NO_production_non_flexible_fields") + get("NO_production_Troll_field") + get("NO_production_Oseberg_field"), total)
    field_sids = [r["sid"].removeprefix("sid=") for r in registry.to_dict("records") if r["model_role"] == "supply"]
    fields = pd.concat([observations[s] for s in field_sids], axis=1)
    compare("all_named_fields_vs_excl_snohvit", fields.sum(axis=1, min_count=len(field_sids)), excl)
    for label, a, b, aggregate in [("DE_NL_benchmarks", "gassco_DE", "gassco_NL", "gassco_NL_and_DE"),
                                  ("FR_BE_benchmarks", "gassco_FR", "gassco_BE", "gassco_FR_and_BE")]:
        compare(label, get("NO\\" + a) + get("NO\\" + b), get("NO\\" + aggregate))
    compare("NL_imports_vs_gassco_NL", get("NL_net_imports_from_Norway"), get("NO\\gassco_NL"))
    # DK uses lower-case eur in the provider ID.
    compare("DK_imports_vs_gassco_DK", observations.get(r"teams\natural_gas\eur\dk_imports_from_no"), get("NO\\gassco_DK"))
    cross["st_fergus"] = st_fergus_overlap(observations[r"gassco\StFergus"], observations[r"gassco\St_Fergus"])
    cross["DE_NL_raw_reconciliation"] = {"status": "BLOCKED", "issue": "Gassco intraday rate/volume sampling unresolved; Dutch EPT1 kWh_d needs approved conversion; benchmark bcm cannot substitute for raw observations"}
    cross["UK_raw_reconciliation"] = {"status": "BLOCKED", "issue": "St Fergus physical continuity/overlap and Gassco intraday aggregation require confirmation"}
    for sid, daily in observations.items():
        if "\\daily_NO\\" not in sid:
            continue
        monthly_sid = sid.replace("\\daily_NO", "")
        if monthly_sid in observations and metadata[sid].get("unit") == metadata[monthly_sid].get("unit") == "mcm_d":
            # Monthly mcm/d is a mean daily rate, not a monthly bcm volume.
            mean = daily.resample("MS").mean()
            counts = daily.resample("MS").count()
            mean = mean.where(counts == mean.index.days_in_month)
            compare("monthly_mean_vs_daily:" + monthly_sid, mean, observations[monthly_sid])
        upstream_sid = monthly_sid.replace("NO_maintenance_", "NO_upstream_maintenance_")
        if upstream_sid in observations and metadata[upstream_sid].get("unit") == metadata[sid].get("unit"):
            compare("normal_vs_upstream:" + sid, daily, observations[upstream_sid])
    for sid in [r"gassco\StFergus", r"gassco\St_Fergus"]:
        mask = audit.sid == sid
        overlap = cross["st_fergus"]["calendar_day_sample_means_exploratory"]
        audit.loc[mask, "notes"] += f"; St Fergus calendar-day overlap={overlap['overlap_count']} despite no identical timestamps; max sample-mean difference={overlap['max_absolute_residual']}; do not sum or stitch without physical-definition approval"
    current = pd.read_csv(ROOT / "config/data_series.csv", keep_default_na=False)
    # Link each candidate to the proposed registry without losing failed old
    # identifiers or the starting registry's unsourced requirements.
    proposed_file = ROOT / "evidence/inputs/data_series_proposed.csv"
    proposed = pd.read_csv(proposed_file, keep_default_na=False) if proposed_file.exists() else current
    sid_to_key = dict(zip(proposed.sid.str.removeprefix("sid="), proposed.key))
    audit["registry_key"] = audit.sid.map(sid_to_key).where(audit.sid.ne(""), audit.key).fillna("")
    starting_blank = audit.sid.eq("") & audit.key.isin(proposed.loc[proposed.sid.ne(""), "key"])
    audit.loc[starting_blank, "notes"] = "Starting registry requirement had no SID; a proposed replacement is audited separately under the same registry_key"
    for name, sid in [("NL_imports_vs_gassco_NL", r"teams\natural_gas\EUR\NL_net_imports_from_Norway"),
                      ("DK_imports_vs_gassco_DK", r"teams\natural_gas\eur\dk_imports_from_no")]:
        result = cross[name]
        mask = audit.sid == sid
        audit.loc[mask, "notes"] += f"; Different benchmark definition/vintage: {result['overlap_count']} shared months; max absolute difference={result['max_absolute_residual']:.6g} bcm; not interchangeable"
        audit.loc[mask, ["semantic_status", "overall_status"]] = "REVIEW"
    findings_path = ROOT / "evidence/inputs/core_contract_findings.json"
    if findings_path.exists():
        findings = json.loads(findings_path.read_text())
        for sid, finding in findings["series_notes"].items():
            mask = audit.sid.eq(sid)
            audit.loc[mask, "notes"] += "; " + finding
            audit.loc[mask, ["semantic_status", "overall_status"]] = "REVIEW"
    audit.to_csv(ROOT / "evidence/inputs/data_series_audit.csv", index=False)
    # Strict JSON: undefined residuals for non-overlap are null, not NaN.
    def finite_json(value):
        if isinstance(value, dict):
            return {key: finite_json(item) for key, item in value.items()}
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    serialisable = finite_json(cross)
    (ROOT / "evidence/inputs/cross_series_audit.json").write_text(json.dumps(serialisable, indent=2), encoding="utf-8")
    print(audit.overall_status.value_counts().to_dict())
    print("Retained successful series", len(observations))


if __name__ == "__main__":
    main()
