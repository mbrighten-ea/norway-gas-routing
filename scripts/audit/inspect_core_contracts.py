"""Reproduce core-contract diagnostics using only retained observations."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from norway_gas_routing.evaluation import read_parquet


def main():
    audit = pd.read_csv(ROOT / "evidence/inputs/data_series_audit.csv", keep_default_na=False)
    selected = {}
    for row in audit.to_dict("records"):
        sid = row["sid"]
        if str(row["retrieval_ok"]).lower() != "true":
            continue
        if (row["key"] in {"production_total_no", "production_non_flexible", "production_troll", "production_oseberg"}
                or "Snohvit" in sid or "gas_production" in sid or sid.startswith("gassco\\")):
            selected[sid] = read_parquet(ROOT / row["raw_file"]).value
    prefix = "teams\\natural_gas\\EUR\\"
    total = selected[prefix + "NO_production"]
    excl = selected[prefix + "NO_production_excl_Snohvit"]
    field = selected[prefix + "NO_production_Snohvit_field"]
    old_sid = next(s for s in selected if s.endswith("gas_production"))
    old = selected[old_sid]
    production = pd.concat([total.rename("total_bcm"), excl.rename("excl_label_bcm"),
                            field.rename("field_label_bcm"), old.rename("older_snohvit_label_bcm")], axis=1)
    production["total_minus_excl_bcm"] = production.total_bcm - production.excl_label_bcm
    # Hypothesis only: do NOT relabel or use this transform as a model input.
    production["field_if_mcm_d_hypothesis_bcm"] = production.field_label_bcm * production.index.days_in_month / 1000
    production["hypothesis_residual_bcm"] = production.total_minus_excl_bcm - production.field_if_mcm_d_hypothesis_bcm
    production["older_if_mcm_d_hypothesis_bcm"] = production.older_snohvit_label_bcm * production.index.days_in_month / 1000
    production["older_hypothesis_residual_bcm"] = production.total_minus_excl_bcm - production.older_if_mcm_d_hypothesis_bcm
    production.to_csv(ROOT / "evidence/inputs/core_production_comparison.csv", index_label="month")
    def residual_summary(values):
        finite = values.dropna()
        return {"n": len(finite), "first": str(finite.index.min()), "last": str(finite.index.max()),
                "min": finite.min(), "max": finite.max(), "mean": finite.mean(),
                "max_abs": finite.abs().max(), "within_1e_10_count": int(finite.abs().le(1e-10).sum())}
    summary = {"production": {}}
    for label, start, end in [("through_2021", "1990", "2021"), ("2022_onwards", "2022", "2030")]:
        p = production.loc[start:end]
        summary["production"][label] = {"unscaled_residual": residual_summary(p.total_minus_excl_bcm-p.field_label_bcm),
                                       "field_mcm_d_hypothesis": residual_summary(p.hypothesis_residual_bcm),
                                       "older_mcm_d_hypothesis": residual_summary(p.older_hypothesis_residual_bcm)}
    shared = pd.concat([old.rename("old"), field.rename("field")], axis=1).dropna()
    summary["production"]["two_snohvit_versions"] = residual_summary(shared.old - shared.field)
    differences = (shared.old - shared.field).abs().gt(1e-10)
    summary["production"]["two_snohvit_versions"]["first_material_difference"] = str(shared.index[differences][0]) if differences.any() else ""
    counts = []
    for sid, values in selected.items():
        if not sid.startswith("gassco\\"):
            continue
        grouped = values.groupby(values.index.normalize())
        daily = grouped.agg(["count", "min", "max", "mean", "first", "last"])
        daily["intraday_range"] = daily["max"] - daily["min"]
        daily["sid"] = sid
        counts.append(daily.reset_index(names="calendar_date"))
    days = pd.concat(counts, ignore_index=True)
    days.to_parquet(ROOT / "evidence/inputs/core_gassco_daily_samples.parquet", index=False)
    regimes = []
    for (sid, year), group in days.groupby(["sid", days.calendar_date.dt.year]):
        regimes.append({"sid": sid, "year": int(year), "days_present": len(group),
                        "min_samples_per_day": int(group["count"].min()), "median_samples_per_day": group["count"].median(),
                        "max_samples_per_day": int(group["count"].max()),
                        "nonconstant_days": int(group.intraday_range.ne(0).sum()),
                        "maximum_intraday_range": group.intraday_range.max()})
    pd.DataFrame(regimes).to_csv(ROOT / "evidence/inputs/core_gassco_sampling.csv", index=False)
    left = days[days.sid.eq(r"gassco\StFergus")].set_index("calendar_date")
    right = days[days.sid.eq(r"gassco\St_Fergus")].set_index("calendar_date")
    overlap = left.add_prefix("new_").join(right.add_prefix("legacy_"), how="inner")
    overlap["sample_mean_difference"] = overlap.new_mean - overlap.legacy_mean
    overlap.to_csv(ROOT / "evidence/inputs/core_st_fergus_overlap.csv", index_label="calendar_date")
    summary["st_fergus"] = {"shared_days": len(overlap), "first": str(overlap.index.min()), "last": str(overlap.index.max()),
                            "missing_overlap_dates": [str(d) for d in pd.date_range(overlap.index.min(), overlap.index.max()).difference(overlap.index)],
                            "mean_difference": residual_summary(overlap.sample_mean_difference),
                            "new_sample_counts": overlap.new_count.value_counts().to_dict(),
                            "legacy_sample_counts": overlap.legacy_count.value_counts().to_dict(),
                            "range_overlap_days": int(((overlap.new_min <= overlap.legacy_max) & (overlap.legacy_min <= overlap.new_max)).sum()),
                            "correlation_of_sample_means": overlap.new_mean.corr(overlap.legacy_mean)}
    # Exact timestamps are never shifted to assert equality. Compare final samples
    # descriptively to determine whether the new daily series looks like a copy.
    overlap["new_vs_legacy_last"] = overlap.new_mean - overlap.legacy_last
    summary["st_fergus"]["new_vs_legacy_last"] = residual_summary(overlap.new_vs_legacy_last)
    overlap.to_csv(ROOT / "evidence/inputs/core_st_fergus_overlap.csv", index_label="calendar_date")
    summary["hypothesis_policy"] = "All rate scaling and sample means are descriptive hypotheses; no provider correction or flow aggregation is approved by these diagnostics."
    (ROOT / "evidence/inputs/core_contract_observations.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    print(pd.DataFrame(regimes).query("year >= 2020").to_string(index=False))


if __name__ == "__main__":
    main()
