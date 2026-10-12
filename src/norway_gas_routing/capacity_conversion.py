"""Fail-closed conversion arithmetic for a future reviewed point contract.

No real point factors are configured or inferred from measured-flow GCV.
"""
from datetime import timedelta
import math
import pandas as pd

from .capacity_contract import IDENTITIES
from .evaluation import check_dates
from .public_capacity import gas_boundary

REQUIREMENTS = ('capacity_basis_verified', 'gross_energy_verified',
                'volume_reference_verified', 'energy_reference_verified',
                'model_reference_compatible', 'compressibility_verified',
                'monthly_alignment_approved', 'physical_mapping_approved')


def convert_gas_day_quantities(days, contract, *, asset_key):
    """Convert complete reported quantities using dated kWh/model-m3 factors.

    Missing days remain unknown; zero remains zero only with complete definitions.
    This utility is not an approval mechanism and never changes optimiser inputs.
    """
    if asset_key not in IDENTITIES or tuple(contract['identity']) != IDENTITIES[asset_key][:3]:
        raise ValueError('Conversion point identity mismatch')
    check_dates(days['gas_day'], 'analysis')
    for column, expected in {'asset_key': asset_key, 'capacity_category': 'point_technical', 'original_unit': 'kWh/d'}.items():
        if column in days and not days[column].eq(expected).all():
            raise ValueError('Incompatible source identity/category/unit: ' + column)
    if not all(contract.get(k) is True for k in REQUIREMENTS):
        raise ValueError('Unsupported conversion definitions or approval')
    if not contract.get('source_url') or not contract.get('source_sha256') or not contract.get('approval_reference'):
        raise ValueError('Traceable source and review reference required')
    if contract.get('monthly_basis') != 'gas_day_start_label':
        raise ValueError('Hourly evidence required for calendar-boundary conversion')
    if contract.get('factor_kind') != 'capacity_basis_kwh_per_model_m3':
        raise ValueError('Measured-flow/settlement GCV is not a capacity factor')
    factors = contract['factor_intervals']
    previous_end = None
    for item in sorted(factors, key=lambda r: r['start']):
        start, end = pd.Timestamp(item['start']), pd.Timestamp(item['end'])
        factor = item['kwh_per_model_m3']
        if (start.tz is None or end.tz is None or end <= start or
                not math.isfinite(factor) or factor <= 0 or
                (previous_end is not None and start < previous_end)):
            raise ValueError('Invalid or overlapping factor validity intervals')
        previous_end = end
    values = []
    for row in days.to_dict('records'):
        start, end = pd.Timestamp(row['gas_day_start']), pd.Timestamp(row['gas_day_end'])
        if start.tz is None or end.tz is None or end <= start:
            raise ValueError('Timezone-aware half-open source gas day required')
        label = pd.Timestamp(row['gas_day']).date()
        if (start != pd.Timestamp(gas_boundary(label)) or
                end != pd.Timestamp(gas_boundary(label + timedelta(days=1)))):
            raise ValueError('06:00 CET/CEST source boundaries required')
        matches = [i for i in factors if pd.Timestamp(i['start']) <= start and pd.Timestamp(i['end']) >= end]
        if len(matches) != 1:
            raise ValueError('Exactly one supported factor for the whole gas day required')
        energy = row['technical_kwh_per_gas_day']
        known = row['quality'] in {'complete', 'reported_zero'} and pd.notna(energy)
        if known and (not math.isfinite(energy) or energy < 0):
            raise ValueError('Invalid original energy quantity')
        values.append(energy / matches[0]['kwh_per_model_m3'] / 1e9 if known else float('nan'))
    result = days.copy()
    result['candidate_bcm'] = values
    result['conversion_source'] = contract['source_url']
    result['approval_reference'] = contract['approval_reference']
    return result


def aggregate_converted_month(days, month):
    """Unknown full-month capacity unless every source gas-day label is present."""
    month = pd.Period(month, freq='M')
    expected = pd.date_range(month.start_time, month.end_time.normalize()).strftime('%Y-%m-%d')
    rows = days.loc[days.gas_day.str[:7].eq(str(month))]
    if not rows.gas_day.is_unique:
        raise ValueError('Duplicate gas-day quantities cannot be summed')
    complete = set(rows.gas_day) == set(expected) and rows.candidate_bcm.notna().all()
    return {'month': str(month), 'candidate_bcm': rows.candidate_bcm.sum() if complete else None,
            'known_subtotal_bcm': rows.candidate_bcm.sum(min_count=1),
            'coverage_status': 'complete' if complete else 'MISSING_DATA'}
