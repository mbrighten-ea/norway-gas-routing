# B1 routing-source audit and integration gate

## B2 closure — 12 October 2026

The default fresh-SID 2024 reconstruction now solves all twelve months.
Hanz January/February are explicitly justified pre-production zeros (production
start 20 April 2024); its returned March zero remains unchanged. The
[narrow evidence/rule](hanz_preproduction.json) is copied into each operational
package and every applied zero is recorded separately from raw observations.
All other missing months/fields still fail. The ledger's current Hanz row links
the successful fresh run and response hash. Forecast viability is assessed
[separately](../forecast_viability_f1/README.md); NPD actuals are not forecasts.

The activation/B1 sections below describe the preceding audit states.

## B2 activation update — 12 October 2026

The ledger and `verified_sources.json` now include direct-response checks of all
46 known candidates; the original B1 audit below and its JSON remain historical
evidence. 45 fields passed complete January–December 2024 coverage. Hanz passed
identity/measurement checks and March–December coverage, but its full-year query
omits January and February: these remain an explicit operational blocker.

NPD actual monthly `bcm` / `bill Sm3` is marketed saleable natural gas, used
directly in bcm/month. Existing worksheet rate conversion and adapter reversal
cancel. Field labels, country, measure, lifecycle, provider, units, dates and
nonnegative observations were checked; old workbook equality is not required.
Sindre returns the old metadata label `NPD\monthly_by_field\SINDRE\Gas - saleable`
alongside the matching current `series_id_name`, field and measurement metadata.
The validator accepts that exact legacy label structure only when all identities
agree; the queried and registered SID remains the known marketed-production SID.
NPD revisions need not share EA workbook import-job identifiers. Existing EA
cohort checks remain, and every operational run queries all inputs fresh.

`scripts/audit/activate_historical_fields.py --apply` validates known candidates
within 2024 and appends passing registry records, after validating the full model
configuration and checking for concurrent changes. `--reference FM` rechecks
Sindre; `--reference GI --start 2024-03 --end 2024-12` records Hanz's partial
coverage without asserting absent months are zero. Responses and before/candidate
snapshots are retained locally in `data/raw/npd_activation/`; per-row paths,
retrieval dates and hashes are in the ledger/contracts. These are evidence, never
a run-input cache. Activation does not authorise new retrieval scopes.

## Original B1 audit

Audit date: 12 October 2026; baseline `0de2ba4`. No source observations were
retrieved, no workbook observations were used, and no holdout values were read.
The audit inspected headers plus January/December 2024 formulas only. Original
workbook, configuration, discovery evidence and script hashes are in
`routing_source_audit.json`. `routing_source_mapping.csv` has one row per reference,
including exact formulas, units, signs, transformation, dependency and candidate.

| Source node | Essential worksheet columns | Count |
|---|---|---:|
| KOLLSNES_FEED | CV FRAM; EW VALEMON | 2 |
| KARSTO_FEED | ES TYRIHANS; FO JOHAN SVERDRUP; DR MIKKEL; CF ALVE; DW NJORD; FT ÆRFUGL NORD; DQ MARULK; CO DRAUGEN; FE VISUND SØR; FN MARIA; DT MORVIN; EP TORDIS; FX FENJA; DK HYME; FW BAUGE; FM SINDRE | 16 |
| SLEIPNER | DF GUDRUN; DG GUNGNE; FQ UTGARD; ED SIGYN | 4 |
| UK_DIRECT | EZ VEGA; DB GJØA; FU DUVA; CG ALVHEIM; EH STATFJORD; FL IVAR AASEN; CQ EDVARD GRIEG; EJ STATFJORD ØST; EM SOLVEIG; FV NOVA; GI HANZ; EI STATFJORD NORD; CK BØYLA; FF VOLUND; FS SKOGUL; EB REV; DL ISLAY | 17 |
| EKOFISK_FEED | CR EKOFISK; CS ELDFISK; CT EMBLA; EO TOR; FY TOMMELITEN A; EX VALHALL; DI HOD | 7 |

**All 46 are essential; none is redundant or solely optional reporting.** Each
2024 formula selects a distinct named leaf from NPD_raw, then converts declared
monthly bcm into an average rate. The retained reader reverses that conversion
and adds it to an existing source node. Each leaf changes both LP source balance
and the national-minus-LNG-minus-mapped residual. Removing it, assigning zero or
moving its volume into another source is a methodology change, not integration.
The worksheet's blank-to-zero formula is not adopted: missing SID months fail.

All 46 have exact returned Directorate discovery candidates in existing evidence.
None is independently verified for this EA numerical contract or registered as an
approved active component. The ledger's candidate strings are search leads, not
invented IDs, confirmed mappings or executable instructions. No additional EA
export SID was found in the inspected headers. **New mappings resolved: zero.**
Before use, verify exact source identity, bounded historical points, monthly
net-saleable units, signs, correspondence with the EA national/component vintage,
and route/aggregation ownership; then review canonical registration and mapping.
No live discovery/retrieval permission has been extended by this audit.

Outside the 46, GD is redundant with the separately selected Snøhvit SID; HH/HG
are alternative ex-LNG accounting references; HM/HN are optional Gassco accounting
diagnostics. EB is an essential Rev leaf already counted once, even though also
used in the optional duplicate-deduction diagnostic. The national/non-flexible
aggregate is not additional supply. `norway_exports_qa` and current destination
comparisons are optional. Seven earlier destination series are essential for the
existing static preferences, despite their registry sourcing-priority label.
No raw-flow alias stitching, new calibration target or topology is introduced.

`verified_sources.json` freezes **28 existing selected contracts**, not new source
approval: 16 named fields, national production, Snøhvit, daily Kollsnes maintenance,
seven earlier allocation proxies and two original combined comparison groups.
It pins exact canonical IDs, raw/reported units, frequency, role, source-file
identity, prior metadata hashes, field memberships, topology and provisional
capacities. Registry REVIEW labels remain unchanged; identity checks do not prove
forecast publication availability or production readiness. Six inactive reference
field SIDs from earlier audits do not resolve any of these 46 active components.

The fresh adapter gates mappings before connecting, then validates each fresh
response's identity, historical boundary, exact dates, units, finite values and
source import cohort. All source points and original metadata are retained before
analytical validation; rejected responses stay in provenance and never enter an
LP. Snøhvit's reported bcm/effective historical mcm/day mismatch is documented and
converted only through the existing July 2025 guard. Signed LNG and maintenance
remain signed. Missing daily derates are never assumed zero. Only unchanged
existing baseline capacity assumptions are accepted; effectiveness remains
unverified. No new energy conversion or field-maintenance subtraction is used.

Optional current comparisons have separate requests from earlier training. Failed
optional queries remain unavailable; UK/FR+BE/NL+DE can show compatible proxy
residuals, while DK signed net and PL/Nybro errors remain withheld. No forecast
comparison or performance scoring is introduced.

The live full model remains **blocked before retrieval on all 46 components**.
Offline success tests use an explicitly reduced synthetic topology, a fixture-only
reviewed contract and mock responses for already selected Kollsnes inputs. Their
success demonstrates the adapter/report pipeline, not resolution of the full
model's missing mappings, a live reconstruction or permission to drop sources.
Deleting components or changing the real topology cannot bypass the gate.

To reproduce formula evidence into a new repository-local directory, use the
workspace interpreter with `scripts/audit/audit_routing_sources.py --output <new-directory>`.
It never overwrites evidence or contacts a service. The ledger is evidence;
configuration remains authoritative and source changes still need review.
