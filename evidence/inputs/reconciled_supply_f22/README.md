# F2.2 historical population and forecast activation gate

One worker; branch `feature/reconciled-supply-f22`, verified base `81114aa`.
Fresh authorised EA/Shooju queries on 12 October 2026; all historical observations
bounded January–December 2024. Workbook formulas/labels identify relationships
only. No workbook observations, 2026 locked actuals, solver or price inputs were
used for this ledger. Prior evidence, topology and objective are preserved.

## Gate 1: not passed

[production_population.csv](production_population.csv) contains every one of the
132 lineage components, a unique prospective owner, source identifier where
resolved, classification, physical category and exact coverage status.
The 16 existing field groups and 46 mapped historical fields retain their accepted
ownership. Snøhvit retains its established historical conversion and guard.
Fresh queries validated all of these original 64 sources (62 fields, national,
Snøhvit); Hanz's existing January/February exception was unchanged.

For the remaining 69:

| Finding | Components |
|---|---:|
| Exact NPD field identity / SID found | 61 |
| Complete twelve-month 2024 observations | 28 |
| Confirmed empty 2024 responses | 27 |
| Partial 2024 responses | 6 |
| No exact standalone source match | 8 |

The ledger conservatively holds 65 field/discovery candidates in classification
5 / UNMAPPED, rather than inventing physical mappings or outside-boundary claims.
Four grouped/calculated project components are provisional classification 2:
Yggdrasil, Skarv Satellite Project, Utsira High Project and PPF project. Their
ownership remains uncertified, so they are not numerically excluded. No additional
component has been asserted to duplicate one of the sixteen fields or verified
outside the export boundary merely because its source has no observations.
The classification is exhaustive but **not a certified mutually exclusive
physical partition**. Unknown relationships remain explicit blockers.

The eight unmatched components are Irpa, Fenris, Bestla, Berling and those four
projects. Six incomplete sources are Gyda, Huldra, Knarr, Oselvar, Trym and
Veslefrikk. All other failures are individually listed in the ledger. A source
identifier's existence does not establish missing-month values. Empty responses
were confirmed with a second bounded native Shooju query; no missing-to-zero rule
or new structural-zero exception was introduced.

The 28 complete additional sources contribute 0.426406 bcm annually: Brage
0.225193, Tune 0.200847 and Vilje 0.000366; the other 25 return explicit source
zeros in all twelve months. These observations are not assumed zeros.
[partial_2024_reconciliation.csv](partial_2024_reconciliation.csv) accounts for
them separately from the accepted 62 mapped fields. The unassigned difference is
0.020453 bcm annually, peaking at 0.018849 bcm in December. Trym's partial source
response is a candidate explanation, **not** permission to fill its missing
January–October observations. Signed rounding-scale discrepancies are retained.
Trym returns 0.001609 bcm in November and 0.018852 bcm in December, matching the
two principal unassigned differences to historical-source rounding precision;
this narrows the numerical explanation without certifying its missing months.
Vilje also returns a signed May value of -0.000073 bcm. It is preserved in the
source diagnostic, not clipped into a nonnegative physical supply assumption.

Brage's Statpipe conditioning/entry, Tune's sale-gas attribution and Trym's Danish
system boundary are already unresolved in canonical model notes. Fresh primary
definition checks support retaining these questions: Brage's gas joins Statpipe
but that alone does not establish the processing entry ([Directorate](https://factpages.sodir.no/en/field/PageView/All/43651));
Tune goes to Oseberg but operator material also describes injection
([Equinor](https://www.equinor.com/energy/oseberg)); Vilje's gas goes through Alvheim
to SAGE ([Directorate](https://factpages.sodir.no/en/field/PageView/All/3392471)).
These facts are evidence, not authorisation to change existing physical attribution.
The prior [field-readiness evidence](../network_forecast_field_readiness.csv)
and `config/model.yaml:routing.notes` retain the same boundary questions.

## Gates 2 and 3 / forecast outcome

No annual residual weights were approved numerically or frozen. UNMAPPED is not
exportable supply, and the 46-only five-node weights are not used. The approved
allocation must wait for a complete source-backed historical population and
defensible boundary certification. No partial real forecast is permitted.

The backend now records the complete population gate and checks two approved
provisional capacity scenarios without changing the 19 canonical envelopes:
Kollsnes 143 central / 156 sensitivity, signed plan once, unknown availability
elsewhere. Historical capacity scenario restrictions remain unchanged.
Snøhvit is retrieved at the same requested prospective origin as the national
forecast; its monthly-bcm label versus rate-scale values and older forecast
boundary remain a blocker. No forecast rate conversion is inferred from the
workbook or inherited from the historical July-2025 exception.
The retrieved Kollsnes plan reaches 156 mcm/day on thirteen days starting
3 September 2027. Subtracting this unchanged from the 143 central envelope
produces negative availability and fails explicitly; no floor or rescaling is
introduced. The 156 sensitivity prepares all nineteen monthly capacity tables
(Kollsnes 2.4735–4.836 bcm/month) but the supply gates still prevent solving.

Use the existing command:
`python scripts/run/run_routing.py --config config/run.yaml --validate-only`
with the approved workspace interpreter. A blocked package explicitly withholds
monthly flows, includes candidate source responses and capacity snapshots, and
preserves Excel/CSV/HTML and hashes. Synthetic workflows remain demonstrations.
No source-backed country allocation, destination-share comparator, feasible-flow
ranges or country sensitivity can be reported while the supply gates fail.

## Provenance and next specific work

[assessment.json](assessment.json) pins the raw evidence directory and metadata
hashes. That unique directory retains the 143-series metadata discovery, exact
2024 SID responses and 27 empty-response probes. Retrieval status and rejected
coverage are preserved; rejected data never enter the optimiser.

Resolve source-supported inactive/pre-production/overlap definitions for the 41
incomplete components, then the positive Brage/Tune/Trym entry/boundary questions.
Reconcile the complete year without implicit zeros or unallocated discrepancy.
Establish the prospective Snøhvit units and compatible vintage through a corrected
source contract. Only then implement/freeze complete-population allocation and
run the requested country forecast and routing sensitivity diagnostics.
