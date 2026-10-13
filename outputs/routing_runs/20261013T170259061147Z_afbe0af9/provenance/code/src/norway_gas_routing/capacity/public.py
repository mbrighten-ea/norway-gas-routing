"""Offline public capacity evidence database; deliberately unconnected to the LP.

Snapshot specifications never become dated daily limits. ENTSOG quantities are
published point technical kWh per source gas day, not upstream availability.
"""
from datetime import date, datetime, timedelta, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
from importlib.metadata import version

import pandas as pd
import yaml

VERSION = 'public-capacity-v1'
GAS_TIMEZONE = 'Europe/Brussels'
PILOT = {
    'north_sea_technical': ('DK-TSO-0001', 'ITP-00630', 'entry', 'NORTH_SEA_ENTRY'),
    'faxe_dk_technical': ('DK-TSO-0001', 'ITP-10009', 'exit', 'BALTIC_PIPE'),
    'faxe_pl_technical': ('PL-TSO-0002', 'ITP-10009', 'entry', 'BALTIC_PIPE'),
}
CATEGORIES = {'Firm Technical': 'point_technical', 'Firm Available': 'commercial_available'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def instant(value):
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError('Validity times must be timezone-aware')
    return result.astimezone(timezone.utc)


def gas_boundary(day):
    # Localise each boundary independently. Adding 24 elapsed hours is wrong at DST.
    return pd.Timestamp(f'{day.isoformat()} 06:00').tz_localize(GAS_TIMEZONE).to_pydatetime()


def historical_window(start, end):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if not date(2021, 1, 1) <= start <= end <= date(2025, 12, 31):
        raise ValueError('Supported historical gas-day labels are 2021-2025 only')
    return start, end


def validate_capture(payload, identity, indicator='Firm Technical'):
    """Validate complete single audit capture; refresh assembles pages separately.

    Exact duplicate JSON observations collapse for expansion, but remain in raw
    capture. A reused record ID with different content fails, even if value agrees.
    Conflicting interval overlaps are flagged by expansion, never silently chosen.
    """
    rows, meta = payload['operationaldatas'], payload['meta']
    if meta.get('count') != len(rows) or meta.get('total') != len(rows):
        raise ValueError('Pagination/count mismatch: complete capture required')
    if meta.get('offset', 0) != 0:
        raise ValueError('Capture must include the first page')
    unique = {}
    for row in rows:
        if tuple(row.get(k) for k in ('operatorKey', 'pointKey', 'directionKey')) != tuple(identity):
            raise ValueError('Operator/point/direction identity mismatch')
        if row.get('indicator') != indicator or indicator not in CATEGORIES:
            raise ValueError('Capacity indicator mismatch')
        if row.get('unit') != 'kWh/d' or row.get('periodType') != 'day':
            raise ValueError('Pilot requires published daily kWh/d quantities')
        if row.get('lastUpdateDateTime'):
            instant(row['lastUpdateDateTime'])
        a, b = instant(row['periodFrom']), instant(row['periodTo'])
        if b <= a:
            raise ValueError('Empty/reversed validity interval')
        value = row.get('value')
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or value < 0):
            raise ValueError('Invalid reported capacity')
        key, encoded = row['id'], canonical(row)
        if key in unique and unique[key][0] != encoded:
            raise ValueError('Conflicting duplicate record ID')
        unique[key] = (encoded, row)
    return [unique[key][1] for key in sorted(unique)]


def usable(row):
    return (row.get('value') is not None
            and str(row.get('isNA')).lower() not in ('true', '1')
            and str(row.get('isUnlimited')).lower() not in ('true', '1'))


def expand_intervals(rows, start, end):
    """Half-open interval coverage; unknown partial/conflicting days stay null.

    Never prorate a daily published quantity across an unsupported partial day.
    Identical overlapping quantities can establish coverage without being summed.
    All contributing IDs/revisions survive in lineage, including NA observations.
    """
    start, end = historical_window(start, end)
    intervals = [(instant(r['periodFrom']), instant(r['periodTo']), r) for r in rows]
    result = []
    day = start
    while day <= end:
        local_a, local_b = gas_boundary(day), gas_boundary(day + timedelta(days=1))
        a, b = local_a.astimezone(timezone.utc), local_b.astimezone(timezone.utc)
        hits = [(s, e, r) for s, e, r in intervals if s < b and e > a]
        bounds = sorted({a, b} | {max(a, s) for s, e, r in hits} | {min(b, e) for s, e, r in hits})
        covered, conflict, values = 0, False, set()
        for x, y in zip(bounds, bounds[1:]):
            segment = [r for s, e, r in hits if s <= x and e >= y and usable(r)]
            if segment:
                covered += (y - x).total_seconds()
                segment_values = {r['value'] for r in segment}
                values.update(segment_values)
                conflict |= len(segment_values) > 1
        duration = (b - a).total_seconds()
        # Different quantities on pieces of a gas day cannot be integrated unless
        # their published rate/reference-duration relationship is established.
        conflict |= len(values) > 1
        quality = ('conflicting_overlap' if conflict else 'complete' if covered == duration
                   else 'partial_unknown' if covered else 'missing')
        value = next(iter(values)) if quality == 'complete' else None
        if value == 0:
            quality = 'reported_zero'
        result.append(dict(gas_day=day.isoformat(),gas_day_start=local_a.isoformat(),
                           gas_day_end=local_b.isoformat(),gas_day_hours=duration/3600,
                           covered_hours=covered/3600,value=value,gwh=None if value is None else value/1e6,
                           quality=quality,source_record_ids=sorted({r['id'] for s,e,r in hits}),
                           source_revisions=sorted({r['lastUpdateDateTime'] for s,e,r in hits
                                                    if r.get('lastUpdateDateTime')})))
        day += timedelta(days=1)
    return result


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE sources (
 source_id TEXT PRIMARY KEY, source_key TEXT NOT NULL, url TEXT NOT NULL,
 request_parameters_json TEXT NOT NULL, raw_capture_path TEXT,
 raw_sha256 TEXT, provenance_capture_path TEXT NOT NULL, provenance_sha256 TEXT NOT NULL,
 capture_kind TEXT NOT NULL, retrieved_at TEXT NOT NULL, retrieved_precision TEXT NOT NULL,
 publication_label TEXT, first_published_at TEXT, vintage_status TEXT NOT NULL,
 evidence_quality TEXT NOT NULL, transformation_version TEXT NOT NULL, metadata_json TEXT NOT NULL
);
CREATE TABLE assets (
 asset_key TEXT PRIMARY KEY, asset_id TEXT NOT NULL, scope TEXT NOT NULL,
 active INTEGER NOT NULL, physical_boundary TEXT NOT NULL, asset_type TEXT NOT NULL,
 operator_key TEXT, point_key TEXT, direction TEXT, associated_model_asset TEXT,
 model_assumption_value REAL, model_assumption_unit TEXT, model_source_key TEXT,
 engineering_event_coverage TEXT NOT NULL, comparison_status TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES sources(source_id), notes TEXT NOT NULL,
 UNIQUE(scope,asset_id), UNIQUE(operator_key,point_key,direction)
);
CREATE TABLE ratings (
 rating_id TEXT PRIMARY KEY, asset_key TEXT NOT NULL REFERENCES assets(asset_key),
 physical_boundary TEXT NOT NULL, value REAL, original_unit TEXT NOT NULL,
 capacity_category TEXT NOT NULL CHECK(capacity_category IN
 ('model_assumption','nameplate_snapshot','processing_snapshot','point_technical','commercial_available','change_evidence')),
 source_id TEXT NOT NULL REFERENCES sources(source_id), verification_status TEXT NOT NULL,
 valid_from TEXT, valid_to TEXT, valid_date_precision TEXT NOT NULL,
 snapshot_label TEXT, effective_change_window TEXT, reference_conditions TEXT,
 revision_timestamp TEXT, first_published_at TEXT, vintage_status TEXT NOT NULL,
 raw_record_id TEXT, raw_record_json TEXT NOT NULL, transformation_version TEXT NOT NULL,
 UNIQUE(source_id,raw_record_id)
);
CREATE TABLE events (
 event_id TEXT NOT NULL, revision_id TEXT NOT NULL, asset_key TEXT NOT NULL REFERENCES assets(asset_key),
 physical_boundary TEXT NOT NULL, event_type TEXT, status TEXT, start_at TEXT, end_at TEXT,
 timezone TEXT, residual_value REAL, reduction_value REAL, original_unit TEXT,
 overlap_group TEXT, dependency_group TEXT, first_published_at TEXT, revision_published_at TEXT,
 verification_status TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES sources(source_id),
 raw_record_json TEXT NOT NULL, PRIMARY KEY(event_id,revision_id)
);
CREATE TABLE daily (
 asset_key TEXT NOT NULL REFERENCES assets(asset_key), gas_day TEXT NOT NULL,
 gas_day_start TEXT NOT NULL, gas_day_end TEXT NOT NULL, timezone TEXT NOT NULL,
 gas_day_hours REAL NOT NULL, covered_hours REAL NOT NULL, original_unit TEXT NOT NULL,
 capacity_category TEXT NOT NULL, technical_kwh_per_gas_day REAL,
 technical_gwh_per_gas_day REAL, engineering_available_kwh REAL,
 commercial_available_kwh REAL, capacity_bcm REAL CHECK(capacity_bcm IS NULL),
 quality TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES sources(source_id),
 source_record_ids_json TEXT NOT NULL, source_revisions_json TEXT NOT NULL,
 vintage_status TEXT NOT NULL, transformation_version TEXT NOT NULL,
 PRIMARY KEY(asset_key,gas_day,capacity_category)
);
CREATE VIEW monthly AS
 SELECT asset_key,substr(gas_day,1,7) AS month,capacity_category,
 count(*) AS requested_gas_days,sum(technical_kwh_per_gas_day IS NOT NULL) AS covered_gas_days,
 CAST(strftime('%d',date(min(gas_day),'start of month','+1 month','-1 day')) AS INTEGER) AS calendar_gas_days,
 sum(technical_kwh_per_gas_day IS NULL) AS unknown_gas_days,
 sum(quality='reported_zero') AS reported_zero_days,
 sum(quality='conflicting_overlap') AS conflicting_days,
 sum(gas_day_hours) AS gas_day_hours,
 sum(technical_kwh_per_gas_day) AS known_subtotal_kwh,
 CASE WHEN count(technical_kwh_per_gas_day)=count(*) AND count(*)=CAST(strftime('%d',date(min(gas_day),'start of month','+1 month','-1 day')) AS INTEGER) THEN sum(technical_kwh_per_gas_day) END AS technical_kwh,
 CASE WHEN count(technical_kwh_per_gas_day)=count(*) AND count(*)=CAST(strftime('%d',date(min(gas_day),'start of month','+1 month','-1 day')) AS INTEGER) THEN sum(technical_kwh_per_gas_day)/1000000.0 END AS technical_gwh,
 NULL AS capacity_bcm,
 CASE WHEN count(*)!=CAST(strftime('%d',date(min(gas_day),'start of month','+1 month','-1 day')) AS INTEGER) THEN 'partial_requested_month' WHEN count(technical_kwh_per_gas_day)=count(*) THEN 'complete' ELSE 'incomplete_unknown' END AS quality,
 'sum published quantities by gas-day start label; no 24h multiplication; requested window only' AS aggregation_basis
 FROM daily GROUP BY asset_key,substr(gas_day,1,7),capacity_category;
CREATE VIEW coverage AS
 SELECT asset_key,substr(gas_day,1,4) AS year,count(*) AS requested_gas_days,
 sum(technical_kwh_per_gas_day IS NOT NULL) AS covered_gas_days,
 sum(quality='reported_zero') AS reported_zero_days,
 sum(quality='missing') AS missing_days,sum(quality='partial_unknown') AS partial_days,
 sum(quality='conflicting_overlap') AS conflicting_days,
 min(gas_day) AS first_requested_day,max(gas_day) AS last_requested_day
 FROM daily GROUP BY asset_key,substr(gas_day,1,4);
CREATE VIEW specification_register AS
 SELECT a.scope,a.asset_id,a.physical_boundary AS model_boundary,a.comparison_status,
 r.*,s.url,s.raw_capture_path,s.raw_sha256,s.capture_kind,s.retrieved_at,s.publication_label
 FROM ratings r JOIN assets a USING(asset_key) JOIN sources s USING(source_id)
 WHERE a.scope='poc_active' AND r.capacity_category!='model_assumption';
CREATE VIEW assumption_comparison AS
 SELECT asset_id,physical_boundary,model_assumption_value,model_assumption_unit,
 model_source_key,comparison_status,engineering_event_coverage,notes
 FROM assets WHERE scope='poc_active';
"""


def insert(connection, table, row):
    columns = ','.join(row)
    connection.execute(f'INSERT INTO {table} ({columns}) VALUES ({",".join("?" for _ in row)})', list(row.values()))


def add_rating(connection, asset_key, source_id, value, unit, category, status,
               precision='unknown', snapshot=None, window=None, conditions=None, raw=None,
               valid_from=None, valid_to=None, revision=None, boundary=None, record_id=None):
    boundary = boundary or connection.execute('SELECT physical_boundary FROM assets WHERE asset_key=?', (asset_key,)).fetchone()[0]
    raw = raw or dict(value=value,unit=unit,definition=boundary,source_id=source_id)
    row = dict(asset_key=asset_key,physical_boundary=boundary,value=value,original_unit=unit,
               capacity_category=category,source_id=source_id,verification_status=status,
               valid_from=valid_from,valid_to=valid_to,valid_date_precision=precision,
               snapshot_label=snapshot,effective_change_window=window,reference_conditions=conditions,
               revision_timestamp=revision,first_published_at=None,vintage_status='origin_availability_unverified',
               raw_record_id=record_id,raw_record_json=canonical(raw),transformation_version=VERSION)
    row['rating_id'] = hashlib.sha256(canonical(row).encode('utf-8')).hexdigest()
    insert(connection,'ratings',row)


RAW_DOCUMENTS = {
    'G_MAP':'map_2024.pdf','G_KOL_2019':'kollsnes_brochure_2019.pdf',
    'G_AR2023':'gassco_2023_report.pdf','G_TERMS':'gassled_terms_2022.pdf',
    'DK_REPORT':'energinet_supply_2023.pdf','G_UMM_RULES':'umm_principles.pdf',
    'G_UMM_EXPORT':'umm_historical_export_template.xlsx','E_MAP2021':'entsog_map_2021.xlsx',
}


def populate_sources(connection, root, audit, register):
    provenance = root/'evidence/inputs/public_capacity_sources.csv'
    for source in register:
        key = source['source_id']
        filename = RAW_DOCUMENTS.get(key)
        if key.startswith('TP_') and key[3:] in PILOT:
            filename = key[3:]+'.json'
        raw = root/'data/raw/public_capacity_audit'/filename if filename else None
        digest=sha256(raw) if raw else None
        logs = [r for r in audit['request_logs'] if r.get('sha256') and digest and r['sha256']==digest]
        log = logs[0] if logs else {}
        insert(connection,'sources',dict(source_id=key,source_key=key,url=source['url'],
            request_parameters_json=canonical(log.get('meta',{}).get('query',{})),
            raw_capture_path=raw.relative_to(root).as_posix() if raw else None,raw_sha256=sha256(raw) if raw else None,
            provenance_capture_path=provenance.relative_to(root).as_posix(),provenance_sha256=sha256(provenance),
            capture_kind='original_public_capture' if raw else 'retained_audit_transcription_original_capture_missing',
            retrieved_at=log.get('retrieved_at',source['retrieved_date']),
            retrieved_precision='timestamp' if log.get('retrieved_at') else 'day',
            publication_label=source['publication_vintage'],first_published_at=None,
            vintage_status='latest_revised_origin_unverified',evidence_quality=source['evidence_quality'],
            transformation_version=VERSION,metadata_json=canonical(dict(source,request_log=log))))
    for key,rel in [('MODEL','config/model.yaml'),('AUDIT_MATRIX','evidence/inputs/public_capacity_coverage.csv')]:
        insert(connection,'sources',dict(source_id=key,source_key=key,url='local:'+rel,
            request_parameters_json='{}',raw_capture_path=rel,raw_sha256=sha256(root/rel),
            provenance_capture_path=rel,provenance_sha256=sha256(root/rel),capture_kind='local_context_not_public_capacity_evidence',
            retrieved_at=audit['audit_date'],retrieved_precision='day',publication_label=None,first_published_at=None,
            vintage_status='local_configuration' if key=='MODEL' else 'retained_audit',evidence_quality='context',
            transformation_version=VERSION,metadata_json='{}'))


def populate_assets(connection, model, matrix):
    statuses={'verified_snapshot_only':'verified_snapshot_only','incompatible_with_model_boundary':'definition_incompatible',
              'provisional':'provisional','verified_point_history_volume_basis_provisional':'provisional'}
    for row in matrix:
        scope, aid = row['model_scope'], row['asset_id']
        active = scope == 'poc_active'
        config = model['routing']['assets'][aid] if active else model['assets'][aid]
        value = config.get('mcm_d',config.get('annual_bcm')) if active else config['technical_capacity_mcm_d']
        unit = 'annual_bcm' if active and 'annual_bcm' in config else 'mcm_d'
        insert(connection,'assets',dict(asset_key=scope+':'+aid,asset_id=aid,scope=scope,
            active=int(config.get('active',True)),physical_boundary=row['physical_identity'],
            asset_type=row['capacity_definition'] or config.get('type','unknown'),
            operator_key=None,point_key=None,direction=None,associated_model_asset=None,
            model_assumption_value=value,model_assumption_unit=unit,
            model_source_key=config.get('source',config.get('availability_series',config.get('maintenance_series'))),
            engineering_event_coverage='unknown_no_verified_event_history',
            comparison_status=statuses.get(row['evidence_status'],'unknown') if active else 'unknown',
            source_id='MODEL',notes=row['definition_and_history_gaps']))
        add_rating(connection,scope+':'+aid,'MODEL',value,unit,'model_assumption','provisional' if active else 'unknown',
                   raw=config,snapshot='Current configuration; no historical validity asserted')
    for probe,(operator,point,direction,model_asset) in PILOT.items():
        insert(connection,'assets',dict(asset_key='point:'+probe,asset_id=probe,scope='public_point',active=0,
            physical_boundary=f'{operator} / {point} / {direction}',asset_type='transmission_point',
            operator_key=operator,point_key=point,direction=direction,associated_model_asset=model_asset,
            model_assumption_value=None,model_assumption_unit=None,model_source_key=None,
            engineering_event_coverage='unknown_reported_technical_not_confirmed_engineering_availability',
            comparison_status='verified_compatible',source_id='TP_'+probe,
            notes='Verified identity for point pilot only; association does not substitute a model pipeline limit'))


def populate_specifications(connection, matrix):
    for row in matrix:
        if row['model_scope']=='poc_active' and row['current_capacity_source_key']=='gassco_map_2024':
            # This is the independently audited source transcription, not the model number.
            add_rating(connection,'poc_active:'+row['asset_id'],'G_MAP',float(row['reported_capacity']),
                       'MSm3/d','nameplate_snapshot','verified_snapshot_only',precision='snapshot_year',
                       snapshot='2024 map; internal February / upload December; effective dates unknown',
                       conditions='Sm3 convention 15 C/1.01325 bar dry in public terms; map does not restate conditions',raw=row)
    # Each conflicting source is a separate observation. No preferred figure selected.
    specifications = [
        ('KOLLSNES_EXPORT',143,'N_PLANTS','dry export','nameplate_snapshot','verified_snapshot_only','undated_current',None),
        ('KOLLSNES_EXPORT',146.5,'N_PLANTS','rich-gas processing','processing_snapshot','definition_incompatible','undated_current',None),
        ('KOLLSNES_EXPORT',143,'G_KOL_NO','narrative export capacity','nameplate_snapshot','provisional','undated_current',None),
        ('KOLLSNES_EXPORT',143,'G_KOL_EN','narrative export capacity','nameplate_snapshot','provisional','undated_current',None),
        ('KOLLSNES_EXPORT',144.5,'G_KOL_EN','fact-table capacity; narrative conflicts','processing_snapshot','provisional','undated_current',None),
        ('KOLLSNES_EXPORT',144.5,'G_KOL_2019','explicit plant export','nameplate_snapshot','verified_snapshot_only','2019 internally dated brochure',None),
        ('KOLLSNES_EXPORT',144.5,'E_KOL_2020','processing capacity; installation planned 2022/2023','processing_snapshot','verified_snapshot_only','September 2020 announcement',None),
        ('KOLLSNES_EXPORT',156,'G_KOL_NO','fact-table capacity; net-dry boundary unconfirmed','processing_snapshot','provisional','undated_current','autumn 2023; exact day unknown'),
        ('KOLLSNES_EXPORT',144.5,'E_KOL2025','pre-upgrade capacity; exact dry boundary unresolved','processing_snapshot','provisional','2025-01-06 publication',None),
        ('KOLLSNES_EXPORT',156,'E_KOL2025','upgraded capacity; exact dry boundary unresolved','processing_snapshot','provisional','2025-01-06 publication','autumn 2023; exact day unknown'),
        ('KOLLSNES_EXPORT',156,'E_AR2024','gas-processing asset','processing_snapshot','provisional','2024 annual report','autumn 2023; exact day unknown'),
        ('KOLLSNES_EXPORT',None,'G_AR2023','successful expansion +8%; no absolute rating in this observation','change_evidence','verified_snapshot_only','2023 annual report published 2024','autumn 2023; exact day unknown'),
        ('KARSTO_PROCESSING',95,'N_PLANTS','approximately 95 rich-gas inlet processing; not net dry','processing_snapshot','definition_incompatible','undated_current',None),
        ('KARSTO_PROCESSING',97,'E_AR2024','gas-processing asset; rich/net dry not specified','processing_snapshot','provisional','2024 annual report',None),
        ('NYHAMNA_EXPORT',84,'G_NYH','explicit plant export specification','nameplate_snapshot','verified_snapshot_only','undated_current',None),
        ('NYHAMNA_EXPORT',84,'E_AR2024','gas-processing asset','processing_snapshot','provisional','2024 annual report',None),
    ]
    for aid,value,source,boundary,category,status,label,window in specifications:
        add_rating(connection,'poc_active:'+aid,source,value,'million Sm3/day',category,status,
                   precision='snapshot_only_effective_unknown',snapshot=label,window=window,
                   boundary=aid.split('_')[0]+' plant / '+boundary,conditions='Source Sm3 label retained; gas/reference composition basis not resolved')
    for aid,value,unit,source,boundary,label in [
        ('NORTH_SEA_ENTRY',27.4,'million m3/day','DK_PLAN','Danish entry/system technical specification','As of 2022-10-01 and end 2023 in 2025 report'),
        ('BALTIC_PIPE',27.4,'million Nm3/day','DK_REPORT','Faxe directional point specification','2023 report'),
        ('BALTIC_PIPE',10,'bcm/year','PL_FULL','Baltic Pipe annual towards-Poland route rating','Full capacity 2022-11-30; initial operation 2022-10-01'),
        ('BALTIC_PIPE',10,'billion Nm3/year','PL_REPORT','Baltic Pipe public reporting label','Mixed report vintages'),
    ]:
        add_rating(connection,'poc_active:'+aid,source,value,unit,'nameplate_snapshot','provisional',
                   precision='snapshot_only_effective_unknown',snapshot=label,boundary=boundary,
                   conditions='Original label retained; compatible volume reference conditions/GCV unverified')


def ingest_point(connection, probe, payload, start, end):
    identity = PILOT[probe][:3]
    rows = validate_capture(payload,identity)
    asset_key, source_id = 'point:'+probe, 'TP_'+probe
    for row in rows:
        add_rating(connection,asset_key,source_id,row.get('value'),'kWh/d','point_technical',
                   'verified_reported_point',precision='exact_source_interval',raw=row,
                   valid_from=row['periodFrom'],valid_to=row['periodTo'],revision=row.get('lastUpdateDateTime'),
                   record_id=row['id'],conditions='Energy quantity per source gas day; capacity-basis GCV unavailable')
    for day in expand_intervals(rows,start,end):
        insert(connection,'daily',dict(asset_key=asset_key,gas_day=day['gas_day'],
            gas_day_start=day['gas_day_start'],gas_day_end=day['gas_day_end'],timezone=GAS_TIMEZONE,
            gas_day_hours=day['gas_day_hours'],covered_hours=day['covered_hours'],original_unit='kWh/d',
            capacity_category='point_technical',technical_kwh_per_gas_day=day['value'],technical_gwh_per_gas_day=day['gwh'],
            engineering_available_kwh=None,commercial_available_kwh=None,capacity_bcm=None,quality=day['quality'],
            source_id=source_id,source_record_ids_json=canonical(day['source_record_ids']),
            source_revisions_json=canonical(day['source_revisions']),vintage_status='latest_revised_origin_unverified',
            transformation_version=VERSION))


def export_query(connection, query, path):
    cursor = connection.execute(query)
    with Path(path).open('w',encoding='utf-8',newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([d[0] for d in cursor.description]); writer.writerows(cursor)


def build_database(root, output, start='2022-10-01', end='2025-12-31'):
    """Build fresh deterministic bytes; refuse overwriting any existing deliverable.

    No network calls, model imports, optimisations, BCM conversions or maintenance
    arithmetic. Rebuild into a fresh path; identical inputs produce identical DB.
    """
    root, output = Path(root).resolve(), Path(output).resolve()
    historical_window(start,end)
    if not output.is_relative_to(root):
        raise ValueError('Output must stay inside the authorised repository')
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Use a fresh output directory; existing deliverables preserved')
    audit_path = root/'evidence/inputs/public_capacity_audit_manifest.json'
    audit = json.loads(audit_path.read_bytes())
    verification = json.loads((root/'evidence/inputs/public_capacity_verification.json').read_bytes())
    for name,digest in verification['evidence_hashes'].items():
        if sha256(root/'evidence/inputs'/name) != digest:
            raise ValueError('Audit evidence hash mismatch: '+name)
    for rel,digest in audit['retained_raw_files'].items():
        if sha256(root/rel) != digest:
            raise ValueError('Immutable raw evidence hash mismatch: '+rel)
    model_path = root/'config/model.yaml'
    if sha256(model_path) != audit['model_sha256']:
        migration_path = root/'evidence/inputs/project_structure_migration.json'
        if not migration_path.is_file():
            raise ValueError('Model changed since audit; inventory review required')
        migration = json.loads(migration_path.read_bytes())
        if (audit['model_sha256'] != migration['model_config']['before_sha256'] or
                sha256(model_path) != migration['model_config']['after_sha256']):
            raise ValueError('Model changed since audit; inventory review required')
    model = yaml.safe_load(model_path.read_text(encoding='utf-8'))
    matrix = read_csv(root/'evidence/inputs/public_capacity_coverage.csv')
    register = read_csv(root/'evidence/inputs/public_capacity_sources.csv')
    if {r['asset_id'] for r in matrix if r['model_scope']=='poc_active'} != set(model['routing']['assets']):
        raise ValueError('Active asset inventory mismatch')
    if {r['asset_id'] for r in matrix if r['model_scope']=='foundation_retained'} != set(model['assets']):
        raise ValueError('Foundation asset inventory mismatch')
    output.mkdir(parents=True,exist_ok=True)
    connection = sqlite3.connect(output/'capacity.sqlite')
    try:
        connection.executescript(SCHEMA)
        with connection:
            populate_sources(connection,root,audit,register)
            populate_assets(connection,model,matrix)
            populate_specifications(connection,matrix)
            for probe in PILOT:
                payload=json.loads((root/'data/raw/public_capacity_audit'/(probe+'.json')).read_bytes())
                ingest_point(connection,probe,payload,start,end)
        assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()
        exports={'assets':'SELECT * FROM assets ORDER BY asset_key',
                 'ratings':'SELECT * FROM ratings ORDER BY asset_key,rating_id',
                 'sources':'SELECT * FROM sources ORDER BY source_id',
                 'events':'SELECT * FROM events ORDER BY event_id,revision_id',
                 'daily':'SELECT * FROM daily ORDER BY asset_key,gas_day',
                 'monthly':'SELECT * FROM monthly ORDER BY asset_key,month',
                 'coverage':'SELECT * FROM coverage ORDER BY asset_key,year',
                 'specification_register':'SELECT * FROM specification_register ORDER BY asset_id,rating_id',
                 'assumption_comparison':'SELECT * FROM assumption_comparison ORDER BY asset_id'}
        for name,query in exports.items():
            export_query(connection,query,output/(name+'.csv'))
        counts={name:connection.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in exports}
        audit_coverage=read_csv(root/'evidence/inputs/public_capacity_point_coverage.csv')
        matched=[]
        for row in connection.execute('SELECT asset_key,year,requested_gas_days,covered_gas_days FROM coverage'):
            probe=row[0].removeprefix('point:')
            reference=next(r for r in audit_coverage if r['probe']==probe and r['year']==row[1])
            # Compare complete audit year only; 2022 is an explicitly labelled commissioning slice.
            if start=='2022-10-01' and end=='2025-12-31' or start=='2023-01-01' and end=='2025-12-31':
                if row[3] != int(reference['fully_covered_gas_days']):
                    raise ValueError('Daily coverage disagrees with completed audit')
                matched.append(dict(probe=probe,year=row[1],covered_days=row[3],audit_covered_days=int(reference['fully_covered_gas_days'])))
    finally:
        connection.close()
    manifest=dict(transformation_version=VERSION,window=dict(first_gas_day=start,last_gas_day=end),
                  transformation_sha256=sha256(Path(__file__)),
                  runtime=dict(python=sys.version.split()[0],sqlite=sqlite3.sqlite_version,
                               pandas=pd.__version__,pytz=version('pytz')),
                  gas_timezone=GAS_TIMEZONE,monthly_policy='gas_day_start_label_sum',
                  source_type='offline_verified_public_audit_captures',counts=counts,audit_coverage_comparison=matched,
                  raw_evidence=dict(audit['retained_raw_files']),audit_manifest_sha256=sha256(audit_path),
                  model_context_sha256=sha256(model_path),vintage_status='latest_revised_origin_unverified',
                  unknown_fields=['engineering availability','maintenance events','capacity bcm','first publication timestamps'],
                  protected_holdout='No 2026 gas-day observations produced; original validity/revision metadata preserved',
                  output_hashes={p.name:sha256(p) for p in sorted(output.iterdir()) if p.is_file()})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
    return manifest
