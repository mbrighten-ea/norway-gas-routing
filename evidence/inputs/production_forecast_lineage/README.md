# Production forecast lineage: Priority 0

Read-only inspection on 12 October 2026, from `993675a2bcdbab398dc6fa1a32b9ab5c521478e2`,
branch `feature/production-forecast-lineage`. This corrects the F2 interpretation:
the 46 additional historically mapped fields have forward calculations in the
production workbook. Missing standalone published field SIDs do **not** mean
their forecasting methodology is absent. No supply accounting, residual weights,
allocation, solver execution or upstream workbook changes were implemented.

## The 18 exports are not independent components

In `Production mcm_d`, IB:IS contains 16 field exports plus ID and IE aggregates.
All exported values are monthly bcm. Row 2 contains their SIDs; row 3 writes
calculated forecasts to Shooju rather than retrieving independent forecasts.

| Export | Field / definition | Production-rate column |
|---|---|---|
| IB | Troll | L |
| IC | Oseberg | Q |
| ID | NON-FLEXIBLE: IE minus IB and IC | aggregate |
| IE | TOTAL W SNOHVIT: GY | aggregate |
| IF | Aasta Hansteen | AC |
| IG | Asgard | AF |
| IH | Gina Krog | AI |
| II | Gullfaks Sor | AN |
| IJ | Heidrun | AQ |
| IK | Kristin | AW |
| IL | Kvitebjorn | AZ |
| IM | Martin Linge | BC |
| IN | Norne | BF |
| IO | Ormen Lange | BI |
| IP | Skarv | BL |
| IQ | Sleipner | BP |
| IR | Visund | BU |
| IS | Dvalin | BX |

The complete field names, exact SIDs, formulas, assumptions and existing mapped
nodes are in [all_field_components.csv](all_field_components.csv) and
[formula_ledger.csv](formula_ledger.csv). The two aggregate identifiers are
`teams\natural_gas\EUR\NO_production_non_flexible_fields` and
`teams\natural_gas\EUR\NO_production` respectively.

## Component membership and Snøhvit bridge

November 2026 is row 466. Shared formulas were expanded without recalculation:

- HB=L (Troll); HC=Q (Oseberg).
- HD=SUM(AC,AF,AI,AM:AN,AQ,AT,AW,AZ,BC,BF,BI,BL,BP,BU,BX): sixteen large
  components, including the other fourteen registered fields plus Gullfaks and Heimdal.
- HE=SUM(CD:FY): 100 small-field components; FZ repeats this sum.
- HF=SUM(GI:GU): thirteen new-field/project components, **including GU**.
- HG=SUM(HB:HF): 131 non-LNG components, explicitly labelled excluding Snøhvit.
- HH=HG*days/1000: monthly bcm excluding Snøhvit, published as
  `teams\natural_gas\EUR\NO\production_total`.
- GY=HH+GD*days/1000; IE=GY: national monthly bcm **including** Snøhvit GD.
- ID=IE-SUM(IB:IC): all components except Troll and Oseberg, **including Snøhvit**.

Thus NON-FLEXIBLE contains the other fourteen registered field forecasts, all
46 additional historical mapped fields, 69 further non-LNG components and Snøhvit.
Adding all sixteen field exports to ID double-counts those fourteen fields.
Snøhvit must not be deducted again from HH. A deduction from IE requires a
compatible GD forecast vintage and unit basis; membership alone does not make
the separately registered Snøhvit SID compatible.

H (SUM OF FIELDS) is a control with a different range, including GD:GE; it is
not the final IE export. G (NPD total) and GZ are also controls, not substitutes
for the published forecast total.

## Reconciliation before any allocation

Saved workbook forward caches were inspected only for October 2026–December
2030 as the user requested, never used as operational inputs. No locked actuals
were read. Workbook identities reconcile in every inspected month within
3.6e-15 bcm. Fresh, same-query-origin EA responses independently satisfy
ID=IE-IB-IC within 3.6e-15 bcm over the same 51 months.

| November 2026 measure | Saved workbook bcm | Fresh EA bcm |
|---|---:|---:|
| Troll | 4.046264 | 4.046264 |
| Oseberg | 0.767752 | 0.767752 |
| NON-FLEXIBLE | 5.993550 | 5.985150 |
| TOTAL W SNOHVIT | 10.807566 | 10.799166 |
| HH excluding Snøhvit | 10.274643 | not queried |
| GD Snøhvit converted from 17.764098 mcm/day | 0.532923 | not queried |
| Sum of sixteen field exports | 8.195620 | see per-field evidence |
| Fourteen fields also inside NON-FLEXIBLE | 3.381604 | see per-field evidence |
| Additional 46 mapped field calculations | 1.532908 | not published individually |
| Remaining 69 non-LNG component calculations | 0.546116 | not published individually |
| HM / gassco_total | 10.072900 | 10.064500 |

The 0.0084 bcm November change matches Dvalin's changed export. Five field
exports differ somewhere across the full window; eleven match exactly.
Different saved and live values are not a rejection criterion, but mixing
saved component forecasts with live national totals is not a coherent input run.
[aggregate_reconciliation.csv](aggregate_reconciliation.csv),
[live_forecast_comparison.csv](live_forecast_comparison.csv) and
[verification.json](verification.json) preserve the checks and monthly detail.

## How the underlying fields are forecast

These are calculated EA forecasts, not 132 independent incoming forecast SIDs.
At November 2026 the component formulas classify as 89 annual-lag declines,
16 depletion-profile forecasts, fourteen outage-adjusted forecasts, ten literal
forward assumptions and three other calculations. This classification describes
that month's formula shape, not a claim that every month follows one algorithm.

Large fields generally subtract maintenance from gross profiles with MAX(...,0).
Troll uses the regression-input sheet's technical-capacity/maintenance equation
and explicit adjustments. Small fields use prior-year rates and plateau/decline
parameters; new fields use depletion profiles with start/peak/end assumptions.
Examples of visible judgemental adjustments include Fram +0.5 mcm/day, Hanz
-0.1 mcm/day and Halten Ost +4 mcm/day. Snøhvit GD uses an annual-lag profile
with its own start/end and decline parameters; it is not one of the 18 exports.

Maintenance pulls the named `NO_maintenance_*` series; Y+1 additions reference
`gassco\unavailability_fields_processing_plants` with sign reversal and monthly
aggregation. Longer-horizon formulas use historical same-month averages, with
some factors of 0.5. One comparison query explicitly uses `@asof:2025-01-01`.
These assumptions and field-level outage deductions must be preserved and
distinguished from network-capacity scenarios to avoid applying losses twice.

Two coverage issues remain in the saved forward sheet: Visund Sor FE has no
October 2026 cell (also a lag seed for October 2027); Hanz GI has no cells for
January–June 2027. Excel SUM ignores these blanks. The ledger and reconciliation
record them explicitly; they are **not approved structural zeros**. All 46
historical mappings have corresponding forward components, but their complete
usable delivery coverage still needs these specific gaps resolved.

## Legacy flows connection

HM publishes `teams\natural_gas\EUR\NO\gassco_total`. HN starts from HG and
deducts Martin Linge, Rev, Vilje, Volund, Boyla, Skogul, Trym, Alvheim **and Rev
again**; HM=HN*days/1000. The duplicate Rev term is an upstream formula finding,
not an authorised correction. This total already excludes Snøhvit and additional
direct-route field volumes; it is not interchangeable with IE or HH.

The legacy flows workbook's `Gassco_raw!B2` requests that same monthly bcm SID.
B1 divides by `EnergyAspects\Calendars\days_per_month_calendar` and multiplies
by 1000 to recover mcm/day. `Forecasts!F184` selects monthly bcm from Gassco_raw
column C; E184 selects the corresponding rate from B. `SJ upload!M3` names the
same SID and M25 reads the Forecasts total, but M2 has no SJWrite. Historical
terminal-sum controls and downstream destination residuals are separate concepts.
The units are mcm/day × calendar days / 1000 = monthly bcm, not an annual scale.

Fresh metadata confirms monthly bcm and forecast lifecycle for the 18 exports.
Generic copied descriptions such as “supply to UK” do not define field membership.
The gassco SID's source-file metadata still names the flows workbook and an older
handover date; the formula trace shows the production HM writer. The separately
registered Snøhvit SID is labelled monthly bcm, whereas GD is mcm/day: do not
reuse its values as GD without resolving that definition/vintage distinction.

## Integration decision and provenance

Prefer an expanded maintained forecast export of these existing field components
or existing-node aggregates, with complete coverage and a common forecast vintage.
Alternatively reproduce the existing formulas only from freshly retrieved source
inputs and explicit approved parameters; saved workbook observations remain
forbidden operational substitutes. No search for 46 nonexistent individual
forecast SIDs or new residual allocation is needed to establish that methodology.
Core's provisional historical shares are only relevant to production that still
genuinely lacks a usable forward forecast after this trace; no weights were fitted.
Resolving the Hanz/Visund Sor forward gaps, export/refresh contract, Snøhvit
compatibility and the Rev discrepancy precedes affected supply implementation.

[manifest.json](manifest.json) records source-response locations, captured origin,
workbook hashes and read boundaries. Fresh raw responses and metadata are retained
under its unique `data/raw/production_forecast_lineage/` directory; originals and
previous task outputs remain intact. Both workbook hashes were verified unchanged.
