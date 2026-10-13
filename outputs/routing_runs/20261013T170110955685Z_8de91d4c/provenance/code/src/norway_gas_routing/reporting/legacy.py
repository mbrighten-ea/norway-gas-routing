"""Read retained legacy forecast exports and cached workbook cells without Excel."""
import io
import json
import posixpath
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
from openpyxl.utils.datetime import from_excel

from ..evaluation import check_dates
from .data import COUNTRIES, GROUPS, dated_csv, sha

NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
SUFFIX = {'UK': 'UK', 'FR+BE': 'FR_and_BE', 'NL+DE': 'NL_and_DE',
          'Baltic Pipe': 'PL', 'DK': 'DK', 'total': 'total'}


def workbook_bytes(path):
    """Existing audit's CRC-checked in-memory ZIP recovery; original stays intact."""
    data = Path(path).read_bytes()
    if zipfile.is_zipfile(io.BytesIO(data)):
        return data, 'Original ZIP readable'
    start = data.find(b'PK\x01\x02')
    if start < 0:
        raise ValueError('No recoverable workbook directory')
    position, records = start, []
    while data[position:position+4] == b'PK\x01\x02':
        names, extra, comment = struct.unpack_from('<HHH', data, position+28)
        size = 46+names+extra+comment
        record = data[position:position+size]
        name = record[46:46+names]
        offset = struct.unpack_from('<L', record, 42)[0]
        local_size = struct.unpack_from('<H', data, offset+26)[0]
        if name.strip(b'\0') and name == data[offset+30:offset+30+local_size]:
            records.append(record)
        position += size
    directory = b''.join(records)
    end = struct.pack('<4s4H2LH', b'PK\x05\x06', 0, 0, len(records), len(records), len(directory), start, 0)
    recovered = data[:start]+directory+end
    with zipfile.ZipFile(io.BytesIO(recovered)) as archive:
        if archive.testzip() is not None:
            raise ValueError('Recovered workbook CRC check failed')
    return recovered, f'In-memory ZIP recovery; {len(records)} entries CRC verified; original unchanged'


def cached_cell(cell, strings):
    if cell is None:
        return None
    value = cell.find('x:v', NS)
    if value is None or value.text is None:
        inline = cell.find('x:is', NS)
        return ''.join(inline.itertext()) if inline is not None else None
    if cell.get('t') == 's':
        return strings[int(value.text)]
    if cell.get('t') in ['str', 'e']:
        return value.text
    return float(value.text)


def selected_sheet(archive, sheet_path, date_column, months, columns, strings):
    """Decode dates first. Numeric outcome cells outside selected months are skipped."""
    found = []
    for _, row in ET.iterparse(archive.open(sheet_path), events=['end']):
        if row.tag != f"{{{NS['x']}}}row":
            continue
        cells = {''.join(filter(str.isalpha, c.get('r', ''))): c for c in row.findall('x:c', NS)}
        date_value = cached_cell(cells.get(date_column), strings)
        month = None
        if isinstance(date_value, (float, int)) and 35000 < date_value < 60000:
            month = str(pd.Period(from_excel(date_value), 'M'))
        if month in months:
            for col in columns:
                cell = cells.get(col)
                value = cached_cell(cell, strings)
                formula = cell.find('x:f', NS) if cell is not None else None
                found.append({'month': month, 'column': col,
                    'cell': f'{col}{row.get("r")}', 'cached': value,
                    'formula': '='+formula.text if formula is not None and formula.text else ''})
        row.clear()
    return pd.DataFrame(found)


def header_cells(archive, path, refs, strings):
    found = {}
    for _, cell in ET.iterparse(archive.open(path), events=['end']):
        if cell.tag == f"{{{NS['x']}}}c" and cell.get('r') in refs:
            found[cell.get('r')] = cached_cell(cell, strings)
        if len(found) == len(refs):
            break
    return found


def load_workbook_history(path, months):
    check_dates(months, 'read')
    path = Path(path).resolve()
    original_hash = sha(path)
    data, status = workbook_bytes(path)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        strings = [''.join(si.itertext()) for si in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        relations = {r.get('Id'): r.get('Target') for r in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        sheets = {}
        for sheet in ET.fromstring(archive.read('xl/workbook.xml')).findall('x:sheets/x:sheet', NS):
            target = relations[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            sheets[sheet.get('name')] = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
        units = header_cells(archive, sheets['SJ upload'], {f'{c}9' for c in ['D','E','F','G','I','J','K','L','M','O']}, strings)
        if len(units) != 10 or any(value != 'bcm' for value in units.values()):
            raise ValueError('Legacy upload units must be explicitly bcm')
        final_units = header_cells(archive, sheets['Forecasts'], {'AT4','AY4','BD4','F4'}, strings)
        if len(final_units) != 4 or any(value != 'bcm' for value in final_units.values()):
            raise ValueError('Legacy final-allocation column units changed')
        cover = ET.fromstring(archive.read(sheets['Cover']))
        cover_month = cached_cell(cover.find(".//x:c[@r='A1']", NS), strings)
        boundary = str(pd.Period(from_excel(cover_month), 'M'))
        cells = selected_sheet(archive, sheets['SJ upload'], 'B', set(months),
            ['D', 'E', 'F', 'G', 'I', 'J', 'K', 'L', 'M', 'O'], strings)
        forecasts = selected_sheet(archive, sheets['Forecasts'], 'D', set(months),
            ['AT', 'AY', 'BD', 'H', 'I', 'L', 'M', 'F'], strings)
        baltic = selected_sheet(archive, sheets['Baltic Pipe'], 'D', set(months), ['P', 'R', 'T'], strings)
        props = ET.fromstring(archive.read('docProps/core.xml'))
        modified = props.find('{http://purl.org/dc/terms/}modified')
        vintage = modified.text if modified is not None else 'unknown'
    if sha(path) != original_hash:
        raise ValueError('Workbook changed during read')
    if cells.empty or (pd.PeriodIndex(months, freq='M') >= pd.Period(boundary, 'M')).any():
        raise ValueError('This adapter is for cached historical context before Cover!A1 only; future workbook outputs need a reviewed adapter')
    if cells.duplicated(['month', 'column']).any():
        raise ValueError('Duplicate legacy workbook month/column')
    # Historical Poland semantics depend on the exact formula path, not the SID label.
    if not cells.loc[cells.column.eq('L'), 'formula'].str.contains('Forecasts!$M$', regex=False).all():
        raise ValueError('Workbook Poland formula path changed; review its physical definition before adapting')
    mappings = {'countries': {'UK': 'D', 'FR': 'E', 'BE': 'F', 'NL': 'I', 'DE': 'J', 'PL': 'L', 'DK': 'O'},
                'groups': {'UK': 'D', 'FR+BE': 'G', 'NL+DE': 'K', 'Baltic Pipe': 'L', 'DK': 'O'},
                'total': {'total': 'M'}}
    rows = []
    for level, mapping in mappings.items():
        for destination, col in mapping.items():
            for _, cell in cells.loc[cells.column.eq(col)].iterrows():
                numeric = float(cell.cached) if isinstance(cell.cached, (int, float)) else np.nan
                compatible = destination not in ['PL', 'Baltic Pipe', 'DK', 'total']
                note = 'Cached revised historical allocation proxy; not a pre-period Excel model forecast'
                if destination in ['PL', 'Baltic Pipe']:
                    note += '; SJ upload!L links Forecasts!M = total Nybro, not Faxe; direct Polish comparison withheld'
                if destination == 'DK':
                    note += '; signed Danish net offtake proxy, not gross physical exports'
                if destination == 'total':
                    note += '; Gassco accounting total, not seven-country gross pipeline exports'
                rows.append({'month': cell.month, 'level': level, 'destination': destination,
                    'value_bcm': numeric, 'compatible': compatible,
                    'cell': 'SJ upload!'+cell.cell, 'formula': cell.formula, 'status': note,
                    'source_unit': 'bcm', 'conversion': 'none', 'source_file': str(path)})
    ledger = []
    for sheet_name, frame in [('SJ upload', cells), ('Forecasts', forecasts), ('Baltic Pipe', baltic)]:
        for _, cell in frame.iterrows():
            ledger.append({'sheet': sheet_name, **cell.to_dict(), 'unit': 'bcm' if sheet_name == 'SJ upload' or
                (sheet_name == 'Forecasts' and cell.column in ['AT', 'AY', 'BD', 'M', 'F']) else 'mcm/day',
                'workbook_sha256': original_hash})
    return {'id': 'workbook', 'label': 'Cached workbook history (context only)', 'kind': 'workbook_history',
        'vintage': f'Workbook modified {vintage}; cached cutoff {boundary}', 'data': pd.DataFrame(rows),
        'ledger': pd.DataFrame(ledger), 'source_hashes': {str(path): original_hash},
        'notes': [status, 'No Excel formulas recalculated. The Forecasts sheet switches to Gassco_raw in historical months.',
            'SJ upload Poland column is total Nybro for these months. Faxe, net Denmark and total Nybro cells are retained separately.',
            'No verified physical observation series is added. EA/Gassco-labelled allocation proxies remain context only.']}


def load_retained_forecast(base, origin, months):
    """Use all retained forecasts, not the narrower seasonal-matched scoring table."""
    check_dates(months, 'read')
    base = Path(base).resolve()
    selected = dated_csv(base/'results.csv', month='target_month')
    selected = selected.loc[selected.method.eq('legacy_asof') & selected.origin.eq(origin)]
    if selected.empty:
        raise ValueError(f'No retained legacy origin {origin}')
    verification = dated_csv(base/'provenance/forecast_verification.csv', month='target_month')
    verification = verification.loc[verification.origin.eq(origin)]
    if selected.duplicated(['target_month', 'destination']).any():
        raise ValueError('Duplicate legacy forecast outputs')
    rows, hashes, ledger = [], {}, []
    for filename in ['results.csv', 'provenance/forecast_verification.csv']:
        hashes[str(base/filename)] = sha(base/filename)
    for destination, suffix in SUFFIX.items():
        if destination == 'total':
            # A named total is not represented in results.csv. Retained raw record
            # is selected from the retained manifest by origin and SID only.
            manifest_path = base/'provenance/retrieval_manifest.json'
            records = json.loads(manifest_path.read_text(encoding='utf-8'))
            matches = [r for r in records if r.get('origin') == origin and
                       r.get('sid', '').endswith('\\gassco_total')]
            if len(matches) != 1:
                continue
            source_name = Path(matches[0]['evidence_file'].replace('\\', '/')).name
            hashes[str(manifest_path)] = sha(manifest_path)
        else:
            evidence = verification.loc[verification.group.eq(destination), 'evidence_file'].unique()
            if len(evidence) != 1:
                raise ValueError('Ambiguous retained legacy evidence')
            source_name = Path(evidence[0].replace('\\', '/')).name
        source_path = base/'provenance/raw'/source_name
        record = json.loads(source_path.read_text(encoding='utf-8'))
        meta = record['metadata']
        if (record.get('origin') != origin or meta.get('unit') != 'bcm' or
            meta.get('frequency') != 'monthly' or meta.get('lifecycle_stage') != 'forecast' or
            not meta.get('source_file', '').endswith('Norwegian flows model.xlsx') or
            not meta.get('forecast_start_date')):
            raise ValueError('Retained source identity/unit/vintage check failed')
        hashes[str(source_path)] = sha(source_path)
        target_values = {}
        retained_window = set(verification.loc[verification.verified_future_forecast.eq(True), 'target_month'])
        for point in record['points']:
            target = str(pd.Period(pd.Timestamp(point['dt']).tz_localize(None), 'M'))
            # Exclude historical cells and out-of-window outcomes BEFORE decoding val.
            if target not in months or target not in retained_window or target <= origin[:7] or target < meta['forecast_start_date'][:7]:
                continue
            if target in target_values:
                raise ValueError('Duplicate retained forecast month')
            check_dates([target], 'read')
            value = float(point['val'])
            if not np.isfinite(value):
                raise ValueError('Nonfinite retained forecast')
            target_values[target] = value
        for month, value in target_values.items():
            if destination != 'total':
                exported = selected.loc[selected.target_month.eq(month) & selected.destination.eq(destination)]
                verified = verification.loc[verification.target_month.eq(month) & verification.group.eq(destination)]
                if len(exported) != 1 or len(verified) != 1 or not bool(verified.iloc[0].verified_future_forecast):
                    raise ValueError('Raw value lacks a verified retained export')
                if abs(value-exported.iloc[0].prediction_bcm) > 5.1e-10:
                    raise ValueError('Raw legacy value differs from retained export precision')
            row = {'month': month, 'level': 'total' if destination == 'total' else 'groups',
                'destination': destination, 'value_bcm': value, 'compatible': True,
                'cell': f'{source_path.name}:points[{month}]', 'formula': '',
                'status': 'Retained-state legacy forecast; public release timing unverified; original grouped definitions',
                'source_file': str(source_path), 'source_unit': 'bcm', 'conversion': 'none'}
            rows.append(row)
            if destination in ['UK', 'DK', 'Baltic Pipe']:
                rows.append(row | {'level': 'countries', 'destination': 'PL' if destination == 'Baltic Pipe' else destination})
            ledger.append(row | {'origin': origin, 'forecast_start_date': meta['forecast_start_date'],
                'record_sha256': hashes[str(source_path)], 'retrieved_at_utc': record.get('retrieved_at_utc'),
                'public_release_timing': 'unverified'})
    return {'id': 'retained:'+origin, 'label': f'Legacy forecast retained at {origin}', 'kind': 'forecast',
        'vintage': f'Retained origin {origin}; retrieved 2026-10-09; release timing unverified',
        'data': pd.DataFrame(rows), 'ledger': pd.DataFrame(ledger), 'source_hashes': hashes,
        'notes': ['France/Belgium and Germany/Netherlands were forecast as groups; individual country forecasts are unavailable.',
            'Original legacy Baltic Pipe and Denmark group definitions are retained. Origin workbook formulas were not retained; physical bases remain unverified.',
            'These compare a revised-input routing reconstruction with an earlier legacy forecast; differences include source vintage and supply-boundary differences. They are not forecast errors.']}
