# Norwegian routing price response feasibility

The seven-country 2025 price-response comparison cannot yet run reliably. Full-year input preparation fails because the retained Snohvit conversion is validated only through July 2025. A Polish price reference is unselected; Danish and Belgian alternatives need product and aggregation decisions. The experiment therefore stops at feasibility, without a price objective, fitted response strength or validation allocation results.

Development ends December 2024; validation is January-December 2025. January-September 2026 remains locked and unscored. This audit loaded retained price observations only through December 2025 using Parquet predicates. It made no service requests, changed no physical assumptions or seasonal preferences, and preserved the current assessments and Git index.

## Baseline verification

The existing PuLP/HiGHS model replayed all twelve 2024 months using unchanged production, capacities, signed maintenance and fixed 2023 shares. Every destination allocation and unrouted volume matches the current reconstruction within 1e-9 bcm. Exports remain 117.0831345 bcm; unrouted supply remains 2.7412485 bcm. Maximum mass-balance residual is 1.776e-15 bcm; maximum capacity violation is zero.

The requested 2025 window was tested through an in-memory configuration copy. `prepare_inputs` rejected it with `Snohvit actual conversion validated only through July 2025 for this POC`; no 2025 month was solved. The existing three stages remain maximum exports, minimum L1 deviation from historical shares, then minimum worst fractional baseline shortfall while preserving both preceding optima.

Physical uncertainty remains: Kollsnes uses 143 mcm/d with a provisional processing-maintenance adjustment, despite unresolved dry-export versus rich-processing definitions and dated upgrades. Karsto uses 95 mcm/d rich processing against net field gas. Direct UK route nameplates and Danish/Polish reference conditions remain unresolved. None was adjusted to improve fit.

## Retained prices and coverage

Counts below are finite published observations in 2025. Having at least one quote in every month does not establish complete delivery-day coverage or a comparable monthly price product.

| Market | Retained source | Original unit | Months with quotes | Quotes | Minimum quotes in a month | Use limitation |
|---|---|---|---:|---:|---:|---|
| UK | Selected Reuters NBP | pence/therm | 12 | 255 | 20 | Dated FX and therm conversion; delivery/calendar definition |
| Netherlands | Selected Reuters TTF | EUR/MWh | 12 | 253 | 20 | Delivery/calendar definition |
| Germany | Selected Reuters THE | EUR/MWh | 12 | 258 | 20 | Earlier NCG-era quotes are not homogeneous THE history |
| France | Selected Reuters PEG | EUR/MWh | 12 | 204 | 11 | Sparse quote coverage and aggregation |
| Belgium | Selected Reuters ZTP | Declared EUR/MWh | Unverified | Unverified | Unverified | No retained cache for this selected identifier |
| Belgium | Alternative EEX ZTP last trade | EUR/MWh | 12 | 299 | 23 | Last trade is not the selected Reuters quote or a daily index |
| Denmark | Alternative EEX ETF last trade | EUR/MWh | 12 | 295 | 23 | ETF proxy is not selected; timestamps and product need validation |
| Poland | No selected reference | Unresolved | Unverified | Unverified | Unverified | Neither TTF nor another proxy is assumed |

Same-date ECB EUR/GBP observations are retained in all 12 validation months (255 observations). Their direction is inferred from the retained identifier and prior diagnostic, not independently verified provider-unit metadata. The existing NBP diagnostic uses `pence/therm / 100 / 0.0293071 / GBP-per-EUR`. This audit reproduces that descriptive calculation without approving it as a model transformation or filling FX gaps.

The coverage CSV also records raw-series availability for 2021-2024, exact identifiers, source files, units and alternative EGIX futures indices. THE-TTF descriptive training spreads exclude pre-October 2021 NCG-era observations. EGIX is futures-based; its permitted history contains a zero observation whose meaning needs review. Monthly EA forecasts and contract delivery grids are not substitutes for realised spot-price histories; futures curves require both valuation and delivery dates.

## Descriptive validation spreads

These are averages of twelve monthly means of matched published quotes, in EUR/MWh. They are descriptive revised-input summaries, not price features available before the delivery month or evidence that allocation responds to prices.

| Spread | Average monthly spread | Matched quote dates | Minimum matched dates in a month |
|---|---:|---:|---:|
| NBP minus TTF | -0.698829 | 251 | 19 |
| THE minus TTF | 1.051511 | 252 | 20 |
| PEG minus TTF | -0.819706 | 201 | 11 |

Only June 2024 TTF snapshots at July 2024 and July 2025 cutoffs are retained among the audited price archive checks, with 20 observations each. They demonstrate limited archive retrieval, not full training/validation price vintages or independently verified publication cutoffs. Complete production, maintenance and effective-capacity origin bundles also remain absent. A future comparison using revised production and realised prices must be labelled a historical reconstruction. Missing origin vintages alone do not preclude that reconstruction once its data and definitions are adequate; they prevent a genuine-forecast claim.

## Conditions for the next experiment

1. Resolve the August-December 2025 Snohvit conversion and establish identical complete production, capacity and observation months for both candidates. Keep the physical assumptions fixed and report the capacity limitations.
2. Select and validate Belgian, Danish and Polish price products or explicitly approve empirical proxies. Define common delivery-date treatment, quote calendars, monthly aggregation, FX and unit conversions. Avoid filling missing prices or replacing last trades with indices silently.
3. Define a single response-strength parameter and its units before fitting on development data only. Preserve the existing static shares; freeze the coefficient, feature scaling and model identity before comparing 2025 outcomes. Do not tune them to the descriptive validation spreads above.
4. An empirical spread preference can be tested without claiming revenue or netbacks. A revenue objective additionally requires evidenced energy-per-volume conversion and route costs. `bcm_to_mwh` and commercial flexibility remain unresolved; no transport costs or contractual flexibility were invented.
5. Keep stage 1 maximum feasible exports fixed. For a future combined stage-2 objective, stage 3 must preserve that combined optimum; fixing the old L1 optimum separately would confine price effects to old ties. At zero strength, require the exact unchanged three-stage baseline. Keep the date gates and locked holdout intact when adding an authorised price-experiment mode.

Price-on seven-country/five-group WAPE, MAE, signed bias, matched allocation coverage, monthly allocation differences and responding routes are unavailable because no price-on validation run was made. The price-free replay and 131 existing targeted solver, capacity, scoring and leakage tests passed. No new price-switch regression is claimed: a price-response implementation does not exist.

Exact price identifiers and bounded coverage are in [price_response_coverage.csv](price_response_coverage.csv); run, input, parameter, code and preservation identities are in [price_response_feasibility_manifest.json](price_response_feasibility_manifest.json). The existing [reconstruction](../../outputs/reconstruction/report.html) remains unchanged. Disposable quote counts, descriptive monthly spreads and replay tables are under `.scratch/runs/20261009-11_price-feasibility/`.
