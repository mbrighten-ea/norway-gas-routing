# EA legacy Norwegian forecast horizon

Verified 12 October 2026. Fresh EA/Shooju forecast responses were captured at
`2026-10-12T17:12:28Z`. This investigation changed no model, configuration,
forecast logic, workbook or existing output, and read no January–September 2026
actual observations.

**The published legacy destination forecasts genuinely extend to December 2030.**
They contain 51 consecutive delivery months from October 2026, or 50 complete
future delivery months from November 2026. The observed design is a **fixed
calendar endpoint**, currently December 2030, providing roughly 4.2 years from
this origin. It is not a rolling 12- or 36-month forecast. Its present length is
within the 48–60-month range, but this does not establish a rolling 60-month
extension policy or guarantee that future vintages retain that length.

## Verified SID coverage

SID suffixes below follow `teams\natural_gas\EUR\`. Exact full identifiers,
per-series metadata boundaries, timestamps and coverage are in
[sid_coverage.csv](sid_coverage.csv). “Months” includes October 2026; subtract
one for complete future delivery months. First/last dates describe the verified
current-origin segment, not the first historical issuance of the series.

| SID suffix | First verified month | Last verified month | Months | Gaps within segment | Dec 2030 |
|---|---|---|---:|---|---|
| `NO\gassco_total` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO\gassco_UK` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO\gassco_FR_and_BE` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO\gassco_NL_and_DE` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO\gassco_PL` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO\gassco_DK` | 2026-10 | 2030-12 | 51 | None | Yes, zero |
| `NO_production` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Troll_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Oseberg_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Aasta_Hansteen_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Asgard_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Gina_Krog_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Gullfaks_Sor_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Heidrun_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Kristin_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Kvitebjorn_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Martin_Linge_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Norne_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Ormen_Lange_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Skarv_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Sleipner_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Visund_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Dvalin_field` | 2026-10 | 2030-12 | 51 | None | Yes |
| `NO_production_Snohvit_field` | 2026-10 | 2029-12 | 39 | None; all 12 months of 2030 absent | No |
| `NO_SNØHVIT_gas_production` (older alternative) | 2026-10 | 2026-12 | 3 | None; 2027 onwards absent | No |
| `daily_NO\NO_maintenance_Kollsnes` | 2026-10 | 2030-12 | 51 | None; 1,553 daily points | Yes |

All monthly observations are finite, with no missing or duplicate delivery dates.
Every series was also queried for **January 2031–December 2040**, with no points
returned. December 2030 is an observed endpoint, not a limit inferred solely from
the model's existing 2030 guard. Denmark has 51 published zero forecasts, not
missing cells. UK + FR/BE + NL/DE + PL reconciles to the published total in every
month, within `3.6e-15` bcm. The workbook's PL export is labelled Baltic Pipe.
Separate France, Belgium, Netherlands and Germany upload columns are labelled
actuals and have blank December 2030 caches: the long forecast is for the
combined destination groups, not four independently forecast country splits.

## Workbook formulas, saved values and publication

| Worksheet | Last dated delivery | What it establishes |
|---|---|---|
| `Forecasts` | December 2030, row 184 | UK AT, FR/BE AY, NL/DE BD, Baltic Pipe M, Denmark H and total F have formulas and finite saved values for all 51 months. Denmark's upload converts H from mcm/day to bcm. |
| `Flows` | December 2029, row 135 | A shorter display linked to `Forecasts`, not the publishing endpoint. |
| `Gassco_raw` | December 2030, row 197 | Imported total forecast in B/C; B2 names `gassco_total`. Future terminal actual columns are blank at the endpoint. |
| `SJ upload` | December 2030, row 204 | D/G/K/L/O feed the destination `SJWrite` calls over rows 25:204. M holds the total, but M2 has no writer. |

The total is written upstream by the production workbook's HM export. Endpoint
cells HM515 and IE515 calculate `gassco_total` and national production. Snøhvit
GD515 also has a forward formula and a saved value for December 2030, despite
the selected Snøhvit SID lacking that month. This is a worksheet calculation,
not an available standalone published Snøhvit observation.

Formula structure and saved values were inspected without recalculation or
executing Shooju Excel functions. All endpoint formulas inspected have finite
caches, but this does not certify a fresh Excel calculation. Saved and published
UK values differ in all 51 months, by up to 0.0509182 bcm. Other groups also differ.
Fresh SID observations, rather than workbook caches, establish publication.
The flows file required the existing in-memory ZIP recovery; both source
workbooks retained their original hashes.

## Vintage and update limits

The destination and national/field series generally report a forecast boundary
of October 2026. `gassco_total` instead reports May 2023, selected Snøhvit October
2025, and the older Snøhvit alternative September 2022. These labels do not prove
that intervening historical deliveries are still genuine forecasts. No earlier
points were retrieved or classified as forecast for this investigation.

The five non-DK flow series expose snapshot job `29997892`, created
28 September 2026 at 14:22:13.760 UTC. National production and all sixteen fields
expose job `30104685`, created 5 October 2026 at 14:01:13.181 UTC. These are import
job timestamps, **not original forecast publication dates**. DK, Snøhvit and
Kollsnes provide no equivalent snapshot job field. A common `@asof` query time
does not establish a common underlying issuance vintage.

Explicit `meta.updated_at` queries are retained per SID in
[update_metadata.json](update_metadata.json). Flow, national and field updates
report 12 October 2026; selected Snøhvit reports 16 October 2025 at
14:15:01.591 UTC, and the older alternative 4 November 2022 at 14:19:19.723 UTC.
Kollsnes reports 12 October 2026 at 17:03:19.280 UTC. Several system update times
postdate the captured query origin, so these system fields cannot certify
archived release availability. Original publication/issuance dates remain
unprovided. Several `date_to_max` fields advertise December 2028 although actual
forecast responses extend through December 2030; those metadata fields are stale.

## Implications for the routing model

1. **Genuine horizon:** monthly grouped-destination forecasts to a fixed December
   2030 endpoint, with 51 current-origin months and 50 full future months. This
   verifies a 3–5-year horizon for the current vintage.
2. **Should ours match?** Support the same endpoint as a long-term planning view
   once its input contracts are complete. Horizon parity alone does not establish
   comparable accuracy or operational readiness.
3. **What prevents it?** National production and the sixteen published fields
   have sufficient coverage. Selected Snøhvit lacks every month of 2030 and still
   has unresolved rate-versus-bcm semantics and vintage compatibility. The older
   SID is shorter and cannot repair this. The production workbook's longer GD
   calculation needs a maintained fresh export or approved source-based
   reproduction, not cached-cell substitution. The remaining field population
   also needs usable fresh exports/decomposition, with the known Hanz and Visund
   Sor forward gaps resolved. National/non-flex aggregates overlap named fields
   and include Snøhvit; blindly adding them would double-count production.
   Kollsnes's complete daily grid contains 55 nonzero derates in 2027 and zero
   derates throughout 2028–2030. Those zeros do not establish known absence of
   outages. Wider network availability, loss overlap and long-term maintenance
   assumptions therefore remain limiting contracts. Legacy terminal capacity
   formulas explicitly switch after 12 months to historical same-month averages.
4. **Design:** use a configurable monthly horizon, preserve the existing
   12-month default as the short-term view, and reject uncovered requested months
   or require separately approved scenario assumptions. The present code already
   accepts `horizon_months` from 1–60 while capping delivery at December 2030.
   At this origin that permits up to 50 complete future months. No parameter or
   guard changes were implemented.

The additional-field, accounting and export limitations are documented in the
existing [production lineage assessment](../../inputs/production_forecast_lineage/README.md).
This investigation confirms horizons; it does not approve new source assumptions.

## Evidence and verification

[Source evidence](source_evidence.json) records exact SID queries, origin-matched
metadata, import jobs and the beyond-endpoint checks.
[Forecast observations](forecast_observations.csv) retain only October 2026 and
later responses. [Workbook evidence](workbook_evidence.json) retains structural
formulas and prospective saved values.
[Coverage checks](coverage_checks.json) records formula coverage, reconciliation,
cache differences, maintenance detail and production endpoint cells.
[Verification](verification.json) records evidence hashes, unchanged source
workbook hashes and preservation of 1,658 pre-existing files, including existing
modified files and outputs. No solver, fitting or scoring was run.

Access used the approved workspace Python interpreter, existing EA helper and
`get_prospective_forecast` for October 2026–December 2030. The separate endpoint
probe used the same helper's read API, exact `@asof` query, metadata forecast gate
and strictly future 2031–2040 bounds. No historical/evaluation safeguard was
modified or bypassed to read actuals.
