"""Optional two-calendar-year net-saleable Snøhvit assumption, never actuals."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .data_functions import get_series, get_metadata
from .evaluation import check_dates
from .routing import finite_nonnegative

HISTORICAL_SID = r'NPD\monthly_by_field\marketed_production\snohvit\gas-saleable'


def seasonal_profile(observations, months, origin, *, allow_partial=False, revision_tolerant=False):
    """Use the latest two complete eligible years; retain signed source values.

    available_at is the observation's information date, or the conservative
    upper bound supplied by an exact archived service-state query. It must never
    be inferred from the delivery month or a latest-revised response.

    Explicit diagnostic flags permit revised pre-origin observations and an
    incomplete seasonal history. A missing calendar month then uses the mean of
    eligible historical daily rates; counts/imputed months are returned in the
    rates attributes. Defaults preserve the strict operational archive contract.
    """
    origin = pd.to_datetime(origin, utc=True)
    if pd.isna(origin):
        raise ValueError('Seasonal Snøhvit requires an explicit information origin.')
    dates = pd.DatetimeIndex(pd.to_datetime(observations.date, utc=True)).tz_localize(None)
    check_dates(dates, 'read')
    if dates.hasnans or dates.has_duplicates or not dates.equals(dates.to_period('M').to_timestamp()):
        raise ValueError('Seasonal history requires unique month-start observations.')
    available = pd.to_datetime(observations.available_at, utc=True)
    if available.isna().any():
        raise ValueError('Missing historical information dates; no latest-revised substitution.')
    if revision_tolerant and (dates.to_period('M') >= origin.tz_localize(None).to_period('M')).any():
        raise ValueError('Revision-tolerant inputs require pre-origin production periods; target-period actuals are forbidden.')
    history = observations.copy()
    history['date'] = dates
    history['monthly_bcm'] = pd.to_numeric(history.monthly_bcm, errors='raise')
    complete_before = dates.to_period('M').end_time < origin.tz_localize(None)
    eligible_information = pd.Series(True,index=observations.index) if revision_tolerant else available <= origin
    history = history.loc[eligible_information.to_numpy() & complete_before].copy()
    complete, gaps = [], {}
    for year in sorted(set(history.date.dt.year), reverse=True):
        if year >= origin.year and not allow_partial:
            continue
        group = history.loc[history.date.dt.year.eq(year)]
        expected = pd.date_range(f'{year}-01-01', f'{year}-12-01', freq='MS')
        finite = group.monthly_bcm.map(lambda v: pd.notna(v) and abs(v) != float('inf'))
        missing = expected.difference(pd.DatetimeIndex(group.loc[finite, 'date']))
        if len(missing) == 0:
            complete.append(year)
        else:
            gaps[str(year)] = missing.strftime('%Y-%m').tolist()
    if not allow_partial and len(complete) < 2:
        raise ValueError('Seasonal Snøhvit requires two complete origin-eligible calendar years; '
                         f'complete years={complete}; missing months={gaps}; no filling.')
    years = sorted(sorted(set(history.date.dt.year),reverse=True)[:2]) if allow_partial else sorted(complete[:2])
    selected = history.loc[history.date.dt.year.isin(years)].sort_values('date').copy()
    if allow_partial:
        selected = selected.loc[selected.monthly_bcm.map(lambda v: pd.notna(v) and abs(v)!=float('inf'))].copy()
        if selected.empty:
            raise ValueError('Seasonal Snøhvit requires some genuine historical observations; no manufactured profile.')
    selected['historical_rate_mcmd'] = selected.monthly_bcm * 1000 / selected.date.dt.days_in_month
    rates = selected.groupby(selected.date.dt.month).historical_rate_mcmd.mean()
    counts = selected.groupby(selected.date.dt.month).size().reindex(range(1,13),fill_value=0)
    imputed = counts.index[counts.eq(0)].tolist()
    if allow_partial:
        rates = rates.reindex(range(1,13)).fillna(selected.historical_rate_mcmd.mean())
    rates.attrs.update(observation_counts=counts.to_dict(),imputed_calendar_months=imputed,
        revision_tolerant=revision_tolerant,allow_partial=allow_partial)
    # Negative accounting observations survive averaging; a negative resulting
    # physical assumption is rejected, not clipped or replaced by another method.
    finite_nonnegative(rates, 'Seasonal Snøhvit average rates; signed history retained')
    months = pd.PeriodIndex(months, freq='M')
    if months.empty or months.hasnans or not months.equals(pd.period_range(months.min(), months.max(), freq='M')):
        raise ValueError('Seasonal forecast requires an ordered complete monthly grid.')
    if months.min() <= origin.tz_localize(None).to_period('M'):
        raise ValueError('Seasonal deliveries must start after their information origin.')
    forecast = pd.Series([rates.loc[m.month] * m.days_in_month / 1000 for m in months],
                         index=months, name='snohvit_bcm')
    return forecast, selected, rates, years, gaps


def retrieve_seasonal_snohvit(months, origin, records, output, client):
    """Fresh exact SID archive; historical bounds stop before the locked holdout."""
    origin = pd.to_datetime(origin, utc=True)
    if pd.isna(origin) or origin > pd.Timestamp.now(tz='UTC'):
        raise ValueError('Seasonal Snøhvit requires a valid non-future information origin.')
    last_year = min(origin.year - 1, 2025)
    start, end = f'{last_year-4}-01-01', f'{last_year}-12-31'
    check_dates([start, end], 'read')
    query = f'sid="{HISTORICAL_SID}"@asof:{origin.strftime("%Y-%m-%dT%H:%M:%S")}'
    output = Path(output)
    record = dict(key='snohvit_seasonal_baseline', sid=HISTORICAL_SID,
        kind='seasonal_historical_baseline', method='seasonal_two_year', asof=origin.isoformat(),
        query=query, start=start, end=end, status='REQUESTED',
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        information_date_basis='Exact archived service state; asof is an availability upper bound, not an individual publication date',
        target_unit='bcm/month', transformation='Signed net-saleable bcm / calendar days * 1000; mean rate by calendar month across latest two complete eligible years; rate * forecast days / 1000')
    records.append(record)
    try:
        try:
            meta = get_metadata(query, client=client)
        except KeyError:
            raise ValueError('Snøhvit native archive has no source metadata at this origin; cannot certify eligible net-saleable history.') from None
        record['metadata'] = meta
        if (meta.get('unit') != 'bcm' or meta.get('frequency') != 'monthly'
                or meta.get('lifecycle_stage') not in {'actual', 'historical'}
                or meta.get('country_iso') != 'NO'
                or meta.get('ea_field_name_standardised') != 'snohvit'
                or meta.get('ea_production_type') != 'marketed_production'
                or meta.get('source_obj', {}).get('aspect') != 'gas-saleable'
                or meta.get('source_obj', {}).get('units') != 'bill Sm3'):
            raise ValueError('Snøhvit archive lacks the native monthly net-saleable source contract.')
        try:
            values = get_series(query, start, end, client=client)
        except KeyError:
            raise ValueError('Snøhvit native archive has no monthly observations at this origin; no revised substitution.') from None
        dates = pd.DatetimeIndex(pd.to_datetime(values.index, utc=True)).tz_localize(None)
        if ((dates < pd.Timestamp(start)) | (dates > pd.Timestamp(end))).any():
            raise ValueError('Snøhvit historical response exceeds requested bounds.')
        raw = output/'raw'/'snohvit_seasonal_history.csv'
        raw.parent.mkdir(exist_ok=True, parents=True)
        if raw.exists():
            raise ValueError('Seasonal raw capture already exists; no overwrite.')
        values.rename('value').rename_axis('date').to_csv(raw, float_format='%.17g')
        record.update(raw_file=raw.relative_to(output.parent).as_posix(),
                      sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
        observations = pd.DataFrame(dict(date=dates, monthly_bcm=values.to_numpy(), available_at=origin.isoformat()))
        forecast, selected, rates, years, gaps = seasonal_profile(observations, months, origin)
        selected.to_csv(output/'snohvit_seasonal_observations.csv', index=False)
        rates.rename('seasonal_rate_mcmd').rename_axis('calendar_month').to_csv(output/'snohvit_seasonal_rates.csv')
        forecast.rename_axis('month').to_csv(output/'snohvit_seasonal_forecast.csv')
        record.update(status='VERIFIED_SEASONAL_ASSUMPTION', selected_years=years,
            incomplete_year_gaps=gaps, selected_observations=selected.to_dict('records'),
            seasonal_rates_mcmd=rates.to_dict(), monthly_forecast_bcm={str(k):v for k,v in forecast.items()},
            qualification='Historical seasonal assumption, not an archived EA Snøhvit forecast; no accuracy score or demand calibration')
        return forecast
    except (ValueError, OSError, KeyError) as exc:
        record.update(status='REJECTED', validation_error=str(exc))
        raise
    finally:
        output.mkdir(exist_ok=True, parents=True)
        (output/'source_metadata.json').write_text(json.dumps(records, default=str, indent=2, allow_nan=False)+'\n', encoding='utf-8')
