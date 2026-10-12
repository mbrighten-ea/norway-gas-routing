# Current implementation state

## Historical NPD input activation B2 — 12 October 2026

Implemented on `feature/historical-npd-input-b2` from verified `be294be`.
All 46 known NPD identifiers passed direct field/measure/unit identity checks
and were added to the canonical registry and existing source contract/ledger.
45 returned complete January–December 2024 coverage. Hanz returned ten months,
March–December; January and February are absent, not assumed zero. Sindre's
old metadata SID label is accepted only with matching current series_id_name,
field and marketed saleable-gas definition. No source discovery was repeated.

Default full-year live command produced
`outputs/routing_runs/20261012T132445551243Z_21658147/`: BLOCKED_INPUTS on
`hanz_net_actual`, missing `2024-01-01, 2024-02-01`. The nine-sheet Excel,
diagnostic dates, raw response hashes and manifest were checked. No optimisation
or full-year real-data result exists. Downstream preparation after this first
coverage error has not been demonstrated with live data. Activation evidence is
retained locally under `data/raw/npd_activation/`; ledger rows identify exact
metadata paths, retrieval dates and hashes. Existing evidence remains preserved.

Validation: 300 regression checks passed, followed by 13 focused NPD checks
after adding the registry activation/recheck test. The latter verifies full
configuration validation, original registry preservation and no duplicate append.
Excel previews were reviewed; unavailable results and Hanz's dates are visible.

Full-network manufactured SID responses exercise all 62 field components,
unchanged capacities, signed LNG accounting, residual supply, LP/reporting and
Hanz failure propagation. This does not manufacture missing live observations.
Price-free objective, EA import checks, forecast-origin requirements, physical
field mappings and locked 2026 holdout remain unchanged. NPD actual monthly bcm
is used directly, independently of the EA import batch and older workbook values.

Restart: inspect Git state; obtain genuine Hanz January/February source coverage
before retrying `scripts/run/run_routing.py --config config/run.yaml` (or
`--validate-only`). If source evidence supports a pre-start zero treatment, that
would require an explicit methodological decision; it is not embedded here.
Real-data preparation is activated, but full-year 2024 execution remains blocked.

The B1 section below records the pre-activation state and is historical.

## Real-data input integration B1 - 12 October 2026

Implemented on `feature/real-data-input-b1` from verified `0de2ba4`.
[Formula-only source audit and ledger](evidence/inputs/routing_sources_b1/README.md)
classify all 46 workbook leaves as essential: Kollsnes 2, Karsto 16, Sleipner 4,
UK-direct 17 and Ekofisk 7. Each has an existing exact Directorate discovery
candidate, but none has a verified canonical EA mapping. Zero new mappings or
registry/status changes. No workbook observations or reserved-period values used.

`routing_inputs.prepare_fresh_inputs` uses existing direct SID interfaces and a
reviewed evidence contract for 28 already selected IDs. It validates canonical
identity, exact monthly/daily coverage, units, historical segments, signed LNG and
maintenance, production import cohorts, physical residuals and unchanged source
memberships/topology/capacities. It saves original responses before analytical
validation; bad essential data never reaches an LP. Optional current comparison
failures remain unavailable and separate from essential earlier training. DK/PL
gross-export errors and all forecast comparisons remain withheld. Milestone A's
CLI, validation-only, unique Excel/CSV/chart/HTML packages and hashes are preserved.

Offline tests exercise successful preparation/solve/reporting using manufactured
SID responses and an explicitly reduced fixture-only topology/contract; this does
not approve dropping any full-model inputs. Existing synthetic/solver/vintage/
reporting tests pass: 289 total, with all 46 source/workflow integration checks
passing again after final provenance changes. Mock Excel comparisons and source
inventory previews were reviewed. Default 2024 validation produces a BLOCKED_INPUTS package
identifying all 46 dependencies before any service connection. No live retrieval,
frozen-input replay, source reallocation, price/evaluation change or holdout access.

Restart: inspect branch/HEAD/status; run the README command with `--validate-only`
to inspect the blocker inventory. Real-data execution is **not operational** until
all essential component identities, monthly semantics and aggregate/vintage
equivalence are independently verified and reviewed into canonical mappings and
the evidence contract. Existing outputs, source evidence and assumptions remain.

## Operational backend Milestone A - 12 October 2026

Implemented on `feature/operational-milestone-a` from verified `4acf8e9`.
`config/run.yaml` and `scripts/run/run_routing.py --config ... [--validate-only]`
separate preparation/validation, optimisation and Excel-first reporting. Each
invocation creates a unique `outputs/routing_runs/<run_id>/` with no baseline
promotion. Exact prepared inputs, original/resolved configuration, source/code
metadata, hashes, solver results and Git identity are retained. See README's
operator guide and INPUTS's operational contract for usage and schemas.

Explicit synthetic demonstration solves the existing seven-sink network and
produces nine labelled Excel sheets, a native chart, CSVs, PNG/SVG, HTML and
provenance. Validation-only performs no LP construction or solver discovery.
Missing EA comparisons remain visibly unavailable. Workflow, workbook numeric
reconciliation, hashes, failure packages, config errors, non-overwrite behaviour,
single-target-month shape and existing solver/vintage/reporting regressions are
covered by synthetic tests; no live retrieval or frozen-input replay is used.
Validation: 20 workflow tests and 229 existing regressions passed; all nine
worksheet previews were reviewed, and a twelve-month CLI demo reconciled Excel
to CSV and every manifest file hash. Supported-input validation stops with the
documented missing-SID inventory rather than consuming retained data.

Fresh-SID real runs still stop before retrieval: 46 workbook-only component
references have no reviewed SID mappings. Forecast modes, price routing and
non-baseline capacities are not exposed by this command. Future one-month-ahead
preparation needs complete independently verified origin evidence and the existing
forecast validator; revised observations cannot substitute. Historical guards,
2026 holdout, canonical assumptions and saved assessments are unchanged.

Restart: inspect branch/HEAD/status, then use README's single command with an
explicit synthetic configuration for an offline demonstration. Next real-data
implementation requires reviewed missing SID mappings and source/vintage semantics;
no previous frozen-input exception is broadened. Generated demo packages remain
local; only task code/config/docs/tests belong in the commit.

## Optional price-response comparison - 12 October 2026

Completed on `experiment/price-response-2024`, based on `e0f524d`. The user
explicitly extended frozen 2024 supply/preferences use to this offline price
experiment and approved common quote-date means, same-date ECB conversion and
TTF as a single DE/NL pool proxy. Prices were queried afresh for 2024 only.
Stage 1 fixes maximum exports; Stage 2 balances L1 preferences against spreads;
Stage 3 preserves that combined optimum. Zero follows the original solve path.
BE/DK/PL have no price coefficient but can move indirectly.

All 672 month/capacity/strength/shock combinations completed; 209 relevant
tests passed. Zero reproduces both price-free capacity cases within 1e-9 bcm.
At 143, observed prices shift UK +0.942437, FR -1.355652 and BE +0.413215 bcm/year;
at assumed 156, UK +0.597724 and FR -0.597724. DE/NL pool totals are unchanged.
Low/medium/high pooled responses coincide for these observations: positive
weights resolve existing L1 ties. Within-pool allocations are not separately
price-identified. Exports remain 117.0831345/119.377524 bcm respectively.

[Report/CSV/charts](archive/20261012-04_price-response/report.html) and
[method](evidence/inputs/price_response_experiment.md) retain provenance and
capacity-versus-price decomposition. Coefficients are illustrative, not fitted;
no forecast validation or revenue claim. Kollsnes dry/maintenance definitions,
UK route limits and collapsed commercial boundaries remain material uncertainties.
Next: modeller review of tie sensitivity, pool proxy and physical/commercial
boundaries before any further approved experiment. No automatic calibration,
promotion, 2025 evaluation or holdout access. Defaults and old results preserved.

## Frozen 2024 capacity comparison - 12 October 2026

Completed on `capacity/frozen-2024-sensitivity` from `0f923b3`. The user's
one-off exception covers verified frozen 2024 inputs solely for this offline
model-to-model comparison; normal fresh-SID and forecast-origin rules remain.
Baseline replay maximum difference is 4.99581e-10 bcm. All eight scenarios ran:
Kollsnes 144.5/156 assumptions add 0.501228/2.2943895 bcm exports; the 156 case
removes mapped disposal, leaving 0.446859 bcm UNMAPPED. Kårstø 97 and evidence-backed
mode do not change exports. No public conversion or default capacity is activated.
242 relevant tests passed. Fixed the inactive contract's hash check to recognise
only the already approved configuration rename; unrelated changes still fail.
Results, charts and provenance: [capacity comparison](archive/20261012-02_capacity-sensitivity/report.html).
Next action is modeller review of plant-boundary/maintenance assumptions and
dated ENTSOG conversion evidence, not automatic promotion or further frozen runs.
Existing archives, registry, 2025 guards and locked 2026 holdout are preserved.

## Source structure - 12 October 2026

Branch `refactor/project-structure` groups capacity components under
`src/norway_gas_routing/capacity/` and reports/visuals under `reporting/`.
The active model, input module, commands, tests, configuration section and
dependency extra use `routing` names. All retained modules have identified
consumers; archived names, raw inputs and saved results remain intact.
Configuration values and optimiser operations are unchanged. The exact naming
migration in `evidence/inputs/project_structure_migration.json` keeps the public
capacity audit's original model identity verifiable.
Validation: 424 synthetic tests passed with one existing pandas warning; three
command help/import checks and a scratch wheel build passed, including the HTML
template. Historical-data evaluation/rebuild tests were not run.
Restart: inspect `git log -1` and the working tree; publication of this feature
branch requires approval. Do not resume the modelling tasks below.

## Git baseline - 12 October 2026

Initial Git baseline: source, tests, configuration, instructions, selected lightweight
evidence and registry migration metadata. Raw data, workbooks, generated outputs and
historical archive bundles remain local and untracked; see README.md. No model
behaviour changed. The obsolete staged `config/sids.py` was empty; its blob and the
original index are preserved in `.scratch/git-initialisation/`. Validation: 192
synthetic tests passed with one existing pandas warning; Python syntax and credential
scans passed. The existing DECISIONS.md EOF blank line is preserved.
Initial commit: `4a951cab437a53adce54240a8c4c70d688126440` on `main`. User approved
publication to `origin/main` (`https://github.com/mbrighten-ea/norway-gas-routing.git`)
on 12 October 2026. Repository-local file work needs no further approval; writes
outside this repository are prohibited. Restart: inspect `git log -1` and the
staged/working-tree state, then verify `origin/main` against the local commit.
Do not resume the modelling tasks below.

Updated 9 October 2026. HiGHS solves the latest-revised 2024 reconstruction.
Production readiness and genuine out-of-sample new-model evaluation remain open.

Snøhvit sensitivity (9 October 2026): both explicitly authorised full-year 2025
diagnostics solved: official net saleable monthly bcm and the selected series
using mcm/day × calendar days / 1,000, including October–December forecasts.
Neither is a validated baseline or genuine historical forecast. Exports are
114.175610333 bcm in both; country allocations match within solver precision.
The selected case excludes 0.0299246 bcm more Snøhvit, reducing only unrouted
residual supply by that amount. Signed net values and single LNG subtraction remain.
The normal July guard remains; an explicit named diagnostic override is restricted
to full-year 2025. Source lineage and aggregate/net boundary reconciliation remain
unresolved. All 2024 results replay within 1e-9 bcm; capacity violations are zero
and maximum balance residual is 1.7764e-15 bcm. 279 tests passed with one existing
pandas warning. No preferences, objectives, capacities, maintenance or active
source configuration changed; 2026 remains locked, unloaded and unscored.
Results: [2025 comparison](archive/20261009-13_snohvit-sensitivity/report.md).

## Chronological evaluation

2025 routing flexibility (9 October 2026): the provisional official-net scenario
has 1.815139 bcm UNMAPPED disposal and 1.667919667 bcm mapped Kollsnes disposal.
Known cached residual fields reconcile the UNMAPPED amount; Halten Øst contributes
1.167452 bcm and remains unclassified. No missing field values were filled.
At unchanged monthly maximum exports, Germany can individually gain up to
19.037721 bcm/year, France 2.732313 and Poland 2.696856. DE/NL share an unconstrained
allocation pool; DK/PL share North Sea Entry. Extrema are not simultaneous targets
or evidence of price causation/commercial flexibility. All 168 endpoint solves,
2024 replay and preserved 2025 scenario checks pass; 284 tests passed with one
existing warning. No optimiser/config/source/capacity changes; no holdout access.
Evidence: [routing flexibility](archive/20261009-14_routing-flexibility/report.md).

User-approved split is enforced by `config/evaluation.yaml` and `evaluation.py`:
development through 2024-12; candidate comparison in 2025-01–2025-12; reserved
2026-01–2026-09 remains locked and unscored. Shares/preferences cannot fit 2025
or 2026 outcomes. The existing price-free baseline still uses 2023 shares.
Cached/retrieved inputs, scoring, plotting and publication have date gates.
Origin-bundle checks require verified archive/release evidence for production,
maintenance, effective technical capacities, historical flows and any prices;
parameter-training vintages cannot pass the 2024 information cutoff. Revised
inputs remain reconstruction, including validation-period reconstructions.
Pre-protocol raw caches/evidence are preserved, not a clean unseen-data claim;
routine reads exclude reserved observations. The old inventory writer embeds
later-value findings and is disabled. No holdout unlock or scoring is implemented.
Full 2025 reconstruction also remains blocked by the existing Snohvit conversion
validation ending July 2025. No new vintages were retrieved for this change.

Chronological enforcement verification is complete: 265 synthetic tests passed
with one existing pandas/NumPy timedelta warning (fresh scratch test run -06).
The seasonal leakage fixture now compares seasonal predictions only. Reserved
Parquet values and technical CSV values are blocked before observation loading;
future forecast-start metadata returns an explicit policy-withheld audit status.
Forecast evidence rejects missing archive/availability dates and capacities not
effective for their claimed monthly coverage. Publication requires results to
match the declared target window. Input records identify categories, consumed
months, units and unverified vintage limitations; parameter and code hashes are
retained in the manifest and final verification.

Only the cached price-free 2024 reconstruction and its diagnosis were rerun.
Final run `20261009-09_routing-diagnosis` matches eight saved destination, flow,
score, scenario, supply, capacity and preference tables (1e-9 numeric tolerance):
supply 119.824383 bcm; exports 117.0831345; unrouted 2.7412485; unclassified
0.446859. Maximum balance residual is 1.776e-15 bcm; capacity violation is zero.
All 524 protected raw-input, frozen-benchmark, configuration, model and index
hashes match; the previous successful assessment is preserved in scratch.
The read-only original benchmark verifier confirmed 120 forecast points,
original identities and constraint paths without recomputing scores. Report
structure, 139 local links and three generated figures were checked. Evidence:
[final chronological verification](outputs/reconstruction/provenance/chronological_verification.json).
No 2025 reconstruction or 2026 holdout score was run; the holdout remains locked.

## Current assessments

Same-origin accuracy comparison requested: select 2024-12-31 and evaluate
2025-01 through 2025-12 without fitting to validation outcomes. A bounded EA
archive probe retained 84 forecast points (production total, five destination
groups and declared total). Selected Snøhvit and Kollsnes maintenance have no
origin values; the production-workbook component snapshot and complete
capacity/training availability evidence are missing. No backtest or accuracy
ranking was generated using revised reconstruction inputs. Required evidence
and exact responses: [origin readiness](archive/20261009-20_forecast-origin-readiness/report.md).
The 2026 holdout and all existing model/results remain unchanged.

User confirmed SID-only sourcing: query Shooju directly on every new run;
workbooks are formula/SID references only. Direct registered-series retrieval
now supports explicit `asof` and retrieves values/metadata afresh, rejecting
empty archives without a cache fallback. Existing routing model/report readers still
use retained workbook/cache paths and are not approved for new data-consuming
runs until migrated. No model mappings or alternative SIDs were adopted to
bypass missing origin data; this migration and missing SID coverage remain open.

- `outputs/reconstruction/`: refined broader-boundary reconstruction; saved
  exports 117.0831345 bcm, unrouted 2.7412485, unclassified 0.446859.
- `outputs/benchmark/`: retained legacy forecasts at 2023-12-31 and 2024-06-30,
  seasonal comparisons and original first-solve reconstruction. It is frozen.
- `archive/20261008-01_first-solve/`: original results and immutable original
  code/config identities; the refined model does not overwrite that evidence.

## Cleanup and verification

Price-response feasibility audit: the unchanged 2024 price-free model replay
matches current results within 1e-9 bcm; 131 targeted solver, capacity, scoring
and leakage tests passed. All 574 protected source/config/raw/result/index
hashes match. Full 2025 input preparation fails at the existing Snohvit
conversion limit ending July 2025, so no 2025 allocation comparison was run.
NBP, TTF, THE and PEG have retained quotes in all 12 validation months; selected
Reuters ZTP has no retained cache, while EEX ZTP and ETF alternatives need
product/calendar selection. Poland has no selected price reference. Monthly
aggregation, FX and origin vintages remain unresolved. The stop condition was
applied: no price objective, response-strength fitting or seasonal changes.
The 2026 holdout remains locked and unscored. Evidence and exact input identities:
[price-response feasibility](evidence/inputs/price_response_feasibility.md).

Structure rules/file gate are in AGENTS.md; implemented roles/commands in README.
The optional full plan remains REPOSITORY_CLEANUP_PLAN.txt. Historical STATUS,
README, configuration and code remain in the cleanup snapshot, with a relocation
map. Existing Git index (staged config/sids.py addition, working deletion) is
preserved; no commits, staging, remote operations or package changes were made.
Post-migration verification: 180 synthetic tests passed (one existing warning);
572 source/config/original-result file hashes, 139 report links and the frozen
first-solve identities passed. Both relocated cached-data drivers produced exact
matching destination/arc/scenario/score tables in temporary experiments, without
replacing current successful assessments. No empty managed folders remain.
Evidence: archive/20261009-01_repository-cleanup/verification.json.

Access limitations: .pytest_cache, .pytest_tmp and pytest-of-martell.brighten
could not be enumerated; contents are unknown and remain untouched. Do not infer
empty folders or change ACLs. The previously confirmed data_series.csv error 32
requires the holding application to release it. Configuration/data bytes were
preserved; historical path strings in frozen evidence/config notes resolve via
the migration map, not by changing original source evidence.

## Remaining lead-modeller choices

Stage 2 public-capacity database (9 October 2026): an offline five-table SQLite
database retains 19 active assumptions, 15 foundation assets, 14 independent
pipeline snapshots, conflicting plant specifications and three separate ENTSOG
technical point histories. All 3,564 daily observations cover October 2022 through
December 2025; 12 point-year counts match the completed audit. Energy aggregates
are provided by source gas-day start label. Events remain empty, engineering
availability and bcm remain null, and historical origin availability is unverified.
No optimiser integration, model assumptions, configuration or result changes.
Before integration, approve point-to-route mappings and conversion/monthly policy,
resolve Kollsnes/Karsto boundaries, and source upstream restriction/publication
history. Commands, limitations and retained milestone:
[Stage 2 public database](evidence/inputs/public_capacity_database.md).

Public technical-capacity source audit (9 October 2026): the 19 active routing model
constraints and 15 retained foundation assets are inventoried. Gassco's 2024 map
corroborates fourteen pipeline snapshots; public ENTSOG intervals cover all
2023-2025 gas days for North Sea Entry and both Faxe directions in energy units.
A complete upstream daily engineering-availability history is not established.
Kollsnes 144.5-to-156 expansion is supported in autumn 2023, but the exact day
and dry-export baseline remain unresolved; Karsto 95 rich-gas processing is not
verified net dry throughput (another public specification reports 97).
Gassco historical UMM probes yielded empty/template responses and GMP timed out.
Stage 2 needs approved boundary mappings, volume reference/GCV definitions,
historical outage/publication vintages and overlap/unknown-day treatment.
No implementation, assumptions, splits or historical results changed. Evidence:
[public capacity findings](evidence/inputs/public_capacity_findings.md).

- Production/target export boundary and revised EA destination proxy definitions.
- Measured Heidrun domestic allocation; Brage Statpipe entry, Tune sale-gas
  attribution, Trym Danish attribution and withheld negative Vilje field cells.
- Kollsnes dry-export capacity versus processing-maintenance basis, Karsto
  rich/net equivalence, effective capacities and direct UK route limits.
- Complete contemporaneous inputs, service cutoff/release timing and missing
  historical Snohvit/Kollsnes inputs for genuine out-of-sample evaluation.

The refined tie-break preserves maximum exports and minimum L1 deviation before
minimising worst fractional shortfall. Negative DK net allocation remains signed
in volume errors and invalidates that month's entire share basket. Monthly
capacity feasibility is not daily scheduling; model disposal is not demonstrated
actual curtailment. Cleanup changes storage/reporting, not these calculations.

## Network and forecast-source audit — 20261009-16

[Findings and recommendations](evidence/inputs/network_forecast_findings.md)
identify Halten Øst and Urd as route/forecast-ready for a separately approved
residual reallocation using the verified workbook snapshot through December 2030.
Brage, Tune and Balder remain conditional; Trym needs a separate Danish source
boundary. All six have cached individual forecasts, but no individual EA SID was
identified. Sixteen selected field forecasts match live EA exports exactly;
the national forecast reconciles including workbook Snøhvit. The selected
Snøhvit SID still lacks 2030, while the workbook contains it.

Seven verified Directorate historical SIDs were appended as optional inactive
references. Existing records, selected inputs, preferences and allocations are
preserved; 286 tests pass and all twelve 2024 months replay within 1e-9 bcm.
Capacity/observation gaps still prevent validated production price-response
claims. Next implementation needs explicit approval for field reallocations,
maintained forecast-source/vintage handling, Kollsnes/Kårstø boundaries and
receiving-point/country definitions. No topology, capacity, guard or split changed;
2026 holdout allocations remain locked and unscored.

## Capacity integration contract — 20261009-18

[Inactive recommendation](evidence/inputs/capacity_integration_recommendation.md)
and [mapping contract](evidence/inputs/capacity_integration_contract.json) retain
three conditional point mappings, complete 2023–2025 energy histories and separate
Faxe sides. No engineering constraint replacement or bcm conversion is approved.
Remaining decisions: dated operator capacity-basis calorific factors and historical
reference conditions, common model volume/month boundaries, shared-system
applicability, restriction independence and publication vintages. Separate approval
is required before any adapter is connected. Model, registry, reconstructions and
2025 diagnostics are preserved; 2026 holdout remains locked and unscored.


## Six-field workbook SID lineage — 20261009-19

[Exact-cell evidence](evidence/inputs/workbook_sid_lineage.md) documents all 138
header cells and the six fields’ forecast/source trails. No individual EA SID
is present in the workbook. Halten Øst uses stored profile inputs, a manual
6.55 scale and temporary +4; Balder stores literals; the other four fields use
annual-lag decline formulas. Maintained refresh ownership and publication vintages
remain unresolved before implementation. No new SID, active input or model change.
186 relevant tests and extraction/preservation checks pass; all previous results,
registry and Git index preserved. No 2026 holdout actual values were accessed.
