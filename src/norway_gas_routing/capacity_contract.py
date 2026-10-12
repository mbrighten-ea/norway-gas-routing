"""Read-only checks for an inactive public point-capacity proposal.

No model adapter or energy-to-volume conversion is provided here.
"""
import json
import hashlib
from pathlib import Path
import sqlite3

import yaml

IDENTITIES = {
    'point:north_sea_technical': ('DK-TSO-0001', 'ITP-00630', 'entry', 'NORTH_SEA_ENTRY'),
    'point:faxe_dk_technical': ('DK-TSO-0001', 'ITP-10009', 'exit', 'BALTIC_PIPE'),
    'point:faxe_pl_technical': ('PL-TSO-0002', 'ITP-10009', 'entry', 'PL_DELIVERY'),
}
ARCS = {
    'EUROPIPE_II': ('KARSTO', 'EUROPIPE_II_SPLIT', 'EUROPIPE_II'),
    'NORTH_SEA_ENTRY': ('EUROPIPE_II_SPLIT', 'DANISH_TRANSIT', 'NORTH_SEA_ENTRY'),
    'DK_OFFTAKE': ('DANISH_TRANSIT', 'DK', None),
    'BALTIC_PIPE': ('DANISH_TRANSIT', 'FAXE', 'BALTIC_PIPE'),
    'PL_DELIVERY': ('FAXE', 'PL', None),
}


def validate_contract(contract, model, db):
    """Fail closed if proposal identity, scope, or its inactive gate changes."""
    if contract['enabled'] or contract['status'] != 'proposal_only':
        raise ValueError('This contract must remain inactive')
    if contract['window'] != ['2023-01-01', '2025-12-31']:
        raise ValueError('Historical window must exclude holdout gas-day labels')
    arcs = {a['id']: a for a in model['poc']['arcs']}
    for name, expected in ARCS.items():
        if tuple(arcs[name][k] for k in ('from', 'to', 'asset')) != expected:
            raise ValueError('Shared corridor/topology changed: ' + name)
    mappings = contract['mappings']
    if len(mappings) != 3 or {m['database_asset'] for m in mappings} != set(IDENTITIES):
        raise ValueError('Exactly three separate point mappings required')
    for mapping in mappings:
        identity = IDENTITIES[mapping['database_asset']]
        if tuple(mapping[k] for k in ('operator', 'point', 'direction', 'candidate_arc')) != identity:
            raise ValueError('Operator/point/direction/arc mismatch')
        actual = db.execute('SELECT operator_key,point_key,direction FROM assets WHERE asset_key=?',
                            (mapping['database_asset'],)).fetchone()
        if actual is None or tuple(actual) != identity[:3]:
            raise ValueError('Database point identity mismatch')
        if (mapping['category'] != 'point_technical' or mapping['original_unit'] != 'kWh/d'
                or mapping['status'] != 'conditional' or mapping['replace_existing']):
            raise ValueError('Unapproved constraint category/replacement')
        conversion = mapping['conversion']
        if conversion['approved'] or conversion['capacity_basis_kwh_per_model_m3'] is not None:
            raise ValueError('Unsupported energy-to-bcm conversion')
    groups = contract['shared_constraints']
    if groups != {
        'upstream': {'asset': 'EUROPIPE_II', 'includes': ['DE', 'DK', 'PL']},
        'north_sea_entry': {'arc': 'NORTH_SEA_ENTRY', 'includes': ['DK', 'PL']},
        'faxe': {'arcs': ['BALTIC_PIPE', 'PL_DELIVERY'], 'includes': ['PL'],
                 'combination': 'separate_serial_inequalities_never_sum'},
    }:
        raise ValueError('Shared constraints cannot be added/interchanged')
    return True


def inspect_contract(root, contract_path):
    """Bounded retrospective diagnostics. Opens the retained SQLite file read-only."""
    root = Path(root).resolve()
    contract = json.loads(Path(contract_path).read_text(encoding='utf-8'))
    model = yaml.safe_load((root/'config/model.yaml').read_text(encoding='utf-8'))
    database = (root/contract['database']).resolve()
    if not database.is_relative_to(root):
        raise ValueError('Database must be in this repository')
    for name, expected in contract['input_sha256'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Proposal input changed; re-audit required: '+name)
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
        validate_contract(contract, model, db)
        db.row_factory = sqlite3.Row
        coverage = []
        for mapping in contract['mappings']:
            for year, expected in [('2023',365), ('2024',366), ('2025',365)]:
                rows = list(db.execute('SELECT * FROM daily WHERE asset_key=? AND gas_day BETWEEN ? AND ? ORDER BY gas_day',
                                      (mapping['database_asset'],year+'-01-01',year+'-12-31')))
                asset = mapping['existing_model_asset']
                assumption = model['poc']['assets'][asset]
                values = [r['technical_kwh_per_gas_day'] for r in rows if r['quality'] in ('complete','reported_zero') and r['technical_kwh_per_gas_day'] is not None]
                coverage.append(dict(database_asset=mapping['database_asset'], year=year,
                    expected_days=expected, recorded_days=len(rows), known_days=len(values),
                    missing_days=expected-len(values), reported_zero_days=sum(v==0 for v in values),
                    min_kwh_per_source_gas_day=min(values) if values else None,
                    max_kwh_per_source_gas_day=max(values) if values else None,
                    model_asset=asset, model_value=assumption.get('mcm_d',assumption.get('annual_bcm')),
                    model_unit='mcm/d' if 'mcm_d' in assumption else 'bcm/year',
                    comparable_bcm=None, numerical_model_difference=None,
                    comparison_status='unsupported_conversion_and_partial_boundary',
                    vintage_status='latest_revised_origin_unverified'))
        differences = [dict(r) for r in db.execute('''SELECT a.gas_day,
            a.technical_kwh_per_gas_day AS dk_exit_kwh_per_source_gas_day,
            b.technical_kwh_per_gas_day AS pl_entry_kwh_per_source_gas_day,
            a.gas_day_hours, a.gas_day_start, a.gas_day_end,
            a.source_record_ids_json AS dk_record_ids, b.source_record_ids_json AS pl_record_ids,
            a.source_revisions_json AS dk_revisions, b.source_revisions_json AS pl_revisions,
            a.vintage_status AS vintage_status
            FROM daily a JOIN daily b ON a.gas_day=b.gas_day
            WHERE a.asset_key='point:faxe_dk_technical' AND b.asset_key='point:faxe_pl_technical'
            AND a.gas_day BETWEEN '2023-01-01' AND '2025-12-31'
            AND a.quality='complete' AND b.quality='complete'
            AND a.technical_kwh_per_gas_day<>b.technical_kwh_per_gas_day ORDER BY a.gas_day''')]
    return coverage, differences
