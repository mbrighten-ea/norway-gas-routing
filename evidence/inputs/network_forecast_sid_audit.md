# SID discovery and forecast verification

Audit: `20261009-16_network-source-audit`, 9 October 2026. The authoritative registry remains `config/data_series.csv`. Registration does not activate a model input. [SID evidence matrix](network_forecast_sid_discovery.csv), [unverified workbook references](network_forecast_unverified_references.csv), [remaining discovery-only field identifiers](network_forecast_unverified_discovery.csv), and [bounded probe provenance](../../archive/20261009-16_network-source-audit/manifest.json) support this report.

## Search scope and access

The dashboard was located from the workspace directory inventory at `../gas_python_dash`; its code, source declarations and `context/shooju_queries.md` were inspected read-only. No dashboard application or cache loader was run, and no cached destination outcomes were read. Relevant declarations include `app/backend/services/norway_cache.py:34` and `_sodir.py:44`. The latter identifies the actual field namespace and lowercase metadata aspect `gas-saleable`; older Excel/legacy queries using `Gas - saleable` for **field metadata** can return no series. That does not invalidate the separate monthly-total SID, whose exact returned spelling contains `Gas - saleable`.

`Norwegian production model.xlsx` has 27 sheets. Labels, formulas, defined names and source-identification cells were inspected; `Production mcm_d!GK23/EQ23/ER23/CL23/CI23/EU23` identify the six residual fields. `NPD_raw!A1` references the official monthly total. The 29-sheet maintenance workbook was inspected for source declarations in its first 100 rows per sheet, defined names and package connections. The flows workbook is not a readable OOXML ZIP container; no password or alternative file was assumed. No exposed connection/query-table/external-link parts or `DataMashup` marker were found in the two readable packages; their custom XML was checked for identifier references. This does not prove that every external dependency or add-in state is retained. Neither workbook was recalculated or written.

Retained production metadata and Parquet were checked with predicates **before** reading values. Live queries returned 20 EA `NO_production*` SIDs and 139 Directorate field identifiers. Scoped and global field-name queries found no individual EA SID for the six residual fields. This is a search result, not proof that an identifier cannot exist under a different namespace. Forecast values were restricted to October 2026–December 2030 after metadata confirmed a forecast handover. Historical checks used 2025 only. Normal model date guards were not changed.

## What is verified

Six priority fields have **51/51 finite cached individual forecast months through December 2030** in the EA production workbook. Values and rate-to-volume units were checked; existing formulas and provider shutdown zeros were retained, never created or fitted. Sixteen selected field forecasts, including Åsgard, Norne and Oseberg, exactly match live EA monthly exports after `mcm/day × calendar days / 1000` for all 51 months. The bounded numeric evidence is [candidate worksheet forecasts](../../archive/20261009-16_network-source-audit/candidate_workbook_forecasts.csv), with [service reconciliation](../../archive/20261009-16_network-source-audit/forecast_workbook_service_reconciliation.csv).

The national monthly EA total equals worksheet `HH + GD × days/1000` exactly: `HH` is the non-LNG worksheet total; `GD` is Snøhvit. The non-flexible EA aggregate equals total minus Troll minus Oseberg within 8.9e-16 bcm. Its components span different routes and include LNG, so it cannot all enter Kårstø. The six fields are separate worksheet leaves, not included in Åsgard AF, Norne BF or Oseberg Q; the national/non-flexible total already includes them. Any mapping transfers existing residual into a physical feed and reduces residual by the same volume; it does not add production.

Eighteen already-registered EA production SIDs have complete 51-month forecasts: 16 selected named fields plus Norway total and non-flexible total. Generic descriptions still say UK supply; client descriptions, units, workbook linkage and numeric checks support production identity, but existing REVIEW records were deliberately not upgraded. The selected Snøhvit SID has only 39 checked months, ending December 2029, despite a metadata unit label of bcm that conflicts with its established rate interpretation. The updated **workbook** Snøhvit forecast extends through 2030. The stale LNG-excluded SID stops December 2026. Neither is substituted into the model. No complete immutable publication-vintage archive was established.

Dashboard `NO\production_total` and `NO\gassco_total` returned monthly bcm metadata and 12 finite 2025 values. The latter has a complete forecast through 2030; the former has no verified forecast handover in its metadata. The dashboard's generic daily-MCM/day interface comments conflict with these monthly contracts. Workbook `HH2`/`HM2` identify these distinct totals. They are already registered and are not interchangeable with the model's LNG-inclusive national production. Workbook `HN` also deducts Rev twice; this is an existing documented legacy accounting issue, not a reason to subtract Snøhvit twice in the optimiser.

## Registry additions

Seven new entries were appended. Every row is `CONFIRMED` **for identifier, historical units and bounded historical source**, `reference_only`, `optional`, `actual`, `forecast_required=false`. Confirmation does not validate a production forecast or approve a physical mapping. Old records and their original byte prefix remain unchanged.

| Key | Exact returned SID | Source and verification |
|---|---|---|
| `halten_ost_net_actual` | `NPD\monthly_by_field\marketed_production\halten_ost\gas-saleable` | Directorate; bcm/bill Sm³, monthly; 11 finite 2025 observations. January missing, not filled. |
| `trym_net_actual` | `NPD\monthly_by_field\marketed_production\trym\gas-saleable` | Directorate; same units; 12 finite 2025 observations. |
| `tune_net_actual` | `NPD\monthly_by_field\marketed_production\tune\gas-saleable` | Directorate; same units; 12 finite 2025 observations. |
| `brage_net_actual` | `NPD\monthly_by_field\marketed_production\brage\gas-saleable` | Directorate; same units; 12 finite 2025 observations. |
| `balder_net_actual` | `NPD\monthly_by_field\marketed_production\balder\gas-saleable` | Directorate; same units; 12 finite 2025 observations. |
| `urd_net_actual` | `NPD\monthly_by_field\marketed_production\urd\gas-saleable` | Directorate; same units; 12 finite 2025 observations. |
| `norway_net_actual` | `NPD\monthly_total\Gas - saleable` | Directorate; bcm/bill Sm³, monthly; 12 finite 2025 observations, 121.839 bcm. |

The six signed annual field quantities reproduce the saved residual contributions. The official national total is **0.0672 bcm above** retained EA 2025 production (121.7718 bcm): a revision/source difference, not extra supply to add. Exact returned casing was retained, and duplicate identifiers/alternate spellings were checked before appending. `load_config` validates the proposed file before writing; explicit source keys select optimiser inputs, so optional references are safe. No active source, status, mapping, capacity or evaluation setting changed.

## Unresolved references and production dependencies

`gassco\past_events` and `gassco\unavailability_fields_processing_plants` remain unverified references here. A table-like event feed may not fit the registry's time-series unit/frequency contract. Private Shooju maintenance observations are not public technical-capacity evidence. Query modifiers such as `@asof`, `@lag` and resampling directives are retrieval expressions, not new SIDs; wildcard field namespaces are discovery queries. Dead dashboard namespaces and worksheet labels were not registered as verified sources.

No individual EA forecast SID was identified for Halten Øst, Trym, Tune, Brage, Balder or Urd. **Their forecasts are not missing from the workbook.** Automated refreshed production use needs a maintained workbook ingestion or provider-confirmed identifiers, vintage capture and boundary checks. Frozen verified workbook forecasts can support the separately proposed Halten Øst/Urd reallocation; other field mappings retain the physical/accounting dependencies in the readiness matrix. No national aggregate split or new forecast was invented.

The broad Directorate query also returned 133 non-priority field identifiers whose individual metadata/values were not validated. They are retained separately as discovery-only candidates with explicit unknown units, coverage and physical-entry treatment; they were not registered or treated as forecasts. This avoids claiming that a returned identifier is already a usable input.


## Exact six-field lineage follow-up, 20261009-19

[The header/formula check](workbook_sid_lineage.md) exports every requested row
1–23, comments and October 2026/December 2030 formula/cache examples. No individual
EA forecast SID is present for the six fields in this workbook. Their rates are
workbook-generated decline/depletion profiles or literal assumptions; this does
not establish a maintained individual provider feed. Global Shooju absence remains
unproven. No registry/source/model change was made.
