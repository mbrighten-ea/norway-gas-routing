# Public capacity integration recommendation

**Decision: retain all three series as energy diagnostics. No existing constraint
can yet be replaced.** The JSON contract is an inactive, read-only proposal;
`enabled=false`, three conditional mappings, no approved conversion factors.
Nothing in the solver imports it. Scope is gas-day labels 2023–2025. October–December
2022 commissioning observations remain in the database but are not projected back
onto a fully commissioned network. No 2026 outcomes were inspected or scored.

## Physical contract

| Database identity (operator / point / direction) | Candidate model boundary | Assessment |
|---|---|---|
| `point:north_sea_technical`: DK-TSO-0001 / ITP-00630 / entry | `NORTH_SEA_ENTRY`: EUROPIPE_II_SPLIT → DANISH_TRANSIT | Exact directional route association; partial match to the model's engineering/volume envelope |
| `point:faxe_dk_technical`: DK-TSO-0001 / ITP-10009 / exit | `BALTIC_PIPE`: DANISH_TRANSIT → FAXE | Exact Danish border-exit identity; partial match to the collapsed Danish transit/Baltic corridor |
| `point:faxe_pl_technical`: PL-TSO-0002 / ITP-10009 / entry | `PL_DELIVERY`: FAXE → PL | Exact Polish border-receipt identity; partial match to aggregated Polish delivery; this arc has no existing asset capacity |

Energinet's upstream terms identify the EP II branch connecting the Norwegian
upstream system to Denmark. North Sea Entry nominations are copied to **Nybro
exit** for that upstream service. This supports the branch association; it does
not identify North Sea Entry with separate Danish-production Nybro entry or prove
that its published point rating equals the full Europipe II pipe rating. The
document is effective 3 February 2023; its provisions are not evidence of an
unchanged historical technical rating.
[Energinet upstream terms, sections 2 and 6.1](https://en.energinet.dk/media/be2ghn5o/general-terms-and-conditions-for-gas-transport-in-the-upstream-pipeline.pdf).

The joint operators' 23 October 2023 report explicitly links ENTSOG Danish
Faxe exit and Polish Faxe entry keys for the Denmark-to-Poland interconnection.
It describes commissioning from October 2022 and full capacity from November
2022. These are opposite sides of one crossing, not two independent pipelines;
reverse Faxe directions are different series. The annual Baltic Pipe project
specification covers a broader infrastructure chain than either point alone.
[Joint demand assessment, pages 3–6](https://www.gaz-system.pl/dam/jcr:671c8941-767d-40bb-add5-b0c7158037ff/2023_10_23_mdar_pl-dk_gaz-system_energinet_eng_fin.pdf).

Model conservation implies Europipe II carries DE plus DK plus PL before the
split, North Sea Entry carries DK plus PL, and the Faxe path carries PL. A future
approved adapter could impose **separate** point inequalities on those flows,
while retaining the upstream engineering cap. It must not sum the three point
ratings, apply Faxe to Danish offtake, or replace Europipe II's 73.5 mcm/day with
the branch point capacity. Danish supplies, storage, other users, pressure
assumptions, fuel and linepack are outside the collapsed Norwegian model;
applicability and any shared use need explicit treatment. Energinet's manual
calculates capacity under network/pressure scenarios, corroborating that a point
rating is a system boundary limit rather than a universal pipe specification.
[Operator capacity calculation manual](https://en.energinet.dk/media/3txcjinn/manual-for-kapacitetsberegninger.pdf).

## Conversion gate

The conversion matrix records requirements separately for each identity. Danish
terms version 23.0 (effective October 2023) define gross-energy kWh, dry normal
volume at 0°C and 1.01325 bar absolute, and a 25°C combustion reference. Primary
indexed text was verified, but the original PDF now redirects to a 404; preceding
and subsequent historical editions remain unverified. These definitions supply
**no numeric capacity-basis calorific value**.
[Energinet terms 23.0](https://en.energinet.dk/media/b03fklth/general-terms-and-conditions-for-gas-transport-23-0_legally-binding-english-version.pdf).

The retained 2025 tariff sheet independently identifies gross-energy conventions;
tariff conventions do not establish a point's engineering capacity conversion
factor. Historical Polish code retrieval returned challenge HTML, so its
applicable reference conditions are unresolved. The source register distinguishes
web-verified text from an actual retained PDF and from an unsuccessful retrieval.
[Energinet tariff sheet, effective January 2025](https://en.energinet.dk/media/fhslybmk/transmission-tariffs-effective-as-of-1st-january-2025-updated-1st-june-2024.pdf).

Before conversion, obtain a dated operator statement of the **capacity-basis**
gross kWh per source cubic metre for each point/direction, including its
temperature, absolute pressure, dry/wet and real-gas/compressibility convention.
Establish the model's common bcm reference and a compatible transformation.
Norwegian Sm³ and Danish Nm³ must not be silently equated. Settlement or measured
flow calorific values, generic constants, rounded paired planning figures and
back-solving from the current 27.4 mcm/day assumption are insufficient.

If a verified factor `H[d]` in kWh per **model-reference** m³ is eventually
approved, a complete gas-day quantity `E[d]` gives `E[d]/H[d]/1e9` bcm, and a
gas-day-labelled monthly limit is their sum. If factors vary within a gas day,
compatible interval energy/factors are required rather than an invented average.
No factor is adopted here. A source daily quantity is already integrated over
its 23, 24 or 25 hours: never multiply it by 24 again. Current database aggregation
assigns the whole quantity to the gas day's start month. A midnight calendar
month cuts boundary gas days: use compatible hourly evidence, or separately
approve a documented alignment convention. An incomplete month has an unknown
total; known subtotal and coverage remain separately visible.

## Constraint types and history

- Engineering/nameplate ratings remain separate dated specifications, including
  the 2024 map snapshots; point observations do not backdate them.
- ENTSOG `Firm Technical` is published entry/exit technical capacity. A reduced
  observation is preserved without claiming a verified physical outage cause.
- Verified independent restrictions would require their own boundary, interval,
  publication and overlap treatment. Empty event history is incomplete evidence,
  not proof of full availability. No extra Gassco deductions are made.
- `Firm Available` is commercial availability and is excluded from this contract.
- Model shared constraints express conservation and common infrastructure. Serial
  caps can constrain the same flow without being additive; overlapping events
  must not be subtracted twice. Do not select a minimum across Faxe sides until
  their energy/volume bases and temporal/physical applicability are verified.

All three series cover **365 / 366 / 365 gas days** in 2023 / 2024 / 2025, with
no missing or reported-zero days in that window. On ordinary 24-hour days their
usual published quantity is 321.864 GWh; DST quantities include 308.453 and
335.275 GWh on 23/25-hour days. Those are different day lengths, not automatically
restrictions. NSE includes a 168 GWh observation on 1 August 2024. The separate
Faxe publications differ on four supported 24-hour days:

| Gas day | DK exit GWh | PL entry GWh |
|---|---:|---:|
| 2023-10-02 | 321.864 | 201.480 |
| 2023-10-09 | 321.864 | 146.280 |
| 2024-07-31 | 247.754 | 321.864 |
| 2024-08-01 | 307.864 | 321.864 |

These compare original reported quantities at the two identified sides, not
harmonised volumetric throughput or confirmed independent engineering
restrictions. CSV evidence retains each side's IDs and revisions. Values are
latest revised: `lastUpdateDateTime` is not proof of availability at a forecast
origin. Current 27.4 mcm/day and 10 bcm/year model assumptions are recorded beside
the coverage, but numerical bcm differences are deliberately unknown. The
existing annual assumption's flat 10/365 basis also needs an approved leap-year
and monthly interpretation before replacement.

## Next decision and reproducibility

Priority order: (1) obtain dated operator capacity-basis factors and historical
reference definitions; (2) approve a common model volume/month boundary;
(3) verify shared-system applicability and restriction independence; (4) obtain
publication vintages for origin-available evaluation. Only then request separate
approval for an adapter adding point upper bounds to the relevant arcs. Keep the
pipeline snapshots and retrospective energy diagnostics distinct meanwhile.

Run `scripts/audit/audit_capacity_contract.py --output <new repository directory>`
with the mandated workspace interpreter to reproduce coverage and Faxe evidence.
SQLite is opened `mode=ro`; pinned input hashes reject changed DB/config inputs.
The CLI does not call a solver or modify the contract. Unit tests reject swapped
identities, duplicate Faxe sides, additive shared limits, commercial substitution,
activation and unsupported factors. The retained-history test checks coverage
and revision lineage. Validation results and preservation hashes are retained in
`archive/20261009-18_capacity-integration-contract/verification.json`.
