# Stage 2 public capacity database

Implemented 9 October 2026. This is an **offline evidence database**, not a source of active optimiser limits. It preserves the [completed audit](public_capacity_findings.md), current assumptions, independent specification observations and three separate ENTSOG point series. No routing model, topology, configuration, evaluation split or historical assessment is changed.

The retained milestone is [archive/20261009-17_public-capacity-database](../../archive/20261009-17_public-capacity-database/README.md). Its functioning SQLite file is [database/capacity.sqlite](../../archive/20261009-17_public-capacity-database/database/capacity.sqlite). CSVs export the same contents. The archive also freezes implementation/test code, audit input evidence and model context, with hashes. Original public captures remain in `data/raw/public_capacity_audit/`, verified against the original audit manifest before each build.

## Contents and distinctions

Five physical tables implement the five logical roles; four views provide aggregation and comparison:

| Table/view | Contents and controls |
|---|---|
| `assets` | 19 active assumptions, 15 separately scoped foundation assets, 3 inactive point-pilot identities; `(operator, point, direction)` uniquely identifies each public point. Scope is part of the key so repeated foundation IDs are not extra active constraints. |
| `ratings` | Current model assumptions classified separately from evidence; 14 Gassco map observations; 16 plant observations; 4 transit specifications; 64 original ENTSOG interval records. Every row records physical boundary, unit, category, source, verification, effective-date precision and vintage. |
| `events` | Empty. No verified historical maintenance events were retrieved. Asset-level engineering event coverage is explicitly unknown. |
| `daily` | Published point technical quantities, gas-day boundaries/duration, coverage/quality, original record IDs and revision lineage. Engineering availability, commercial availability and bcm remain null. |
| `sources` | Citation and retrieval metadata, original capture/hash when retained, audit-transcription/hash when the original page was not retained, publication description and unknown first publication timestamps. Original capture gaps are visible. |
| `monthly` | Sum of daily kWh and GWh quantities by **local gas-day start-date month**; covered/missing/zero/conflicting day counts and elapsed hours. Complete-month totals are null if any day is unknown or the request covers only part of the month. Known subtotals remain labelled separately. |
| `coverage` | Requested/covered/zero/missing/partial/conflicting counts by point and year. |
| `specification_register` | Public specification observations for all 19 active assets; distinct conflicting sources preserved. |
| `assumption_comparison` | Exact current optimiser assumption, boundary and comparison status. |

The database contains 37 assets, 132 ratings, 39 source/provenance records, zero events, 3,564 daily observations, 117 monthly observations and 12 point-year summaries. Repeated construction into fresh paths produces identical SQLite and CSV hashes with the same inputs/runtime. Existing outputs are never overwritten. Schema/version and implementation hash are recorded in the database build manifest.

## Technical specifications versus model assumptions

All fourteen pipeline assumptions numerically match the independently audited Gassco 2024 transport map. Their status remains **verified snapshot only**: `valid_from` and `valid_to` are null. A year-labelled document is not evidence that a rating began on 1 January or applied unchanged during 2021–2025.

Kollsnes retains 143 dry-export statements, the 144.5 export figure in the internally dated 2019 brochure, the 144.5 processing description in the 2020 announcement, conflicting current English/Norwegian tables and the 156 upgrade evidence. The 146.5 rich-processing figure is also retained as definition-incompatible with net dry export. Gassco's successful **autumn 2023** expansion is qualitative change evidence with null exact effective dates. No preferred conflicting rating is selected, and no Kollsnes daily history is fabricated.

Kårstø retains approximately 95 million Sm3/day **rich-gas inlet processing** separately from the 97 generic processing figure in Equinor's 2024 annual report. The model's dry-gas throughput comparison is **definition incompatible**. Nyhamna's explicit 84 export specification is **verified snapshot only**, without invented unchanged historical validity.

North Sea Entry and Baltic Pipe model comparisons remain **provisional**. The specification labels include m3, Nm3 and annual bcm; matching gas reference conditions and a capacity-basis calorific conversion are not established. The Faxe entry/exit series are point observations associated with the Baltic route, not automatic substitutes for the route's 10 bcm/year assumption or any upstream pipe rating. The point assets are `verified compatible` with the pilot's identity/unit boundary only, and have `active=0`; no upstream engineering relationship is approved.

Web sources whose original pages were not retained are explicitly `retained_audit_transcription_original_capture_missing`. The verified audit statement and its hash are retained, but that does not manufacture an original page capture or a historical publication vintage. PDFs and pilot JSON have original capture paths and hashes.

## Daily pilot and monthly aggregation

Exactly three `Firm Technical` datasets are ingested:

| Identity | Boundary | Coverage |
|---|---|---|
| DK-TSO-0001 / ITP-00630 / entry | North Sea Entry | 2022-10-01–2025-12-31 |
| DK-TSO-0001 / ITP-10009 / exit | Faxe Danish side | 2022-10-01–2025-12-31 |
| PL-TSO-0002 / ITP-10009 / entry | Faxe Polish side | 2022-10-01–2025-12-31 |

Each contains 92 commissioning gas days in 2022 and complete 365/366/365 gas days for 2023/2024/2025. All twelve point-year coverage counts match the completed audit. Pre-October 2022 is outside the default pilot window; it is not backfilled. Original validity intervals and revision timestamps, including metadata extending beyond 2025, are preserved unchanged. Derived gas-day labels are capped at 31 December 2025; no holdout outcomes are loaded or scored.

Boundaries are independently localised at **06:00 Europe/Brussels (CET/CEST)** and converted to UTC for elapsed-time checks. Thus the gas day beginning 30 March 2024 has 23 hours and that beginning 26 October has 25 hours. Published kWh/d values already reflect the source gas day: normal 321.864 GWh, short 308.453 GWh, long 335.275 GWh at North Sea Entry. No extra multiplication by 24 or DST adjustment is applied. Leap day is included.

Intervals are half-open `[from,to)`, intersected with each requested gas day. Exact duplicate records collapse without summation; conflicting duplicate identities fail validation. Equal overlapping quantities can establish coverage once. Conflicting overlaps, unsupported intra-day changes, missing/NA/unlimited values and partial coverage leave the daily derived quantity null, retaining contributing record/revision lineage. No unsupported carry-forward occurs. Reported zero is a valid quantity with a distinct `reported_zero` flag. Capture counts/totals and first-page offset must be consistent before ingestion.

`technical_gwh_per_gas_day = original_kwh_per_gas_day / 1,000,000`. Monthly quantities sum those published daily quantities by start-date labels, **not calendar-midnight time slices**. February 2024 at normal capacity is `29 × 321,864,000 kWh`. This policy describes a source-point energy aggregate, not an approved monthly bcm limit or daily routing feasibility. Partial requested months retain only labelled subtotals; unknown days never become zero or full capacity.

The Danish and Polish Faxe sides remain separate. For example, on 2 October 2023 Denmark reports 321.864 GWh/day while Poland reports 201.480. They are neither averaged nor minimised into a new constraint. North Sea Entry's reported October 2022 zeros are preserved without labelling them outage events. `Firm Available` is recognised as commercial availability by classification but is not ingested in this pilot. No maintenance deductions are applied to already published technical values.

## Rebuild and query

From the repository, prepare a new named scratch experiment and use the approved workspace interpreter. The builder makes no network calls; its default output is a new uniquely named experiment:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$capacityScratch = Join-Path (Get-Location) '.scratch/runs/<new-named-run>'
New-Item -ItemType Directory -Path $capacityScratch | Out-Null
$env:TEMP = $capacityScratch
$env:TMP = $capacityScratch
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/audit/build_public_capacity.py --output "$capacityScratch/database"
```

`--from-day` and `--to-day` accept explicit 2021–2025 gas-day labels; default coverage is 2022-10-01–2025-12-31. Requests for 2026 or later are rejected. Changing the model or immutable audit evidence fails hash verification and requires an explicit new inventory review, not automatic source remapping. Do not overwrite the archived database; rebuild into a fresh directory.

Example SQLite queries:

```sql
SELECT * FROM assumption_comparison ORDER BY asset_id;
SELECT asset_key, month, technical_gwh, quality FROM monthly ORDER BY asset_key, month;
SELECT source_id, valid_from, valid_to, revision_timestamp, raw_record_json
FROM ratings WHERE capacity_category='point_technical';
```

An **optional, separate retrieval-only** command is provided as `scripts/audit/refresh_public_capacity.py`. It requests only these three public `Firm Technical` series, requires a new directory under `data/raw/public_capacity_refresh/`, rejects later historical dates and validates pagination/duplicate identities. It writes original pages and a retrieval manifest; it never replaces audit captures, imports into the database or connects the optimiser. No refresh was performed for this milestone. Refreshed captures require a separately reviewed source/vintage manifest before offline ingestion; the initial builder intentionally accepts only the audit's pinned captures. The fixed audit snapshots remain reproducible.

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/audit/refresh_public_capacity.py --output data/raw/public_capacity_refresh/<new-vintage> --from-day 2022-10-01 --to-day 2025-12-31
```

## Validation and next integration requirements

Targeted tests cover source identities/mappings, exact raw record replication, clipping, half-open intervals, DST/leap days, pagination, duplicates and overlaps, missing versus zero, separate Faxe values, partial-month quality, null engineering availability/bcm, technical/commercial classification, original revision/provenance flags and byte-identical rebuilds. Existing repository tests are also run; final counts and protected-file checks are in the retained milestone verification.

Validation completed: **322 tests passed**, one existing pandas/NumPy warning. A subsequent preservation check identified five files changed during the task without writes from this implementation: `config/data_series.csv`, `tests/integration/test_registry_references.py`, and `network_forecast_capacity_coverage.csv`, `network_forecast_sid_discovery.csv`, `network_forecast_unverified_references.csv` under `evidence/inputs/`. None is consumed by this database; all were preserved, and their before/after hashes are recorded. The 36 new capacity tests plus two registry-reference tests were rerun after that finding: **38 passed**. Model YAML, optimiser, prior results, public-capacity audit inputs and the Git index remain unchanged.

Priorities before optimiser integration:

1. Approve physical point-to-route boundaries, shared constraints and how Danish/Polish Faxe differences should limit transit. Association alone is insufficient.
2. Obtain documented compatible capacity-basis calorific values and volume reference conditions, and approve the energy-to-volume and monthly-boundary policy. All current bcm fields are deliberately null and guarded against population.
3. Resolve Kollsnes's dry-export baseline, exact expansion date and upgraded boundary; establish Kårstø net dry throughput. Preserve unresolved conflicts until evidence supports a choice.
4. Obtain dated upstream ratings and verified engineering restriction histories with overlap/dependency semantics. Missing event history remains unknown; never add unproven maintenance deductions.
5. Retain first publication/archive vintages for genuine forecast-origin use. Revision timestamps alone do not demonstrate earlier availability; this database is latest-revised reconstruction evidence.

The proposed next step is a reviewed **read-only mapping and conversion contract**, exercised with synthetic fixtures, followed by an explicit approval decision about which database fields can supply limits. No active model integration is included here.
