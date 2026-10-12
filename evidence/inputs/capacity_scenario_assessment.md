# Capacity adapter and optional scenarios

## Completed one-off 2024 sensitivity, 12 October 2026

The user authorised read-only use of independently hash-verified frozen 2024
prepared inputs for offline capacity sensitivities only. This supersedes the
pending sourcing decision below solely for this completed experiment. Normal
fresh-SID requirements and origin-matched validation requirements are unchanged.

[Results, charts and CSVs](../../archive/20261012-02_capacity-sensitivity/report.html)
retain all eight scenarios. Baseline replay agrees within 4.99581e-10 bcm.
Exports rise from 117.0831345 to 117.5843625 bcm with assumed Kollsnes 144.5,
and to 119.377524 bcm with assumed 156. Unrouted gas falls from 2.7412485 to
2.2400205 and 0.446859 bcm respectively. UNMAPPED is unchanged at 0.446859.
The 156 case removes 2.2943895 bcm mapped disposal; Kollsnes throughput increases
by the same amount. Its annual utilisation falls from 99.9943% to 95.4864%,
and binding months from eleven to zero. Annual destination changes are UK
+2.12638858, Belgium +0.41321509 and France -0.24521417 bcm; DE/NL/DK/PL
are unchanged within numerical precision under fixed baseline preferences.
Kårstø throughput remains 24.328211 bcm, and 97 adds no export benefit.
Autumn endpoint and combined scenarios match the 156 case in 2024.

Evidence-backed mode retains baseline because no public candidate passes all
gates. These are hypothetical dry-boundary plant assumptions, not verified
engineering corrections, actual exports or forecast improvements. Kollsnes
commissioning/maintenance compatibility, Kårstø rich/dry equivalence and dated
point-capacity conversions remain unresolved. No defaults changed, no 2025 run
was made and the 2026 holdout remains locked. 242 relevant tests passed.

The public database is now connected to a read-only model-facing candidate layer.
The default remains `config/model.yaml` and the existing preparation arithmetic.
**No public capacity is eligible to replace a historical model limit yet.**
The adapter, scenario selection and conversion arithmetic are implemented and
tested; historical routing comparisons are awaiting a sourcing decision.

The work package is [20261009-21_capacity-scenarios](../../archive/20261009-21_capacity-scenarios/report.md).
The configuration before changes and its SHA-256, source/result hashes, database
hash and Git index identity are recorded there. The database and original captures
are unchanged. The existing staged addition/working deletion of `config/sids.py`
and the untracked repository tree were preserved. An unreadable Office lockfile
was excluded from hashing and left untouched; the workbook was neither read for
model values nor modified.
Concurrent changes were detected in `visual_data.py`, `visual_figures.py` and
`visual_report.py`; they were preserved and recorded with before/after hashes.

The latest retained working assessment is the 2024 broader-boundary reconstruction:
119.824383 bcm supply, 117.0831345 exports, 2.7412485 unrouted and 0.446859 UNMAPPED.
The saved official-net-production 2025 diagnostic exports 114.175610333 bcm.
These identify existing assessments; they are not newly reproduced outcomes.

## Physical boundaries

The [mapping matrix](../../archive/20261009-21_capacity-scenarios/candidate_tables/physical_mapping_matrix.csv)
retains all three operator/point/direction identities separately. North Sea Entry
is the Danish upstream branch of Europipe II, before Danish offtake and Polish
transit separate. The [Energinet upstream terms](https://en.energinet.dk/media/be2ghn5o/general-terms-and-conditions-for-gas-transport-in-the-upstream-pipeline.pdf)
link its entry nomination to Nybro exit; it is not Danish-production Nybro entry.
The model branch carries DK+PL; Europipe II upstream carries DE+DK+PL.

The [joint Faxe assessment](https://www.gaz-system.pl/dam/jcr:671c8941-767d-40bb-add5-b0c7158037ff/2023_10_23_mdar_pl-dk_gaz-system_energinet_eng_fin.pdf)
identifies the Danish exit and Polish entry as two sides of the Denmark-to-Poland
crossing. Their proposed constraints apply only to PL transit. Separate serial
inequalities preserve both observations; they never add capacity or restrict DK
offtake. The tested constraint utility is inactive for the real candidates.
It requires reviewed mapping/conversion eligibility and an activation reference.
No network node, arc, source, country-allocation freedom or upstream cap changed.

`Firm Technical` means published point technical capacity, not a demonstrated
unchanging nameplate. Dated reductions are observations, without a verified outage
cause or proof that they fully represent operational availability. Pressure,
system co-use, fuel and linepack are not resolved by the collapsed graph.
`Firm Available`, bookings and historical flows are excluded as engineering caps.
The four retained Faxe differences remain unaltered in the prior contract CSV and
the separate database histories.

## Conversion assessment

The [conversion evidence matrix](../../archive/20261009-21_capacity-scenarios/conversion_evidence_matrix.csv)
adds operator context without adopting a factor. Gassled defines dry Sm3 at 15 C
and 1.01325 bar absolute; Nm3 uses 0 C at the same pressure. This is corroborated
in the [2023 terms](https://gassco.eu/wp-content/uploads/2023/10/Gassled-Terms-and-Conditions-01.10.2023-w.-attachmenst.pdf),
but does not harmonise the mixed model assumptions or define each plant rating.
The earlier Danish contract evidence specifies gross energy, 0 C dry volume and
25 C combustion. Its historic version coverage remains incomplete.

The [GAZ-SYSTEM project Q&A](https://www.gaz-system.pl/dam/jcr:a8adca37-fac3-4dcf-8713-99f828b9f05a/20170921_qanda.pdf)
directs shippers to operator-published values for energy-to-volume recalculation;
it does not provide a dated Faxe capacity-basis factor. Older Polish codes and
Yamal documentation do not establish applicable 2023-2025 Faxe conditions.
The [ENTSOG publication format](https://transparency.entsog.eu/pdf/TRA158_ENTSOG%20TP%20Data%20Publication%20Format_v3%2017052016.pdf)
distinguishes technical capacity and GCV observations. Measured-flow GCV and
settlement conventions do not by themselves establish a rating's capacity basis.
The Danish planning conversion of 12.1 kWh/Nm3 is retained as planning evidence,
not adopted for these source histories.

All three normal quantities remain 321.864 GWh/source gas day. Conversion is
blocked by numeric capacity-basis GCV, applicable historical reference conditions,
common model volume basis, compressibility and calendar/gas-month alignment.
No arbitrary 11/12 constant or ideal-gas temperature scaling is used.

The conversion module accepts a fully reviewed dated contract, then calculates
`E[d]/H[d]/1e9`. It never multiplies an integrated source-day quantity by 24.
Whole gas days start at 06:00 CET/CEST, retain 23/25-hour days, leap days, original
zero, half-open intervals and revision lineage. Complete monthly totals use start
labels only after explicit alignment approval; calendar-boundary splitting needs
hourly evidence. Missing coverage never becomes zero or full capacity.

## Kollsnes

The [internally dated 2019 operator brochure](https://gassco.eu/wp-content/uploads/2023/04/091540-Kollsnes_NORSK_spreads_22.10.2019-1-1.pdf)
explicitly describes 144.5 million Sm3/day export capacity. It is stronger evidence
for a historical export specification than an undated processing table, but not a
complete unchanged pre-upgrade schedule. The 2020 MEG announcement is a processing
description and a planned installation window, not commissioning evidence.

[Equinor's January 2025 statement](https://www.equinor.com/news/20250106-troll-highest-natural-gas-production-ever)
supports the increase from 144.5 to 156 million Sm3/day. The
[2023 Gassco report](https://gassco.eu/wp-content/uploads/2024/03/Gassco-aarsrapport-2023-ENGELSK.pdf)
places successful robustness/capacity work in autumn 2023; the
[2024 report](https://gassco.eu/wp-content/uploads/2025/04/gassco-aarsrapport-2024-signertavrevisor-ENGELSK-11.april_-1.pdf)
corroborates that window. No exact operational day was found in the bounded review.

Current Gassco English/Norwegian pages retain conflicting narrative/table figures.
The [Directorate facility page](https://www.norskpetroleum.no/produksjon-og-eksport/landanlegg/)
still distinguishes 146.5 rich processing and 143 dry export. Those quantities
cannot be interchanged. The upgrade evidence, dry-export equivalence and the
maintenance series' signed reference baseline have not been jointly verified.

Consequently 144.5 and 156 are implemented only as assumed dry-boundary
sensitivities, preserving the current signed maintenance once. Additional nominal
technical volume before maintenance is 0.549/4.758 bcm in leap-year 2024 and
0.5475/4.745 bcm in 2025 respectively. These are **capacity-envelope differences,
not increases in routed exports**. The autumn early/late scenarios use Sep 1 and
Dec 1 as modelling endpoints, not historical actual dates or proven tight bounds.
Both yield 156 throughout 2024-2025; their date sensitivity matters in 2023 only.
They do not alter training preferences, which remain fixed at the baseline values.

## Kårstø

Public evidence supports approximately 95 million Sm3/day rich-gas processing,
and the retained Equinor 2024 annual-report snapshot gives 97 generic processing.
Neither is a verified dry export rating. Operator terms identify rich-gas areas A
(Statpipe) and B (Asgard Transport), Area C processing, and dry output into Area D.
Extraction trains 100, 200, 410 and 420 are identified, without separately dated
train limits. Field-specific rich factors, composition, liquids extraction, fuel,
flare and ethane reinjection prevent a universal fixed shrinkage conversion.
The model sums net saleable source gas on its processing arc; constraining that
sum by a rich-inlet number can overstate the dry capacity associated with a given
inlet ceiling. A rigorous model would require consistent rich feed/composition or
a verified dry-output envelope, plus shared train constraints where evidenced.

Keep the provisional 95 baseline. `karsto-97-proxy` retains a finite processing
constraint and tests a 97 dry-equivalent **assumption**, increasing nominal 2024
capacity by 0.732 bcm (2025: 0.730). No net-dry historical schedule was manufactured.
The combined scenario tests interactions with Kollsnes; it does not verify either
engineering boundary or change production sources.

There is a model-only redundancy result without consuming historical supply:
Kårstø's outlets are bounded by 12 (Statpipe) + 73.5 (Europipe II) = 85.5 mcm/day.
With no Kårstø maintenance deduction, the 95 processing envelope already exceeds
that combined bound in every month. Raising it to 97 leaves the feasible set and
maximum exports unchanged; the outlet constraints dominate. A synthetic solved
test verifies this. This does not establish physical plant shrinkage, nor confirm
that a newly solved degenerate country-allocation tie would be identical.

## Other limits and restrictions

All fourteen existing pipeline assumptions match the independently retained 2024
Gassco map. No materially different, dated compatible correction was established
for Nyhamna, Langeled north/south, Europipe I/II, Zeepipe, Franpipe or Norpipe.
Binding diagnostics prioritise those corridors and Kollsnes, but do not identify
engineering ratings from observed flow or fit a cap to country errors.

The [coverage export](../../archive/20261009-21_capacity-scenarios/candidate_tables/coverage.csv)
retains the three point histories. The events table remains empty. Upstream
engineering restrictions for every requested asset remain unknown. The prior UMM
empty/template responses, inaccessible GMP and publication thresholds remain
limitations; no repeated historical-system probing was undertaken. Receiving-point
histories are not substitutes for upstream pipelines and clustered capacities must
not be summed. No maintenance deduction was made from an already reduced point
quantity. The adapter exposes unknown restriction coverage alongside every value.

## Modes and use

`prepare_inputs(..., capacity_scenario='baseline')` is mode A and never reads the
database. Mode B, `evidence-backed`, reads the pinned database, exports statuses,
and retains all baseline assumptions explicitly because no candidate is eligible.
Mode C selects the named assumptions in `capacity_inputs.SCENARIOS`. Selection is
explicit; inputs are copied and default configuration is never edited. Selected
capacity, status, fallback, scenario, maintenance policy and provenance are stored.
Unknown source observations remain null even when an existing baseline assumption
is retained for the solver.

`scripts/audit/build_capacity_candidates.py --output <new-directory>` exports public
candidate/coverage tables without private production data or solver calls.
`scripts/run/run_capacity_scenarios.py` supports a separately authorised frozen-input
comparison, requiring explicit scenarios, years, a new output directory,
`--frozen-input-comparison` and `--authorization-reference`. It keeps the existing
three objectives, checks baseline replay within 1e-9 bcm, reports monthly/annual
seven countries and five groups, plant/transit throughput and utilisation,
disposal, binding constraints, stage-1 LP duals and every node balance. Duals are
local, possibly nonunique export-capacity sensitivities, not price valuations.
Observed-flow accuracy scoring is deliberately separate and absent.

The newer SID-only sourcing rule blocks an ordinary fresh historical run until
all production components have identified SIDs and fresh complete responses.
The six manual fields remain UNMAPPED; they have no individual forecast SIDs.
Norway production, exactly-once Snøhvit exclusion, the ordinary July-2025 guard,
network and 2026 holdout policy are unchanged. A frozen-vector comparison needs
the explicit exception requested during this task; elapsed time is not approval.

## Future forecasts through 2030

Capacity records need separate effective time and publication/vintage time:

| Input class | Required treatment |
|---|---|
| Historical verified rating | Exact compatible boundary/units and supported validity; do not backdate snapshot |
| Latest-revised historical point technical | Preserve revisions; no origin-available claim without publication evidence |
| Historical operational restriction | Independent event definition, overlap/dependency and revision treatment |
| Scheduled future outage | Dated operator plan/vintage, cancellation/supersession; never copy historical outages |
| Assumed future technical rating | Explicit source, assumption start/end and model reference conditions |
| Forecast-effective scenario | Separate reviewed rating/maintenance bundle valid at forecast origin |
| Unknown future availability | Null with explicit coverage; no guarantee or automatic full capacity |

The historical scenarios expire at the exclusive 2026-01-01 boundary. No rating
or outage is projected to December 2030. Current evaluation guards continue to
block 2026/future analysis; later forward forecasting requires its own approved
policy and source bundle. The reusable arithmetic and ledger structure do not
constitute that approval or invent a maintenance forecast.

Recommendation: retain the default, adopt the adapter/status/provenance safeguards,
and prioritise operator confirmation of Kollsnes dry capacity and maintenance
reference. Obtain dated point-capacity factors and common volume/month definitions,
then Kårstø feed/output composition or dry envelope. Review model-to-model impacts
before any default capacity change. No price optimisation is introduced.
