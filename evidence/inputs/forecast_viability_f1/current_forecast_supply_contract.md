# F2 current forecast supply contract — physical-design decision

**12 October Priority 0 correction:** the [production formula trace](../production_forecast_lineage/README.md)
establishes forward calculations for all 46 additional mapped fields. The review
below records the earlier published-SID gap, not absence of a forecast methodology.
Prefer integrating the existing component calculations through a coherent fresh
source/export contract before considering residual allocation. NON-FLEXIBLE
overlaps fourteen registered fields and includes Snøhvit; national, HH and
gassco_total have distinct accounting boundaries. Specific forward gaps and the
duplicate Rev deduction are documented in the new trace. No accounting changes
have yet been implemented.

Reviewed from `ab07f65`, accepted decisions, canonical model, F1 matrices and
existing forecast architecture. No repeated field-discovery search, workbook
numerical ingestion, allocation fit or physical mapping change.

The available 16 field forecasts populate their existing nodes, but cannot alone
provide the **complete active source vector**. National/non-flex production is
an accounting total spanning multiple evacuation/processing routes and LNG.
`non-flex = national - Troll - Oseberg` does not identify node memberships or
monthly evacuation volumes. The documented residual is forced unrouted; assigning
it to CORE or another node is forbidden. Dropping 46 active leaves into residual
would change the refined physical model, even if that reduced model solves.

| Existing node | Additional historical fields needing a forecast contract |
|---|---:|
| KOLLSNES_FEED | 2 |
| KARSTO_FEED | 16 |
| SLEIPNER | 4 |
| UK_DIRECT | 17 |
| EKOFISK_FEED | 7 |

**Smallest practical alternatives for the physical-design workstream:**

1. **Direct node aggregation feeds (preferred sourcing route).** Obtain five
   maintained monthly bcm forecast aggregates with explicitly reviewed component
   membership. They may cover just the missing leaves, then be added to the
   existing 16 fields; or cover whole nodes, replacing those nodes' individual
   fields. Do not combine both. No arbitrary allocation is necessary, and 46
   individual SID searches are unnecessary if these feeds exist. The workstream
   must approve scope, sum-versus-replacement semantics, net gas units, national/LNG
   compatibility and declared forecast vintage. No such source is presently
   identified or approved in the canonical registry.
2. **Conservative identified-field scenario.** Route only the known 16 and retain
   the remaining national-minus-LNG volume as forced unrouted. This could give a
   limited-supply scenario, not a complete terminal-flow forecast: it removes
   known contributions particularly to Karsto, direct UK and Ekofisk. Requires
   explicit approval of reduced scope and labelling. Not implemented silently.
3. **Fixed source-node allocation of residual.** A pre-origin physical split or
   historical-share construction would fill the vector but introduces a new
   allocation methodology, potentially ignoring field decline, outages and new
   developments. Requires approved shares/basis, scope, vintage, expiry and
   sensitivity treatment; unavailable inputs must not be silently zero-filled.
   No fitting, national aggregate splitting or such scenario was implemented.

All complete contracts must reconcile once:
`pipeline = national - Snøhvit`,
`UNMAPPED = pipeline - sum(distinct mapped source supply)`.
Negative residuals or duplicate component ownership must fail. Existing national
and non-flex totals cannot be added as extra gas.

Two further decisions remain: confirm the selected Snøhvit forecast's rate-versus-
bcm interpretation and stale-vintage compatibility (no extension of the historical
July-2025 guard); and approve a prospective capacity scenario. Proposed
`baseline_prospective` holds the 19 canonical envelopes constant, with only the
existing signed Kollsnes maintenance plan applied once. Its processing/dry-gas
scope and potential production-outage overlap need approval. Other assets' lack
of derates is an explicit scenario assumption, not verified absence of outages.
The scenario name/config selection is **not approval**.

Live F2 validation, November 2026–October 2027, retrieved 19 same-origin sources:
16 fields and national passed exact monthly bcm coverage; Snøhvit's twelve raw
months passed coverage but conversion remains pending; Kollsnes passed exact
365-day mcm/day plan coverage. The unsolved package is
`outputs/routing_runs/20261012T145039391075Z_40ff1f36/`.
No historical NPD values were requested for future delivery.

The twelve-month synthetic workflow solved successfully in
`outputs/routing_runs/20261012T145249435605Z_686418fd/`, with mass balance,
capacity checks, nine-sheet Excel, CSVs, charts, HTML and hashes verified. It is
explicitly manufactured, not an EA forecast. Current-origin `@asof` queries are
bounded to prospective delivery only; actual read/fit/score gates stay locked.

Once the physical-design decision and compatible complete source/units/capacity
contracts are supplied, add that approved preparation path to
`forecast_inputs.prepare_current_inputs`, reuse existing aggregation/capacity
equations and validate current-origin development-window preferences before LP
construction. The workflow deliberately cannot promote today's partial vector
merely by changing a config flag. Historical walk-forward and prices remain out
of scope.
