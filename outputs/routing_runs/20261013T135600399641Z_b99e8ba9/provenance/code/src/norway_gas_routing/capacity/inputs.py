"""Opt-in historical capacity candidates; public observations are not LP limits.

The archived SQLite database is always opened read-only. No public observation
currently passes all definition, unit, effective-date and maintenance gates.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
import sqlite3

import pandas as pd

from .contract import ARCS, IDENTITIES
from ..evaluation import check_dates
from .public import sha256

DATABASE = 'archive/20261009-17_public-capacity-database/database/capacity.sqlite'
DATABASE_SHA256 = '5e6e2b14c76a0afb94aa487e316c617f37fd78f95f117d96ec30232b180721a4'
STATES = {'VERIFIED_COMPATIBLE', 'CONDITIONAL', 'DEFINITION_MISMATCH',
          'INSUFFICIENT_EVIDENCE', 'MISSING_DATA'}
# All rates below are assumptions on the existing dry-volume model boundary.
# Dates are sensitivity endpoints, never asserted commissioning dates.
SCENARIOS = {
    'baseline': {},
    'evidence-backed': {},
    'kollsnes-144.5': {'KOLLSNES_EXPORT': [('2023-01-01', '2026-01-01', 144.5)]},
    'kollsnes-156': {'KOLLSNES_EXPORT': [('2023-01-01', '2026-01-01', 156.)]},
    'kollsnes-autumn-early': {'KOLLSNES_EXPORT': [
        ('2023-01-01', '2023-09-01', 144.5), ('2023-09-01', '2026-01-01', 156.)]},
    'kollsnes-autumn-late': {'KOLLSNES_EXPORT': [
        ('2023-01-01', '2023-12-01', 144.5), ('2023-12-01', '2026-01-01', 156.)]},
    'karsto-97-proxy': {'KARSTO_PROCESSING': [('2023-01-01', '2026-01-01', 97.)]},
    'kollsnes-156-karsto-97-proxy': {
        'KOLLSNES_EXPORT': [('2023-01-01', '2026-01-01', 156.)],
        'KARSTO_PROCESSING': [('2023-01-01', '2026-01-01', 97.)]},
}


def baseline_rate(entry):
    """Read a known baseline assumption; absent values never imply zero."""
    if entry.get('mcm_d') is not None:
        value = float(entry['mcm_d'])
    elif entry.get('annual_bcm') is not None:
        value = float(entry['annual_bcm']) * 1000 / 365
    else:
        raise ValueError('Missing baseline capacity; no zero/full-capacity default')
    if not math.isfinite(value) or value < 0:
        raise ValueError('Invalid baseline capacity')
    return value


def validate_point_topology(model, db):
    arcs = {a['id']: a for a in model['routing']['arcs']}
    for name, expected in ARCS.items():
        if name not in arcs or tuple(arcs[name][k] for k in ('from', 'to', 'asset')) != expected:
            raise ValueError('Capacity mapping topology changed: ' + name)
    for key, identity in IDENTITIES.items():
        actual = db.execute('SELECT operator_key,point_key,direction FROM assets WHERE asset_key=?', (key,)).fetchone()
        if actual is None or tuple(actual) != identity[:3]:
            raise ValueError('Capacity point identity mismatch: ' + key)


def observation_state(row):
    if row['value'] is None:
        return 'INSUFFICIENT_EVIDENCE'
    boundary = row['physical_boundary'].lower()
    if row['asset_id'] == 'KARSTO_PROCESSING' or 'rich' in boundary:
        return 'DEFINITION_MISMATCH'
    # All retained specifications lack an exact historical validity schedule.
    if row['capacity_category'] == 'point_technical':
        return 'CONDITIONAL'
    return 'INSUFFICIENT_EVIDENCE'


def database_candidates(root, model, months):
    """Return every distinct specification/point observation by model asset/month.

    Snapshots retain null effective dates. They are not replicated as daily facts.
    candidate_bcm remains null until a separate reviewed schedule is supplied.
    """
    months = pd.PeriodIndex(months, freq='M')
    check_dates(months, 'analysis')  # Before opening/reading source values.
    path = (Path(root) / DATABASE).resolve()
    if sha256(path) != DATABASE_SHA256:
        raise ValueError('Pinned capacity database changed; re-audit required')
    result = []
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        validate_point_topology(model, db)
        db.row_factory = sqlite3.Row
        specifications = [dict(r) for r in db.execute('''SELECT a.asset_id,
            a.physical_boundary AS model_boundary,r.*,s.url,s.raw_sha256,
            s.capture_kind,s.retrieved_at FROM assets a JOIN ratings r USING(asset_key)
            JOIN sources s USING(source_id) WHERE a.scope='poc_active'
            AND r.capacity_category!='model_assumption' ORDER BY a.asset_id,r.rating_id''')]
        for month in months:
            for row in specifications:
                result.append(dict(row, month=str(month), status=observation_state(row),
                    coverage_status='snapshot_effective_dates_unknown',
                    conversion_methodology='blocked: definition/dated validity not verified',
                    candidate_bcm=None, optimiser_eligible=False,
                    restriction_coverage='unknown', input_class='historical_specification_snapshot'))
            for key, identity in IDENTITIES.items():
                asset = 'NORTH_SEA_ENTRY' if identity[3] == 'NORTH_SEA_ENTRY' else 'BALTIC_PIPE'
                monthly = db.execute('SELECT * FROM monthly WHERE asset_key=? AND month=?', (key, str(month))).fetchone()
                lineage = [dict(r) for r in db.execute('''SELECT gas_day,gas_day_start,gas_day_end,
                    gas_day_hours,quality,source_id,source_record_ids_json,source_revisions_json
                    FROM daily WHERE asset_key=? AND substr(gas_day,1,7)=? ORDER BY gas_day''', (key, str(month)))]
                source = db.execute('''SELECT s.* FROM sources s JOIN assets a USING(source_id)
                    WHERE a.asset_key=?''', (key,)).fetchone()
                known = monthly is not None and monthly['quality'] == 'complete'
                result.append(dict(asset_id=asset, month=str(month), asset_key=key,
                    physical_boundary=identity[3], model_boundary=identity[3],
                    operator=identity[0], point=identity[1], direction=identity[2],
                    rating_id=key + ':' + str(month), value=monthly['technical_kwh'] if known else None,
                    known_subtotal_kwh=monthly['known_subtotal_kwh'] if monthly else None,
                    original_unit='kWh/source-gas-day aggregated by start month',
                    capacity_category='point_technical',
                    valid_from=lineage[0]['gas_day_start'] if lineage else None,
                    valid_to=lineage[-1]['gas_day_end'] if lineage else None,
                    valid_date_precision='source_gas_day',
                    coverage_status=monthly['quality'] if monthly else 'missing_month',
                    covered_days=monthly['covered_gas_days'] if monthly else 0,
                    status='CONDITIONAL' if known else 'MISSING_DATA',
                    conversion_methodology='blocked: capacity-basis GCV/model reference/month alignment',
                    candidate_bcm=None, optimiser_eligible=False,
                    source_id=source['source_id'], url=source['url'],
                    raw_sha256=source['raw_sha256'], capture_kind=source['capture_kind'],
                    retrieved_at=source['retrieved_at'],
                    revision_lineage=json.dumps(lineage, sort_keys=True),
                    vintage_status='latest_revised_origin_unverified',
                    restriction_coverage='unknown; published reductions not attributed to outages',
                    input_class='latest_revised_historical_point_technical'))
    return pd.DataFrame(result)


def dated_daily_rates(intervals, months):
    """Explicit half-open calendar-date schedule; never fill past validity ends."""
    days = pd.date_range(months.min().start_time, months.max().end_time.normalize())
    values = pd.Series(float('nan'), index=days)
    previous_end = None
    for start, end, rate in sorted(intervals):
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        if (start.tz is not None or end.tz is not None or start != start.normalize()
                or end != end.normalize() or end <= start
                or not math.isfinite(rate) or rate < 0):
            raise ValueError('Invalid dated capacity interval')
        if previous_end is not None and start < previous_end:
            raise ValueError('Overlapping capacity intervals')
        previous_end = end
        values.loc[(days >= start) & (days < end)] = rate
    if values.isna().any():
        raise ValueError('Missing capacity schedule coverage; no forward filling')
    return values


def select_capacity_scenario(inputs, model, *, scenario='baseline', candidates=None):
    """Copy prepared inputs, select explicit assumptions, retain baseline fallbacks.

    Baseline never opens the database. Evidence-backed mode currently changes no
    limits; no retained public source meets the full eligibility contract.
    Sensitivities preserve the original signed maintenance deduction exactly once.
    """
    if scenario not in SCENARIOS:
        raise ValueError('Explicit known capacity scenario required')
    months = pd.PeriodIndex(inputs['months'], freq='M')
    check_dates(months, 'analysis')
    if scenario == 'evidence-backed' and candidates is None:
        raise ValueError('Evidence-backed selection requires database candidates')
    if candidates is not None and candidates.optimiser_eligible.any():
        raise ValueError('No public schedule currently has reviewed activation evidence')
    changed = deepcopy(inputs)
    capacities = inputs['capacities'].copy(deep=True)
    ledger = []
    daily = inputs.get('capacity_daily')
    for asset in capacities.columns:
        entry = model['routing']['assets'][asset]
        adjustment = pd.Series(0., index=months)
        if asset in SCENARIOS[scenario]:
            rates = dated_daily_rates(SCENARIOS[scenario][asset], months)
            if entry.get('technical_series_file') or 'mcm_d' not in entry:
                raise ValueError('Sensitivity requires the exact constant baseline rating')
            original = float(entry['mcm_d'])
            adjustment = (rates - original).groupby(rates.index.to_period('M')).sum() / 1000
            if entry.get('maintenance_series'):
                if daily is None:
                    raise ValueError('Signed baseline maintenance lineage required')
                rows = daily.loc[daily.asset.eq(asset)].copy()
                rows.index = pd.to_datetime(rows['date'])
                expected = rates.index
                if not rows.index.is_unique or set(rows.index) != set(expected):
                    raise ValueError('Complete unique daily maintenance coverage required')
                rows = rows.reindex(expected)
                if not rows.technical_capacity_mcm_d.eq(original).all():
                    raise ValueError('Baseline technical rating changed')
                residual = rates - rows.maintenance_derate_mcm_d
                if not residual.map(math.isfinite).all() or (residual < 0).any():
                    raise ValueError('Invalid daily capacity after original maintenance')
            capacities[asset] += adjustment
            if daily is not None:
                mask = changed['capacity_daily'].asset.eq(asset)
                delta = pd.to_datetime(changed['capacity_daily'].loc[mask, 'date']).map(rates - original).to_numpy()
                for column in ('technical_capacity_mcm_d', 'available_capacity_mcm_d'):
                    changed['capacity_daily'].loc[mask, column] += delta
            if 'capacity_monthly' in changed:
                mask = changed['capacity_monthly'].asset.eq(asset)
                delta = changed['capacity_monthly'].loc[mask, 'month'].map(lambda m: adjustment.at[pd.Period(m, freq='M')]).to_numpy()
                for column in ('technical_capacity_bcm', 'available_capacity_bcm'):
                    changed['capacity_monthly'].loc[mask, column] += delta
        for month in months:
            is_changed = asset in SCENARIOS[scenario]
            eligible_observations = candidates.loc[candidates.asset_id.eq(asset) & candidates.month.eq(str(month))] if candidates is not None else None
            if asset == 'KARSTO_PROCESSING':
                status = 'DEFINITION_MISMATCH'
            elif is_changed:
                status = 'CONDITIONAL'
            else:
                status = 'INSUFFICIENT_EVIDENCE'
            ledger.append(dict(month=str(month), asset=asset, scenario=scenario,
                mode='A' if scenario == 'baseline' else 'B' if scenario == 'evidence-backed' else 'C',
                baseline_bcm=inputs['capacities'].at[month, asset],
                selected_bcm=capacities.at[month, asset], delta_bcm=adjustment.at[month],
                status=status, public_candidate_eligible=False,
                use_basis='explicit_assumption_sensitivity' if is_changed else 'baseline_assumption_fallback',
                fallback=not is_changed, public_observations=0 if eligible_observations is None else len(eligible_observations),
                capacity_class='assumed_historical_effective' if is_changed else 'existing_provisional_model_assumption',
                maintenance_policy='retain original signed deduction once; compatibility unresolved' if entry.get('maintenance_series') else 'no new deduction; engineering availability unknown',
                provenance='capacity_inputs.SCENARIOS; operator rating evidence; dates and dry equivalence assumed' if is_changed else 'config/model.yaml and original capacity preparation'))
    if not capacities.map(lambda v: math.isfinite(v) and v >= 0).all().all():
        raise ValueError('Nonfinite/negative selected capacity')
    changed['capacities'] = capacities
    changed['selected_capacity_inputs'] = pd.DataFrame(ledger)
    changed['capacity_scenario'] = scenario
    changed.setdefault('provenance', []).append({'category': 'capacity_scenario',
        'scenario': scenario, 'mode': 'A' if scenario == 'baseline' else 'B' if scenario == 'evidence-backed' else 'C',
        'schedules': deepcopy(SCENARIOS[scenario]), 'forecast_effective': False,
        'verified_public_replacements': 0, 'baseline_fallbacks_explicit': True})
    return changed
