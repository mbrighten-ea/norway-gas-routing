# F2.3 physical-input decision — 13 October 2026

**BLOCKED_INPUTS. No prospective source vector, frozen weights or country forecast
was released.** The target is 38 months, November 2026–December 2029. The 12-month
default and December 2030 option remain unchanged.

One worker, isolated `.scratch/worktrees/f23`, branch
`feature/physical-input-contract-f23`. Verified `a34bc72` has `f4a742e` as its
direct parent; no investigation history was merged. This work adds evidence and
diagnostic functions only. No active input contract, registry, network, objective,
capacity rating, forecast preparation or historical safeguard was changed.

| Contract | Investigated and verified | Still unresolved / required decision | Decision |
|---|---|---|---|
| Production accounting / allocation | Fresh bounded 2024 queries of existing ledger SIDs; exact explanation of the 0.020453 bcm gap; Oseberg composite ownership; priority evacuation paths below | Missing observations, four project/group memberships, signed Vilje accounting, Heidrun domestic split, incompatible national-total vintages. Core must certify the distinct-volume boundary and memberships before approving the revised frozen-weight denominator | **BLOCKED**, no weights |
| Snøhvit | 38/38 prospective months at October 1 and current capture; identical values; historical rate conversion equals native saleable volumes rounded to five decimals | SID mislabels its dimension; prospective standard conditions, net-saleable definition and component compatibility with national forecast are not source-certified. Obtain a source-owner declaration and compatible national/component provenance, then Core approval | **BLOCKED**; conversion diagnostic only |
| Kollsnes | Daily 1,157/1,157 coverage at both origins; monthly SID equals daily mean in current capture; 156 upgrade supported; 13 days have unavailable=156; both vintages calculated separately | No proof of an independent continuing 143 dry-export limit with compatible 156/loss measurement; no event/revision ledger proving net deductions and overlap treatment. Core must approve a documented boundary, effective dates and loss-reference contract before any dual constraint | **BLOCKED**; dual formula inactive |

## Production arithmetic and ownership

[Monthly accounting](monthly_accounting_2024.csv), [132-slot inventory](component_inventory.csv)
and [Oseberg membership reconciliation](oseberg_component_ownership_2024.csv) retain
signed observations and missing cells. `annual_observed_subtotals_bcm` in
[assessment.json](assessment.json) is **not** a certified all-field annual ledger.

| 2024 quantity | bcm | Coverage / interpretation |
|---|---:|---|
| EA national historical segment | 126.231133 | 12 observations, latest revised |
| Original 62 mapped series | 119.377524 | Existing Hanz-only Jan/Feb structural-zero authority reused; no new zero assumption |
| Complete additional 28 | 0.426406 | Brage 0.225193, Tune 0.200847, Vilje 0.000366; 25 sources explicitly return twelve zeros |
| Trym returned observations | 0.020461 | November 0.001609; December 0.018852. January–October absent, never filled |
| Native NPD Snøhvit saleable | 6.406742 | 12 monthly billion Sm3 observations |
| Legacy Snøhvit rate conversion | 6.406750 | Every month equals native saleable rounded to five decimals |
| Independently retrieved NPD national total | 126.247000 | 12 three-decimal observations; separate source revision/boundary gate |

The F2.2 gap is exactly **0.020461 − 0.000008 = 0.020453 bcm**. Trym's partial
source was omitted from the complete-response subtotal. The five-decimal Snøhvit
conversion introduces +0.000008 bcm relative to native six-decimal saleable
observations. Trym's raw SHA is unchanged from F2.2; this discrepancy does not
require a new Trym revision or balancing adjustment. Its field identity is NPD
18081500, distinct Norwegian marketed gas processed through Harald/Tyra, outside
the existing modelled Norwegian export entries. No Danish-node assignment was made.

Using native Snøhvit, the remaining difference is numerically zero in January–October
and equals the returned Trym points in November/December (floating residual <1e-12).
That equation does **not** establish zeros or ownership for unavailable components.
The full observed-subtotal equation is
`126.231133 = 119.377524 + 0.426406 + 0.020461 + 6.406742`.

EA Oseberg is a verified historical composite: native Oseberg 8.365876 + Oseberg Sør
0.479749 + Oseberg Øst 0.005558 = 8.851183 bcm, monthly discrepancy <1e-12. Its
members must not be added independently to the existing EA parent. Tune is separate
from that composite in these observations. The national EA–NPD difference is
−0.015867 bcm, reaching −0.004724 in October. It exceeds simple three-decimal
rounding bounds: the NPD total was updated September 22, the native field ledger
and EA snapshot October 12. A revision bridge is absent; timestamps alone do not
prove the cause. Neither total was substituted for the other.

The 69 extra slots are not 69 independent producers. Of 61 exact SIDs, 28 are
complete, 27 independently confirmed empty and six partial. Eight lack a standalone
identity; four of those are project/group calculation slots, with unverified child
ownership. Lifecycle descriptions explain many retired or future developments but
do not turn missing SID observations into zeros. The operational 41-component
coverage/classification blocker is retained.

Priority physical findings from the [SODIR descriptions-only table](https://factpages.sodir.no/en/field/TableView/Description):
Brage gas enters Statpipe (candidate Kårstø path); Tune receives corresponding
Oseberg sales-gas entitlement after injection; Vilje uses Alvheim/SAGE; Trym uses
Harald/Tyra; Heidrun has both Kårstø and domestic Tjeldbergodden paths. These are
documented paths, not approved new allocations. Vilje's May −0.000073 bcm remains
signed and unexplained; gas lift is documented but not proof of that adjustment's
cause. Heidrun's 2024 total is 1.658415 bcm; the domestic fraction remains unknown.

No residual source-node weights were calculated or approved. The revised denominator
must contain only independently owned, export-eligible residual saleable volumes;
node numerators must list defensibly mapped memberships. LNG, Trym/outside volumes
and genuinely unresolved export-eligible volumes stay separate. A near-zero total
identity cannot supply those missing physical memberships.

## Snøhvit dimensional test and compatibility

[38-month conversion diagnostic](snohvit_conversion_diagnostic.csv) applies only
`monthly_average_mcm_d × calendar_days / 1000`. Converted sums: November–December
2026 **1.085490**, 2027 **5.327747**, 2028 **4.807613**, 2029 **6.334864 bcm**.
Rates are 0–18.209667 mcm/day, monthly volumes are nonnegative and below national
production. Zero observations in April–May 2027 and April–June 2028 are returned
source values, not imputed shutdowns. No 2030 extension or selected-source replacement.

The selected source was updated October 16, 2025 at 14:15:01.591 UTC; the national
snapshot October 12, 2026 at 17:13:14.388 UTC. Both were queryable `@asof` October 1,
2026; national archive metadata has a September forecast boundary. Import/update
timestamps are not certified economic publication dates. Different vintages alone
are not grounds for rejection: incompatible component definitions remain the issue.

Native historical Snøhvit metadata explicitly identifies marketed gas-saleable in
bill Sm3. The prospective SID only describes supply for LNG and incorrectly says
bcm. Workbook lineage `IE=GY=HH+GD*days/1000` supports subtracting its own LNG
component once; it does not prove that the stale selected GD export is the component
in the newer national SID. Historical national-minus-dashboard agrees with converted
Snøhvit within 0.000004 bcm, but the dashboard SID fails the **prospective lifecycle
gate**; no future actual-labelled points were fetched to bypass it. Gross wet feed,
CO2 removal, LNG sendout and net marketed production cannot be treated as synonymous.
The historical July-2025 guard and signed historical convention remain intact.

## Kollsnes diagnostics and country consequences

The [2019 Gassco brochure](https://gassco.eu/wp-content/uploads/2023/04/091540-Kollsnes_NORSK_spreads_22.10.2019-1-1.pdf)
describes 144.5 MSm3/day export capacity.
[Gassco's 2023 report](https://gassco.eu/wp-content/uploads/2024/03/Gassco-aarsrapport-2023-ENGELSK.pdf)
dates completion of an approximately 8% upgrade to autumn 2023.
[Equinor's January 2025 statement](https://www.equinor.com/news/20250106-troll-highest-natural-gas-production-ever)
confirms an increase from 144.5 to 156 MSm3/day contributing to 2024 production.
Current Gassco pages still disagree between narrative and facts; the
[government facility description](https://www.norskpetroleum.no/produksjon-og-eksport/landanlegg/)
distinguishes rich processing from dry export. These do not establish a simultaneous
143 dry limit and 156 processing limit measured on the same gas basis, nor an exact
effective day. The upgrade evidence is not approval to promote 156 centrally.

[Gassco UMM publication principles](https://umm.gassco.no/resources/Principles%20for%20publication%20on%20umm.pdf)
define unavailable versus remaining available capacity and aggregate dependent
field/processing outages by **net** impact. That supports investigating unavailable
capacity, not assuming an EA calculator SID is a fully deduplicated event ledger.
The retained capacity database contains no event records; the retained historical
export template is not actual notices. The EA daily SID provides no event/revision
IDs or rating basis. Its upstream comparator has 358 partial/intraday points,
inadequate for event reconciliation. Production lineage already deducts field outages
in several field forecasts; upstream losses must not be deducted from production again.

| September 2027 arithmetic, bcm | October 1 archive | October 13 capture |
|---|---:|---:|
| 143 − unavailable | 1.998000 **invalid** | 2.083500 **invalid** |
| 156 − unavailable sensitivity | 2.388000 | 2.473500 |
| Hypothetical min(143, 156 − unavailable) | 2.262500 | 2.291500 |

Both central cases have thirteen −13 mcm/day daily values, despite positive monthly
sums; they cannot be solved as valid capacities. Tables preserve those invalid values.
Daily and monthly [October 1](october01_archive_capacity_monthly.csv) and
[current-capture](current_capture_capacity_monthly.csv) calculations cover all 38
months separately. Maximum vintage change is 41 mcm/day; do not mix these origins.
The dual hypothesis reduces September's capacity versus 156 sensitivity by **0.1255**
or **0.1820 bcm**, respectively. No-loss 2028/2029 observations are source plan values,
not certification of no future outages. No active capacity contract was implemented.

Quantifiable routing exposure: Brage+Tune **0.426040 bcm** has distinct Statpipe/Oseberg
entry implications and therefore UK-versus-continent consequences; Vilje's signed
**0.000366 bcm** concerns the UK-direct proxy; Trym's observed **0.020461 bcm** concerns
an external Danish path, not Baltic Pipe/DK offtake. Heidrun's unknown domestic share
lies within its **1.658415 bcm total**, a bound rather than an estimated diversion.
The Kollsnes capacity differences above are potential throughput differences, not
country flow forecasts. Network interactions can rearrange other flows; individual
market changes cannot be inferred from these packets alone.

No LP source-weight sensitivity was run: no defensible complete same-national-boundary
source vector exists, and using an invented domestic or unresolved allocation would
manufacture the comparison. Physical exits Langeled/Vesterled, Franpipe and Zeepipe
must be distinguished from UK_DIRECT and Emden NL/DE country proxies. Legacy FR+BE
and NL+DE groups cannot validate individual terminal deliveries. Nothing here is a
certified or commercially validated country forecast.

## Validation, retained evidence and restart

[Validation](validation.json): **27 focused and 596 full regression checks passed**;
one existing pandas warning. The full suite includes historical reconstruction,
validate-only, holdout/vintage guards and synthetic 12/50-month execution. No shared
packages were changed. Existing hash-referenced offline capacity fixtures were copied
for testing only; two original tracked files' byte serialization was restored afterward.

Fresh live validation at October 1:
`outputs/routing_runs/20261013T105227167672Z_fc7923e9/` retains Excel, chronological
38-row monthly CSV, HTML and complete provenance. All 16 fields and national returned
38 months; Kollsnes returned 1,157 days; Snøhvit returned 38 months but failed its
unit/compatibility gate. Status **BLOCKED_INPUTS**, empty solver results, flow cells
unavailable. No forecast LP ran. The package's Git snapshot notes temporary fixture
byte differences; no substantive model/config change occurred or is committed.

Fresh raw captures are under `data/raw/physical_contract_f23/20261013T101258056170Z/`;
[file hashes](capture_file_hashes.json) cover raw observations, metadata, empty-source
confirmations, October-origin probes and description-only source data. The reusable
audit command is `scripts/audit/assess_physical_input_contracts.py`; each execution
queries SIDs afresh into a unique capture and emits diagnostics, never active inputs.
Supplemental targeted probes establish Oseberg membership and origin availability;
they do not repeat general SID discovery. Original F2.2 evidence is unchanged.

No protected January–September 2026 actual SID observations were requested or used.
A web search preview incidentally surfaced protected production rows; these were
excluded from retained numeric evidence, fitting and scoring. Subsequent public
queries were restricted to definitions and dated capacity documents.

Restart: obtain the source-owner contracts and Core decisions in the table, bridge
national revisions, certify independent production ownership/coverage and the domestic
split, then calculate fresh frozen-2024 weights. Only after all gates pass may the
existing `forecast_end_month: '2029-12'` workflow prepare supply and solve. Keep
143 central and all existing blockers until an explicitly approved contract replaces them.
