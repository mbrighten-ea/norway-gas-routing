# Current implementation state

## Project cleanup and supported workflow

Branch `maintenance/project-cleanup-f212` starts from retained F2.11 `da10771`.
Use `config/run.yaml` and `scripts/run/run_routing.py`; the redundant F2.4 example
and implicit standalone scenario entry were retired. The unchanged 12-month
default still requires explicit Core opt-in for a provisional forecast.
README now contains one workflow and the committed release index (182 lines,
previously 452). Old cleanup plan/verifier are under the existing cleanup archive;
the CSV verifier imports its library directly rather than importing the runner.
New timestamped output is ignored until deliberately verified and retained.

Recovered the exact missing F2.3 `f23-live.yaml` from its original worktree;
its SHA matches the existing manifest. No existing release bytes were changed.
Seventeen hash manifests, 2,415 files and 51 report links resolve. F2.4/F2.6 and
F2.7 all-four-case saved-input replays pass with unchanged monthly results;
F2.10 independent accounting/scoring verification passes. F2.8 historical code
hashes resolve to its original Git revision, rather than the later helper version.
The ordinary suite passes in a fresh tracked-file export: 639 passed, 14
evidence-dependent tests deselected, one existing warning; focused checks: 62 passed.
The supported CLI's source-free synthetic `--validate-only` smoke check passes
for the normal 12-month window without constructing an LP.

Top-level source groups/foundation validation still have live consumers, so remain
intact; only `model.yaml.routing` feeds the executable LP. Broader I/O/reporting
refactors, pinned output deletion, untracked evidence and other unpushed worktrees
were deliberately deferred. No physical, supply, preference, scenario, historical
comparison or holdout behaviour changed. Next work remains the Core review below.

## 2025 routing-error attribution

[F2.11 report](outputs/routing_error_attribution_2025/report.html) and its
[monthly attribution](outputs/routing_error_attribution_2025/results.csv) use the
unchanged F2.10 package `a676910`. Branch `analysis/routing-errors-2025-f211` adds
analysis only: no retrieval, model/configuration change, new forecast or holdout read.

At a common actual export volume, mean misallocated volume is 0.463 bcm/month
for physical routing, 0.287 for EA and 0.526 for all-twelve-month 2023 shares.
The network improves static shares overall, especially UK, but worsens FR/BE.
December, May and June explain 1.131 bcm of the 2.107 bcm annual model-minus-EA
routing-error distance. Static preferences miss seasonal destination changes;
UK-direct floors are only 0.65–0.69 bcm in these months and do not pin total UK.

Fifty-four bounded LP queries, using only frozen forecast inputs, preserve the
original physical constraints and optionally all three saved objective optima.
The final optimal set still permits UK/FR-BE exchanges of 0.351, 0.364 and
0.263 bcm in those months. DE/NL is pinned by the combined corridor envelope
and preference-selected Nordic allocation, not independently by physical exits.
The 143 Kollsnes case slightly worsens normalised allocation error (0.480 bcm/month).
Capacity applicability remains provisional; this audit proves no topology error.

Next Core decision: investigate whether annual-2023 preferences and unresolved
final-objective ties meaningfully identify flexible UK versus France/Belgium.
Do not select a new optimal point from 2025 scores or change weights/capacities.
143 focused regression tests passed; frozen-package hashes, score identities and
all diagnostic node/capacity checks pass. The original Excel and forward model remain intact.

## First revision-tolerant 2025 accuracy comparison

[Excel comparison](outputs/revision_tolerant_2025/results.xlsx) and
[analytical report](outputs/revision_tolerant_2025/report.html) are available for
the December-31-2024 origin and all twelve 2025 deliveries. Branch
`feature/revision-tolerant-2025-f210` starts from clean `3313de7`, containing F2.7–F2.9.
The user approved revised pre-origin histories and provisional input assumptions;
the exercise is explicitly not a verified real-time backtest.

Current SIDs provide 24 native Snøhvit observations for 2022/2023 and the 2023
production-owner cohort. Monthly national accounting closes below 6e-15 bcm. Residual
denominator 19.346535 bcm; UK-direct share 34.911735%; 0.120104 bcm is UNMAPPED
(0.620804% of residual: Vale 0.093766, Atla 0.026338 bcm) and remains unrouted.
Missing Tommeliten/Hanz/Trym source
months are explicit observed-subtotal limitations, never filled. Core routes are
applied to the pilot only with unique ownership; Balder/Urd each have twelve
explicit zero observations, Rev twelve observations, Halten Øst no 2023 addend.
Oseberg's three-child aggregate and Åsgard's native ownership reconcile.

Reference 156 and predeclared 143 Kollsnes planning cases each solved twelve
months before any target actual retrieval. No historical planned outages were
invented. Reference exports 119.675641 bcm; unrouted 0.148967 bcm is the unmapped
packet. Stress exports 118.575710 bcm; additional disposal 1.099932 bcm. No
capacity violations or operational model changes occurred. No 2025 production
in weights, source sensitivity, parameter tuning or protected actual retrieval.

Raw WAPE model/EA: UK 16.25/10.07%; FR+BE 16.23/10.43%; NL+DE 3.84/5.90%;
common adjusted three-group total 4.13/4.37%. These are mixed sample rankings,
not overall superiority. After removing common-volume error for scoring, EA has
lower destination-share MAE for all three groups. The apparent physical NL+DE
raw advantage partly reflects error cancellation. Shared national forecast bias
is +2.840609 bcm; seasonal LNG bias +0.674669; pipeline bias +2.165940 bcm.
Individual DE/NL and DK/PL remain proxies; wider export total is unscored.

Next analytical review: source-mix and static-preference contributions to UK/FR+BE
overallocation and NL+DE conditional underallocation, using the frozen comparison.
Do not change parameters based on this small sample or activate 2025 weights.
639 ordinary regression tests passed, 14 external-evidence tests explicitly
deselected, one existing pandas warning. F2.7 strict package verification still passes.

## Minimum December-2024 backtest package

F2.9's [single focused attempt](outputs/minimum_backtest_f29/report.html) returns
**BLOCKED_INPUTS (deliverable B)**. Branch `audit/minimum-backtest-f29` starts from
clean `4465c87`, containing F2.7/F2.6. No model, configuration, calibration,
source allocation or operational forecast was changed.

Fresh exact December-31-2024 SID archives recover all 17 production forecasts
and four legacy forecast groups for every 2025 month. Origin-available 2023
preferences supply ten valid baskets under the unchanged rule. Native/selected
Snøhvit history is empty; the older series has only Jan-Aug 2022 historical
observations. Its Sep2022-Dec2023 cells are forecasts and cannot form the seasonal
baseline. All 75 residual-owner SIDs are empty for 2023, including the original
46 mapped residual fields. Archived national production minus the explicit 16
is 25.076500 bcm, containing LNG plus residual production; no denominator or
weights were invented. The numeric Kollsnes reference remains unverified in
the dated records reviewed; no planned-outage schedule or retrospective rating
was introduced.

Stop reached: no LP run, actual-2025 retrieval, scoring or comparison Excel.
Next is one source-owner/provider bundle of dated 2022/2023 Snøhvit net-saleable
observations, a mutually exclusive 2023 ledger with origin-known mappings or
evidenced exclusions, and an applicable dated Kollsnes technical rating. Dated
EA/SODIR snapshots could substitute after Core source/ownership approval; later
revisions cannot become an origin-correct backtest through approval alone.
The exact missing components, forecast imports and hashes are retained in the
linked report. 106 existing seasonal/vintage/holdout checks passed. Full regression
was not repeated for this evidence-only task. No protected 2026 actuals were read.

## Seasonal history and chronological allocation readiness

F2.8 uses isolated `feature/seasonal-inputs-f28`, based on clean F2.7 `d4e3f57`
containing F2.6 `b8d8e03`; no investigation merges. `snohvit_method:
seasonal_two_year` is an explicit optional historical assumption in the existing
fresh Core current-input workflow. The SID-backed default and approved live
weights/capacities/optimiser remain unchanged. No historical runner was unlocked.

The [input comparison](outputs/chronological_inputs_f28/report.html) retains fresh
exact-origin SID responses and hashes at October 13, 2026 and December 31, 2024.
2024/2025 native net-saleable history yields 38 seasonal forecast months totalling
16.855625 bcm versus 17.555713 bcm from the selected SID. Signed history, selected
years, rates, information cutoff and monthly values are retained. The unchanged
same-origin F2.7 supply basis remains nonnegative under the seasonal assumption.
December-2024 native and selected Snøhvit archives are unavailable; this cannot yet
be a genuine historical forecast input. No protected actuals or scoring occurred.

The 2025 residual denominator is 20.010318 bcm. Existing owners' observed subtotal
18.842866 plus Halten Øst's observed 1.167452 matches it; missing Rev Oct-Dec and
Halten Øst January are not zeros. Balder/Urd contribute 0.047575 bcm with unknown
entries. Halten Øst group ownership/entry needs approval, and Verdande/national
revision differences remain separate. Indicative UK-direct share is 25.746%, versus
approved 2024 31.775%; its same-residual-basis supply difference is -5.782919 bcm.
These are observed-subtotal diagnostics, not complete or activated rolling weights.
The December-2024 candidate Dec2023-Nov2024 ledger cannot be certified because
native residual owner archives are unavailable; the 2026 certificate is not reused
as an origin-correct calibration.

Historical Kollsnes fallback is full applicable technical capacity with no invented
planned outages. The 2023 report proves a pre-origin upgrade but supplies only an
approximate 8% increment; the precise 156 statement is January 2025. One dated
pre-origin numeric/boundary contract is still needed. Live Kollsnes is unchanged.

Next: obtain one December-2024 archive bundle of eligible LNG history, owner ledger
and contemporaneous mappings, plus the dated technical rating; Core must approve
the rolling-weight contract. Existing F2.5 archived production/legacy forecasts
and origin-available preferences provide the other starting inputs for an untuned
2025 comparison. Do not start scoring or apply diagnostic shares automatically.

Validation: 634 ordinary regressions passed; 14 retained-public-evidence tests
were explicitly deselected because this clean worktree lacks their external
bundle. One existing pandas warning remains. The 31 focused method/package
checks passed, and strict F2.7 package verification preserves all four released
totals. No source mapping, network, capacity, objective or holdout policy changed.

## Live forecast acceptance

[Live scenario Excel](outputs/forward_scenarios/20261013T165915778836Z/results.xlsx)
uses fresh EA SID queries at explicit origin 2026-10-13 16:59:13 UTC, with F2.6
implementation `b8d8e03`. All four scenarios are OPTIMAL for November 2026–December
2029 (152 monthly solves); raw sources agree across cases, source ownership is
unique, national closure is <6e-15 bcm and capacity violations are zero. Exports
A/B/C/D are 358.366178 / 354.060774 / 353.399510 / 349.094107 bcm. The fresh rolling
12-month reference also ran and matches A's first 12 monthly results. No model
code, physical assumptions, parameter fitting or protected-actual reads changed.

Ready for routine **provisional** analyst use with explicit `core_f24` settings.
Conditional mapped eligible coverage is 100%; 26.74% of pipeline supply remains a
frozen residual-mix proxy, not independently verified future entry-point coverage.
The [live report and acceptance provenance](outputs/forward_scenarios/20261013T165915778836Z/report.html)
include compatible prospective EA comparisons: adjusted UK +7.711552 bcm (+10.62%),
FR+BE +0.106316 (+0.11%), NL+DE -11.274491 (-7.31%). No accuracy scores were computed.
June 2027's UK comparable physical minimum at the same maximum exports is 1.608043
bcm versus EA 1.287610; some excess is forced under these assumptions, while the
exact allocation is not uniquely determined by physics. Core review should focus
on summer UK/continental differences, residual UK-direct mix, dated technical
capacities and preference-selected DE/NL and DK/PL splits. Heidrun remains an
outside-network bound, not a domestic forecast; mixed LNG vintage and provisional
capacity availability remain disclosed. No hard live-input obstacle was found.

## Operational release hardening

The exact four F2.4 scenario YAML snapshots have been recovered and restored with
their original manifest hashes. Nested `.scratch` ignores no longer omit snapshots.
The [primary scenario Excel](outputs/forward_scenarios/20261013_f26/results.xlsx)
combines existing monthly/annual flows, sensitivities, accounting, source nodes and
capacity utilisation. Original forecast values and release files remain intact.
Use the normal operator command with `compare_scenarios: true` for four scenarios;
the ordinary 12-month default remains unchanged. Retained-evidence tests have an
explicit opt-in and original public-bundle prerequisites; see README.md.
QA: the fixture-free clean checkout passed 614 ordinary regressions (14 explicitly
deselected evidence checks), with one existing pandas warning. All 14 retained-
evidence checks passed separately against their original hash-verified bundle.
Five focused workflow checks also cover the verifier's pre-read holdout boundary.
Strict restored-release hashes and all 152 saved-input replays pass. The ordinary
12-month command and 50-month validation-only command were demonstrated using
clearly labelled synthetic inputs. No model assumptions or forecast values changed.

## F2.4 provisional forward routing — 13 October 2026

Core approved the explicit provisional input contract, superseding the F2.3
non-material blockers for this experiment. One worker, isolated worktree
`.scratch/worktrees/f24`, branch `feature/provisional-routing-f24` from verified
`2335831 -> a34bc72 -> f4a742e`; no investigation merges or retained evidence edits.
Approval is recorded in DECISIONS.md; source equations and exclusions in INPUTS.md.
The unmodified `config/run.yaml` retains the ordinary 12-month default. F2.4 opts
in through the explicit Core settings in `config/run.yaml` and the supported
`scripts/run/run_routing.py` command. Original F2.4 run requests remain in the
released packages; the redundant standalone example has been retired.

[Released POC and scenario links](outputs/forward_scenarios/20261013T134952692166Z/report.html):
all four scenarios completed 38 monthly solves OPTIMAL (152 total), based on
implementation `c18c12e`, with identical freshly queried raw sources at the common
origin 2026-10-13 13:49:52 UTC. Every national balance closes <6e-15 bcm. A totals:
376.310523 national = 17.555713 LNG + 0.104469 external Trym + 358.366178 exports
+ 0.284163 modelled forced disposal; UNMAPPED zero under the approved annual proxy.
Eligible network representation is 100%; pipeline-boundary representation 99.97088%.
Frozen residual proxy supplies 26.73568% of pipeline volume: this does not certify
future field memberships. Denominator 18.785806; node weights Kårstø 39.39453%,
UK direct 31.77533%, Ekofisk 14.07254%, Kollsnes 8.48259%, Sleipner 5.09695%,
Oseberg 1.06914%, external Trym 0.10892%, UNMAPPED 0. Heidrun is explicit, never
residual; signed Vilje annual net stays positive. Native zero owners are observed,
not missing-to-zero. Existing Hanz-only structural zeros are separately recorded.

Exports A/B/C/D: 358.366178 / 354.060774 / 353.399510 / 349.094107 bcm. Domestic
bound excludes that month's Heidrun, totalling 4.305403 bcm. Largest monthly
country sensitivity: D minus A France April 2027 -0.518767 bcm (-31.90446%).
At the same export-volume basis, physical constraints reallocate 22.354393 bcm
(6.24%) versus naive 2023 shares. Net UK +13.178474 and FR +9.012093 versus that
baseline; DE -13.781778 and NL -3.565803. Franpipe/Zeepipe export bind 23/26 months,
Kollsnes 4; Europipe I/Norpipe also frequently bind. Binding parallel arcs can be
nonunique; DE/NL and DK/PL individual allocations have broad physical ranges and
depend primarily on preferences/proxies. UK has an infrastructure floor in some
high-supply months. No claim of independently identified market demand.

[Verification](outputs/forward_scenarios/20261013T134952692166Z/provenance/validation.json)
records raw/source and workbook checks. 43 focused and 624 full regression checks
passed; one existing pandas warning. All four packages retain Excel/CSV/HTML/charts,
country/corridor outputs, source ownership/weights, shares, constraints and provenance.
No network, objective, historical reconstruction or holdout guard was changed; no
protected 2026 actual observations retrieved or exposed. Existing offline fixtures
were copied for tests only, original tracked bytes restored. Matplotlib cache was
redirected to repository-local scratch for subsequent wrapper runs.

Release is a provisional partial-coverage physical-routing POC, not a commercial
forecast. Remaining limitations: residual future mix, mixed-vintage LNG, unverified
dry-export/other future availability, hypothetical domestic boundary and monthly
versus daily feasibility. No hard target-window input or accounting blockers remain.
Restart: use the existing F2.4 operator command with fresh SIDs; preserve current
packages. Full-field prospective certification and commercial/walk-forward work
remain separate scopes requiring approval.

## F2.3 physical-input contracts — 13 October 2026

One worker on `feature/physical-input-contract-f23` in `.scratch/worktrees/f23`,
based on verified `a34bc72` directly above F2.2 `f4a742e`. No investigation merges.
[Contract decisions and evidence](evidence/inputs/physical_contract_f23/README.md):
all three mandatory contracts remain BLOCKED; no frozen weights, prospective supply
vector, active dual capacity interpretation or country forecast. Production's
0.020453 bcm gap is exactly Trym's returned 0.020461 minus 0.000008 Snøhvit
five-decimal precision difference. EA Oseberg owns Oseberg/Sør/Øst saleable volumes;
Tune is separate. Missing component coverage, signed Vilje, group ownership,
Heidrun's domestic split and the -0.015867 EA/NPD national revision bridge prevent
complete allocation certification. Selected Snøhvit covers all 38 target months at
October 1, but conversion does not establish prospective definition compatibility.
Kollsnes's documented upgrade does not verify simultaneous 143/156 constraints or
the daily SID's event aggregation; 13 central-case days remain incompatible.

The requested November 2026–December 2029 validation wrote a fresh 38-month
BLOCKED_INPUTS Excel/CSV/HTML/provenance package at
`outputs/routing_runs/20261013T105227167672Z_fc7923e9/`, with no LP. Diagnostic
conversion and capacity helpers are disconnected from operational preparation.
27 focused and 596 full regression checks passed; one existing pandas warning.
The 12-month default, 50-month endpoint, network/objective and historical guards
are unchanged. No protected actual SID observations were queried; a search-preview
exposure is recorded and excluded from numeric evidence, fitting and scoring.

Restart: obtain source-owner declarations and Core decisions listed in the evidence
table; bridge national revisions and certify independent monthly ownership before
calculating fresh frozen-2024 weights. Verify rating boundaries, effective dates
and net event revisions before considering the dual constraint. Do not activate
`forecast_end_month: '2029-12'` as a solved live forecast until every gate passes.

## F2 forecast horizon endpoint — 13 October 2026

Branch `feature/forecast-horizon-2030` is isolated in
`.scratch/worktrees/horizon-2030/`, based directly on `f4a742e` (implementation
`524ee59`); no investigation branch or concurrent commit/revert history was merged.
`forecast_end_month: null` preserves the 12-month default. An explicit quoted
`'2030-12'` takes precedence over `horizon_months`, with the resolved count recorded
in settings/provenance. October 2026 origins produce November 2026–December 2030,
50 complete monthly deliveries. Source/export gates check the entire resolved
window and record missing delivery months/dates. Multi-year chart labels remain
readable while every monthly bar/row is retained. Physical topology, optimiser,
population/allocation methodology, ratings and historical/evaluation guards are
unchanged. Operator configuration and troubleshooting are in README.md/INPUTS.md.

[Validation evidence](evidence/inputs/forecast_horizon_2030/validation.json)
records 12- and 50-month synthetic OPTIMAL packages, identical repeated 50-month
results, chronological monthly Excel/CSV/HTML/chart ranges, validation-only
packages and all package hashes. These are explicitly manufactured fixtures,
never EA forecasts or a remedy for unavailable sources.

Fresh full-window live validation is `BLOCKED_INPUTS`, with no LP or supply vector:
`outputs/routing_runs/20261013T084959806649Z_e6a9cd6f/` in the isolated worktree.
National production and all 16 fields returned 50/50 months; Kollsnes returned
1,522/1,522 daily points. Selected Snøhvit returned 38/50 months through December
2029; every January–December 2030 month is identified as missing, with the raw
response unchanged. Its unit/vintage approval is still absent. The complete 2024
identity/classification gate fails for 41 components; no frozen residual weights
exist. Kollsnes's 156 mcm/day derate on thirteen September 2027 days remains
incompatible with the 143 central envelope. The 156 sensitivity passing capacity
preparation does not approve a new central rating or unblock source preparation.

Verification: 51 focused checks passed. Full regression ran 584 tests: 571 passed;
13 initially failed/errored because the isolated worktree lacked existing offline
capacity fixtures and their exact archived byte serialization. After copying only
the hash-referenced fixtures from this repository, all 33 capacity fixture/contract
checks passed on rerun, verifying all 584 distinct tests. Model content and hash
guards were not changed; the copied fixtures are untracked and excluded from the
commit. One pre-existing pandas deprecation warning remains. No protected
January–September 2026 actuals were accessed or scored.

Restart: use the isolated horizon branch/worktree and README endpoint option.
Resolve the original F2.2 population, frozen-weight, Snøhvit and 143-maintenance
contracts before any live activation. Do not extrapolate 2030 LNG or infer future
maintenance certainty. Historical walk-forward and commercial optimisation remain
outside scope.

## F2.2 complete-population gate and provisional capacities — 12 October 2026

Branch `feature/reconciled-supply-f22` from verified `81114aa`; one worker.
Final implementation is isolated in `.scratch/worktrees/f22/`: a concurrent task
switched the shared checkout to `investigation/ea-legacy-forecast-horizon` during
validation. Misplaced task commit `26d74e5` was copied as `524ee59` onto this branch
directly from `81114aa`, then reverted locally on the investigation branch with
`abaa299`. Its tree matches the concurrent task's `5cdc04b` exactly; no history
was rewritten or investigation commit pushed. Tests/code/configuration are
identical between the verified implementation and this isolated copy. Raw audit
evidence and demonstration packages remain in the shared repository paths below;
their manifests preserve the actual execution Git identity and code snapshots.
[Full findings and 132-component ledger](evidence/inputs/reconciled_supply_f22/README.md)
replace the old 46-only forecast blocker. Fresh 2024 queries validated all original
62 fields, national and historical Snøhvit, plus 28 additional components.
The 69 candidates have 61 exact NPD identities: 28 complete, 27 confirmed empty,
six partial; eight unmatched project/discovery components. Provisional classification
holds 65 candidates as UNMAPPED (class 5), four group/calculation candidates as
unresolved class 2; no new entry node or outside-boundary assumption was embedded.
The partial annual discrepancy is 0.020453 bcm, principally explained by Trym's
returned November/December observations; missing months remain unavailable.
Brage/Tune/Trym attribution and signed Vilje accounting remain specific questions.
The complete historical gate did not pass; no annual weights or allocation logic
were activated, and no source-backed country forecast or routing sensitivity ran.

Core's revised annual-2024 allocation is recorded as conditional approval, not the
older 46-only five-node weights. Backend checks complete ownership, explicit
UNMAPPED, historical coverage and certification before any forecast activation.
The approved 19-envelope scenarios are supported: Kollsnes 143 central / 156
sensitivity, maintenance once, unknown availability elsewhere. The live derate
reaches 156 mcm/day on thirteen September 2027 days, incompatible with 143 without
an additional reference/maintenance decision; 156 prepares monthly capacities.
Prospective Snøhvit values exceed national production under their reported bcm
label; conversion/vintage remains rejected and the historical guard is unchanged.

Live validation packages (both BLOCKED_INPUTS, no LP, all flow cells unavailable):
`outputs/routing_runs/20261012T172125088253Z_0e170c57/` (143),
`outputs/routing_runs/20261012T172306930302Z_a9d6e057/` (156).
Nine-sheet Excel, HTML, 12-month CSVs, source records and 83/85 package hashes
verified. All 567 regression checks passed; one existing pandas deprecation warning.
The old registry migration test was corrected narrowly for B2's exact 46 reviewed
active sources; no registry row, physical topology or solver objective changed.

Restart: resolve the 41 incomplete component coverage/membership cases without
missing-to-zero substitutions, certify the Brage/Tune/Trym/Vilje boundaries and
complete identity, establish compatible prospective Snøhvit, then freeze complete
2024 weights and implement the approved allocation. Resolve 143-reference derate
compatibility before central-case execution. Holdout and historical replay remain
locked/unsupported as before. Existing raw/evidence/output work is preserved.

## Priority 0 production forecast trace — 12 October 2026

Branch `feature/production-forecast-lineage` from `993675a`; one worker.
[Read-only lineage findings](evidence/inputs/production_forecast_lineage/README.md)
correct the F2 sourcing interpretation: all 46 additional historical mapped fields
have workbook forward calculations, although standalone published forecast SIDs
were not identified. IB:IS is sixteen fields plus two overlapping aggregates.
NON-FLEXIBLE = TOTAL W SNOHVIT - Troll - Oseberg; both national/non-flex include
Snøhvit, while HH and HM/gassco_total already exclude it. Saved forward identities
and fresh aggregate SID identities reconcile over 51 months to rounding precision.
No accounting logic, weights, solver run or workbook changes were made.

Specific remaining issues: Hanz forward blanks January–June 2027; Visund Sor blank
October 2026 and resulting lag-seed concern; coherent expanded source exports or
fresh-source reproduction of existing formulas; Snøhvit export basis/vintage;
duplicate Rev deduction in upstream gassco formula; prospective capacity scope.
Restart: use the component/formula ledgers before implementing the existing
forecast aggregation, resolve those specific gaps, and use Core provisional
historical shares only for production genuinely lacking a usable forward forecast.
Do not combine workbook caches and fresh SID forecasts as operational inputs.

## F2 rolling current forecast workflow — 12 October 2026

Branch `feature/current-forecast-f2` from verified `ab07f65`; one worker.
`config/run.yaml` now defaults to a 12-month current forecast request. Null origin
captures UTC execution time; explicit current-month origins use same-origin
`@asof` metadata/points. Future deliveries are separated from all historical
read/fit/score/export guards; no generic unlock, actual-as-forecast or holdout access.

Live November 2026–October 2027 validation retrieved 19 sources with no coverage
failures: sixteen field forecasts and national monthly bcm, twelve native Snøhvit
months (conversion approval pending), and 365 signed daily Kollsnes plan points.
`outputs/routing_runs/20261012T145039391075Z_40ff1f36/` is BLOCKED_INPUTS:
no partial supply vector or LP. [Physical contract review](evidence/inputs/forecast_viability_f1/current_forecast_supply_contract.md)
finds no approved decomposition of national/non-flex into five affected nodes.
46 additional fields need a forecast or explicit node-feed contract, Snøhvit's
forecast basis/vintage needs confirmation, and future capacities/maintenance
scope need approval. Individual discovery/certification was not repeated.

Synthetic 12-month CLI workflow is OPTIMAL at
`outputs/routing_runs/20261012T145249435605Z_686418fd/`, explicitly manufactured,
not an EA forecast. Supply/LNG/residual balances, feasibility/capacity residuals,
nine-sheet Excel, CSV/charts/HTML, raw provenance and package hashes checked.
Validation-only stays unsolved and non-overwriting packages remain intact.
Historical reconstruction settings and functionality are retained; canonical
physical mappings, source registry, model capacities and evaluation policy unchanged.

Validation: 329 regression checks passed, then 28 focused checks after adding
malformed-origin/scenario cases; current-mode failure propagation covers
coverage, units, actual lifecycle, origins, negative/nonfinite values and missing
archive responses, plus locked/out-of-window exports. Restart: inspect Git state,
review source-contract alternatives with physical design, then implement only the
approved complete-source/units/capacity preparation. Current real-data forecasting
is not operational; no historical replay or price logic was introduced.

## B2 closure and F1 — 12 October 2026

Branch `feature/b2-closure-forecast-viability-f1` from verified `9390691`.
Hanz production began 20 April 2024 (Directorate and operator evidence).
Only missing January/February become explicit structural zeros; fresh March is
0 bcm. Raw observations are unchanged, rules are snapshotted, contradictions
fail. Full source-backed 2024 is OPTIMAL for all twelve months:
`outputs/routing_runs/20261012T141200162824Z_fa3c46c3/`.
Exports 117.0831345 bcm; max mass residual 1.776e-15 bcm; capacity violation zero.
Excel worksheets, charts, supply identities, Hanz provenance and hashes checked.

[F1 readiness and matrices](evidence/inputs/forecast_viability_f1/README.md)
record 51/51 prospective months through 2030 for sixteen EA fields and national
total; all 46 historical NPD leaves still lack identified forecast counterparts.
Selected Snøhvit ends December 2029; Kollsnes returns 1553 daily plan points,
but future capacities remain scenario assumptions. Prospective forecast inspection
is a separate bounded metadata-gated path; normal historical/evaluation gates
and the January–September 2026 holdout were not changed or accessed.

National and original five-group EA forecast archives recovered at all twelve
2024 month-end cutoffs. Original issuance dates remain unknown; import-job dates
are recorded separately. At the first origin all sixteen selected EA fields pass;
selected Snøhvit and maintenance return no origin values throughout 2024. Legacy
Snøhvit returns all twelve deliveries at the first origin but requires rate/cohort
review before selection. Full 2023 training at that origin crosses the forecast
boundary. No complete routing-origin bundle or forecast score exists. Revised
actuals for three EA allocation groups are compatible; DK/PL scoring withheld.
Three EEX curves return no first-origin values; other forward-price vintages remain
unverified and are not required by the price-free model.

Checks: 311 regression tests passed, then 24 focused checks after Hanz
reactivation coverage was added. Existing untracked evidence/outputs preserved.
Restart: verify Git state; resolve identified field/LNG/maintenance sources and
approve forecast capacity scenarios, original-issuance versus service-cutoff
comparison protocol, and origin-safe training rule before implementing either
forecast mode. No aggregate splitting, backdating or frozen-input exception.

Earlier sections below retain the pre-closure state.

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
The optional full plan is now `archive/20261009-01_repository-cleanup/REPOSITORY_CLEANUP_PLAN.txt`. Historical STATUS,
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
