# Snøhvit input audit and partial 2025 baseline

Full-year 2025 remains blocked. August–December observations are present, but the selected Snøhvit import is not validated as actual net production for those months. The July guard is retained. No model, selected source, capacity, routing preference or evaluation setting changed.

## Why July is the cutoff

The retained [Directorate field page](https://factpages.sodir.no/en/field/PageView/All/2053062), saved in `data/raw/series_audit/snohvit_sodir_primary_20261008.html`, contains all twelve 2025 monthly net-saleable and gross-well gas entries. This audit independently reparsed only 2025 rows, filtering the year before converting production cells. No new retrieval was needed. Public actuals are therefore available; missing public observations are not the blocker.

The selected `teams\natural_gas\EUR\NO_production_Snohvit_field` import has a misleading provider `bcm` label. Historical comparisons support a monthly-average **mcm/d** interpretation: multiply by calendar days and divide by 1,000. The official comparison column is net gas in billion standard cubic metres (`bill Sm3`), numerically bcm. This is a rate-to-volume conversion, not an LNG-density or calorific-value conversion. Gas reference conditions beyond the retained standard-volume labels have not been independently reconciled; no additional adjustment is inferred.

January–July 2025 converted values match official net saleable gas within 0.0000051 bcm, the existing comparison tolerance for rounding. They do not match gross well production. Subsequent months fail that actual-data check:

| Month | Selected import converted, bcm | Official net saleable, bcm | Difference, bcm | Status |
|---|---:|---:|---:|---|
| August | 0.4229156 | 0.373753 | +0.0491626 | Historical-labelled mismatch |
| September | 0.5385501 | 0.549747 | −0.0111969 | Historical-labelled mismatch |
| October | 0.5479056 | 0.545442 | +0.0024636 | Source forecast |
| November | 0.5383848 | 0.538306 | +0.0000788 | Source forecast |
| December | 0.5580695 | 0.568669 | −0.0105995 | Source forecast |

The selected source metadata declares `forecast_start_date=2025-10-01`. Retained revision evidence shows its latest import is the October 16, 2025 Excel job 27343398; the current field series equals that import. The August/September discrepancies already existed then. The exact generating workbook and its cell formulas are unavailable. No earlier Directorate publication snapshot is retained to establish whether those discrepancies reflect estimates, revisions or another accounting adjustment. Extending a date check would admit these discrepancies and the three forecast months without resolving them.

## Exclusion accounting and missing evidence

The unchanged accounting is `pipeline supply proxy = Norway total production − Snøhvit net production`; mapped fields are then reconciled to this proxy through `UNMAPPED`. The total is not added to its component fields. Snøhvit is subtracted once, rather than subtracted again from an already LNG-excluded aggregate. The older `NO_production_excl_Snohvit` and `NO_SNØHVIT_gas_production` imports are stale November 2022 vintages and cannot replace the current inputs.

May–July 2025 official net entries are negative and match the signed selected series within rounding. They remain signed in the exclusion identity; clipping them to zero would change established accounting. Net field production is an accounting boundary, not proof of physical negative LNG output or measured LNG cargo exports. Gross well production is a different boundary and is not a substitute.

The aggregate Norway-total import was revised October 7, 2026, whereas the Snøhvit field import remains October 2025. The missing evidence is a corrected actual August–December field import with verified units and formulas, reconciled to the selected aggregate production boundary, or a documented replacement source contract proving how official net saleable volumes belong in that aggregate. Public figures alone do not validate the currently selected values or explain their differences. Substituting the official series would be a source update requiring that reconciliation, rather than a justified extension of the existing guard. No substitution, interpolation, zero fill or bypass was made. Exact revision evidence remains in [core_production_source_trace.json](core_production_source_trace.json).

## Runs and verification

The unchanged price-free PuLP/HiGHS three-stage model solved **January–July 2025 only**, using the fixed 2023 routing preferences. All requested production and comparison months were present; retained capacity/maintenance preparation completed without filling missing production. Exports total 66.982 bcm and unrouted supply 1.662089 bcm. Maximum mass-balance residual is 1.7764e−15 bcm; maximum model capacity violation is zero. This is a partial revised-input reconstruction, not full-year validation or a genuine historical forecast.

The twelve-month 2024 replay matches every saved destination allocation and unrouted volume within 1e−9 bcm. Exports remain 117.0831345 bcm and unrouted supply 2.7412485 bcm. Mass-balance and capacity maxima are respectively 1.7764e−15 bcm and zero. The replay also asserts the single Snøhvit subtraction and source reconciliation identity. The full-year 2025 preparation test confirms the existing guard still rejects the window.

187 targeted solver, scoring, capacity, configuration and chronology tests passed without warnings. Read-only checks matched hashes for 574 existing code, configuration, raw-data, assessment and Git-index files before retention; only the output-index documentation is subsequently updated to link this milestone. No correction was justified, so no production-code change or new synthetic unit-test implementation was needed. The experiment adds explicit evidence assertions for the cutoff, signed net entries, single subtraction and 2024 replay.

Development remains through December 2024, validation remains 2025, and the 2026 holdout remains locked and unscored. This audit loaded no 2026 production or allocation values. No parameters were fitted. Existing Kollsnes and other capacity-definition uncertainties persist; monthly feasibility does not establish daily operational feasibility. Source vintage/publication evidence does not establish a complete forecast-origin bundle.

## Retained evidence

- [Monthly source comparison](snohvit_2025_comparison.csv).
- [Run manifest](snohvit_2025_baseline_manifest.json): exact source paths/hashes, input coverage, policy, preservation checks and run identity.
- [Partial 2025 allocations](../../archive/20261009-12_snohvit-baseline/baseline_2025-partial.csv), [scores](../../archive/20261009-12_snohvit-baseline/scores_2025-partial.csv), [supply reconciliation](../../archive/20261009-12_snohvit-baseline/reconciliation_2025-partial.csv) and [capacity limits](../../archive/20261009-12_snohvit-baseline/capacities_2025-partial.csv). The diagnostic score file's inherited `*_annual_bcm` column names contain seven-month totals only; they are not annualised.
- [2024 replay](../../archive/20261009-12_snohvit-baseline/baseline_2024.csv) and [read-only audit script](../../archive/20261009-12_snohvit-baseline/audit.py).

Temporary test files remain in `.scratch/runs/20261009-12_snohvit-baseline/`. The current successful reconstruction and benchmark assessments are preserved.
