"""Bounded verification of transport for the existing 2024 residual field ledger."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evidence/inputs"


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        value = value.strip()
        if value:
            self.parts.append(value)


def retrieve(row):
    field = row.header_evidence.split(f"{row.column}23: ")[-1].strip()
    slug = field.lower().replace("ø", "o").replace("æ", "ae")
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    url = "https://www.norskpetroleum.no/en/facts/field/" + slug + "/"
    result = {"column": row.column, "field": field, "url": url,
              "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(url, headers={"User-Agent": "Norway-routing-research/1.0"}), timeout=35) as response:
            parser = Text()
            parser.feed(response.read().decode("utf-8"))
        start = parser.parts.index("Transport") + 1
        end = parser.parts.index("Status", start)
        result["transport"] = " ".join(parser.parts[start:end])
        result["status"] = "verified current primary description; check historical applicability"
    except Exception as error:
        result.update(status="unverified", error=str(error))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = pd.read_csv(ROOT / "outputs/benchmark/details/unclassified_fields_annual.csv")
    # These two already-mapped fields matter to domestic and capacity compatibility.
    rows = list(ledger.loc[ledger.volume_bcm.gt(0)].itertuples())
    from types import SimpleNamespace
    rows += [SimpleNamespace(column="AQ", header_evidence="AQ23: HEIDRUN"),
             SimpleNamespace(column="AN", header_evidence="AN23: GULLFAKS SOR")]
    path = OUT / "field_transport_evidence.json"
    if path.exists():
        raise FileExistsError("Retained route evidence is immutable; use the existing file")
    with ThreadPoolExecutor(max_workers=4) as pool:
        evidence = list(pool.map(retrieve, rows))
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in evidence:
        print(row["column"], row["field"], row.get("transport", row.get("error")))


if __name__ == "__main__":
    main()
