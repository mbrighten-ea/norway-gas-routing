# Optional empirical routing incentive — completed 2024 experiment

The user explicitly approved extending frozen 2024 supply, maintenance and fixed
preferences to this offline price experiment, with the empirical conventions
below. That approval does not extend to operational forecasting or origin-matched
validation. Normal fresh-SID requirements remain; all price/FX values were queried
afresh within 2024 bounds. [Report, charts and CSVs](../../archive/20261012-04_price-response/report.html).

The unchanged Stage 1 minimises disposal/maximises exports. Optional Stage 2 is:

`minimise L1 allocation deviation (bcm) - lambda × sum(destination bcm × spread / 10 EUR/MWh)`.

Stage 3 minimises worst fractional share shortfall while preserving both Stage 1
and the combined Stage 2 optimum. It does not fix the old price-free L1 optimum.
At lambda zero the original objective/constraint path is followed exactly.
The default remains zero with no required price data.

The illustrative grid is zero/low/medium/high = 0/0.25/1/4, with fixed
10 EUR/MWh scaling. These parameters are not fitted or approved operational
coefficients. Synthetic feature shocks are -20/+20 EUR/MWh to UK, France or the
shared DE/NL pool. The equal DE/NL coefficient prevents separate within-pool
price incentives. BE/DK/PL are price-neutral but may move indirectly when priced
routes change. No commercial flexibility fraction or hard contracts are inferred.

Historical features query registered Reuters NBP, PEG and TTF afresh,
restricted to 2024. NBP converts pence/therm to EUR/MWh using same-date ECB
GBP per EUR and 0.0293071 MWh/therm. Monthly features use common observed quote
dates, arithmetic means, no missing-value fill and no delivery-day weighting.
TTF is an approved experimental proxy for the entire DE/NL pool. Quote-date/product,
FX timing and sparse PEG coverage remain qualifications. Fresh metadata confirms
price units and actual lifecycle; ECB SID metadata does not declare its FX unit.
The [ECB base-currency convention](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
and [UK energy-unit guidance](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/829953/BEIS_OPRED_Offshore_ESOS_Phase_2_Guidance_September_2019.pdf)
support direction and therm scaling. This is an empirical allocation preference,
not revenue, a netback, validated trade economics or an origin-matched forecast.

`scripts/run/run_price_response.py` requires a separate explicit frozen-2024
price exception and authorisation reference. It checks the retained capacity
comparison's input/config hashes, compares each zero solve to its corresponding
price-free 143/156 result within 1e-9 bcm, checks Stage 1/combined Stage 2 optima
and mass balance, and writes monthly allocations, capacity/price deltas, annual
tables, arc flows, constraints, fresh price responses and provenance.
`reporting.price_response.retain_price_report` renders charts and retains a new
milestone. Both paths were executed; common matched quote coverage is 224 dates,
with 14–23 dates per month. Historical freeze identities and returned values,
units, source metadata, methods, code hashes and approvals are retained.

Validation: 209 relevant tests passed. Positive/negative shocks move synthetic
allocations, larger strength increases the incentive score, zero reproduces
both synthetic capacity cases, and all physical/shared limits remain enforced.
Other tests cover common-date conversion, missing/nonfinite/duplicate quotes,
holdout rejection, and preserved 2025 source guards.

## Findings and attribution

All 672 monthly combinations passed. Zero reproduces corresponding retained
143/156 price-free capacity allocations within 4.97e-12 bcm. The independent
objective check recomputes L1 minus incentive from solved destination volumes;
Stage 1 exports and the combined Stage 2 optimum remain fixed within tolerance.

At 143, annual observed-price shifts are UK +0.94243654, FR -1.35565163 and
Belgium +0.41321509 bcm. At assumed 156, UK +0.59772418 and FR -0.59772418 bcm;
other pool/neutral totals are unchanged within precision. Pooled monthly gross
reallocation summed across the year is 2.831536/2.268630 bcm. Net annual shifts
can be smaller because monthly shifts offset. Exports remain 117.0831345 and
119.377524 bcm: the 2.2943895 bcm export gain comes entirely from capacity,
not prices. CSVs separate capacity-only shifts and additional price/capacity
interaction at the same feature/strength, plus 20-EUR/MWh shock differences.

For observed spreads, low/medium/high pooled responses coincide. Any positive
weight can resolve L1 ties; these are stepwise LP responses, not smooth fitted
elasticities. Within-DE/NL changes are not separately identified by prices and
must not be attributed to a German-versus-Dutch spread. Pooled reallocation
excludes that internal contribution; seven-country shifts remain in the CSVs.
At high response, a synthetic UK +20 EUR/MWh feature shock shifts approximately
13.58/11.46 bcm toward UK at 143/156; France and shared-pool shocks also respond
until route limits bind. These are stress tests, not plausible commercial bounds.

With observed prices, Kollsnes binds eleven months at 143 and none at 156.
Europipe I, Norpipe, Zeepipe export and Zeepipe IIB bind all twelve months;
Europipe II binds five, France's corridor four, and Langeled south one/two.
Kårstø processing is not binding in these cases. Price-neutral destinations
can move indirectly, so missing commercial boundaries still limit interpretation.

Next: review tie sensitivity, calibration methodology and physical/commercial
definitions before separately approving further experiments. No automatic fitting.
Kollsnes 156 remains hypothetical. Kollsnes dry/maintenance compatibility,
Kårstø rich/dry equivalence, UK route limits, and collapsed DE/NL boundaries
remain physical limitations. No default capacity or source configuration changed.
