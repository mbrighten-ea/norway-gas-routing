# Coded-model input gaps - 8 October 2026

Scope: this repository and targeted read-only helper_functions retrieval/discovery examples, plus narrow public research on official capacity/asset sources under the updated boundaries. Targeted live SID discovery/samples permitted in this follow-up; no additional EA repositories, internal reports/knowledge systems, configuration changes or commercial assumptions. Canonical config and proposed registry are distinguished; legacy KNOWN does not override the retained audit.

Current code loads and validates the network, converts complete daily capacity to monthly bcm, applies signed Kollsnes maintenance, and derives/reconciles monthly destination flows. It does not implement an optimiser, source aggregation/residual decomposition, availability/fraction ingestion, calibrated routing shares, or a commercial price/netback objective. Schema validity is not operational readiness.

## Every canonical registry requirement

The table below preserves the pre-population 64-key audit baseline. The canonical registry was subsequently populated on 8 October 2026 with 191 rows (99 CONFIRMED / 77 REVIEW / 15 TODO), including retained reference candidates and known price SIDs. Current metadata/statuses are in config/data_series.csv; remaining scope and methodology gaps below still apply. Earlier canonical/proposal counts and write-block statements describe the prior snapshot.

Layers: PHYSICAL = current capacity utilities / planned physical solver; CALIBRATION = historical flow targets/backtesting; COMMERCIAL = planned price objective; QA/SCOPE = reconciliation or inactive supply; NONE = optional or unreferenced by the coded network.

| Key | Coded use | Canonical / audit status | Blocked layer | Exact gap or evidence |
|---|---|---|---|---|
| production_troll | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_oseberg | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. 4 negative production observations require treatment; align_monthly rejects negatives. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_non_flexible | QA / inactive full-supply scope | KNOWN / REVIEW | QA/SCOPE; future full-supply PHYSICAL | Assigned only to inactive OTHER_RESIDUAL. No residual exclusion calculation; overlaps named fields, LNG/domestic allocations must be resolved before activation. |
| production_total_no | QA / inactive full-supply scope | KNOWN / REVIEW | QA/SCOPE; future full-supply PHYSICAL | QA total equals Troll + Oseberg + non-flexible; never add to component supply. Source-vintage changes established; metadata identity remains REVIEW. |
| production_aasta_hansteen | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_asgard | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_gina_krog | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. 1 negative production observations require treatment; align_monthly rejects negatives. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_gullfaks_sor | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_heidrun | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_kristin | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_kvitebjorn | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_martin_linge | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_norne | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_ormen_lange | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_skarv | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_sleipner | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_visund | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_dvalin | Active source supply | KNOWN / REVIEW | PHYSICAL; CALIBRATION | Retrieved monthly bcm; forward coverage through Dec 2030 measured. Generic UK-supply description conflicts with field/client production identity; still REVIEW. Raw monthly DatetimeIndex needs an explicit monthly PeriodIndex for existing data utilities. |
| production_snohvit | QA / inactive full-supply scope | TODO / TODO; proposal REVIEW | QA/SCOPE; future full-supply PHYSICAL | Canonical SID blank; proposal candidate REVIEW. Historical monthly-average mcm/d and official negative net-gas accounting established; 2022 exclusion formula verified; mixed vintages established. Transformation/forecast source issues remain; not a routed source. |
| norway_domestic_gas_use | QA / inactive full-supply scope | TODO / TODO | QA/SCOPE; future full-supply PHYSICAL | No domestic-use SID; conditional scope adjustment, not an active input. Inclusion in production inputs remains unresolved. |
| exit_zeebrugge | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. |
| exit_dunkerque | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. |
| exit_emden | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. |
| exit_dornum | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. |
| exit_easington | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. |
| exit_segal | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. |
| exit_st_fergus_a | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. 47 shared days; sum/stitch unapproved. Existing destination function expects one resolved St Fergus input. |
| exit_st_fergus_b | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. 47 shared days; sum/stitch unapproved. Existing destination function expects one resolved St Fergus input. |
| exit_nybro | Destination calibration / QA | KNOWN / REVIEW | CALIBRATION | Retrieved mixed intraday values; physical versus nomination, rate/volume, gas-day assignment and monthly bcm aggregation unresolved. |
| country_nl_tso_actual | Destination calibration / QA | KNOWN / TODO; proposal REVIEW | CALIBRATION | Canonical triple-space SID failed. Proposal has retrieved single-space EPT1 SID (REVIEW); gross calorific conversion, reference conditions and period alignment unresolved. 0.095 is diagnostic only. |
| benchmark_uk_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_fr_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_be_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_fr_be_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_nl_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_de_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_nl_de_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_pl_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_total_forecast | Optional benchmark only | KNOWN / CONFIRMED | NONE | Confirmed retrieved monthly benchmark; not an independent physical calibration target or source input. |
| benchmark_dk_forecast | Optional benchmark only | KNOWN / REVIEW | NONE | DK benchmark has 6 negatives; REVIEW. Optional QA only; not a solver/calibration dependency. |
| calendar_days_per_month | Optional calendar reference | KNOWN / CONFIRMED | NONE | Confirmed calendar SID; existing conversion computes days/completeness from timestamps, so this SID is not necessary to execute it. |
| price_uk | Six-market price definition | TODO / TODO | COMMERCIAL | Candidates retrieved below; canonical SID remains blank. THE/Denmark long-term forecast and benchmark/valuation choices remain unresolved. |
| price_de | Six-market price definition | TODO / TODO | COMMERCIAL | Candidates retrieved below; canonical SID remains blank. THE/Denmark long-term forecast and benchmark/valuation choices remain unresolved. |
| price_nl | Six-market price definition | TODO / TODO | COMMERCIAL | Candidates retrieved below; canonical SID remains blank. THE/Denmark long-term forecast and benchmark/valuation choices remain unresolved. |
| price_dk | Six-market price definition | TODO / TODO | COMMERCIAL | Candidates retrieved below; canonical SID remains blank. THE/Denmark long-term forecast and benchmark/valuation choices remain unresolved. |
| price_be | Six-market price definition | TODO / TODO | COMMERCIAL | Candidates retrieved below; canonical SID remains blank. THE/Denmark long-term forecast and benchmark/valuation choices remain unresolved. |
| price_fr | Six-market price definition | TODO / TODO | COMMERCIAL | Candidates retrieved below; canonical SID remains blank. THE/Denmark long-term forecast and benchmark/valuation choices remain unresolved. |
| maintenance_kollsnes | Active asset constraint | KNOWN / CONFIRMED | PHYSICAL | Confirmed daily signed processing maintenance and forecast coverage; reference baseline absent, so capacity_for_asset fails. Negatives approved; no clipping. |
| availability_nyhamna | Active asset constraint | TODO / TODO | PHYSICAL | Conditionally redundant raw availability SID: audited daily NO_maintenance_Nyhamna can provide signed derate; confirm reference baseline and plant-only scope before mapping. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_karsto | Active asset constraint | TODO / TODO | PHYSICAL | Conditionally redundant raw availability SID: audited daily NO_maintenance_Karsto exists; rich/dry reference and shared plant scope remain unresolved. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_ogt | Active asset constraint | TODO / TODO | PHYSICAL | Genuine missing corridor outage evidence. Oseberg/Heimdal field or site maintenance is validation-only; not established as OGT pipe derate. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_langeled_south | Active asset constraint | TODO / TODO | PHYSICAL | Easington daily maintenance is validation-only landing evidence; full southern-pipeline scope/reference not established. Route availability remains REVIEW. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_vesterled | Active asset constraint | TODO / TODO | PHYSICAL | St_Fergus daily maintenance is validation-only terminal evidence; do not combine SEGAL or infer full Vesterled pipe outage. Route availability remains REVIEW. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_europipe_i | Active asset constraint | TODO / TODO | PHYSICAL | Genuine missing corridor outage evidence. Emden/Dornum terminal maintenance does not identify this pipeline separately. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_europipe_ii | Active asset constraint | TODO / TODO | PHYSICAL | Genuine missing shared-corridor outage evidence. Dornum site maintenance does not separately measure the upstream corridor or Danish branch. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_norpipe | Active asset constraint | TODO / TODO | PHYSICAL | Genuine missing corridor outage evidence. Emden terminal/Ekofisk field maintenance is validation-only, not a proven Norpipe derate. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_zeepipe_export | Active asset constraint | TODO / TODO | PHYSICAL | Zeebrugge daily maintenance is validation-only receiving-terminal evidence; export pipe outage/reference not established. Route availability remains REVIEW. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_franpipe | Active asset constraint | TODO / TODO | PHYSICAL | Dunkerque daily maintenance is validation-only terminal evidence; full Franpipe pipe outage/reference not established. Route availability remains REVIEW. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_nybro_exit | Active asset constraint | TODO / TODO | PHYSICAL | Conditionally redundant raw availability SID: daily NO_maintenance_Nybro exists; establish North Sea Entry rather than combined Nybro scope and reference conditions first. Code currently ingests maintenance only for Kollsnes; no mapping changed. |
| availability_emden_receiving | Inactive EMDEN_RECEIVING | TODO / TODO | NONE | No SID; asset inactive and absent from all arcs. Not an active solver input. |
| availability_dornum_receiving | Registry only | TODO / TODO | NONE | Not required by an active source, asset or destination calculation. |
| availability_langeled_north | Registry only | TODO / TODO | NONE | Not required by an active source, asset or destination calculation. |
| availability_zeepipe_iia_iib | Registry only | TODO / TODO | NONE | Not required by an active source, asset or destination calculation. |
| availability_statpipe_core | Registry only | TODO / TODO | NONE | Not required by an active source, asset or destination calculation. |

Canonical 64-row audit mapping: {'REVIEW': 28, 'TODO': 25, 'CONFIRMED': 11}. Reviewed proposal: 24 CONFIRMED / 36 REVIEW / 23 TODO; it includes reference-only additions and is not the canonical file. No write/lock retry was needed for this analysis.

## Technical capacities of the actual assets

All 15 configured technical_capacity_mcm_d values are null. Public candidates below now establish published technical/transport facts; none is an approved model maintenance reference or configured baseline. Observed maxima, maintenance adjustments, booked rights and available capacity were not substituted for technical capacity.

| Asset | Active arcs | Active? | Dynamic input | Local technical-capacity evidence / consequence |
|---|---|---|---|---|
| NYHAMNA_INJECTION | NYHAMNA_CORE | True | availability_nyhamna | Published candidate remains unapproved; dynamic scope assessed below. |
| KOLLSNES_INJECTION | KOLLSNES_CORE | True | maintenance_kollsnes | Missing reference baseline blocks the implemented signed-maintenance utility; derate SID confirmed. |
| KARSTO_INJECTION | KARSTO_CORE | True | availability_karsto | Published candidate remains unapproved; dynamic scope assessed below. |
| OGT | OSEBERG_CORE | True | availability_ogt | Published candidate remains unapproved; dynamic scope assessed below. |
| VESTERLED | OSEBERG_VESTERLED_UK | True | availability_vesterled | Published candidate remains unapproved; dynamic scope assessed below. |
| LANGELED_SOUTH | CORE_LANGELED_UK | True | availability_langeled_south | Published candidate remains unapproved; dynamic scope assessed below. |
| EUROPIPE_I | CORE_EUROPIPE_I_EMDEN | True | availability_europipe_i | Published candidate remains unapproved; dynamic scope assessed below. |
| NORPIPE | CORE_NORPIPE_EMDEN | True | availability_norpipe | Published candidate remains unapproved; dynamic scope assessed below. |
| EUROPIPE_II | KARSTO_EUROPIPE_II | True | availability_europipe_ii | Published candidate remains unapproved; dynamic scope assessed below. |
| NYBRO_EXIT | EUROPIPE_II_DENMARK | True | availability_nybro_exit | Published candidate remains unapproved; dynamic scope assessed below. |
| ZEEPIPE_EXPORT | CORE_ZEEPIPE_BELGIUM | True | availability_zeepipe_export | Published candidate remains unapproved; dynamic scope assessed below. |
| FRANPIPE | CORE_FRANPIPE_FRANCE | True | availability_franpipe | Published candidate remains unapproved; dynamic scope assessed below. |
| EMDEN_RECEIVING | None | False | availability_emden_receiving | Inactive, not an active solver blocker; no sourced baseline. |
| UK_DIRECT_ROUTE | UK_DIRECT_UK | True | None | No baseline or dynamic series; direct-route constraint treatment is REVIEW, not automatically unlimited. |
| DE_DIRECT_ROUTE | None | False | None | Inactive, not an active solver blocker; no sourced baseline. |

CORE intentionally has no aggregate capacity; no additional core baseline is missing. The EUROPIPE_II asset is shared by the upstream corridor before the Germany/Denmark split; it must not be duplicated into two independent full-capacity branches. NYBRO_EXIT is separate. EMDEN_RECEIVING is inactive and unused by arcs.

The four Emden firm technical identifiers below now have retained metadata and three eight-day samples (January 2025, September 2026, December 2030). They concern GTS transport-point rights and directions, not proven Norwegian pipeline or receiving-plant nameplate capacity:

- `ENTSOG\transport_point\NL-TSO-0001\Emden (NPT) (GTS)\exit\Firm Technical`
- `ENTSOG\transport_point\NL-TSO-0001\Emden (NPT) (GTS)\entry\Firm Technical`
- `ENTSOG\transport_point\NL-TSO-0001\Emden (EPT1) (GTS)\entry\Firm Technical`
- `ENTSOG\transport_point\NL-TSO-0001\Emden (EPT1) (GTS)\exit\Firm Technical`

Firm Available and Firm Booked identifiers at these points are also retained: available rights and bookings are distinct from Firm Technical. Interruptible Total/Available/Booked are separate products. None establishes a mcm/d nameplate baseline. NL underground/LNG storage-capacity identifiers are outside the coded network and were excluded.

## Availability versus existing maintenance: all 11 active requirements

There is no requirement for an independent raw availability SID if a matching daily signed maintenance derate and approved reference already determine the same constraint. For Nyhamna, Karsto and Nybro, an additional availability representation is conditionally redundant; it is not another subtraction or independent validation target. Eight corridor requirements remain unresolved: four have no matching corridor evidence (OGT, Europipe I, Europipe II, Norpipe); four have landing-terminal maintenance leads only (Langeled South, Vesterled, Zeepipe export, Franpipe). Landing-series use could avoid another SID only after the full-route scope is established; terminal and pipe derates must not be added blindly.

All relevant retained daily maintenance series span 2021-01-01 to 2030-12-31 in mcm_d with audited daily spacing; they are reference-only except approved Kollsnes. Prefix: `teams\natural_gas\EUR\daily_NO\NO_maintenance_`. Exact suffixes: Nyhamna, Karsto, Nybro, Easington, St_Fergus, Zeebrugge, Dunkerque, Emden, Dornum, Oseberg, Heimdal, Sleipner. Scope in the retained description is the named site only. Oseberg/Heimdal/Sleipner and all upstream/field maintenance remain QA/reference, avoiding double counting exogenous production outages. Pre-opening zero Nybro adjustments do not prove physical availability before 2022. Existing signed negative diagnostics and available = reference - maintenance remain unchanged.

Registry-only Langeled North, Zeepipe IIA/IIB, Statpipe core and Dornum receiving availability, plus inactive Emden receiving availability, are not current coded input requirements. This does not establish that those physical facilities never constrain the real network.

### Capacity-to-arc scope checks

- OGT's physical Oseberg-to-Heimdal-bypass segment precedes both the Vesterled and Statpipe/core branches. Coded OGT constrains OSEBERG_CORE only; UK bypasses it. The 35.0 candidate therefore does not establish correct shared enforcement without a modeller decision.
- Karsto processing is upstream of both Statpipe/core and Europipe II. Coded KARSTO_INJECTION constrains KARSTO_CORE only; KARSTO_EUROPIPE_II bypasses it. Do not silently apply a plant number to the core branch or introduce a shared constraint.
- Europipe II is correctly represented as one upstream asset before Germany/Denmark split. Its 73.5 cannot be granted independently to both destinations. North Sea Entry is an additional branch constraint, not a second independent supply.
- Other corridor endpoints match the collapsed CORE/landing arcs, subject to the model's existing collapse. Norpipe originates at Ekofisk rather than CORE; Zeepipe's 42.2 is the export leg, not internal 55.0; Langeled South's 73.8 is not North's 74.7. Do not import internal transfer capacities as extra constraints during sourcing.
- Eight Gassco values are explicit MSm3/d transport capacities as of 2024, not available/booked or observed maxima. Exact change dates, hydraulic conditions and validity through 2030 are not documented by the map; retain REVIEW for configuration application.
- Nyhamna's 84 plant export capacity and 2024 Langeled North 74.7 are different asset/reference facts. Do not select a minimum or overwrite the existing injection definition during this pass.

### Emden GTS small-sample results

All four candidates retrieve successfully: unit kWh_d (source kWh/d), metadata actual/daily, one observation per day in each of three inclusive eight-day windows. EPT1 entry is 963,600,000 kWh/day in January 2025 and September 2026, and 878,400,000 in December 2030. EPT1 exit, NPT entry and NPT exit are zero in all sampled windows. Zero technical capacity in these samples is not proof of permanent absence of a physical connection. Source point keys are ITP-00160/EPT1 and ITP-00161/NPT; directions are from GTS's perspective. Generic economic_property=exports is misleading for entry: source_obj.directionkey is the relevant direction.

GTS explicitly identifies interdependence of free capacity at Emden EPT/NPT; do not sum them. EPT1 entry is relevant to the Dutch allocation branch and is distinct from Norwegian corridor/Emden receiving nameplate; the current Dutch arc has no capacity asset. EPT1 exit is reverse direction. No automatic sum of NPT/EPT1, no conversion to mcm/d without matching calorific/reference conditions, and no new Dutch branch constraint. Firm Technical is the maximum firm transport product, distinct from Firm Available and Firm Booked; neither scope nor guaranteed future availability follows from its distant dates. Samples retained under sourcing_followup; full capacity history was not audited.

## Public capacity candidates - researched 8 October 2026

These are published asset-capacity candidates, not approved config values. Source date/as-of scope is distinct from exact commissioning/effective date; no constant capacity history through 2030 has been inferred. All technical_capacity_mcm_d fields remain null.

| Coded asset | Published value and unit | Definition / asset match | Source vintage / effective-date limit | Model-use status |
|---|---|---|---|---|
| OGT | 35.0 MSm3/d | Oseberg to Heimdal Bypass; reported pipeline transport capacity | Gassco system at 2024; exact change date absent | REVIEW: strong mapped candidate; application period/technical definition to approve |
| VESTERLED | 35.0 MSm3/d | Heimdal Bypass to St Fergus; pipeline transport capacity | System at 2024; exact change date absent | REVIEW: mapped candidate |
| LANGELED_SOUTH | 73.8 MSm3/d | Sleipner to Easington; southern segment only | System at 2024; exact change date absent | REVIEW: mapped candidate; not whole Langeled or North capacity |
| EUROPIPE_I | 48.0 MSm3/d | Map calls it Europipe, Draupner E to Dornum/Emden | System at 2024; exact change date absent | REVIEW: mapped candidate; undated older interactive map says 45.7 with incomplete unit wording |
| NORPIPE | 34.0 MSm3/d | Ekofisk to Emden; pipeline transport capacity | System at 2024; exact change date absent | REVIEW: mapped candidate |
| EUROPIPE_II | 73.5 MSm3/d | Karsto to Dornum; shared upstream corridor | System at 2024; exact change date absent | REVIEW: not an additional independent full capacity on each split branch |
| ZEEPIPE_EXPORT | 42.2 MSm3/d | Sleipner to Zeebrugge export segment | System at 2024; exact change date absent | REVIEW: internal Sleipner-Draupner Zeepipe segment has a different 55.0 value and is not this asset |
| FRANPIPE | 54.2 MSm3/d | Draupner E to Dunkerque; pipeline transport capacity | System at 2024; exact change date absent | REVIEW: mapped candidate |
| KOLLSNES_INJECTION | 156 million Sm3/day; conflicting 143 on same Gassco page | Current processing-capacity facts table; Equinor confirms upgrade from 144.5 to 156 | Equinor publication 6 Jan 2025 describes contribution to 2024 record; exact upgrade date absent | REVIEW: current 156 corroborated, 143 site text conflicts; official Norskpetroleum distinguishes older 146.5 rich-gas processing from 143 dry-gas export; 156 processing cannot automatically be equated to dry-gas injection; maintenance reference baseline not established by nameplate alone |
| NYHAMNA_INJECTION | 84 million Sm3/day | Plant export capacity after expansion | Gassco report 1 Oct 2017 says already 84; corroborated current page, accessed 8 Oct 2026; exact upgrade day not supplied | REVIEW: strong plant candidate, maintenance reference/time history not approved; distinct from Langeled North 74.7 |
| KARSTO_INJECTION | Around 95 million Sm3 rich gas/day; Equinor current prose says around 98 million Sm3 without denominator | Official Norskpetroleum explicitly verifies daily rich-gas processing; not dry-gas export | Undated current official page accessed 8 Oct 2026; Equinor expansion report 29 Sep 2005 establishes historical 88 million Sm3/day | REVIEW: current 95 versus 98 not resolved; rich/dry boundary and reference baseline unapproved |
| NYBRO_EXIT | 27.4 mcm/day in technical N-1 tables; 27 rounded in prose; annual 10,387 mcm differs | North Sea Entry Norwegian branch, part of combined Nybro entry; not Denmark-only consumption | Danish Energy Agency plan dated 28 Feb 2025 covers 2023-2027; full commissioning 1 Dec 2022; Energinet 2020 expected 13,400 MWh/hour from Oct 2022 | REVIEW: technical definition now explicit; normal/standard conditions, numerical reference differences and transit scope remain unresolved |
| UK_DIRECT_ROUTE | None identified | Aggregated direct UK route, not one independently defined public asset | No dated mapped baseline | REVIEW: baseline/constraint treatment unresolved |
| EMDEN_RECEIVING | None identified | Inactive; GTS Firm Technical catalogue entries are transport rights, not proven receiving-plant nameplate | Daily kWh/d samples now retained; directions and product distinct from receiving plant | Not an active blocker |
| DE_DIRECT_ROUTE | None identified | Inactive conceptual route | No dated mapped baseline | Not an active blocker |

Sources (all accessed 8 October 2026):

- [Gassco transport system at 2024](https://gassco.eu/wp-content/uploads/2024/12/Det-norske-gasstransportsystemet-2024.pdf): dated 2024 map, table explicitly in MSm3/d; pipeline endpoints and reported capacity, not measured historical maxima, outage-adjusted capacity or bookings. Exact hydraulic/reference conditions and capacity-change dates are not specified.
- [Gassco older Europipe interactive page](https://map.gassco.eu/rorledninger/europipe): 45.7 ?mill?, undated/incomplete unit wording; not preferred over the dated table.
- [Gassco Kollsnes](https://gassco.eu/prosessanlegg/kollsnes/): body 143 MSm3/day versus facts table 156 million Sm3/day.
- [Equinor, 6 January 2025](https://www.equinor.com/news/20250106-troll-highest-natural-gas-production-ever): Kollsnes processing upgrade 144.5 to 156 million Sm3/day, contributing to 2024 production record.
- [Gassco Nyhamna](https://gassco.eu/prosessanlegg/nyhamna/): explicitly 84 million standard m3/day export capacity.
- [Equinor Karsto](https://www.equinor.com/energy/karsto): around 98 million standard m3 rich-gas receive/process capacity; does not state a time denominator in that sentence. [Gassco Karsto](https://gassco.eu/prosessanlegg/karsto/) distinguishes incoming rich gas and outgoing dry gas; its capacity table is liquids in tonnes/hour, not a dry-gas mcm/day baseline.
- [Energinet Security of Gas Supply 2022](https://en.energinet.dk/media/u1qnouel/gasredegoerelse-22-engelsk.pdf): winter scenario box gives EP II import up to 27.4 million Nm3/day; document also has a separate 32.4 million Nm3/day Nybro receiving-terminal total linked to domestic offshore production. That total is not the Norwegian-import branch baseline. Forecasted booked capacity in tariff projections is not nameplate and was excluded.

New targeted primary evidence (all accessed 8 October 2026):

- [Gassco Nyhamna, 1 October 2017](https://gassco.eu/nyhamna-styrker-norges-posisjon-som-gasseksportor/) establishes 84 million Sm3/day export capacity already after expansion, rather than an undated first assertion.
- [Official Norskpetroleum land facilities](https://www.norskpetroleum.no/produksjon-og-eksport/landanlegg/) establishes around 95 million Sm3/day rich-gas Karsto processing; distinguishes older Kollsnes rich feed 146.5 from dry export 143. [Equinor Karsto expansion, 29 September 2005](https://www.equinor.com/news/archive/2005/09/29/KrstExpansionOnTimeAndUnderBudget) establishes historical 88 million Sm3/day. Neither historical 88 nor current 95/98 is an approved dry-gas reference for this model. [2018 Gassco brochure](https://gassco.eu/wp-content/uploads/2023/04/Karsto-brosjyren-engelsk-final-1218-1.pdf) separates rich input, dry output and liquid products; outlet pipeline capacities are not a plant nameplate inferred by summation.
- [Danish Energy Agency Preventive Action Plan, 28 February 2025](https://ens.dk/media/5370/download), pp.9 and 25-27, explicitly labels North Sea Entry technical capacity 27.4 mcm/day, rounds to 27 in prose and lists 10,387 mcm/year (not arithmetically identical to 27.4 x 365). Annual-table volumes use 12.1 kWh/Nm3; this document-specific factor is not approved for EPT1 or other gas. [Energinet branch methodology](https://en.energinet.dk/media/ycuhglla/methodology-for-integrating-baltic-pipe-in-the-danish-market-model.pdf), p.15, distinguishes expected technical 13,400 MWh/hour, sold 10,600 and available 2,800 for North Sea Entry from October 2022. These are different quantities, not interchangeable capacities.
- [GTS cross-border capacity appendix](https://www.gasunietransportservices.nl/uploads/fckconnector/ba836e79-1c54-5d75-b40e-33b76da2ac38) draft dated 1 November 2021, Appendix VI p.124, lists Emden EPT entry 40.2 GW for October 2021-2027. The SID sample 963.6 million kWh/day equals 40.15 GW, consistent with that rounded energy capacity; sampled December 2030 equals 36.6 GW and is lower than the older draft projection. [GTS interdependence definition](https://www.gasunietransportservices.nl/begrippenlijst/onderlinge-afhankelijkheid) explicitly states Emden EPT/NPT free capacities are interdependent; no independent capacity sum is defensible. [ENTSOG April 2026 outlook](https://www.entsog.eu/sites/default/files/2026-04/SO0069-26_Summer%20Supply%20Outlook%202026.pdf), p.11, defines technical capacity as the maximum firm offer subject to integrity/operational requirements; it is not a historical maximum or automatically an unchanging engineering nameplate.

No maintenance reference was equated automatically to a published technical capacity. The approved signed maintenance convention remains intact. No conversion between Nm3, Sm3, rich-gas feed, dry-gas sales or energy units was invented. Prices remain EA-SID requirements: public price observations were neither sourced nor substituted.

## Retrieved wholesale price candidates - 8 October 2026

These are sourcing candidates, not approved commercial inputs. Exact SIDs, metadata and returned observations are retained under data/raw/series_audit/sourcing_followup. EA monthly NBP/TTF/ZTP/PEG series include history and forecast; a forecast lifecycle does not turn earlier values into an independent validation target. All five primary monthly price candidates report source workbooks; THE points to a different workbook, has no forecast-start metadata and stops at December 2026. Its pre-October 2021 history cannot be called historical THE without resolving the predecessor splice. NBP_EUR_MWh avoids a new analyst-invented FX/therm conversion; the existing converted series is a candidate whose source conversion remains unverified.

Denmark: ETF is an actual Danish hub candidate, not a selected TTF/THE proxy. EEX ETF metadata lacks country_iso, explaining its absence from country-filtered discovery. No long-term EA Danish forecast was identified in the targeted EA price container. The ETF forward curve stops in November 2026. Selection of ETF versus another approved Danish benchmark remains an analyst choice.

Public definitions: [EEX indices](https://www.eex.com/en/markets/natural-gas/gas-market-transparency) distinguishes futures-based Daily EGIX, delivery-period EGSI, within-day and front-month settlement indices. [EEX spot products](https://www.eex.com/en/markets/natural-gas/gas-spot) identifies day-ahead contracts. [EEX January 2026 volumes](https://www.eex-group.com/fileadmin/SAP_Marketing_Cloud_E-Mail_Attachments/communications_and_marketing/Press_Releases/20260204_EEX_Group_January_2026_Volumes_table.pdf) explicitly identifies Danish ETF. [EEX German merger notice](https://www.eex.com/en/newsroom/detail?cHash=5aca64ffd331779039946fc1b1abab29&tx_news_pi1%5Baction%5D=detail&tx_news_pi1%5Bcontroller%5D=News&tx_news_pi1%5Bnews%5D=3149) dates THE market merger to 1 October 2021. Accessed 8 October 2026; no public prices substituted for EA data.

All retrieved price series have no explicit nulls, duplicates or negative observations. Missing calendar/trading periods are distinct from explicit nulls. Most EEX histories stop in April/May 2026; PEG last-trade history stops in October 2024. Noon naive timestamps do not establish gas-day assignment. Curve observations are monthly delivery dates, not a history of daily valuation dates: latest valuation/as-of freshness cannot be inferred from long delivery coverage or lifecycle=actual. No spot/futures/EA forecast blend or monthly price averaging has been chosen.

| SID | Unit; metadata lifecycle/frequency | Actual coverage; count | Value range; zeros; largest spacing | Assessment |
|---|---|---|---|---|
| `teams\natural_gas\price\nbp` | p_therm; forecast/monthly | 2008-01-01 to 2030-12-01; 276 | 11.646 to 366.455; 0 zeros; 31 days 00:00:00 | Monthly history + EA forecast; historical label/provenance not independently verified; explicit forecast start Oct 2026; complete monthly horizon to Dec 2030 |
| `teams\natural_gas\price\ttf` | eur_MWh; forecast/monthly | 2008-01-01 to 2030-12-01; 276 | 4.591 to 235.553; 0 zeros; 31 days 00:00:00 | Monthly history + EA forecast; historical label/provenance not independently verified; explicit forecast start Oct 2026; complete monthly horizon to Dec 2030 |
| `teams\natural_gas\price\THE` | eur_MWh; forecast/monthly | 2015-01-01 to 2026-12-01; 144 | 5.066 to 113.904; 0 zeros; 31 days 00:00:00 | Monthly history + EA forecast; historical label/provenance not independently verified; ends Dec 2026, forecast boundary absent, pre-Oct 2021 hub splice unresolved |
| `teams\natural_gas\price\ZTP` | eur_MWh; forecast/monthly | 2015-01-01 to 2030-12-01; 192 | 4.446 to 175.302; 0 zeros; 31 days 00:00:00 | Monthly history + EA forecast; historical label/provenance not independently verified; explicit forecast start Oct 2026; complete monthly horizon to Dec 2030 |
| `teams\natural_gas\price\peg` | eur_MWh; forecast/monthly | 2015-01-01 to 2030-12-01; 192 | 4.520 to 154.033; 0 zeros; 31 days 00:00:00 | Monthly history + EA forecast; historical label/provenance not independently verified; explicit forecast start Oct 2026; complete monthly horizon to Dec 2030 |
| `teams\natural_gas\price\NBP_EUR_MWh` | eur_MWh; forecast/monthly | 2015-01-01 to 2030-12-01; 192 | 4.481 to 150.771; 0 zeros; 31 days 00:00:00 | Monthly history + EA forecast; historical label/provenance not independently verified; explicit forecast start Oct 2026; complete monthly horizon to Dec 2030 |
| `teams\natural_gas\price\TTF_forecaster` | eur_MWh; forecast/monthly | 2022-01-01 to 2030-12-01; 108 | 10.000 to 235.553; 0 zeros; 31 days 00:00:00 | Monthly history + EA forecast; historical label/provenance not independently verified; explicit forecast start Oct 2026; complete monthly horizon to Dec 2030 |
| `eex2\future\month\nbp\settlement_price\future_curve` | p_therm; actual/daily | 2026-05-01 to 2028-04-01; 24 | 73.960 to 118.051; 0 zeros; 31 days 00:00:00 | Monthly delivery grid despite daily metadata; lifecycle actual means market quote, not realised delivery; valuation date unverified |
| `eex2\future\month\ttf\settlement_price\future_curve` | eur_MWh; actual/daily | 2026-05-01 to 2033-04-01; 84 | 20.308 to 46.757; 0 zeros; 31 days 00:00:00 | Monthly delivery grid despite daily metadata; lifecycle actual means market quote, not realised delivery; valuation date unverified |
| `eex2\future\month\the\settlement_price\future_curve` | eur_MWh; actual/daily | 2026-05-01 to 2033-04-01; 84 | 22.812 to 47.546; 0 zeros; 31 days 00:00:00 | Monthly delivery grid despite daily metadata; lifecycle actual means market quote, not realised delivery; valuation date unverified |
| `eex2\future\month\ztp\settlement_price\future_curve` | eur_MWh; actual/daily | 2026-05-01 to 2026-11-01; 7 | 44.836 to 46.407; 0 zeros; 31 days 00:00:00 | Monthly delivery grid despite daily metadata; lifecycle actual means market quote, not realised delivery; valuation date unverified |
| `eex2\future\month\peg\settlement_price\future_curve` | eur_MWh; actual/daily | 2026-05-01 to 2033-04-01; 84 | 20.231 to 45.944; 0 zeros; 31 days 00:00:00 | Monthly delivery grid despite daily metadata; lifecycle actual means market quote, not realised delivery; valuation date unverified |
| `eex2\future\month\etf\settlement_price\future_curve` | eur_MWh; actual/daily | 2026-05-01 to 2026-11-01; 7 | 45.232 to 48.440; 0 zeros; 31 days 00:00:00 | Monthly delivery grid despite daily metadata; lifecycle actual means market quote, not realised delivery; valuation date unverified |
| `eex2\indices\egix_day\nbp` | p_therm; actual/daily | 2019-01-03 to 2026-04-30; 1826 | 0.000 to 699.757; 1 zeros; 5 days 00:00:00 | Business-day futures-based EGIX, not spot EGSI; ends Apr 2026; zeros require interpretation |
| `eex2\indices\egix_day\ttf` | eur_MWh; actual/daily | 2019-10-01 to 2026-04-30; 1649 | 0.000 to 278.387; 1 zeros; 5 days 00:00:00 | Business-day futures-based EGIX, not spot EGSI; ends Apr 2026; zeros require interpretation |
| `eex2\indices\egix_day\the` | eur_MWh; actual/daily | 2021-10-01 to 2026-04-30; 1161 | 0.000 to 321.949; 1 zeros; 5 days 00:00:00 | Business-day futures-based EGIX, not spot EGSI; ends Apr 2026; zeros require interpretation |
| `eex2\indices\egix_day\ztp` | eur_MWh; actual/daily | 2019-01-03 to 2026-04-30; 1826 | 0.000 to 291.500; 1 zeros; 5 days 00:00:00 | Business-day futures-based EGIX, not spot EGSI; ends Apr 2026; zeros require interpretation |
| `eex2\indices\egix_day\peg` | eur_MWh; actual/daily | 2019-01-03 to 2026-04-30; 1826 | 0.000 to 234.552; 1 zeros; 5 days 00:00:00 | Business-day futures-based EGIX, not spot EGSI; ends Apr 2026; zeros require interpretation |
| `eex2\indices\egix_day\etf` | eur_MWh; actual/daily | 2019-01-03 to 2026-04-30; 1826 | 0.000 to 341.289; 1 zeros; 5 days 00:00:00 | Business-day futures-based EGIX, not spot EGSI; ends Apr 2026; zeros require interpretation |
| `eex2\spot\day_ahead\ttf\last_price` | eur_MWh; actual/daily | 2018-12-14 to 2026-05-01; 1827 | 3.000 to 306.900; 0 zeros; 178 days 00:00:00 | Day-ahead last trade, not daily index; irregular trading-date observations; gap/freshness and gas-day alignment unresolved |
| `eex2\spot\day_ahead\the\last_price` | eur_MWh; actual/daily | 2021-09-30 to 2026-05-01; 1299 | 17.775 to 306.800; 0 zeros; 4 days 00:00:00 | Day-ahead last trade, not daily index; irregular trading-date observations; gap/freshness and gas-day alignment unresolved |
| `eex2\spot\day_ahead\ztp\last_price` | eur_MWh; actual/daily | 2019-01-02 to 2026-05-01; 1834 | 2.975 to 246.050; 0 zeros; 174 days 00:00:00 | Day-ahead last trade, not daily index; irregular trading-date observations; gap/freshness and gas-day alignment unresolved |
| `eex2\spot\day_ahead\peg\last_price` | eur_MWh; actual/daily | 2019-09-16 to 2024-10-24; 1386 | 3.050 to 228.000; 0 zeros; 32 days 00:00:00 | Day-ahead last trade, not daily index; irregular trading-date observations; gap/freshness and gas-day alignment unresolved |
| `eex2\spot\day_ahead\etf\last_price` | eur_MWh; actual/daily | 2018-12-14 to 2026-05-01; 1817 | 4.175 to 308.750; 0 zeros; 185 days 00:00:00 | Day-ahead last trade, not daily index; irregular trading-date observations; gap/freshness and gas-day alignment unresolved |

## Derived targets and controls

| Requirement | Status / blocker |
|---|---|
| exit_st_fergus | REVIEW: YAML retains proposed alias sum with decision_required; package does not implement that sum. |
| flow_uk_actual | REVIEW / CALIBRATION: Easington + SEGAL + resolved St Fergus; raw Gassco conversion and alias treatment unresolved. |
| flow_be_actual | REVIEW / CALIBRATION: relies on unapproved raw Gassco monthly conversion. |
| flow_fr_actual | REVIEW / CALIBRATION: relies on unapproved raw Gassco monthly conversion. |
| flow_dk_actual | REVIEW / CALIBRATION: relies on unapproved raw Gassco monthly conversion. |
| flow_de_nl_landing_actual | REVIEW / CALIBRATION: monthly Emden + Dornum semantics unresolved. |
| flow_nl_actual | REVIEW / CALIBRATION: EPT1 conversion unresolved; Germany also needs monthly Emden + Dornum. Use gassco_DE only as QA. |
| flow_de_actual | REVIEW / CALIBRATION: EPT1 conversion unresolved; Germany also needs monthly Emden + Dornum. Use gassco_DE only as QA. |
| physical_exit_total_actual | REVIEW / CALIBRATION: all eight distinct exits needed; no duplicate St Fergus sum. |
| solver.unrouted_volume_penalty | TODO / COMMERCIAL / planned solver: null; no default inferred |
| solver.reconciliation_tolerance_bcm | TODO / CALIBRATION: null; no default inferred |
| calibration.training_start | TODO / CALIBRATION: null; no default inferred |
| calibration.training_end | TODO / CALIBRATION: null; no default inferred |
| calibration.validation_start | TODO / CALIBRATION: null; no default inferred |
| calibration.validation_end | TODO / CALIBRATION: null; no default inferred |
| calibration.initial_global_flexible_fraction | TODO / CALIBRATION: null; no default inferred |
| units.bcm_to_mwh | TODO / COMMERCIAL: null; no gas-energy conversion selected |
| model.reference_price_market | REVIEW / COMMERCIAL: current config uses NETHERLANDS; conceptual DE reference is not final. No change selected |
| Routing shares / flexible fraction | TODO / planned solver and calibration: fitting/application not implemented; output calibration path is designated only |
| Tariffs / other netback costs | Not coded input fields; no artificial SID requirement or commercial assumption introduced |

## Practical blockers and decisions

- Existing schema/reachability checks can run; implemented Kollsnes capacity calculation needs its reference baseline. Monthly physical-flow derivation needs approved Gassco normalisation, one St Fergus series, and EPT1 energy-to-volume alignment.
- Planned physical optimiser: implementation absent; 16 active field series remain audit REVIEW (two have negative observations), three new availability representations are conditionally redundant and eight corridor outage scopes remain unresolved; published capacity candidates are evidenced but unapproved, and UK_DIRECT_ROUTE constraint treatment is unresolved. Inactive residual/direct Germany sources are not current solver requirements; full-Norway reconciliation is incomplete.
- Calibration: training/validation dates, reconciliation tolerance, shares/flexible fraction and independent normalised targets missing. Nybro begins September 2022, limiting the common six-market history; exact usability cannot be judged without the chosen calibration window. Existing-model country benchmarks do not independently validate targets derived from the same sources.
- Commercial layer: price candidates above are retrieved; THE EA forecast ends in 2026 and no long-dated Danish forecast was identified; benchmark choice and valuation-date freshness, reference market, energy conversion and unrouted penalty remain unresolved; objective implementation absent. Choose Danish hub/proxy and price delivery/valuation conventions only with analyst approval.
- Required analyst decisions: reference-baseline evidence and dynamic-capacity definitions; treatment of negative field production; St Fergus canonical series; EPT1 calorific/reference conditions; calibration windows/tolerance and flexibility controls; commercial conventions/reference market and Danish proxy. Established historical Snohvit units, 2022 exclusion arithmetic, mixed vintages and official negative net-gas findings are carried forward, not reopened.

Evidence: config/model.yaml; canonical config/data_series.csv; reviewed diagnostics/data_series_proposed.csv; diagnostics/data_series_audit.csv; retained data/raw/series_audit/catalogue.json (identifier-only); diagnostics/core_production_source_trace.json and core_contract_findings.json; src/norway_gas_routing/{network,config,data,maintenance,units,validation,diagnostics}.py; relevant INPUTS.md and DECISIONS.md passages. Targeted new Emden samples and price observations were retrieved via the existing helper; no maintenance/production audit was repeated. Public capacity source URLs, dates and unresolved definition/effective-period details are recorded above.


## Destination-classification readiness follow-up - 8 October 2026

This supersedes earlier unsourced historical-price/Poland gaps, not the unresolved
physical-data contract. Full matrix: `destination_readiness.csv`; numerical checks,
public source URLs and controls: `destination_readiness.json`. Latest-revised
exploration only; no change to model configuration or methodology.

| Destination | Best monthly observation candidate / period | Price coverage | Statistical readiness / blocker |
|---|---|---|---|
| UK | EA gassco_UK, bcm, Nov 2014-Sep 2026, no missing months | NBP-TTF Jan 2015-Sep 2026 | QA descriptions only; St Fergus handover, nominations break and omitted/different UK scope unresolved |
| DE | EA gassco_DE, bcm, Nov 2014-Sep 2026, no missing months | THE-TTF Oct 2021-Sep 2026 | Emden+Dornum minus EPT1 blocked by matched GCV/gas-day/physical definitions; no commercial swap inference |
| NL | EA gassco_NL, bcm, Nov 2014-Sep 2026, no missing months; EPT1 daily physical energy retained | TTF Jan 2015-Sep 2026 | EPT1 volume conversion/alignment unresolved; landing entry not commercial destination |
| BE | EA gassco_BE, bcm, Nov 2014-Sep 2026, no missing months | Stability test needs no Belgian price | QA stability only; Zeebrugge physical/nominations break and monthly source provenance unresolved |
| FR | EA gassco_FR, bcm, Nov 2014-Sep 2026, no missing months | PEG-TTF Nov 2019-Sep 2026, sparse | Dunkerque reporting break/provenance plus incomplete PEG assessment calendar |
| DK | EA gassco_DK, bcm, Nov 2022-Sep 2026, no missing months but six negative months | Not required | Nybro import includes transit; net allocation definition and Poland overlap unresolved |
| PL | EA gassco_PL Nov 2022-Sep 2026; better independent route candidate is PL-TSO-0002 Faxe entry Physical Flow, Oct 2022-Sep 2026 | Not required | 48 complete monthly energy summaries are descriptively usable; provisional/publisher differences, Norwegian-origin allocation and bcm shares unresolved |

The four exact price SIDs were retrieved from the existing registry. Metadata
confirms actual daily Reuters observations, NBP p_therm, others eur_MWh. Dated
ECB EUR/GBP (GBP per EUR) supports same-date NBP conversion using 29.3071 kWh/therm.
The diagnostic spread means use only matched dates with published observations;
there is no filling, trading-holiday inference or weekend delivery weighting.
THE's pre-Oct 2021 values are not treated as THE; precursor lineage remains to
validate. PEG has an empty Oct 2019 and later gaps up to 12 days, so available
monthly sample means do not establish a complete delivery-day price index.

No common consistent physical Norwegian-export denominator is ready. EA seven-
market sums differ from total by up to 0.216800 bcm/month; negative DK allocations,
UK scope and total's stale forecast-boundary metadata prevent valid export shares.
Gassco's 2024 public delivery table groups Germany/Denmark because gas volumes are
exchanged between markets; Nybro entry is not Danish consumption. DE/NL landing
splits similarly cannot identify contractual recipients or commercial swaps.

Descriptive benchmark rate CVs (std/mean, Jan 2015-Sep 2026) are BE 11.8%, FR 15.0%,
DE 24.3%, UK 33.1%, NL 40.5%. They describe EA workbook series, not validated
physical/commercial classifications. Faxe's independent Polish-side monthly
reported-energy rate CV is 23.9% in 2023-2025; 2025's average is materially higher.
Commissioning, capacity changes, maintenance, seasonality and trends must be
separated from commercial responsiveness. No unresolved flow series was regressed.

Calendar/day-count controls are available. Retained monthly production has
source/vintage/aggregation caveats; signed per-asset maintenance has 2021 onward
coverage but scope/baseline and production overlap remain unresolved. Date-based
asof retrieves historical Faxe revisions and TTF snapshots as well as previously
verified production/EA forecast vintages. Deep retention, publication timing,
timezone and complete vintage coverage still require validation. Never backfill
missing historical snapshots from current data. Actual contemporaneous monthly
price means are not available at the beginning of that month.

Recommendation: prioritise resolving physical/monthly provenance for BE/FR and
UK, EPT1 GCV/alignment for DE/NL, and Norway-origin/transit reconciliation for DK/PL.
Belgium's reported stability is a useful hypothesis lead; the full baseload versus
price-responsive split remains untested. Configuration/status labels were not
promoted by this assessment.
