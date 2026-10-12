# Input and data contract

## Milestone A operational contract

`config/run.yaml` references the canonical files and requests exact target months,
mode, origin and price-free baseline. `operational.prepare_run_inputs` separates
preparation from `operational.optimise` and `reporting.operational.report_run`.
The fresh-SID adapter is blocked by missing component mappings; the retained
`routing_inputs.prepare_inputs` is never called by the operational command.
`synthetic_demo` is explicitly manufactured, never a cached-input exception.

Preparation returns `months` (monthly PeriodIndex), `supply` (month × every source
node, bcm), `capacities` (month × every asset, bcm), daily/monthly capacity tables,
seven `preferences` summing to one, earlier `training_observations`, excluded
training months and source provenance. Missing, nonfinite, negative or mismatched
model inputs fail before LP construction. Single-month requests are compatible
with a future walk-forward adapter, but forecasts remain unsupported until the
complete existing origin-vintage validator can be satisfied.

`results.csv` is one target month with seven `*_volume_bcm` fields, exports,
unrouted/unclassified supply, pipeline supply and status. Network flow detail is
month × arc; comparison detail is month × original five-group definition. Missing
EA references/errors remain blank CSV numbers and visibly “Unavailable” in Excel.
Excel reports saved calculations; it does not implement an alternative model.
Provenance preserves exact model-ready inputs, source metadata, resolved settings,
solver results, code/configuration snapshots, hashes and Git identity.

## Direct SID sourcing

User instruction of 9 October 2026 supersedes the older cached-input commands:
query EA/Shooju directly each time input/reference data are consumed. Use exact
registered SIDs and explicit date bounds. Historical forecasts require an
origin-matched `@asof` query; historical actuals use the separately identified
historical segment, never future forecast values. Retain returned metadata,
queries, retrieval times, units and hashes. Workbooks may identify formulas and
SIDs but cannot supply numerical model inputs or comparison values. Do not fall
back to cached files when a SID is absent or an origin query is empty.

The legacy routing model and visual report readers still contain cached/workbook paths.
They are not approved for new data-consuming runs under this rule until their
adapters are migrated. Existing results/graphics remain historical evidence.
`project_data.get_registered_series(..., asof=...)` supports direct origin
retrieval; it does not approve metadata or bypass forecast/holdout validation.

The authorised 2025 Snøhvit sensitivity accepts an explicit diagnostic-only
monthly bcm override through `prepare_inputs(..., analysis_mode='snohvit_sensitivity',
diagnostic_scenario=..., diagnostic_snohvit_bcm=...)`. The only scenarios are
`official-net-production` and `selected-series-mixed-vintage`, restricted to all
twelve 2025 months with complete finite signed values. Official net gas is already
monthly bcm; the selected rate uses mcm/day × calendar days / 1,000 throughout.
The normal validated-input reader retains its July 2025 guard. This interface
does not change the active source registry, approve a baseline or bypass the
chronological policy. [Comparison and evidence](archive/20261009-13_snohvit-sensitivity/report.md).

Material methodology is in [DECISIONS.md](DECISIONS.md). The two canonical config
files define series metadata and model structure; no auxiliary configuration CSVs
are needed. Neither contains credentials. `KNOWN` means a series identifier is
known, not that observations, units or coverage have been verified. The audited
replacement uses `CONFIRMED`, `REVIEW` and `TODO`: confirmed means actual
observations support the stated role, review means material semantics/data issues
remain, and TODO means no SID is identified or retrieval failed. Legacy labels
remain loadable while the replacement is blocked by a Windows file-write denial.

## Registry and configuration

The existing registry column names are retained: `target_unit` is the intended
normalised unit, `source_frequency` describes retrieval frequency, `lifecycle`
describes historical/forecast provenance, `model_role` controls intended use and
`required_level` describes sourcing priority. `status`, `notes` and blank SIDs keep
unresolved inputs visible. `query_or_transform_hint` is evidence from the existing
scaffold, **not executable conversion logic**. SIDs are retained verbatim, including
the existing mixed `sid=` prefixes. The audit scripts call the established
`helper_functions_ea.ShoojuTools` retrieval methods; no new provider client is used.
`evidence/inputs/data_series_audit.csv` holds validation evidence, and unmodified
observations/metadata are retained under `data/raw/series_audit/`. The proposed
registry uses bare SID paths, which the helper converts to exact SID queries.

Additional nullable metadata: `history_required`, `forecast_required` (literal
`true`/`false`, or blank when unresolved), `raw_unit`, `input_semantics`, `asset`,
`display_source`, `economic_property`. Target units must not be mistaken for raw
provider units. Existing physical-exit conversions and the Dutch TSO hint require
verification before retrieval/calibration; no heating-value conversion is inferred.

`model.yaml` holds source-to-series mapping, junctions, assets, identified arcs,
markets, declared maintenance inputs, proposed/accepted transformation metadata,
reconciliation identities and unresolved solver/calibration controls. The loader
rejects duplicate YAML keys/CSV identifiers, unknown structural keys, bad references,
invalid controls, cycles, incompatible flow-expression units and benchmark leakage.
Null capacities and TODO series are loadable and reported separately by diagnostics.
Asset type `source_capacity` denotes source-group infrastructure, not a field limit.
`load_config(model_path, series_path)` returns `(model, series)`: the ordinary YAML
dictionary and a pandas metadata DataFrame indexed by `key`. Source definitions,
arcs, assets, markets and maintenance declarations remain directly accessible
dictionaries/lists, without conversion into domain classes.

`technical_capacity_mcm_d` replaces the scaffold's entirely null
`nominal_capacity_bcm_month`; no numerical values were changed or supplied. Other
unclassified `availability_*` inputs remain TODO with unresolved semantics. They
cannot be consumed by the maintenance-capacity utility until explicitly classified.

## Package time series

`data.time_series(key, values, unit, frequency)` returns an ordinary dictionary
with those four keys. `values` is a pandas Series. Monthly volumes
use `unit='bcm'`, `frequency='monthly'`, and a monthly `PeriodIndex`. This is the
representation of model `bcm/month`; it is a monthly volume, not a rate. Daily rates
use `unit='mcm_d'`, `frequency='daily'`, and timezone-free midnight calendar dates.
Timezones and source gas-day conventions must be resolved upstream rather than
silently normalised. Values must be finite, numeric and nonmissing; dates must be
unique. Transformations sort dates deterministically and require equal month sets.
They never fill gaps, use aggregate benchmarks as substitutes or repair negatives.

`read_parquet_series` reads exactly one `value` column with that date/month index;
the caller declares key, unit and frequency explicitly. Raw retrieval files may
retain provider metadata separately; this narrow reader is for normalised series.

Validation and copying happen explicitly in `time_series`, not in a class
constructor. Functions also accept manually created dictionaries with the same
four keys and check their observations at the calculation boundary.

`units.mcm_d_to_monthly_bcm` requires every calendar day of each supplied month,
including intervening months, and sums daily rates divided by the single central
conversion factor `MCM_PER_BCM`. Leap years are handled by the calendar. Partial
months and missing days fail; no assumption about missing maintenance being zero
is made. `maintenance.daily_maintenance_capacity` requires a known technical rate
and a signed daily maintenance adjustment, then returns daily and monthly
available capacity. The approved provisional convention is
`available_capacity = reference_capacity - maintenance`: negative maintenance
increases capacity above the reference baseline without clipping. Negative counts
remain diagnostic evidence. Missing baselines and negative resulting available
capacity fail; no baseline or physical maximum is inferred from maintenance.
Capacity results are `{"daily": series_dictionary, "monthly": series_dictionary}`. This is
capacity arithmetic only; it does not calculate flow or claim that a monthly
aggregate enforces constraints on every day of a subsequently optimised month.

## Physical observations and validation

The Stage 2 public-capacity database remains separate from active baseline limits.
`prepare_inputs` reads it only under explicit optional capacity-scenario selection;
no current public observation is optimiser-eligible. Its three ENTSOG
pilot series retain published technical kWh per source gas day, timezone-aware
06:00 CET/CEST intervals and original revision/provenance. Monthly energy totals
use gas-day start labels; these are not monthly bcm limits. Snapshot specifications
have unknown effective dates. Engineering availability, outage coverage and
compatible energy-to-volume factors remain unknown. Missing days are never filled;
commercial availability is a different category. Schema, rebuild commands and
integration requirements: [public database contract](evidence/inputs/public_capacity_database.md).

`data.derive_de_nl` implements the accepted identities in DECISIONS.md using
normalised monthly Emden, Dornum and Netherlands observations. Germany is never
an independently sourced calibration target. Any negative residual is flagged,
including small negatives; no positive analytical tolerance has been approved.
`reconcile_de_nl` checks every supplied DE/NL target against the input identities.

`derive_other_destinations` takes Easington, SEGAL, an **already resolved** St Fergus
observation, Nybro, Zeebrugge and Dunkerque. The scaffold's addition of St Fergus A
and B is retained as `decision_required` config evidence and is not implemented.
No generic config-expression executor exists. `reconcile_destinations` compares all
six destination totals with the eight distinct physical exit observations. Both
reconciliation helpers require a caller-supplied nonnegative `tolerance_bcm`; the
production control remains null pending modeller approval.

The Kollsnes registry entry and `maintenance_inputs.KOLLSNES_PROCESSING` capture the
accepted provisional metadata in DECISIONS.md. Use `capacity_for_asset` with a
config returned by `load_config`: maintenance semantics are checked once while
loading, and the calculation checks the asset is active and the series matches.
Historic Kollsnes maintenance coverage is not claimed by the forecast series.

Config formula validation supports only flat sums and differences of named series,
as used in the canonical YAML. It does not parse general Python expressions or
execute formulas.


## Dashboard reference candidates

Ten optional REVIEW rows added on 8 October 2026 retain sourcing evidence from
`gas_python_dash`: alternative Norway production_total, Reuters day-ahead hub
prices, and historical TTF/THE/PEG/NBP settlement curves. These are unmapped
reference candidates, not selected model prices or a replacement production total.
For the four curve rows, `sid` holds a contract-object identifier: use the
`contract_obj.id` query in `query_or_transform_hint`, requesting
`contract_obj.contract_date`. Point date is market date; the metadata date is
delivery date. Generic exact-SID retrieval is unsuitable. Price raw units are
dashboard-code evidence pending live validation; NBP needs dated FX conversion.
The prior audit/proposal files do not establish validation of these additions.
