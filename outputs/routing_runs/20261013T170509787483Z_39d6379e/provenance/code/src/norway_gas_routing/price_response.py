"""Bounded fresh 2024 price features for empirical routing experiments."""
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data_functions import connect_shooju, get_series, get_metadata
from .project_data import get_registered_series
from .evaluation import check_dates

FX_SID = r'ECB_exchange_rates\euro_to_gbp'
THERM_MWH = .0293071
PRICE_SCALE = 10.
STRENGTHS = {'zero': 0., 'low': .25, 'medium': 1., 'high': 4.}


def monthly_features(quotes):
    """Matched quote-date means, no filling or delivery-day weighting."""
    required = ['nbp_day_ahead', 'peg_day_ahead', 'ttf_day_ahead', 'eur_gbp']
    if set(quotes) != set(required):
        raise ValueError('Exact NBP, PEG, TTF and dated GBP-per-EUR series required')
    cleaned = {}
    for name in required:
        values = quotes[name].copy()
        dates = pd.DatetimeIndex(values.index)
        check_dates(dates, 'fit')
        if dates.tz is not None:
            dates = dates.tz_localize(None)
        if dates.has_duplicates or not dates.equals(dates.normalize()):
            raise ValueError('Unique midnight quote-date labels required')
        if not len(values) or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError('Empty/nonfinite price or FX observations')
        if set(dates.year) != {2024}:
            raise ValueError('This experiment consumes only 2024 quotes')
        values.index = dates
        cleaned[name] = values
    if (cleaned['eur_gbp'] <= 0).any():
        raise ValueError('GBP-per-EUR must be positive')
    daily = pd.concat(cleaned, axis=1).dropna()
    daily['NBP_EUR_MWh'] = daily.nbp_day_ahead / 100 / THERM_MWH / daily.eur_gbp
    daily['UK'] = daily.NBP_EUR_MWh - daily.ttf_day_ahead
    daily['FR'] = daily.peg_day_ahead - daily.ttf_day_ahead
    daily['DE_NL'] = 0.
    monthly = daily.groupby(daily.index.to_period('M')).mean()
    monthly['matched_quote_dates'] = daily.groupby(daily.index.to_period('M')).size()
    if not monthly.index.equals(pd.period_range('2024-01', '2024-12', freq='M')):
        raise ValueError('Missing monthly price coverage; no filling')
    return monthly, daily


def retrieve_features(output, *, client=None):
    """Query exact SIDs afresh with explicit 2024 bounds; no retained fallback."""
    output = Path(output)
    output.mkdir()
    client = connect_shooju() if client is None else client
    quotes, ledger = {}, []
    expected = {'nbp_day_ahead': 'p_therm', 'peg_day_ahead': 'eur_MWh', 'ttf_day_ahead': 'eur_MWh'}
    for name, unit in expected.items():
        response = get_registered_series(name, '2024-01-01', '2024-12-31', client=client)
        metadata = response['metadata']
        if metadata.get('unit') != unit:
            raise ValueError('Unexpected raw price unit: '+name)
        if metadata.get('lifecycle_stage') not in ('actual', 'historical'):
            raise ValueError('Historical quote lifecycle unverified: '+name)
        quotes[name] = response['values']
        ledger.append(dict(key=name, sid=response['registry']['sid'], raw_unit=unit,
                           metadata={k: metadata.get(k) for k in ['unit', 'frequency', 'name', 'description', 'lifecycle_stage']}))
    quotes['eur_gbp'] = get_series(FX_SID, '2024-01-01', '2024-12-31', client=client)
    fx_metadata = get_metadata(FX_SID, client=client)
    ledger.append(dict(key='eur_gbp', sid=FX_SID, raw_unit='GBP per EUR; source identity and ECB convention',
                       metadata={k: fx_metadata.get(k) for k in ['unit', 'frequency', 'name', 'description']}))
    for name, values in quotes.items():
        values.rename('raw_value').rename_axis('date').to_csv(output/(name+'.csv'), float_format='%.15g')
    monthly, daily = monthly_features(quotes)
    monthly.to_csv(output/'monthly_prices.csv', float_format='%.15g')
    daily.to_csv(output/'matched_daily_prices.csv', float_format='%.15g')
    manifest = dict(retrieved_at=datetime.now(timezone.utc).isoformat(), start='2024-01-01', end='2024-12-31',
                    sources=ledger, query_policy='Fresh exact SID values and metadata; no cache or workbook fallback',
                    fx_convention='Same-date GBP per EUR; NBP pence/therm /100 /0.0293071 /FX',
                    aggregation='Common observed quote dates; arithmetic monthly means; no fill or delivery weights',
                    pool_proxy='TTF; identical DE/NL incentive', feature_scale_eur_mwh=PRICE_SCALE,
                    caveat='Empirical realised-price reconstruction, not revenue, netback or forecast validation',
                    references=['https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html',
                                'https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/829953/BEIS_OPRED_Offshore_ESOS_Phase_2_Guidance_September_2019.pdf'])
    (output/'price_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return monthly
