"""Read-only Shooju retrieval for the routing audit; no registry edits."""

import hashlib
import json
from pathlib import Path

import pandas as pd
from helper_functions_ea import ShoojuTools, check_env


ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from norway_gas_routing.evaluation import ROUTINE_END, check_dates
RAW = ROOT / "data/raw/series_audit"


def evidence_name(sid):
    return hashlib.sha256(sid.encode()).hexdigest()[:16]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence/inputs").mkdir(exist_ok=True)
    check_env()
    sj = ShoojuTools(silence_alerts=True)
    snapshot = RAW / "registry_before_audit.csv"
    if not snapshot.exists():
        snapshot.write_bytes((ROOT / "config/data_series.csv").read_bytes())
    registry = pd.read_csv(snapshot, keep_default_na=False)
    candidates = []
    for row in registry.to_dict("records"):
        if row["sid"]:
            sid = row["sid"].removeprefix("sid=")
            candidates.append({"key": row["key"], "sid": sid,
                               "intended_role": row["model_role"], "category": row["category"]})
    # Only the relevant Norway and raw Gassco containers are searched.
    catalogue = []
    for query in [r"sid:teams\natural_gas\EUR\NO", r"sid=teams\natural_gas\EUR\NO_*",
                  r"sid:teams\natural_gas\EUR\daily_NO",
                  r"sid=teams\natural_gas\EUR\NL_*", r"sid=teams\natural_gas\EUR\DK_*",
                  r"sid:ENTSOG\transport_point\NL-TSO-0001"]:
        # The helper's fields=['*'] discovery branch duplicates series_id in
        # Shooju get_df. Its explicit-field branch avoids that upstream bug.
        frame = sj.get_fields_from_query(query, fields=["series_id"])
        records = frame.to_dict("records")
        catalogue.extend(records)
        print("Catalogue", query, len(records), flush=True)
    (RAW / "catalogue.json").write_text(json.dumps(catalogue, indent=2, default=str), encoding="utf-8")
    seen = {item["sid"].lower() for item in candidates}
    terms = ["maintenance", "snohvit", "snøhvit", "excl", "gassco", "netherlands", "denmark"]
    for meta in catalogue:
        sid = str(meta.get("series_id", ""))
        if not sid or sid.lower() in seen:
            continue
        text = (sid + " " + str(meta.get("description", ""))).lower().strip()
        if sid.lower().startswith("entsog"):
            if "emden" not in text or not text.endswith("\\entry\\physical flow"):
                continue
        elif "\\nl_" in text or "\\dk_" in text:
            if not any(term in text for term in ["norway", "norwegian", "imports_from_no"]):
                continue
        elif not any(term in text for term in terms):
            continue
        seen.add(sid.lower())
        category = "maintenance" if "maintenance" in text else "qa"
        if "production" in sid.lower():
            category = "production"
        candidates.append({"key": "candidate_" + evidence_name(sid), "sid": sid,
                           "intended_role": "REFERENCE ONLY", "category": category})
    pd.DataFrame(candidates).to_csv(ROOT / "evidence/inputs/audit_candidates.csv", index=False)
    for number, item in enumerate(candidates, 1):
        sid = item["sid"]
        name = evidence_name(sid)
        path = RAW / (name + ".json")
        # A completed retrieval is retained, so rerunning does not overwrite evidence.
        if path.exists() and (RAW / (name + ".parquet")).exists():
            continue
        record = {**item, "retrieved_at": pd.Timestamp.now(tz="UTC").isoformat(),
                  "date_start": "MIN", "date_finish": ROUTINE_END, "max_points": -1}
        try:
            record["metadata"] = sj.get_fields_from_sid(sid, fields=["*"])
            values = sj.get_points_from_sid_into_series(sid, "MIN", ROUTINE_END, -1)
            check_dates(values.index, 'read')
            values.to_frame("value").to_parquet(RAW / (name + ".parquet"))
            record["retrieval_ok"] = True
            print(number, len(candidates), sid, len(values), flush=True)
        except Exception as error:
            record["retrieval_ok"] = False
            # Error class only: avoid saving provider messages that might expose credentials.
            record["error_type"] = type(error).__name__
            print(number, len(candidates), sid, "FAILED", type(error).__name__, flush=True)
        path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
