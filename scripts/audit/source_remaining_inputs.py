"""Targeted read-only SID discovery and small samples for sourcing gaps."""
import hashlib
import json
from pathlib import Path

import pandas as pd
from helper_functions_ea import ShoojuTools, check_env

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from norway_gas_routing.evaluation import ROUTINE_END, check_dates
OUT = ROOT / 'data/raw/series_audit/sourcing_followup'


def main():
    OUT.mkdir(exist_ok=True)
    check_env()
    sj = ShoojuTools(silence_alerts=True)
    queries = ['energy_product=natural_gas economic_property=price country_iso=GB',
               'energy_product=natural_gas economic_property=price country_iso=NL',
               'energy_product=natural_gas economic_property=price country_iso=DE',
               'energy_product=natural_gas economic_property=price country_iso=BE',
               'energy_product=natural_gas economic_property=price country_iso=FR',
               'energy_product=natural_gas economic_property=price country_iso=DK',
               r'sid:teams\natural_gas\price', r'sid:eex2\indices',
               r'sid:eex2\spot\day_ahead',
               r'sid:eex2\future\month\etf']
    for query in queries:
        name = hashlib.sha256(query.encode()).hexdigest()[:16]
        path = OUT / ('query_' + name + '.json')
        if path.exists():
            continue
        frame = sj.get_fields_from_query(query, fields=['series_id'])
        record = {'query': query, 'retrieved_at': pd.Timestamp.now(tz='UTC').isoformat(),
                  'sids': frame.index.tolist()}
        path.write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(query, len(frame), flush=True)
    for point in ['NPT', 'EPT1']:
        for direction in ['entry', 'exit']:
            sid = rf'ENTSOG\transport_point\NL-TSO-0001\Emden ({point}) (GTS)\{direction}\Firm Technical'
            sample(sj, sid)
    for hub in ['nbp', 'ttf', 'THE', 'ZTP', 'peg']:
        sample(sj, 'teams\\natural_gas\\price\\' + hub, full=True)
        sample(sj, 'eex2\\future\\month\\' + hub.lower() + '\\settlement_price\\future_curve', full=True)
    sample(sj, r'teams\natural_gas\price\NBP_EUR_MWh', full=True)
    sample(sj, r'teams\natural_gas\price\TTF_forecaster', full=True)
    for hub in ['nbp', 'ttf', 'the', 'ztp', 'peg', 'etf']:
        sample(sj, rf'eex2\indices\egix_day\{hub}', full=True)
    sample(sj, r'eex2\future\month\etf\settlement_price\future_curve', full=True)
    for hub in ['ttf', 'the', 'ztp', 'peg', 'etf']:
        sample(sj, rf'eex2\spot\day_ahead\{hub}\last_price', full=True)


def sample(sj, sid, full=False):
    name = hashlib.sha256(sid.encode()).hexdigest()[:16]
    path = OUT / (name + '.json')
    if path.exists():
        return
    record = {'sid': sid, 'retrieved_at': pd.Timestamp.now(tz='UTC').isoformat()}
    try:
        record['metadata'] = sj.get_fields_from_sid(sid, fields=['*'])
        record['samples'] = []
        windows = [('2025-01-01', '2025-01-08')]
        if full:
            windows = [('MIN', ROUTINE_END)]
        for start, finish in windows:
            values = sj.get_points_from_sid_into_series(sid, start, finish, -1)
            check_dates(values.index, 'read')
            label = start.replace('-', '')
            values.to_frame('value').to_parquet(OUT / (name + '_' + label + '.parquet'))
            valid = values.dropna()
            record['samples'].append({'start': start, 'finish': finish, 'n': len(values),
                'first_valid': str(valid.index.min()), 'last_valid': str(valid.index.max()),
                'min': valid.min(), 'max': valid.max(),
                'median': valid.median(), 'missing': int(values.isna().sum()),
                'negatives': int((values < 0).sum()), 'duplicates': int(values.index.duplicated().sum()),
                'spacing': values.index.to_series().diff().value_counts().astype(int).to_dict()})
        print(sid, [(r['start'], r['n']) for r in record['samples']], flush=True)
    except Exception as error:
        record['error_type'] = type(error).__name__
        print(sid, type(error).__name__, flush=True)
    # Timedelta dictionary keys need explicit strings for JSON.
    for row in record.get('samples', []):
        row['spacing'] = {str(k): v for k, v in row['spacing'].items()}
    path.write_text(json.dumps(record, indent=2, default=str), encoding='utf-8')


if __name__ == '__main__':
    main()
