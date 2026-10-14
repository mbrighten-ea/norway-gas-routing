# Norwegian gas routing

A monthly, price-free physical routing model for Norwegian pipeline gas. It uses
EA/Shooju production forecasts, supported source-node ownership, capacity envelopes
and historical destination preferences to allocate gas to UK, France, Belgium,
Germany, Netherlands, Denmark and Poland. Each month solves independently with
the existing PuLP/HiGHS optimiser.

Results are a **provisional partial-coverage physical-routing POC**, not a commercial
forecast or a complete Norwegian export forecast. DE/NL are allocation proxies;
DK/PL are corridor allocations. Unknown production stays unmapped and unrouted.

## Run a forecast

Edit **[config/run.yaml](config/run.yaml)**. It is the only analyst run request.
`config/model.yaml` defines the model, `config/data_series.csv` is the SID registry,
and `config/evaluation.yaml` protects historical evaluation. Do not edit these
developer inputs to select a run scenario.

The shipped run request preserves the original 12-month default and older blocked
input contract. To use the approved provisional reference, select these existing
options in that same file:

```yaml
physical_input_contract: core_f24
heidrun_treatment: export_eligible
capacity_scenario: core_f24_156
forecast_end_month: null
compare_scenarios: false
```

The commented recipe is also in `run.yaml`. Set `compare_scenarios: true` for all
four approved cases in one combined Excel workbook:

| Case | Heidrun | Kollsnes |
|---|---|---|
| A reference | No additional domestic deduction | 156 minus verified unavailability |
| B domestic bound | Forecast component outside the network | Same reference |
| C capacity stress | No additional domestic deduction | 143/156 times reference availability |
| D combined stress | Forecast component outside the network | Same stress |

For a single stress case use `core_f24_proportional_143`; for the hypothetical
Heidrun exclusion use `domestic_bound`. These are existing assumptions, not fitted
alternatives or best-estimate domestic consumption.

From the repository root, prepare the approved workspace interpreter's local scratch:

```powershell
New-Item -ItemType Directory -Force .scratch/tmp | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = (Resolve-Path '.scratch/tmp').Path
$env:TMP = $env:TEMP
$env:MPLCONFIGDIR = Join-Path $env:TEMP 'matplotlib'
```

Validate inputs before solving:

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/run/run_routing.py --config config/run.yaml --validate-only
```

Run the forecast with the same command, omitting `--validate-only`:

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/run/run_routing.py --config config/run.yaml
```

The command prints status, delivery period, scenario, the primary Excel path and
qualifications. Exit 0 means completed or validated-only; exit 2 means blocked or
failed. Validation-only produces no country forecast and never constructs an LP.
Do not invoke the internal four-scenario implementation as another runner.

## Period, inputs and results

`origin: null` captures this execution's UTC origin. An explicit origin must be in
the current UTC month, no later than execution. Deliveries start with the first
complete month after the origin. Keep `start` and `end` null for current forecasts.
`horizon_months: 12` is the default; a non-null quoted `forecast_end_month` takes
precedence. October 2026 to `'2029-12'` gives 38 months; `'2030-12'` gives 50.
The existing maximum is 60 months and the endpoint cannot exceed December 2030.

Fresh, origin-matched SIDs supply operational inputs. Workbook caches and saved
release snapshots are not operational fallbacks. Missing coverage, duplicate
ownership, negative residuals or invalid maintenance retain `BLOCKED_INPUTS`.
The selected Snøhvit source was verified through December 2029; missing 2030
observations block longer live runs. No source or maintenance is extrapolated.

Open the Excel path printed by the runner:

- Single case: `outputs/routing_runs/<run>/results.xlsx`.
- Four cases: `outputs/forward_scenarios/<run>/results.xlsx`, combining monthly and
  annual country flows, scenario differences, accounting, coverage and constraints.

CSV, HTML and charts support the workbook. Each case retains resolved requests,
SID metadata/raw responses, supply/capacity tables, solver results and hashes in
`provenance/`. Original YAML snapshots remain inside released packages. All four
cases use the same source boundary and approved scenario definitions.

Frozen 2024 residual shares approximate future field mix. Snøhvit's rate conversion
and mixed vintage, external Trym exclusion, unmapped production and provisional
technical capacities remain disclosed. See [INPUTS.md](INPUTS.md) for contracts,
[DECISIONS.md](DECISIONS.md) for approvals and [STATUS.md](STATUS.md) for limitations.

## Retained outputs

These packages are committed, including their inputs and provenance; they do not
depend on a temporary worktree or local untracked fixtures. Use the integrated
branch containing them. The older main checkout remains on an investigation branch.

| Package | Primary result |
|---|---|
| Original F2.4 and hardened F2.6 | [Combined Excel](outputs/forward_scenarios/20261013_f26/results.xlsx); [original report](outputs/forward_scenarios/20261013T134952692166Z/report.html) |
| F2.7 fresh October-origin acceptance | [Combined Excel](outputs/forward_scenarios/20261013T165915778836Z/results.xlsx); [report](outputs/forward_scenarios/20261013T165915778836Z/report.html) |
| F2.8 seasonal inputs and rolling-weight evidence | [Assumption comparison](outputs/chronological_inputs_f28/report.html) |
| F2.10 first 2025 accuracy comparison | [Excel](outputs/revision_tolerant_2025/results.xlsx); [report](outputs/revision_tolerant_2025/report.html) |
| F2.11 routing-error attribution | [Report and monthly table](outputs/routing_error_attribution_2025/report.html) |
| F2.13 physical validation and commercial-choice design | [Decision report](outputs/physical_commercial_gate_f213/report.html) |

The 2025 comparison is a revision-tolerant historical reconstruction, not a verified
real-time backtest. No target-year actuals entered forecast inputs; normalisation
in the error diagnostic is post-forecast only. January–September 2026 actuals remain
locked. Historical preferences, approved forward weights and all released results
are unchanged by cleanup.

Verify/replay the retained forward release without source retrieval:

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' scripts/verify/verify_forward_scenarios.py outputs/forward_scenarios/20261013_f26 --replay
```

Use the F2.7 summary path instead to verify that release. This checks hashes,
ownership, accounting, capacity limits and monthly replay to 1e-7 bcm. Do not use
`--write-validation` on a frozen package. Verify the historical comparison with:

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' outputs/revision_tolerant_2025/provenance/code/verify_results.py
```

## Tests and project layout

Ordinary regressions run offline using synthetic fixtures:

```powershell
& 'C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe' -m pytest -q
```

Fourteen `retained_evidence` tests are reported separately as deselected. They
require the original public-capacity audit and SQLite bundle; run with
`--run-evidence -m retained_evidence` only after restoring those prerequisites.
Missing prerequisites produce an explicit error. Required paths are
`evidence/inputs/public_capacity_audit_manifest.json`,
`evidence/inputs/public_capacity_verification.json`, their referenced raw/evidence
files and `archive/20261009-17_public-capacity-database/database/capacity.sqlite`.
The database SHA-256 is `5e6e2b14c76a0afb94aa487e316c617f37fd78f95f117d96ec30232b180721a4`.
Do not regenerate historical evidence to fit a test or change the shared environment.

| Directory | Purpose |
|---|---|
| `config/` | One analyst run request; developer model, SID registry and evaluation policy |
| `src/norway_gas_routing/` | Optimiser, source accounting and input preparation; `capacity/` and `reporting/` retain their existing roles |
| `scripts/run/` | Supported runner and explicitly authorised specialist diagnostics |
| `scripts/verify/`, `scripts/audit/` | Release checks and bounded source investigations |
| `tests/unit/`, `tests/integration/` | Offline regression and workflow checks |
| `data/raw/`, `evidence/` | Original source captures and reusable evidence |
| `outputs/` | Committed releases and meaningful current assessments, indexed above |
| `archive/` | Frozen earlier milestones; optional old cleanup plan/verifier under `20261009-01_repository-cleanup/` |
| `.scratch/` | Ignored experiments, disposable logs, plots, test output and local worktrees |

New timestamped run/comparison packages are ignored by Git until deliberately
retained. Validate every manifest reference and hash, then stage the exact complete
release paths with `git add -f`, including configuration snapshots. Already committed
packages remain tracked and unchanged. Do not stage all generated output by default.

Only `config/model.yaml.routing` defines the executable seven-destination LP
network. Top-level source groups remain input memberships; the retained six-market
foundation supports metadata, diagnostics and public-capacity validation. It is not
another operational optimiser. See [config/README.md](config/README.md).

Current input preparation is `forecast_inputs.py`/`operational.py`; the historical
workbook adapter in `routing_inputs.py` is retained for explicitly authorised older
diagnostics. Other specialist commands may retrieve data or need local archive
bundles; they are not the normal forecasting workflow. Do not delete untracked
source evidence, historical snapshots or unpushed worktrees during housekeeping.
