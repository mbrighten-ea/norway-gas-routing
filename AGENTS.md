# Repository operating rules

- This is an independent Git repository. Work only inside this repository and preserve existing edits, including the index.
- Use one worker unless the task explicitly authorises helpers.
- Query EA/Shooju SIDs directly on every new data-consuming model, evaluation or reporting run. Historical forecasts use explicit origin-matched `@asof` queries. Workbooks are references for formulas and SID identification only; never scrape cached workbook numbers into active inputs or use retained caches as a substitute for a fresh SID query. Keep saved solver results and immutable historical evidence; record fresh responses and metadata for provenance. Missing SIDs/origin values are blockers, not permission to substitute data. Keep the 2026 holdout locked.
- Every Python command must use `C:\Users\martell.brighten\Documents\repos\.envs\env1.0\python.exe`. Do not use another interpreter or change the shared environment/packages without approval. Report access or dependency blockers.
- Follow the parent [Windows sandbox access procedure](../README_AGENT_WORKSPACE.md#windows-sandbox-access). Distinguish file locks from access restrictions before retrying writes; Windows error 32 was confirmed for `config/data_series.csv` on 2026-10-08.
- The lead modeller approves material scope, methodology, judgemental assumptions and production readiness. Record unresolved material choices in `STATUS.md`; stop the affected implementation before embedding a choice.
- Work affecting only files in this repository is authorised without further approval. Never modify files outside `norway-gas-routing`. External publication and deployment require explicit authorisation.
- Read targeted context and use proportionate verification. Use `README.md`, `INPUTS.md`, `DECISIONS.md` and `STATUS.md` for their distinct purposes; do not duplicate them or create process artefacts without a need.
- File placement: reusable code in `src/`; commands in `scripts/run`, `scripts/verify`, `scripts/audit`; synthetic tests in `tests/unit` or `tests/integration`; authoritative inputs in `data/raw`; reusable findings in `evidence`; current assessments in `outputs/<assessment>/{report.html,results.csv,details/,provenance/}`. Create folders only when needed.
- Within `src/norway_gas_routing/`, keep capacity components in `capacity/` and visual/reporting components in `reporting/`. Use descriptive routing names; do not introduce `poc` in active code or future filenames. Preserve historical archive names and identities.
- New-file gate: require a concrete consumer/decision/evidence purpose, reuse an existing artifact where possible, and choose active/evidence/archive/temporary retention. Regenerable intermediates and test outputs belong in ignored `.scratch/`. Keep original data and meaningful provenance; do not retain obsolete loose scripts or empty placeholders.
- Experiments use `.scratch/runs/YYYYMMDD-NN_short-description/`; date/sequence ensure uniqueness and description says what changed/tested, not the outcome. Never overwrite experiments. Archive meaningful milestones under the same names and link them from the retained-output table in `README.md`; current successful assessments keep stable paths. Detailed IDs/vintages/settings belong in manifests.
- These bullets are the durable structure rules. Read `README.md` only for commands/details; the old plan/verifier under `archive/20261009-01_repository-cleanup/` and archive snapshots are historical references, not mandatory routine context. `STATUS.md` holds current evidence/blockers.
- Use synthetic fixtures for unit tests; do not require live EA services. No external data sourcing unless the task authorises it.
- Keep analyst-readable code: small functions/modules, pandas and ordinary dictionaries/lists. Keep network rows as YAML dictionaries. Add an abstraction or dependency only when it solves a demonstrated current problem; keep analytical equations visible.

## Project Git additions

- Use `STATUS.md` for short restart notes on multi-session tasks; include the next exact action and links to relevant evidence.
- The external-publication approval rule above includes Git pushes. An existing remote or upstream alone does not authorise publication.
