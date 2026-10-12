# Minimal routing config

This folder has two canonical configuration files.

1. `data_series.csv` - the only sourcing registry. Fill SIDs/status for raw production, physical exits, prices and maintenance/availability series here. Rows marked `TODO` are the data-sourcing queue.
2. `model.yaml` - the model definition. It contains source aggregation, junctions, assets, arcs, markets, derived-series formulae, reconciliation rules, solver controls and calibration settings.

The `poc` section is the executable seven-destination historical network. Its
provisional sourced capacities, nodes/arcs and 2023/2024 baseline/run windows are
separate from the retained six-market foundation above it. The driver exports
the actual LP network to `outputs/reconstruction/provenance/network_definition.yaml`; that file is
generated evidence, not a third canonical configuration. Plots use exactly the
same definitions. Optional `technical_series_file` on a POC asset accepts a
repository-local CSV with `date,technical_capacity_mcm_d`; it is forward-filled
on calendar days without backward filling. Maintenance must remain complete.

Do not maintain separate node, arc, asset, market, field-mapping, derived-series or sourcing-checklist CSVs. Those should be generated from these two files if a tabular view is needed.

Input semantics are defined in [INPUTS.md](../INPUTS.md); accepted methodology,
including Germany's derived historical target, is in [DECISIONS.md](../DECISIONS.md).

## Recommended workflow

Edit raw-series metadata in `data_series.csv` and structure/static capacities in
`model.yaml`. Fill technical capacities only when sourced or approved. Schema
validation permits explicit TODO/null inputs and reports them via package
diagnostics; it does not supply defaults. Query hints and decision-required
formulae are retained evidence, not executable transformations.

## Project labels

`key` is the unique, readable lowercase ASCII `snake_case` identifier used by
both the model and analysts. The former `custom_id` values are now these keys;
the duplicate column has been removed.
Use the entity first, then the measure, with frequency, provider, price unit or
source variant where needed to distinguish separate series. For example,
`nyhamna_maint_d`, `troll_prod`, and
`nbp_forecast_eur`.

`custom_description` briefly describes what the data is in a natural sentence.
`description` remains the existing source/intended description;
`notes` holds caveats, model-use guidance, detailed evidence and unresolved issues. Labels do not override
REVIEW/TODO status or establish that two similarly named SIDs can be combined.
Legacy compact, underscore and Norwegian naming variants remain distinct.

Keep keys to entity + measure: `troll_prod`, `emden_flow`, `nyhamna_avail_cap`
and `de_flow_qa`. `prod` means production, `maint` maintenance, `avail_cap`
available capacity and `qa` benchmark-only. Maintenance suffixes `_d`/`_m`
distinguish daily/monthly series; `_adj` means the source's adjusted variant.
Keep `_upstream` separate from ordinary plant maintenance. `_compact`, `_snake`
and `_native` identify original SID spelling variants, not chronological versions.
Transport-point names retain point/direction, e.g. `emden_ept1_in_tech_cap`
(firm technical capacity) versus `emden_ept1_in_flow`. Units/provider details
stay in metadata. `evidence/inputs/series_key_shortening.csv` retains prior names;
the main historical-key crosswalk now points directly to current keys.

`sid` remains the provider identifier. To look up a SID after loading the config:

```python
sid = series.loc["nyhamna_maint_d", "sid"]
```

Fill `key` and `custom_description` for every new row. The loader rejects missing
descriptions, duplicate keys, Python keywords and invalid identifiers.
Historical audit identifiers are linked through
`evidence/inputs/series_key_migration.csv`; retained observations are unchanged.

## Sorting metadata and column order

Columns start with `key`, `sid`, descriptions and sorting labels. Status, model
role and units follow; technical retrieval details come later and `notes` is last.

- `country` / `country_iso`: series scope for sorting, using ISO alpha-2 codes
  (`GB` for the UK). Multiple countries use semicolons. Terminals use receiving
  countries; Dutch ENTSOG rows use the GTS reporting scope. Blank means no single
  country is established, or country is not applicable (calendar/corridor).
- `balance_item`: descriptive production, domestic consumption, LNG exports,
  pipeline imports or pipeline exports. Other measures are `not_applicable`.
  These labels do not define a model balance or approve series reconciliation.
- `data_item`: the reported measure, such as gas production, gas price,
  maintenance, available capacity or firm technical capacity.
- `asset_type`: field, plant, terminal, pipeline, transport point, aggregate,
  upstream group, field/site, price hub or calendar; uncertain field/site scope
  stays explicit.
- `market_area`: identified price hub (NBP, TTF, THE, ZTP, PEG, ETF); blank for
  non-price rows or unselected benchmarks. This does not select a commercial proxy.
- `price_type`: forecast, forward curve, contract history, futures index
  or day-ahead quote/last trade; blank for non-price rows.

`notes` contains brief actionable caveats. Full pre-shortening notes remain in
`evidence/inputs/data_series_notes_detail.csv`, keyed by the current registry key.
Audit observations and source evidence remain in their existing locations.
`project_data.select_series()` accepts these sorting filters, including matching
one country within a semicolon-separated country group.

For the five selected dashboard hubs, `markets.*.price_series` now references
the historical Reuters day-ahead series; `forecast_price_series` retains the
separate EA monthly forecast. Neither field implements price aggregation or
conversion. NBP is raw pence/therm and still needs dated FX/energy conversion.
Denmark remains unresolved. Selection does not promote an unaudited SID to CONFIRMED.

Price keys omit redundant gas/price/unit/frequency wording. Use `ttf_day_ahead`
for the selected dashboard quote, `the_forecast` for the EA forecast,
`ttf_eex_curve` / `ttf_eex_last` / `ttf_eex_egix` for distinct EEX measures,
and `nbp_futures_settle` for contract settlement history. `nbp_forecast_eur`
distinguishes the EUR variant from native `nbp_forecast`; `ttf_forecast_interface`
distinguishes the separate forecaster series. Full definitions remain in metadata.
`evidence/inputs/price_key_migration.csv` maps previous price names; the main key
crosswalk and detailed-note keys also point to the current names.
