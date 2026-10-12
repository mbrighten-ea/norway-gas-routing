# B2 closure and F1 forecast readiness — 12 October 2026

Baseline `9390691`; one worker; fresh EA/Shooju queries only. No holdout actuals,
forecast solver, forecast scores, workbook numerical inputs or new price model.
The [assessment manifest](assessment_manifest.json) links bounded responses,
metadata, import-job records, hashes, Git identity and HTML/CSV assessments.

| Mode/input | Verified availability | Specific limitation |
|---|---|---|
| 2024 reconstruction | All 62 mapped fields, national/LNG accounting, maintenance and earlier shares; 12 optimal months | Existing provisional physical/capacity assumptions remain |
| Current monthly forecasts, Oct 2026–Dec 2030 | 16 selected EA fields, national and non-flex total: 51/51 months each | No individual forecast counterpart identified for the other 46 fields |
| Current LNG/capacity inputs | Selected Snøhvit: 39 months to Dec 2029; Kollsnes plan: 1553/1553 daily points to Dec 2030 | Snøhvit 2030 absent; forecast rate semantics and maintenance scope require validation; technical capacities are baseline scenarios |
| Historical first origin, 31 Dec 2023 | January 2024 forecasts for national + 16 EA fields + five original EA flow groups | 46 field forecasts unidentified; selected Snøhvit/maintenance absent; capacity and training origin contracts incomplete |
| 2024 monthly origins | National: 12/12; original EA flows: 60/60 group-months | Zero complete routing input bundles; actual issuance dates unverified |

## Hanz closure

The [Directorate field record](https://factpages.sodir.no/en/field/PageView/All/25307278)
records production from **20 April 2024**, corroborated by the operator's
[Q1 transcript](https://akerbp.com/wp-content/uploads/2024/04/2024-q1-transcript.pdf).
Fresh Hanz data returns March **0 bcm**, April **0.0001 bcm**, and ten observations
through December. January/February alone become structural zeros, with an explicit
[rule/evidence record](../routing_sources_b1/hanz_preproduction.json); the raw
response is unchanged. Contradictory pre-production values and other missing
months/fields fail. This authorisation does not generalise missing-to-zero.

The [source-backed Excel](../../../outputs/routing_runs/20261012T141200162824Z_fa3c46c3/results.xlsx)
and provenance package passed all monthly supply identities and solver checks:
exports **117.0831345 bcm**, maximum mass-balance residual **1.776e-15 bcm**,
capacity violation **0**. All package hashes and nine worksheets were checked;
missing legacy forecasts and incompatible comparisons remain unavailable.

## Current forecast contract

[Current coverage](current_forecast_coverage.csv) identifies exact SIDs, metadata
units, delivery dates, source hashes and missing months. Existing EA monthly
field/national forecasts are bcm directly. The historical NPD sources are actuals,
not forward forecasts; the [46-field matrix](field_forecast_mapping.csv) preserves
their routing-node identities. Scoped `NO_production*` and `NO\*` discovery found
no replacements; this is not a global proof of absence. The existing workbook
formula/lineage audit does not authorise its cached forecast numbers.

Latest retrieved means today's service state, not recent issuance: selected
Snøhvit's forecast boundary remains October 2025 and the legacy excluded total's
September 2022. These stale feeds are not silently treated as a current cohort.

The legacy Snøhvit and LNG-excluded total extend only to December 2026 (3/51
requested months). The dashboard production total lacks a verified forecast
boundary and was rejected before point retrieval. Gassco's forecast total has
51/51 months but is an export-accounting total, not the LNG-inclusive supply
boundary. Non-flex production overlaps named fields and LNG; it cannot be added
or split across missing nodes without changing methodology. Forecast Snøhvit's
mislabelled bcm-versus-rate semantics must be checked for each chosen vintage;
the historical conversion guard was not extended.

`project_data.get_prospective_forecast` is a separate inspection path: metadata
must declare a genuine forecast segment before point I/O, dates must be current
month or later, never before October 2026, and end by December 2030. Returned
out-of-bounds points are rejected before persistence. Ordinary historical reads,
evaluation and operational forecast gates remain unchanged. Prospective execution
will need its own controlled preparation path once complete sources exist.

## Historical replay and comparisons

[Single-origin checks](single_origin_coverage.csv) recover the December 2023
service state. The legacy Snøhvit source also returns 12/12 2024 forecast months
at this cutoff; it is a candidate requiring rate/cohort validation, not a silent
replacement. Selected Snøhvit and maintenance return no values at all twelve
monthly cutoffs. Technical schedules/effective dates at those origins are absent.
All seven full-year 2023 training series cross their archived forecast boundary;
four also have incomplete observed months. Thus today's fixed 2023 preferences
cannot simply be labelled origin-available; define and freeze a pre-target
training rule using contemporaneous actuals before implementing replay.

[2024 delivery/origin coverage](walk_forward_2024_coverage.csv) records each
month, production/EA import timestamps and explicit gaps. Month-end cutoffs are
inspection dates, **not original EA issuance dates**. At the first cutoff,
production imports date to 4 December and four flow-group imports to 18 December
2023. Public issuance/release metadata was not found; DK lacks a snapshot-job
timestamp. The other 16 field origins were not queried after the first complete
selected-field check, because essential forecast/maintenance dependencies remain.

[Actual comparison coverage](actual_comparison_coverage.csv) confirms 12/12
revised EA monthly allocation observations for each original group. UK, FR+BE
and NL+DE support allocation-group comparisons, not independent terminal-receipt
claims. DK signed net offtake and PL historical Nybro entry are incompatible with
gross exports: scoring remains withheld. No grouped series is disaggregated.

Three registered EEX delivery-curve SIDs (TTF, NBP, PEG) returned no values for
January 2024 at the first cutoff. This does not establish global archive absence.
Other origins/products, quote valuation dates, delivery-contract mapping, dated
FX and unit conversion remain unverified. Revised realised prices are not
origin forward prices. Price-free routing does not depend on these inputs.

## Next development decision

Both forecast modes are **blocked by specific sourcing dependencies**; neither
can be implemented directly on the complete existing physical model. First obtain
maintained direct forecast feeds for the 46 leaves (or explicitly approve a
documented forecast construction), complete compatible Snøhvit through 2030,
and origin maintenance/technical schedules. Establish original EA issuance
evidence or approve service-cutoff comparisons with explicit limitations; approve
the origin training rule and forecast capacity scenarios. Recover one complete
bundle before building walk-forward execution. No current aggregate split,
historical capacity backdating, price calibration or frozen-input exception was
adopted here.

Reproduce with `scripts/audit/assess_forecast_viability.py` and its
`--supplement` checks using the approved interpreter. Each invocation creates
unique source and assessment packages; it does not solve, fit or score.
