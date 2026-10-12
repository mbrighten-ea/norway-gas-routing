"""Reviewed SID contracts and fresh response validation; no workbook data reader."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unicodedata

import pandas as pd

from .evaluation import check_dates
from .project_data import get_registered_series
from .routing import DESTINATIONS

CONTRACT = 'evidence/inputs/routing_sources_b1/verified_sources.json'
MAPPING_LEDGER = 'evidence/inputs/routing_sources_b1/routing_source_mapping.csv'


def source_contract(root):
    contract = json.loads((Path(root)/CONTRACT).read_text(encoding='utf-8'))
    if contract.get('schema_version') != 1:
        raise ValueError('Unknown reviewed source-contract schema; do not infer mappings.')
    return contract


def check_registered(key, registry, contract):
    spec = contract['sources'].get(key)
    if spec is None or key not in registry.index:
        raise ValueError(key+': missing verified SID contract or canonical registry record.')
    row = registry.loc[key]
    if not isinstance(row, pd.Series):
        raise ValueError(key+': duplicate registry key.')
    if not row['sid']:
        raise ValueError(key+': missing SID in canonical registry.')
    for column, expected in [('sid', spec['sid']), ('raw_unit', spec['raw_unit']),
                             ('source_frequency', spec['frequency']), ('model_role', spec['registry_role']),
                             ('target_unit', 'mcm_d' if spec['frequency']=='daily' else 'bcm')]:
        if row[column] != expected:
            raise ValueError(key+': canonical '+column+' differs from the independently reviewed contract; source review required.')
    return spec


def source_requirements(root, model, registry):
    """Return essential/optional/derived consumers with explicit mapping blockers."""
    from .routing_inputs import PRODUCTION_COLUMNS, workbook_source_columns
    contract = source_contract(root)
    if contract['component_columns'] != PRODUCTION_COLUMNS:
        raise ValueError('Reviewed component-column identities changed; source review required.')
    if {k:model['routing'][k] for k in ['nodes', 'arcs']} != contract['network']:
        raise ValueError('Routing topology/component references differ from the reviewed physical model; do not remove essential inputs to bypass the source blocker.')
    rows, components, assigned = [], {}, set()
    def add(key, consumer, classification, transformation):
        try:
            spec = check_registered(key, registry, contract)
            status, blocked = 'Existing verified historical identity; fresh response checks required', False
        except ValueError as error:
            spec, status, blocked = {}, str(error), True
        rows.append(dict(key=key, identifier=spec.get('sid', ''), consumer=consumer,
            classification=classification, status=status, blocked=blocked,
            raw_unit=spec.get('raw_unit', ''), metadata_unit=spec.get('metadata_unit', ''),
            model_unit='bcm/month', frequency=spec.get('frequency', ''), transformation=transformation,
            evidence=spec.get('evidence', CONTRACT)))
    for node, entry in model['routing']['nodes'].items():
        if entry['kind'] != 'source' or entry.get('residual'):
            continue
        keys = list(model['sources'][entry['source_group']]['series']) if entry.get('source_group') else []
        if len(keys) != len(set(keys)) or assigned.intersection(keys):
            raise ValueError('Duplicate production component across source nodes; no double counting.')
        if entry.get('source_group') and set(keys) != set(contract['source_groups'].get(entry['source_group'], [])):
            raise ValueError(node+': source-group components differ from the reviewed mapping.')
        if any(key not in PRODUCTION_COLUMNS for key in keys):
            raise ValueError(node+': unverified or aggregate production component; no inferred field mapping.')
        if any(contract['component_groups'][key] != entry['source_group'] for key in keys):
            raise ValueError(node+': field mapping differs from the accepted source group.')
        assigned.update(keys)
        components[node] = keys
        for key in keys:
            add(key, node, 'essential_optimisation', 'Sum distinct field monthly bcm into the established source node')
        if not keys and not entry.get('workbook_columns'):
            raise ValueError(node+': source has no mapped components; do not assume zero.')
    workbook_source_columns(model['routing']['nodes'], assigned)
    ledger = pd.read_csv(Path(root)/MAPPING_LEDGER, keep_default_na=False)
    for node, entry in model['routing']['nodes'].items():
        for column in entry.get('workbook_columns', []):
            match = ledger.loc[ledger.reference.eq(column) & ledger.node.eq(node)]
            field = match.iloc[0]['field'] if len(match)==1 else 'Unreviewed field reference'
            mapping = contract.get('historical_components', {}).get(column)
            if mapping:
                key = mapping['key']
                spec = contract['sources'].get(key, {})
                if (mapping.get('node') != node or spec.get('provider_contract') != 'npd_historical'
                        or len(match)!=1 or match.iloc[0].verified_key!=key
                        or match.iloc[0].verified_sid!=spec.get('sid')
                        or field_identity(field)!=field_identity(spec.get('npd_field_label',''))):
                    raise ValueError(column+': historical field mapping/ledger identity mismatch.')
                if key in assigned:
                    raise ValueError('Duplicate production component across source nodes; no double counting: '+key)
                assigned.add(key)
                components[node].append(key)
                add(key,node,'essential_optimisation',
                    'NPD monthly bcm directly; worksheet rate conversion and old adapter reversal cancel')
                rows[-1].update(reference=column,field=field)
                continue
            rows.append(dict(key='unresolved_component_'+column, identifier='', consumer=node,
                field=field, reference=column, classification='essential_optimisation', blocked=True,
                status='BLOCKED: '+field+' has no verified canonical EA SID mapping',
                raw_unit='monthly-average mcm/day reference', model_unit='bcm/month', frequency='monthly',
                transformation='rate * calendar days / 1000; candidate Directorate SID is not approved', evidence=MAPPING_LEDGER))
    add('norway_prod', 'national supply boundary', 'essential_optimisation', 'Total minus Snøhvit once minus mapped fields -> UNMAPPED')
    add('snohvit_net_prod', 'LNG exclusion', 'essential_optimisation', 'Signed historical rate * calendar days / 1000; July 2025 guard')
    for asset, entry in model['routing']['assets'].items():
        if contract['capacity_assumptions'].get(asset) != entry:
            raise ValueError(asset+': capacity assumption differs from the accepted baseline; source review required.')
        if entry.get('maintenance_series'):
            add(entry['maintenance_series'], asset, 'essential_optimisation', 'Signed capacity derate only; never reduce production')
        rows.append(dict(key=asset, identifier='config/model.yaml:routing.assets.'+asset,
            consumer='asset capacity', classification='essential_assumption', blocked=False,
            status='Existing provisional engineering envelope; not a verified historical vintage',
            raw_unit='mcm/day' if 'mcm_d' in entry else 'bcm/year', model_unit='bcm/month',
            frequency='daily', transformation='Calendar-day sum of technical minus signed derate / 1000',
            evidence=entry.get('source', 'config/model.yaml')))
    for d in DESTINATIONS:
        add(d.lower()+'_flow_qa', 'earlier routing preference '+d, 'essential_training', 'Earlier complete nonnegative baskets -> static soft shares')
    for group, key in OPTIONAL_GROUPS.items():
        add(key, 'actual comparison '+group, 'optional_comparison', 'Original EA group; no disaggregation; incompatible DK/PL errors withheld')
    rows.append(dict(key='UNMAPPED', identifier='derived identity', consumer='unrouted accounting',
        classification='derived', status='National minus LNG minus mapped supply, not extra input', blocked=False,
        model_unit='bcm/month', transformation='Residual remains forced unrouted'))
    return pd.DataFrame(rows), components, contract


OPTIONAL_GROUPS = {'UK': 'uk_flow_qa', 'FR+BE': 'fr_be_flow_qa',
                   'NL+DE': 'nl_de_flow_qa', 'Baltic Pipe': 'pl_flow_qa', 'DK': 'dk_flow_qa'}


def field_identity(value):
    """Normalise labels only, never manufacture a SID."""
    value = str(value).casefold().replace('ø', 'o').replace('æ', 'ae')
    return '_'.join(unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().replace('_', ' ').split())


def verify_response(key, response, spec, dates, frequency):
    """Accept historical segments only; reported units never imply conversions."""
    if response.get('asof') is not None or '@asof' in str(response.get('query', '')):
        raise ValueError(key+': archived/origin response supplied to revised reconstruction; no vintage substitution.')
    returned = response.get('registry', {})
    if returned.get('key') != key or returned.get('sid') != spec['sid']:
        raise ValueError(key+': response source identifier differs from requested canonical SID.')
    meta = response.get('metadata', {})
    if meta.get('series_id') is not None and meta['series_id'] != spec['sid']:
        legacy = str(meta['series_id']).split('\\')
        legacy_identity = (spec.get('provider_contract')=='npd_historical' and len(legacy)==4
            and legacy[:2]==['NPD','monthly_by_field'] and legacy[-1]=='Gas - saleable'
            and field_identity(legacy[2])==spec['npd_field']
            and meta.get('series_id_name')=='\\'.join(spec['sid'].split('\\')[2:]))
        if not legacy_identity:
            raise ValueError(key+': provider metadata SID mismatch.')
    if meta.get('unit') != spec['metadata_unit'] or meta.get('frequency') != frequency:
        raise ValueError(key+': inconsistent source units/frequency; expected '+spec['metadata_unit']+'/'+frequency+'.')
    if spec.get('provider_contract') == 'npd_historical':
        source = meta.get('source_obj', {})
        if (meta.get('row_level') != 'field' or meta.get('country_iso') != 'NO'
                or meta.get('ea_production_type') != 'marketed_production'
                or meta.get('economic_property') != 'production'
                or meta.get('energy_product') != 'natural_gas'
                or source.get('aspect') != 'gas-saleable'):
            raise ValueError(key+': incompatible NPD field/marketed saleable-gas definition.')
        if (field_identity(meta.get('ea_field_name_standardised', '')) != spec['npd_field']
                or field_identity(source.get('discovery_field_name', '')) != field_identity(spec['npd_field_label'])):
            raise ValueError(key+': returned NPD field identity differs from workbook field/candidate SID.')
        if meta.get('lifecycle_stage') not in {'actual', 'historical'} or source.get('units') not in {'bill Sm3', 'bcm'}:
            raise ValueError(key+': NPD requires historical monthly billion-standard-cubic-metre volumes.')
        if meta.get('source') not in {'Norwegian Petroleum Directorate', 'Norwegian Offshore Directorate'}:
            raise ValueError(key+': unexpected NPD provider identity.')
        if not str(meta.get('source_url', '')).startswith(('https://factpages.npd.no/', 'https://factpages.sodir.no/')):
            raise ValueError(key+': unexpected Directorate source URL.')
        first = meta.get('forecast_start_date')
        if first and dates.max().to_period('M') >= pd.Period(pd.Timestamp(first), 'M'):
            raise ValueError(key+': requested historical months cross the returned forecast boundary.')
    else:
        if not str(meta.get('source_file', '')).replace('\\', '/').endswith('/'+spec['source_file']) and meta.get('source_file') != spec['source_file']:
            raise ValueError(key+': provider source-file identity changed.')
        if meta.get('lifecycle_stage') not in {'forecast', 'actual', 'historical'}:
            raise ValueError(key+': unverified lifecycle; historical observations required.')
        first = meta.get('forecast_start_date')
        if not first:
            raise ValueError(key+': missing historical/forecast boundary; no future observation substitution.')
        if pd.isna(pd.Timestamp(first)) or dates.max().to_period('M') >= pd.Period(pd.Timestamp(first), 'M'):
            raise ValueError(key+': requested historical months cross the returned forecast boundary.')
    values = response['values']
    if not isinstance(values.index, pd.DatetimeIndex) or not values.index.is_unique or values.index.hasnans:
        raise ValueError(key+': missing/duplicate timestamp; no aggregation or filling.')
    # A timezone must represent UTC midnight; no unapproved gas-day conversion.
    actual = values.index
    if actual.tz is not None:
        if str(actual.tz) != 'UTC':
            raise ValueError(key+': unresolved source timezone; do not silently change gas days.')
        actual = actual.tz_localize(None)
    if not actual.equals(actual.normalize()) or (frequency=='monthly' and not actual.equals(actual.to_period('M').to_timestamp())):
        raise ValueError(key+': expected midnight '+frequency+' observation dates.')
    if not actual.sort_values().equals(dates):
        missing = dates.difference(actual)
        extra = actual.difference(dates)
        fmt = lambda values: ', '.join(str(d.date()) for d in values[:15]) or 'none'
        raise ValueError(key+': incomplete or out-of-bounds '+frequency+' coverage; missing '+fmt(missing)+
                         '; unexpected '+fmt(extra)+'; no filling/interpolation.')
    normal = pd.Series(pd.to_numeric(values.to_numpy(), errors='raise'), index=actual, name=key).sort_index()
    if normal.isna().any() or not normal.map(lambda v: float('-inf') < float(v) < float('inf')).all():
        raise ValueError(key+': missing/nonfinite source observations.')
    return normal.astype(float)


def retrieve_checked(root, key, dates, registry, contract, records, provenance_dir, *, client=None):
    """Fresh helper query, durable raw response, then explicit analytical validation."""
    spec = check_registered(key, registry, contract)
    check_dates(dates, 'read')
    start, end = str(dates.min().date()), str(dates.max().date())
    if spec['frequency'] == 'monthly':
        end = str(dates.max().to_period('M').end_time.date())
    record = dict(key=key, sid=spec['sid'], category=spec['category'],
        query='sid="'+spec['sid'].removeprefix('sid=')+'"', start=start, end=end,
        target_months=dates.to_period('M').unique().astype(str).tolist(), raw_unit=spec['raw_unit'],
        reported_unit=spec['metadata_unit'], target_unit='bcm/month', asof=None,
        retrieved_at=datetime.now(timezone.utc).isoformat(), source_contract=CONTRACT,
        transformation='Unchanged monthly bcm' if spec['raw_unit']=='bcm' else
            'Signed monthly-average mcm/day * calendar days / 1000' if spec['frequency']=='monthly' else
            'Signed daily mcm/day capacity derate; subtract once from technical baseline',
        vintage_status='Latest revised historical segment; no origin/publication claim', status='REQUESTED')
    records.append(record)
    out = Path(provenance_dir) if provenance_dir is not None else None
    def retain():
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out/'source_metadata.json').write_text(json.dumps(records, default=str, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    try:
        try:
            response = get_registered_series(key, start, end, registry=registry, client=client, asof=None)
        except Exception as exc:
            # Never emit credentials or opaque service response strings.
            raise ValueError(key+': fresh SID retrieval failed ('+type(exc).__name__+'); check service/credentials/source availability. No cached fallback.') from None
        values = response['values']
        check_dates(values.index, 'read')  # Before serialising any observations.
        record['metadata'] = response['metadata']
        record['registry'] = response['registry']
        record['returned_asof'] = response.get('asof')
        record['returned_query'] = response.get('query')
        if out:
            raw = out/'raw'
            raw.mkdir(parents=True, exist_ok=True)
            suffix = start+'_'+end
            file = raw/(key+'_'+suffix+'.csv')
            if file.exists():
                raise ValueError(key+': raw response destination already exists; never overwrite.')
            values.rename('value').rename_axis('date').to_csv(file, float_format='%.17g')
            record['raw_file'] = file.relative_to(out.parent).as_posix()
            record['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        normal = verify_response(key, response, spec, dates, spec['frequency'])
        record['status'] = 'VERIFIED_HISTORICAL_RESPONSE'
        return normal
    except (ValueError, OSError, KeyError) as exc:
        record['status'] = 'REJECTED'
        record['validation_error'] = str(exc)
        raise
    finally:
        retain()
