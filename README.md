# Norwegian gas routing

Monthly Norwegian pipeline gas routing to UK, France, Belgium, Netherlands,
Germany, Denmark and Poland. The historical reconstruction solves with HiGHS;
forecast validity and production readiness remain unresolved.

## Operational operator guide

**F2.2 status:** the complete production-population gate is blocked. The default
`provisional_kollsnes_143` scenario is approved provisionally (19 existing
envelopes; Kollsnes 143 mcm/day, signed maintenance once). Select
`provisional_kollsnes_156` for the approved sensitivity; other future availability
is disclosed as unknown. These scenarios do not approve incomplete production.
`baseline_prospective` remains an alias for the 143 central case.

The [complete component ledger and source checks](evidence/inputs/reconciled_supply_f22/README.md)
replace the earlier blanket 46-field forecast blocker. The backend checks the
entire 132-component population, preserves UNMAPPED, and refuses to derive
weights from only the original 46. The approved annual-2024 allocation method
cannot activate until complete classifications, source coverage and the national
identity pass. Snøhvit's prospective units/vintage also remain incompatible.
`--validate-only` retains an explicitly blocked Excel/CSV/HTML package, exact
forecast responses, the population ledger and checked provisional capacities;
blank flow results mean unavailable, not zero exports. No source-backed country
forecast or sensitivity conclusions are currently available.

Troubleshoot coverage against `production_population.csv`, `assessment.json`
and raw SID responses. Resolve provider omissions or document a specific
source-supported relationship; never turn an empty response into zero. Resolve
project/group membership and Brage/Tune/Trym's accepted boundary questions.
Correct or independently establish Snøhvit's forecast contract before deduction.
Do not combine workbook values with SID forecasts or reuse old five-node weights.

Use `config/run.yaml` as the single run request. Its repository-relative paths
reference the canonical model, registry and locked evaluation policy without
duplicating network/source mappings. The default is `current_forecast`, with
`origin: null`, `horizon_months: 12`, `forecast_end_month: null`, `start: null`, `end: null`,
`input_source: fresh_sid`, `capacity_scenario: provisional_kollsnes_143` and
`price_enabled: false`. It retrieves/checks candidates, then reports the pending
physical-input decisions; it cannot yet issue a complete EA routing forecast.

From this repository, prepare the local process environment once:

```powershell
New-Item -ItemType Directory -Force .scratch/tmp | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = (Resolve-Path '.scratch/tmp').Path
$env:TMP = $env:TEMP
$env:MPLCONFIGDIR = Join-Path $env:TEMP 'matplotlib'
```

The single execution command is:

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/run/run_routing.py --config config/run.yaml
```

Append `--validate-only` to prepare/check inputs and write an unsolved package
without constructing an LP, checking solver availability or optimising.
`--solver HiGHS` optionally overrides the configured installed solver.
Exit 0 means complete or validated-only; exit 2 means blocked/failed. Configuration
errors stop before package creation. Later failures retain an explanatory package.

**Current forecast settings:** null origin records this execution's UTC timestamp;
an explicit quoted timestamp within the current UTC month selects that same
`@asof` state for every candidate source. Future origins and older replay origins
are rejected. Deliveries start with the next complete calendar month: currently
November 2026–October 2027. Set integer `horizon_months` (default 12; maximum 60)
or a quoted `forecast_end_month`. **A non-null endpoint takes precedence over
the length setting.** Start/end must stay null or match the resolved window;
the endpoint must include at least one delivery month and cannot exceed December
2030. Settings and provenance record the resolved start, end and actual month
count. Historical reconstruction uses start/end and requires a null endpoint.

To request the full extended horizon, edit these settings in the run YAML:

```yaml
mode: current_forecast
origin: null
start: null
end: null
horizon_months: 12
forecast_end_month: '2030-12'
```

For any October 2026 information origin this resolves to November 2026–December
2030, exactly **50 monthly deliveries**. With `forecast_end_month: null` the
unchanged default is November 2026–October 2027, **12 deliveries**. Later origins
produce shorter endpoint-based windows; they always start in the first complete
month after the UTC information origin. Run the same command with
`--validate-only` first. This requests fresh origin-matched SID observations
over the entire delivery window and does not construct an LP.

Changing horizon never fills source months. Selected Snøhvit stops in December
2029, so every requested 2030 month is missing and the extended live run stays
`BLOCKED_INPUTS`. Its units/vintage remain incompatible even for the short view.
The complete 2024 population/classification gate and absence of frozen residual
weights remain blockers. The 156 sensitivity passing capacity preparation does
not approve a replacement central rating or solve these source problems.
`source_metadata.json` records expected/returned point counts and missing dates
and delivery months; `forecast_blockers.json` separates structured source gaps
from unresolved physical decisions. Missing dates and unavailable outputs remain
missing, not zeros. Prospective technical envelopes remain explicitly provisional,
with unknown availability outside the approved signed Kollsnes-plan contract.

Excel, CSV, HTML, charts and provenance retain every chronological monthly row
across calendar years and use monthly bcm units. For an explicit manufactured
50-month demonstration, additionally set `input_source: synthetic_demo` and
`capacity_scenario: synthetic_fixture`. It is labelled SYNTHETIC throughout and
queries no EA data; these fixture values cannot substitute for blocked live inputs.

The sixteen identified field forecasts and national total are monthly bcm.
Snøhvit is retrieved unchanged pending forecast-unit/vintage confirmation.
The approved provisional capacity scenario holds canonical technical envelopes
constant and uses the signed Kollsnes plan once. Source/reference incompatibility
still blocks execution: the current plan reaches 156 mcm/day on thirteen days,
exceeding the 143 central envelope. The 156 sensitivity accepts this plan; neither
scenario resolves the population or Snøhvit gates.
Future actuals/comparison scores are never requested. Excel records origin,
deliveries, assumptions, source checks and explicit unavailable flow results.
`provenance/forecast_requirements.csv` lists every affected field/node;
`forecast_blockers.json` separates source failures from physical decisions.
The [F2 supply-contract decision](evidence/inputs/forecast_viability_f1/current_forecast_supply_contract.md)
documents direct node-feed, reduced-scope and residual-split alternatives. No
arbitrary national/non-flex allocation or partial real-data LP is implemented.

**Historical reconstruction:** set mode to `historical_reconstruction`, start to
`'2024-01'`, end to `'2024-12'`, origin to null and capacity_scenario to `baseline`.
Use the same command and validation flag. B2 completed the real-data 2024 run.
All 46 NPD identities are registered; Hanz's absent January/February alone are
explicit structural zeros justified by its 20 April 2024 production start. March's
returned zero and all later observations remain unchanged. The raw response and
[Hanz evidence](evidence/inputs/routing_sources_b1/hanz_preproduction.json) are
retained in provenance. Other missing observations fail; no workbook substitution
or general missing-to-zero rule applies. Inspect `results.xlsx` (Read me, Input
sources, Diagnostics) and `provenance/source_metadata.json` in the printed package.
The [source ledger](evidence/inputs/routing_sources_b1/README.md) records identities,
units, transformations, coverage and hashes.

**F1 forecast readiness:** current and historical forecast execution remain
blocked by specific source/vintage dependencies, not a blanket SID certification
gate. See the [readiness report and 2024 monthly matrix](evidence/inputs/forecast_viability_f1/README.md).
`scripts/audit/assess_forecast_viability.py` and `--supplement` inspect bounded
forecasts/archives without solving or scoring. Prospective inspection has its own
forecast-only access path; historical guards and the 2026 holdout stay locked.

On every fresh run, the adapter queries EA/Shooju through
the existing helper, validates source identity, units/frequency, complete dates,
historical/forecast boundaries, signs and production import cohort, and retains
original responses and metadata before preparing model inputs. Incorrect essential
inputs stop optimisation with a failure package. Optional current comparisons are
queried separately; their failures remain visibly unavailable. Earlier observations
required for static preferences are essential and cannot use current outcomes.
Price-free routing, Snøhvit's historical conversion guard, existing provisional
capacities and the locked holdout are unchanged. A live full-model 2024
reconstruction has been demonstrated; it is revised history, not a forecast.

For an offline demonstration, copy `config/run.yaml` to a repository-local
`.scratch/demo-run.yaml`, change `input_source` to `synthetic_demo` and
`capacity_scenario` to `synthetic_fixture` for current mode, and pass
that path to the same command. This explicitly manufactures supply, capacity and
earlier training fixtures on the existing network. Every output says SYNTHETIC;
it is neither an EA reconstruction nor a forecast. No actual/legacy values or
forecast scores are invented.

Each invocation reserves a new `outputs/routing_runs/<UTC timestamp>_<unique id>/`;
existing packages, reconstructions and archives are never promoted or overwritten.
Open **results.xlsx** first. Read me defines every sheet and boundary; monthly
destination flows, group comparisons, capacities, arc flows, preferences, source
inventory, settings and diagnostics follow. The workbook is a typed numeric/date
snapshot with filters, frozen headers and a monthly flow chart after a solve.
Editing it does not rerun the optimiser. “Unavailable” means missing, unsolved or
incompatible, never assumed zero. EA actuals and forecasts remain unavailable in
synthetic packages. Future real comparisons must retain original groups, origins
and historical-segment checks; Poland/Nybro and signed Danish net values cannot
score gross physical exports.

For SID inputs, `provenance/raw/` contains exact returned observations, and
`source_metadata.json` retains query bounds, timestamps, raw/reported units,
transformations, provider vintages and validation status, including rejected
responses. The reviewed source contract and mapping ledger are copied into the
package. Compatible actual allocation proxies may appear alongside model flows;
forecast references remain unavailable. Failed optional queries never supply
training inputs or zero comparisons. Tests label manufactured SID responses as
MOCK, and use a fixture-specific topology/contract rather than altering the live
model. Run focused offline integration checks with the workspace interpreter and
`-m pytest tests/integration/test_fresh_routing_inputs.py` using the documented
repository-local temporary environment.

`results.csv` is one target month with seven destination bcm columns, exports,
supply, disposal and status. `details/` contains comparison/arc CSVs, independent
solver checks and charts; `report.html` explains the package. `input_sources.csv`
identifies required/consumed sources, dates, units and transformations.
`provenance/inputs/` retains exact prepared tables and preferences. Provenance also
contains source metadata, resolved settings, original code/configuration
snapshots, solver results/statistics and Git identity. `run_manifest.json` hashes
every package file except itself. CSV snapshots use 17 significant digits; Excel
shows six decimal places while retaining numeric precision.

Troubleshooting: inspect “Action required”, workbook Diagnostics and the manifest
blocker. Missing mappings need source review; empty/incompatible vintages must stop
the future adapter. A missing solver needs an approved installed backend. Permission
errors need the workspace path/ACL/file-lock diagnosis. No environment/package
change is automatic. Current mode permits only bounded prospective forecast
deliveries and matching-origin forecast responses; ordinary historical reads,
exports, fitting and scoring still reject dates after 2025 and the locked holdout.
Current real-data optimisation remains blocked on the explicit supply/units/
capacity decisions, with original responses retained. Historical replay and
walk-forward scoring are not implemented; their origin-bundle guards remain.

## Git baseline

The initial baseline retains code, tests, configuration, instructions and selected
lightweight evidence and registry migration metadata. Raw observations, workbooks,
generated results and historical archive bundles remain local and are not part of
the Git baseline. Links to those retained artifacts require the original local
workspace. Tests that consume retained historical evidence need those local files;
synthetic tests do not authorise new model runs or live data retrieval.

**Current sourcing rule:** new real-data runs must query EA/Shooju SIDs directly
each time; workbooks are formula/SID references only. The operational command
blocks incomplete real-source preparation. Older cached diagnostic commands are
retained for context and need separate explicit authorisation. The visual-report
command now uses fresh SID references; saved model results remain historical
evidence. Existing outputs remain available.
Historical retrieval is supported by
`project_data.get_registered_series(key, start, end, asof='2024-12-31T23:59:59Z')`.
Missing SIDs/origin values stop the affected run; there is no workbook fallback.

Start with [the output index](outputs/README.md). Each current assessment has
one HTML report and one main results CSV, with technical detail below them.

| Location | Contents |
|---|---|
| `config/` | Active model and series configuration |
| `src/norway_gas_routing/` | Reusable model, data and reporting code |
| `src/norway_gas_routing/capacity/` | Capacity inputs, constraints, conversions, maintenance and public evidence |
| `src/norway_gas_routing/reporting/` | Assessment reports, dashboard, figures, SID references and legacy adapters |
| `scripts/run/` | Reconstruction driver |
| `scripts/verify/` | Saved-evidence checks and routing diagnosis |
| `scripts/audit/` | Maintained input/source investigations |
| `tests/unit/`, `tests/integration/` | Synthetic behaviour and workflow tests |
| `data/raw/` | Original retained inputs; workbooks in `legacy/` |
| `evidence/inputs/`, `evidence/legacy/` | Reusable audit findings and workbook investigations |
| `outputs/reconstruction/`, `outputs/benchmark/` | Current successful assessments |
| `archive/YYYYMMDD-NN_description/` | Meaningful frozen milestones and original identities |
| `.scratch/` | Disposable experiments, test outputs and caches; ignored by Git |

Create processed inputs, shared fixtures or notebooks only when actually used.
The compact new-file gate and naming rules are in [AGENTS.md](AGENTS.md).

The executable model is `routing.py`; input preparation is `routing_inputs.py`,
and its configuration section is `routing`. Install the solver dependencies with
the `routing` extra when setting up an approved environment. Archived code,
historical manifest keys and persisted database identifiers retain their original
names for provenance; they are not active module names.

Run from this repository with the approved workspace interpreter. Prepare scratch
parents first; pytest creates its basetemp directory but not missing parents:

```powershell
New-Item -ItemType Directory -Force .scratch/tmp, .scratch/tests | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = (Resolve-Path '.scratch/tmp').Path
$env:TMP = $env:TEMP
$env:MPLCONFIGDIR = Join-Path $env:TEMP 'matplotlib'
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' -m pytest -q -p no:cacheprovider --basetemp=.scratch/tests/current
```

Supported commands (append to that interpreter):

| Command | Purpose |
|---|---|
| `scripts/run/run_routing.py --config config/run.yaml` | Unique Excel-first operational package; explicit fresh-SID blocker; synthetic demonstration available |
| `scripts/run/run_snohvit_sensitivity.py` | Explicit full-year 2025 official/selected Snøhvit diagnostics in a new named experiment; no baseline promotion |
| `scripts/run/run_routing_flexibility.py` | Individual physical destination min/max at fixed 2025 stage-1 exports; no preference or price objective |
| `scripts/verify/diagnose_routing.py` | Cached before/after scenarios and physical/scoring checks |
| `scripts/verify/verify_initial_benchmark.py` | Read-only original forecast/archive verification |
| `scripts/verify/verify_repository.py` | Preserved source/result hashes, report links and layout audit |
| `scripts/audit/build_public_capacity.py` | Offline public SQLite capacity database and CSVs in a fresh experiment; no optimiser integration |
| `scripts/audit/build_capacity_candidates.py --output <new-directory>` | Read-only public capacity candidate layer, monthly preparation, identity and coverage exports; no production inputs or solver |
| `scripts/run/run_capacity_scenarios.py --help` | Explicit optional capacity comparisons; frozen-input mode requires a separately authorised SID-only exception |

The standalone [public capacity database](evidence/inputs/public_capacity_database.md)
retains source snapshots, separate Danish/Polish point histories and unknown
engineering availability. Its optional retrieval-only refresh command never
replaces pinned audit evidence or supplies active optimiser limits.

The initial benchmark is frozen. Its scoring/vintage functions remain
in `src/norway_gas_routing/benchmark.py`; the obsolete full replay driver is
retained inside the cleanup snapshot. Current refined configuration must not
silently replace the original assessment.
A new forecast assessment needs a reviewed contemporaneous input bundle.
The fixed protocol is in `config/evaluation.yaml`: development through 2024-12,
validation 2025-01–2025-12 for candidate comparison only, and locked final holdout
2026-01–2026-09. `evaluation.py` guards fitting, retrieval, cached reads, scores,
plots and assessment publication. Parameters cannot use 2025/2026 outcomes.
There is no routine holdout unlock flag. Explicit approval and a frozen model
identity are prerequisites for a separately implemented final evaluation.
Run manifests contain the split/hash, experiment identity, parameters/hash and
input vintages. The current routing model reader permits revised-input reconstructions;
it rejects genuine-forecast mode without a complete verified origin bundle.
Archive queries alone do not verify public release timing. The frozen benchmark
predates this protocol; its partial 2025 coverage is not a full validation run.
Audit commands may retrieve data or write proposals; cleanup does not authorise
new sourcing. Completed registry migrations are frozen inside the cleanup snapshot.

Temporary experiments use `.scratch/runs/YYYYMMDD-NN_short-description/`, such as
`20261009-02_capacity-review`. Describe what was tested, not the result. Sequence
considers existing scratch experiments and retained archives; never overwrite one.
Current successful assessment paths remain stable. Retain only meaningful
milestones under `archive/` and add them to the output index.

Authoritative records: [INPUTS.md](INPUTS.md) for data contracts,
[DECISIONS.md](DECISIONS.md) for accepted modelling choices,
[STATUS.md](STATUS.md) for current limitations and verification.
Original code/configuration/manifests and historical documents are frozen in the
cleanup milestone; path relocation is recorded without rewriting old evidence.
The full [cleanup plan](REPOSITORY_CLEANUP_PLAN.txt) is optional historical context.

The standalone retrieval helpers are in `src/norway_gas_routing/data_functions.py`;
project-aware registry helpers are in `project_data.py`. Preserve raw units,
timestamps, negatives and missing values before analytical validation.
Within this package both retrieval interfaces bound `MAX` to 2025-12-31 and
reject explicit later/relative requests. Old raw caches and pre-protocol findings
may contain later dates; they remain preserved, while routine Parquet readers
filter them before loading values. The historical sourcing-inventory writer is
disabled because its embedded findings include reserved-period observations.

## Reusable routing visual reports

The command below describes the previously generated offline graphics package.
It still reads retained comparison sources and must be migrated to fresh SID
queries before a new run under the current sourcing rule. It does not execute
the requested same-origin forecast backtest. See
[December 2024 origin readiness](archive/20261009-20_forecast-origin-readiness/report.md).

Build presentation graphics and CSV tables from saved solver results, without running
the optimiser, retrieving observations or recalculating Excel:

```powershell
New-Item -ItemType Directory -Force .scratch/tmp | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = (Resolve-Path '.scratch/tmp').Path
$env:TMP = $env:TEMP
$env:MPLCONFIGDIR = Join-Path $env:TEMP 'matplotlib'
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/run/build_routing_visuals.py
```

Open `outputs/routing_graphics/details/` for the PNG/SVG graphics, organised
by model run, scenario and year. `outputs/routing_graphics/figures.csv` lists
every graphic's relative path. `results.csv` contains the supply/export totals;
`details/*.csv` contains comparisons, map flows, capacities and allocation shares.
Source ledgers and verification are in `provenance/`. The default package
includes the saved 2024 reconstruction and official-net-production 2025 diagnostic,
both retained legacy forecast origins, cached workbook history as separate context,
PNG/SVG figures and one-page visual briefings. No dashboard is generated by default.
The earlier dashboard in `outputs/routing_visuals/` is preserved. Use `--html`
only if an optional self-contained dashboard is wanted alongside the graphics.

Rerun this command at any time to regenerate from the selected saved results.
It does not run the optimiser or automatically select a newer archive. Use
`--run` for a new saved result and `--output` for a separate dated export folder.
Rerunning into the same folder replaces generated files of the same name.

Select an individual archive, scenario, period and comparison source:

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/run/build_routing_visuals.py --run archive/20261009-13_snohvit-sensitivity --scenario official-net-production --legacy-source retained:2024-06-30 --legacy-source workbook --start 2025-01 --end 2025-12 --output outputs/routing_graphics_2025
```

Repeat `--run` to compare multiple saved runs. If `--scenario` is supplied,
provide one per `--run`, in matching order. Available sources are `workbook`
and `retained:YYYY-MM-DD` for an origin in the frozen benchmark. Optional
`--legacy-archive` chooses a retained forecast folder using the benchmark export
and verification schema. `--legacy-workbook` chooses another workbook with the same verified cached-cell
contract. A changed formula path or unit fails closed. The selected mixed-vintage
2025 diagnostic is also supported; it retains its diagnostic label. Unsupported
archive schemas or new topology nodes need a reviewed adapter/layout, rather than
guessing a connection. No new package installation is required in the current
workspace environment.

Run the focused reporting tests with the workspace interpreter:
`-m pytest -q -p no:cacheprovider --basetemp=.scratch/tests/visual_reporting tests/unit/test_visual_reporting.py`.
Checks reconcile countries/groups, saved graph/flows, capacities, disposal and
annual sums. Source cell and forecast-point ledgers record exact values, original
units, formula ranges, vintages and hashes. Missing values remain missing.
Charts are regenerated from these data; no figures are hardcoded from an experiment.

The workbook's historical Poland-labelled upload is total Nybro entry, so direct
Polish comparisons are withheld. Individual FR/BE/NL/DE legacy forecasts and a
full-year 2025 legacy forecast are unavailable. Matched partial periods are shown
separately, with no extrapolation or observation substitution. Named legacy totals
retain their original difference from the sum of destination allocations.
See [the source definitions and exact ranges](evidence/legacy/visual_reporting_sources.md).

This pipeline reports revised reconstructions and diagnostics, not genuine current
forecasts. Its adapters reuse saved output tables and producer identities. The
fixed evaluation policy currently blocks dates after 2025. Future forecast reports
through December 2030 require real origin-bundle outputs and a separately approved
forward-reporting policy; there is no bypass flag and no holdout access.
