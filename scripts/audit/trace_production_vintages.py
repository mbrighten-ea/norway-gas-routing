"""Compare retained production imports at a common Shooju job vintage."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from norway_gas_routing.evaluation import read_parquet
RAW = ROOT / 'data/raw/series_audit'


def main():
    audit = pd.read_csv(ROOT / 'evidence/inputs/data_series_audit.csv', keep_default_na=False).set_index('sid')
    prefix = 'teams\\natural_gas\\EUR\\'
    def retained(sid):
        return read_parquet(ROOT / audit.loc[sid, 'raw_file']).value
    def snapshot(job, number):
        return read_parquet(RAW / f'core_production_asof_{job}_{number}.parquet').iloc[:, 0]
    old_sid = next(s for s in audit.index if s.endswith('gas_production'))
    total_2022, excl_2022, snohvit_2022 = [snapshot(15462336, n) for n in range(3)]
    total_now = retained(prefix + 'NO_production')
    excl_now = retained(prefix + 'NO_production_excl_Snohvit')
    field_now = retained(prefix + 'NO_production_Snohvit_field')
    frame = pd.concat([total_2022.rename('total_2022'), excl_2022.rename('excl_2022'),
                       snohvit_2022.rename('snohvit_rate_2022'), total_now.rename('total_retained'),
                       excl_now.rename('excl_retained'), field_now.rename('field_rate_retained')], axis=1)
    days = frame.index.days_in_month
    frame['common_2022_residual_bcm'] = frame.total_2022 - frame.excl_2022 - frame.snohvit_rate_2022 * days / 1000
    frame['total_revision_bcm'] = frame.total_retained - frame.total_2022
    frame['excl_revision_bcm'] = frame.excl_retained - frame.excl_2022
    frame['snohvit_revision_bcm'] = (frame.field_rate_retained - frame.snohvit_rate_2022) * days / 1000
    frame['mixed_vintage_residual_bcm'] = frame.total_retained - frame.excl_retained - frame.field_rate_retained * days / 1000
    frame['revision_explained_residual_bcm'] = frame.total_revision_bcm - frame.excl_revision_bcm - frame.snohvit_revision_bcm
    frame.to_csv(ROOT / 'evidence/inputs/core_production_vintage_decomposition.csv', index_label='month')
    def summary(s):
        s = s.dropna()
        return {'n': len(s), 'max_abs_bcm': float(s.abs().max()), 'mean_bcm': float(s.mean())}
    jobs = {}
    for number, sid in enumerate([prefix + 'NO_production', prefix + 'NO_production_excl_Snohvit',
                                 prefix + 'NO_production_Snohvit_field', old_sid]):
        records = json.loads((RAW / f'core_revision_jobs_{number}.json').read_text())
        jobs[sid] = records[0] if records else None
    result = {
        'source': 'Retained metadata plus helper_functions_ea ShoojuTools read-only job and as-of retrieval methods.',
        'source_path': r'E:\2. Research - Gas\2. Spreadsheets\1. Europe\SO Data\Norway\Norwegian production model.xlsx',
        'workbook_access': 'Exact path absent; no E drive available. No workbook copy retained in this repository. Exact-name SharePoint search could not execute because connector is not connected.',
        'latest_returned_change_jobs': jobs,
        'job_history_limit': 'Helper bounds revision history to retained changing/adding/deleting jobs; this proves returned import changes, not immutable workbook file versions or no-op runs.',
        'common_2022_observed_exclusion_formula': 'excl_bcm = total_bcm - snohvit_monthly_average_mcm_d * calendar_days_in_month / 1000; algebra observed from exports, Excel cell references not read.',
        'common_2022_historical_through_2022_08': summary(frame.loc[:'2022-08', 'common_2022_residual_bcm']),
        'common_2022_forecast_from_2022_09': summary(frame.loc['2022-09':'2025-12', 'common_2022_residual_bcm']),
        'excl_latest_equals_2022_snapshot_max_abs': float((excl_now - excl_2022).abs().max()),
        'older_snohvit_latest_equals_2022_snapshot_max_abs': float((retained(old_sid) - snohvit_2022).abs().max()),
        'field_latest_equals_2025_import_max_abs': float((field_now - snapshot(27343398, 4)).abs().max()),
        'mixed_vintage_residual_minus_revision_decomposition': summary(frame.mixed_vintage_residual_bcm - frame.revision_explained_residual_bcm),
        'negative_accounting_limit': 'Official net-gas entries reproduce the historical negatives; gross well production is a different measure. Available net/gross aggregates do not uniquely identify fuel, imports, inventory, allocation or corrections. No causal explanation adopted.',
        'aug_sep_2025_limit': 'Both discrepancies were already in the October 16 2025 import, which is unchanged. No earlier Directorate publication snapshot or workbook cell formula is retained to distinguish estimates from later source revisions.',
        'gassco_scope': 'Scraper investigation and external repository access stopped at explicit user instruction; no code repository downloaded or local sibling scraper repo scanned.',
    }
    (ROOT / 'evidence/inputs/core_production_source_trace.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
