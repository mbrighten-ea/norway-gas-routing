# Accepted modelling decisions

## Core F2.4 provisional release approval (13 October 2026)

The modeller explicitly approved the 2024 EA component equation, selected Snøhvit
monthly-average rate conversion and mixed-vintage limitation, 156-minus-unavailability
technical reference, and proportional 143 stress. Use four independent price-free
monthly scenarios over November 2026–December 2029. A/C make no additional domestic
Heidrun deduction; B/D use the forecast component as a hypothetical whole-field
outside-network bound. No commercial calibration, topology or LP objective change.

This authorises frozen mutually exclusive annual residual weights with supported
existing entries, separate external Trym and unrouted UNMAPPED, including signed
Vilje net accounting. It does not authorise treating all workbook slots as independent
fields, zero-filling missing history, adding the NPD revision difference or claiming
that future field mix and domestic consumption are certified. Small documented
unresolved scope may be released as a partial-coverage POC when the core monthly
balance and input checks pass. The ordinary default and historical/holdout guards
remain unchanged. Exact contract and operator options are in INPUTS.md/README.md.

Established from the lead modeller's agreed initial design, 2026-10-07. This file
records acceptance; unresolved alternatives belong in [STATUS.md](STATUS.md).
Configuration is the authoritative machine-readable mapping, not an approval
mechanism. Numerical assumptions are not inferred from missing data.

## Chronological evaluation (approved 2026-10-09)

- Fit/develop with information available through 2024-12. Compare fixed candidate
  parameters on 2025-01–2025-12; never fit to those outcomes.
- Reserve 2026-01–2026-09. Routine calibration, plots, diagnostics and model
  selection cannot access it. Final scoring requires explicit approval and a
  frozen selected model; no final scoring is currently implemented.
- Separate realised/revised reconstructions from origin-only retrospective
  forecasts. Missing or unverified vintages prevent forecast claims. Preserve
  the price-free baseline; do not introduce price response for this task.
- `config/evaluation.yaml` and the evaluation guards implement these boundaries;
  manifests retain split, input, parameter and experiment identities.

## Supply and network

F2.2 (user instruction, 12 October 2026): approve provisionally an allocation of
the national forecast remainder, after sixteen explicit fields and compatible
Snøhvit, using frozen annual-2024 shares from the **complete reconciled** population.
Include all eligible mapped components; retain outside-boundary and UNMAPPED
shares separately. Approval is conditional on the complete historical ledger
passing; it does not approve the older five-node/46-field-only weights or allow
unknown production to enter convenient nodes. No weights have been frozen.
Approve the existing 19 envelopes, Kollsnes 143 mcm/day central and 156 sensitivity,
signed maintenance once, and disclosure of other unknown future availability.
Keep topology and price-free objective unchanged. Forecast units/vintages and
historical component ownership remain source-validation requirements.

B2 closure (user's conditional authorisation, verified 12 October 2026): Hanz's
missing January/February 2024 are structural pre-production zeros, specifically
supported by the Directorate's production start of 20 April 2024 and the
operator's Q1 transcript. Preserve the returned March zero and all raw data;
reject contradictory pre-start observations. This rule applies to this field and
these two months only. See [evidence](evidence/inputs/routing_sources_b1/hanz_preproduction.json).

Data sourcing rule confirmed by the user, 9 October 2026: every new run queries
EA/Shooju SIDs directly. Forecast replay uses the same forecast-origin `@asof`
for production and legacy destination forecasts. Workbooks are formula/SID
references only, never numerical input sources. Saved solver outputs and source
responses remain provenance, not substitutes for fresh retrieval. Missing
component SIDs or origin values must stop the affected calculation.

- Field production forecasts are exogenous supply constraints. Do not impose
  individual-field technical capacities; infrastructure capacities are separate.
- The named-field aggregation in `config/model.yaml` and `config/data_series.csv`
  is accepted for NYHAMNA, KOLLSNES, KARSTO, OSEBERG_HEIMDAL, SLEIPNER and UK_DIRECT.
  Martin Linge initially belongs to UK_DIRECT; additional UK-direct fields require
  identification. DE_DIRECT requires demonstrated effectively fixed German
  evacuation and has no identified production yet.
- OTHER_RESIDUAL is a temporary reconciliation bucket, never silently allocated.
  The aggregate/non-flexible production series must not be added to named component
  production without an approved decomposition. Snøhvit/Melkøya LNG is outside the
  European pipeline optimiser. Exclude domestic use from exportable production or
  represent it separately when the relevant data exist; avoid double subtraction.
- The six primary destinations are UK, Germany, Netherlands, Denmark, Belgium and
  France. Poland is not currently an optimisation sink.
- Use the configurable simplified graph in `config/model.yaml`. CORE represents
  interconnected Sleipner/Draupner dry-gas transfer as a mass-balance junction with
  no independent capacity. Collapse pipes while retaining source identity,
  processing constraints, major export corridors, shared bottlenecks and choices.
  The existing junctions represent Europipe II's shared Germany/Denmark corridor
  and the Emden-area DE/NL allocation pool. No hydraulic calculations are intended.

## Historical calibration observations

Gassco's physical Emden and Dornum flows define:

```text
DE_NL_total = Emden + Dornum
NL = Dutch TSO / ENTSOG Netherlands flow at Emden EPT1
DE = DE_NL_total - NL
```

Germany is a derived historical target. Detect missing components, incompatible
units, negative residuals and reconciliation failures in package code. Existing
EA aggregate DE/NL and destination forecasts are QA benchmarks only, with no
calibration leakage or circular use as physical inputs.

Other agreed identities are UK = Easington + SEGAL + St Fergus; Denmark = Nybro;
Belgium = Zeebrugge; France = Dunkerque. Do not infer additional transformations.
Identification of the two existing raw St Fergus series remains unresolved.

## Infrastructure capacity and maintenance

Available daily capacity equals technical capacity minus maintenance derate.
Monthly available bcm is the calendar-day sum of the daily available mcm/d divided
by 1000. [INPUTS.md](INPUTS.md) defines the unit and coverage contract. Missing
technical capacities remain explicit nulls until sourced or analytically approved.
An optional effective operating capacity requires evidence and modeller approval;
never lower it simply to improve historical fit.

**Maintenance reduces capacity, not flow.** A derate affects routed flow only when
an infrastructure constraint binds. For example, reducing 150 to 130 mcm/d must
leave a required 110 mcm/d flow unchanged. Technical capacity can exceed the
operating limit because another bottleneck binds first. Do not silently clip
unusual maintenance observations or interpret outage values as available capacity.

The preferred Kollsnes input is
`teams\natural_gas\EUR\daily_NO\NO_maintenance_Kollsnes`: daily, `mcm_d`, display
source Gassco, economic property outages, lifecycle forecast. Provisionally treat
it as a Kollsnes processing-capacity derate. Do not also apply
`teams\natural_gas\EUR\NO_upstream_maintenance_Kollsnes` as a plant constraint;
it may overlap upstream effects in production forecasts.

Analyst-approved provisional convention, 2026-10-08:
`available_capacity = reference_capacity - maintenance`. Negative maintenance
means additional capacity relative to the reference baseline and is not clipped.
Keep negative-value diagnostics; their sign alone no longer blocks use. A baseline
still requires sourcing/approval, and negative resulting available capacity fails
without clipping. This convention does not infer a technical/nameplate maximum or
approve additional upstream constraints.

## Intended commercial framework (later implementation)

```text
BaseSupply = (1 - phi) * Supply
FlexibleSupply = phi * Supply
```

Use one calibrated global flexibility parameter initially; its value is unresolved.
Calibrate historical base shares. Base routing is preferred/structural routing,
not an immutable contract: capacity restrictions must be able to force rerouting.
Commercial optimisation should mainly affect flexible supply, not send all supply
to the highest-priced destination.

Intended market proxies are NBP (UK), THE (Germany), TTF (Netherlands), ZTP (Belgium)
and PEG (France). Danish pricing remains to be agreed. Prefer relative destination
values/netbacks. Germany may conceptually be the reference (`value_DE = 0`, other
values = destination price minus DE price); final configuration of this reference
requires resolving the existing Netherlands setting. Prices, marginal transport
costs, energy conversions and long-dated assumptions are not invented.

Calibration, the PuLP routing model and production readiness are outside the
initial foundation implementation. Package structures, validations and synthetic
tests implement only the agreed subset, leaving unresolved controls explicit.

## Analyst-selected price sources, 8 October 2026

Use the retained dashboard Reuters day-ahead price SIDs for historical NBP, TTF, THE, ZTP and PEG prices. EA monthly price series, including teams\natural_gas\price\THE, are forecasts and are kept separately; they are not actual-price sources. Market configuration distinguishes price_series from forecast_price_series. Selection does not resolve live validation, NBP FX/therm conversion, monthly aggregation, forecast extension or Danish pricing. No commercial optimiser is implemented.

## Revision-tolerant December-2024 pilot and Core ownership approval

F2.10 explicitly permits currently revised historical production from pre-origin
periods, the seasonal historical LNG assumption and a declared historical capacity
planning case. This approval does not permit target-year actuals in model inputs,
recalibration from scores, holdout access or alteration of the live forward model.

Core approved Halten Øst→KARSTO_FEED, Rev→UK_DIRECT, Balder→KARSTO_FEED and
Urd→KARSTO_FEED, conditional on unique ownership. Core also approved origin-frozen
weights from the latest sufficiently complete twelve consecutive eligible months,
including external/unresolved production and retaining the last complete window
when newer data have material gaps. The first diagnostic retains the specifically
requested 2023 window; newer-window gaps are documented and no operational
chronological selector or indicative 2025 weight sensitivity is activated.
The pilot records retrospective mapping assumptions and leaves unknown production
unrouted. The working F2.7 operational contract remains unchanged.
