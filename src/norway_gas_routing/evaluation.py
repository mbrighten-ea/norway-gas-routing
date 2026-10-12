"""Fixed chronological protocol and fail-closed forecast information checks.

Reconstruction inputs may be revised. Forecast inputs must prove availability
at the origin; observation/effective dates alone do not prove availability.
No holdout evaluation or routine unlock is implemented.
"""
import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
TRAIN_END = pd.Period('2024-12', 'M')
VALIDATION_END = pd.Period('2025-12', 'M')
TRAIN_CUTOFF = pd.Timestamp('2024-12-31T23:59:59Z')
ROUTINE_END = '2025-12-31'


class EvaluationError(ValueError):
    pass


def load_policy(path=None):
    path = Path(path or ROOT / 'config/evaluation.yaml')
    policy = yaml.safe_load(path.read_text(encoding='utf-8'))
    expected = {'training': {'end': '2024-12', 'information_cutoff': '2024-12-31T23:59:59Z'},
                'validation': {'start': '2025-01', 'end': '2025-12'},
                'holdout': {'start': '2026-01', 'end': '2026-09', 'locked': True,
                            'frozen_model': None, 'approval': None},
                'price_response_enabled': False}
    if policy != expected:
        raise EvaluationError('Fixed evaluation protocol changed or holdout unlock attempted; requires a separately approved protocol')
    return {**policy, 'config_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def months_of(values):
    if isinstance(values, pd.PeriodIndex) or isinstance(getattr(values, 'dtype', None), pd.PeriodDtype):
        return pd.PeriodIndex(values).asfreq('M')
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True)).tz_localize(None).to_period('M')


def check_dates(values, purpose='analysis'):
    """Reject holdout/future data before fitting, scoring, diagnostics or plotting."""
    load_policy()
    if purpose not in {'fit', 'analysis', 'score', 'plot', 'selection', 'read'}:
        raise EvaluationError(f'Unknown evaluation purpose: {purpose}')
    months = months_of(values)
    if purpose in {'fit', 'score', 'selection'} and months.hasnans:
        raise EvaluationError(f'{purpose}: missing dates cannot be assigned to a split')
    limit = TRAIN_END if purpose == 'fit' else VALIDATION_END
    if (months.dropna() > limit).any():
        raise EvaluationError(f'{purpose}: dates exceed {limit}; training ends 2024-12 and 2026 holdout is locked')
    return months


def request_bounds(start='MIN', end='MAX', purpose='read'):
    """Bound unqualified requests; reject explicit future requests before I/O."""
    limit = '2024-12-31' if purpose == 'fit' else ROUTINE_END
    end = limit if end == 'MAX' else end
    try:
        check_dates([end] + ([] if start == 'MIN' else [start]), purpose)
        if start != 'MIN' and pd.Timestamp(start) > pd.Timestamp(end):
            raise EvaluationError('Requested start is after end')
    except EvaluationError:
        raise
    except (TypeError, ValueError) as exc:
        raise EvaluationError('Use explicit absolute date bounds, not relative dates') from exc
    return start, end


def read_parquet(path, *, purpose='read', date_column=None, start='MIN', end='MAX'):
    """Predicate-filter cached timestamp Parquet BEFORE loading observation values.

    Old raw caches are preserved, even when they contain reserved observations.
    Non-temporal indexes require an explicit date_column; there is no unbounded
    fallback. Period extension indexes cannot be predicate-filtered by the
    installed Arrow: inspect only their date column and refuse unsafe files.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq
    start, end = request_bounds(start, end, purpose)
    schema = pq.read_schema(path)
    metadata = json.loads(schema.metadata.get(b'pandas', b'{}')) if schema.metadata else {}
    index_columns = metadata.get('index_columns', [])
    column = date_column or (index_columns[0] if len(index_columns) == 1 and isinstance(index_columns[0], str) else None)
    if column is None or column not in schema.names:
        raise EvaluationError(f'{path}: explicit temporal index/date_column required')
    field = schema.field(column)
    pandas_column = next((c for c in metadata.get('columns', []) if c.get('field_name') == column), {})
    period = pandas_column.get('numpy_type', '').startswith('period[')
    if period:
        frequency = pandas_column['numpy_type'][7:-1]
        upper = pd.Period(end, frequency).ordinal + 1
        lower = None if start == 'MIN' else pd.Period(start, frequency).ordinal
        # Read dates only; never load observation values from an unsafe file.
        stored = pq.ParquetFile(path).read(columns=[column]).column(0).combine_chunks()
        ordinals = stored.storage.to_pylist() if isinstance(stored, pa.ExtensionArray) else stored.to_pylist()
        if any(v is None or v >= upper or (lower is not None and v < lower) for v in ordinals):
            raise EvaluationError('Period-index cache crosses requested boundary; timestamp-normalised cache required, original unchanged')
        frame = pd.read_parquet(path)
        check_dates(frame.index, purpose)
        return frame
    elif pa.types.is_timestamp(field.type):
        upper = pd.Timestamp(end).normalize() + timedelta(days=1)
        lower = None if start == 'MIN' else pd.Timestamp(start)
        if field.type.tz:
            upper = upper.tz_localize('UTC') if upper.tzinfo is None else upper.tz_convert('UTC')
            if lower is not None:
                lower = lower.tz_localize('UTC') if lower.tzinfo is None else lower.tz_convert('UTC')
    elif pa.types.is_date(field.type):
        upper = (pd.Timestamp(end).normalize() + timedelta(days=1)).date()
        lower = None if start == 'MIN' else pd.Timestamp(start).date()
    else:
        raise EvaluationError(f'{path}: unsupported temporal storage {field.type}')
    filters = [(column, '<', upper)]
    if lower is not None:
        filters.append((column, '>=', lower))
    frame = pd.read_parquet(path, filters=filters)
    check_dates(frame[date_column] if date_column else frame.index, purpose)
    return frame


def check_table(frame, purpose='analysis'):
    for column in ('month', 'target_month', 'date', 'calendar_date', 'timestamp'):
        if column in frame:
            check_dates(frame[column], purpose)
    return frame


def validate_forecast_inputs(records, origin, *, price_enabled=False):
    """Validate a complete origin bundle, never substitute latest inputs.

    Required categories include parameters' training flows. Each record needs
    immutable identity, archive query evidence and independently checked release
    availability. Forecast/known-plan effective dates may follow the origin;
    realised observations may not. Technical changes need dated effectiveness.
    """
    origin = pd.Timestamp(origin)
    if pd.isna(origin):
        raise EvaluationError('Forecast origin must be a valid date')
    origin = origin.tz_localize('UTC') if origin.tzinfo is None else origin.tz_convert('UTC')
    check_dates([origin], 'read')
    required = {'production', 'maintenance', 'technical_capacity', 'historical_flows'}
    if price_enabled:
        required.add('prices')
    if required - {r.get('category') for r in records}:
        raise EvaluationError('Incomplete historical vintage bundle: missing input categories')
    for record in records:
        if not all(record.get(k) for k in ('key', 'sha256', 'evidence_file', 'query', 'asof', 'available_at')):
            raise EvaluationError('Incomplete historical vintage evidence; reconstruction only')
        if record.get('availability_verified') is not True or record.get('archive_verified') is not True:
            raise EvaluationError('Unverified archive/release timing; reconstruction only')
        try:
            asof, available = pd.to_datetime([record['asof'], record['available_at']], utc=True)
        except (TypeError, ValueError) as exc:
            raise EvaluationError('Archive and availability must be valid dates') from exc
        if pd.isna(asof) or pd.isna(available):
            raise EvaluationError('Archive and availability must be valid dates')
        if asof > origin or available > asof:
            raise EvaluationError('Input became available after its archive cutoff/origin')
        if '@asof' not in record['query'] or record['asof'] not in record['query']:
            raise EvaluationError('Archive query does not match recorded asof')
        targets = check_dates(record.get('target_months', []), 'read')
        if len(targets) == 0 or targets.hasnans:
            raise EvaluationError('Input target coverage must be explicit and nonempty')
        kind = record.get('kind')
        if kind not in {'actual', 'forecast', 'known_plan', 'technical_schedule'}:
            raise EvaluationError('Explicit input kind required')
        origin_month = origin.tz_localize(None).to_period('M')
        if kind == 'actual' and (targets > origin_month).any():
            raise EvaluationError('Future realised observations in forecast bundle')
        if kind == 'actual' and (targets.to_timestamp(how='end').normalize().tz_localize('UTC') > available.normalize()).any():
            raise EvaluationError('Monthly actual claimed available before its observation period ended')
        if kind == 'forecast':
            first = record.get('forecast_start')
            if not first or (targets <= origin_month).any() or (targets < pd.Period(first, 'M')).any():
                raise EvaluationError('Future values are not verified genuine forecasts')
        if record['category'] == 'technical_capacity':
            if not record.get('effective_at'):
                raise EvaluationError('Technical capacity requires dated effectiveness, not backfilling')
            try:
                effective = pd.to_datetime(record['effective_at'], utc=True)
            except (TypeError, ValueError) as exc:
                raise EvaluationError('Technical capacity effectiveness must be a valid date') from exc
            if pd.isna(effective) or effective > targets.min().start_time.tz_localize('UTC'):
                raise EvaluationError('Technical capacity is not effective throughout its claimed monthly coverage')
        if record['category'] == 'historical_flows':
            check_dates(targets, 'fit')
            if available > min(origin, TRAIN_CUTOFF) or asof > min(origin, TRAIN_CUTOFF):
                raise EvaluationError('Parameter training vintage exceeds training information cutoff')
    return True


def reconstruction_evaluation(root, inputs, settings, experiment_id):
    """Save the frozen parameter identities and explicitly unverified input vintages."""
    check_dates(inputs['months'])
    check_dates(inputs['training_observations'].index, 'fit')
    parameters = {'historical_routing_shares': inputs['preferences'],
                  'seasonal_preferences': None, 'price_response': {'enabled': False},
                  'training_start': settings['baseline_start'], 'training_end': settings['baseline_end'],
                  'information_cutoff': str(TRAIN_CUTOFF),
                  'training_vintage_status': 'latest/revised; availability by training cutoff unverified'}
    parameters_hash = hashlib.sha256(json.dumps(parameters, sort_keys=True, default=str).encode()).hexdigest()
    vintages = [{**r, 'kind': 'current technical envelope' if r.get('category') == 'technical_capacity' else 'realised/revised',
                 'available_at': None, 'availability_verified': False, 'archive_verified': False,
                 'vintage_limitation': 'Historical effectiveness and availability unverified; no backdated forecast claim'
                    if r.get('category') == 'technical_capacity' else
                    'Latest/revised retained values; archive and public release timing unverified'}
                for r in inputs['provenance']]
    return {'split': load_policy(), 'experiment_id': experiment_id, 'analysis_mode': 'historical_reconstruction',
            'forecast_origin': None, 'target_start': str(inputs['months'].min()), 'target_end': str(inputs['months'].max()),
            'period_role': 'development' if inputs['months'].max() <= TRAIN_END else 'validation comparison only',
            'model_parameters': parameters, 'parameters_sha256': parameters_hash,
            'input_vintages': vintages, 'complete_origin_vintages': False,
            'forecast_blockers': ['Production workbook, production/Snohvit, maintenance and technical capacities lack complete verified origin vintages',
                                 'Training-flow availability by 2024-12 cutoff and public release timing unverified'],
            'holdout_scored': False, 'model_frozen': False}


def validate_manifest(manifest):
    evaluation = manifest.get('evaluation')
    if not evaluation or evaluation.get('split') != load_policy():
        raise EvaluationError('Run manifest requires the fixed split and its configuration identity')
    check_dates([evaluation['target_start'], evaluation['target_end']], 'score')
    parameters = evaluation['model_parameters']
    check_dates([parameters['training_start'], parameters['training_end']], 'fit')
    digest = hashlib.sha256(json.dumps(parameters, sort_keys=True, default=str).encode()).hexdigest()
    if digest != evaluation['parameters_sha256'] or evaluation['experiment_id'] != manifest['run_id']:
        raise EvaluationError('Experiment/parameter identity mismatch')
    if parameters['price_response']['enabled']:
        raise EvaluationError('This protocol preserves the price-free baseline; no price model is authorised')
    if evaluation['analysis_mode'] == 'retrospective_forecast':
        validate_forecast_inputs(evaluation['input_vintages'], evaluation['forecast_origin'],
                                 price_enabled=parameters['price_response']['enabled'])
    elif evaluation['analysis_mode'] != 'historical_reconstruction':
        raise EvaluationError('Unknown analysis mode')
    if evaluation.get('holdout_scored') is not False:
        raise EvaluationError('Holdout scoring is not authorised')


def validate_result_dates(frame, manifest):
    """Require dated results to match the complete declared monthly window."""
    check_table(frame, 'score')
    column = next((name for name in ('month', 'target_month', 'date') if name in frame), None)
    if column is None or frame.empty:
        raise EvaluationError('Published results require nonempty dated coverage')
    actual = check_dates(frame[column], 'score').unique().sort_values()
    evaluation = manifest['evaluation']
    expected = pd.period_range(evaluation['target_start'], evaluation['target_end'], freq='M')
    if not actual.equals(expected):
        raise EvaluationError('Result coverage does not match declared manifest target window')
