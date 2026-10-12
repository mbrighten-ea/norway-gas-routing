"""Targeted, read-only provider checks; no model/configuration changes."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from helper_functions_ea import ShoojuTools, check_env

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from norway_gas_routing.evaluation import read_parquet, check_dates, ROUTINE_END
RAW = ROOT / 'data/raw/series_audit/destination_readiness'
DIAG = ROOT / 'evidence/inputs'


def retrieve():
    check_env()
    sj = ShoojuTools(silence_alerts=True)
    registry = pd.read_csv(ROOT / 'config/data_series.csv', keep_default_na=False).set_index('key')
    candidates = {key: (registry.loc[key, 'sid'], '2015-01-01') for key in
                  ['nbp_day_ahead', 'ttf_day_ahead', 'the_day_ahead', 'peg_day_ahead']}
    candidates.update({
        'eur_gbp': (r'ECB_exchange_rates\euro_to_gbp', '2014-12-20'),
        'pl_faxe_physical': (r'ENTSOG\transport_point\PL-TSO-0002\Faxe\entry\Physical Flow', '2022-10-01'),
        'dk_faxe_physical': (r'ENTSOG\transport_point\DK-TSO-0001\Faxe\exit\Physical Flow', '2022-10-01'),
    })
    RAW.mkdir(exist_ok=True)
    for key, (sid, start) in candidates.items():
        path = RAW / f'{key}.parquet'
        if path.exists():
            continue
        settings = {'sid': sid, 'query': f'sid="{sid}"', 'date_start': start,
                    'date_finish': ROUTINE_END, 'max_points': -1,
                    'retrieved_at': pd.Timestamp.now(tz='UTC').isoformat()}
        try:
            settings['metadata'] = sj.get_fields_from_sid(settings['query'], fields=['*'])
            s = sj.get_points_from_sid_into_series(settings['query'], start, ROUTINE_END, -1)
            check_dates(s.index, 'read')
            s.rename('value').to_frame().to_parquet(path)
            settings['retrieval_ok'] = True
            print(key, len(s), s.index.min(), s.index.max(), flush=True)
        except Exception as error:
            settings.update(retrieval_ok=False, error_type=type(error).__name__)
            print(key, 'FAILED', type(error).__name__, flush=True)
        (RAW / f'{key}.json').write_text(json.dumps(settings, default=str, indent=2) + '\n', encoding='utf-8')
    vintage_path = RAW / 'historical_asof_checks.json'
    records = json.loads(vintage_path.read_text()) if vintage_path.exists() else []
    for key in ['pl_faxe_physical', 'ttf_day_ahead']:
        sid = candidates[key][0]
        for cutoff in ['2024-07-01T23:59:59', '2025-07-01T23:59:59']:
            path = RAW / f'{key}_asof_{cutoff[:10]}.parquet'
            if path.exists():
                continue
            query = f'sid="{sid}"@asof:{cutoff}'
            record = {'sid': sid, 'query': query, 'cutoff': cutoff, 'date_start': '2024-06-01',
                      'date_finish': '2024-06-30', 'max_points': 31,
                      'retrieved_at': pd.Timestamp.now(tz='UTC').isoformat()}
            s = sj.get_points_from_sid_into_series(query, '2024-06-01', '2024-06-30', 31)
            s.to_frame('value').to_parquet(path)
            record.update(n=len(s), sum=float(s.sum()),
                          metadata=sj.get_fields_from_sid(query, ['unit', 'source', 'source_obj']))
            records.append(record)
    if not vintage_path.exists() or len(records) != len(json.loads(vintage_path.read_text())):
        vintage_path.write_text(json.dumps(records, indent=2, default=str) + '\n', encoding='utf-8')


def analyse():
    """Descriptive diagnostics only: no regression on unresolved flow targets."""
    def values(key):
        return read_parquet(RAW / f'{key}.parquet').value

    price_checks = {}
    for key in ['nbp_day_ahead', 'ttf_day_ahead', 'the_day_ahead', 'peg_day_ahead', 'eur_gbp']:
        s = values(key)
        counts = s.resample('MS').count()
        price_checks[key] = {
            'first': str(s.index.min()), 'last': str(s.index.max()), 'n': len(s),
            'nulls': int(s.isna().sum()), 'nonfinite': int((~np.isfinite(s)).sum()),
            'duplicate_dates': int(s.index.duplicated().sum()),
            'negative': int(s.lt(0).sum()), 'zero': int(s.eq(0).sum()),
            'largest_gap_days': int(s.index.to_series().diff().max().days),
            'missing_months': [str(d.date()) for d in counts[counts.eq(0)].index],
            'months_with_under_15_quotes': {str(d.date()): int(n) for d, n in counts[counts.lt(15)].items()},
        }
        assert s.index.is_unique and np.isfinite(s).all()
    prices = pd.DataFrame({hub: values(f'{hub}_day_ahead') for hub in ['nbp', 'ttf', 'the', 'peg']})
    prices['eur_gbp'] = values('eur_gbp')
    # Same-date FX only: no forward/back-fill and no future FX observations.
    prices['nbp_eur_mwh'] = prices.nbp / 100 / .0293071 / prices.eur_gbp
    spreads, spread_summary = [], {}
    for name, col, first in [('NBP-TTF', 'nbp_eur_mwh', '2015-01-01'),
                             ('THE-TTF', 'the', '2021-10-01'),
                             ('PEG-TTF', 'peg', '2019-11-01')]:
        pair = prices.loc[first:, [col, 'ttf']].dropna()
        delta = pair[col] - pair.ttf
        mean, count = delta.resample('MS').mean(), delta.resample('MS').count()
        for month in mean.index:
            spreads.append({'month': str(month.date()), 'spread': name,
                            'published_quote_mean_eur_mwh': mean.loc[month],
                            'matched_dates': int(count.loc[month])})
        spread_summary[name] = {'months': int(mean.notna().sum()), 'matched_dates': len(pair),
                                'first': str(pair.index.min()), 'last': str(pair.index.max()),
                                'min_month_quotes': int(count.min()),
                                'mean_eur_mwh': float(mean.mean()), 'std_eur_mwh': float(mean.std())}
    pd.DataFrame(spreads).to_csv(DIAG / 'historical_price_monthly_spreads.csv', index=False)

    audit = pd.read_csv(DIAG / 'data_series_audit.csv', keep_default_na=False)
    flows, flow_checks, benchmark_stats = {}, {}, {}
    for country in ['UK', 'DE', 'NL', 'BE', 'FR', 'DK', 'PL', 'total']:
        sid = 'teams\\natural_gas\\EUR\\NO\\gassco_' + country
        row = audit.loc[audit.sid.str.lower().eq(sid.lower())].iloc[0]
        s = read_parquet(ROOT / row.raw_file).value
        meta = json.loads((ROOT / row.metadata_file).read_text())['metadata']
        flows[country] = s
        expected = pd.date_range(s.index.min(), s.index.max(), freq='MS')
        flow_checks[country] = {'sid': sid, 'unit': meta.get('unit'), 'first': str(s.index.min()),
            'last': str(s.index.max()), 'n': len(s), 'missing_months': len(expected.difference(s.index)),
            'explicit_nulls': int(s.isna().sum()), 'duplicate_dates': int(s.index.duplicated().sum()),
            'negative_months': int(s.lt(0).sum()), 'forecast_start': meta.get('forecast_start_date'),
            'lifecycle': meta.get('lifecycle_stage'), 'source_file': meta.get('source_file'),
            'role': 'Retained EA workbook QA benchmark; monthly physical provenance not established'}
        assert s.index.is_unique and len(expected.difference(s.index)) == 0
        if country in ['UK', 'DE', 'NL', 'BE', 'FR']:
            sample = s.loc['2015-01':'2025-12']
            rate = sample / sample.index.days_in_month
            benchmark_stats[country] = {'n': len(rate), 'sample': '2015-01..2025-12',
                'mean_bcm_per_day': float(rate.mean()), 'cv_monthly_daily_rate': float(rate.std() / rate.mean()),
                'annual_2023_bcm': float(s.loc['2023'].sum()), 'annual_2024_bcm': float(s.loc['2024'].sum()),
                'interpretation': 'Descriptive benchmark variability only; no physical/commercial classification'}
    f = pd.DataFrame(flows).loc['2015-01':'2025-12']
    res5 = (f[['UK', 'DE', 'NL', 'BE', 'FR']].sum(axis=1, min_count=5) - f.total).loc[:'2022-09']
    res7 = (f[['UK', 'DE', 'NL', 'BE', 'FR', 'DK', 'PL']].sum(axis=1, min_count=7) - f.total).dropna()
    shares = {'usable_total_export_shares': False, 'renormalised': False,
        'five_market_pre_baltic_n': int(res5.notna().sum()),
        'five_market_pre_baltic_mean_residual_bcm': float(res5.mean()),
        'seven_market_n': len(res7), 'seven_market_mean_residual_bcm': float(res7.mean()),
        'seven_market_max_abs_residual_bcm': float(res7.abs().max()),
        'reason': 'Different scopes; omitted/direct UK routes, Danish transit, six negative DK months and total forecast-boundary conflict. No sum-to-one shares or physical denominator approved.'}

    pl, dk = values('pl_faxe_physical'), values('dk_faxe_physical')
    assert pl.index.is_unique and pl.notna().all() and pl.ge(0).all()
    assert len(pd.date_range(pl.index.min(), pl.index.max()).difference(pl.index)) == 0
    monthly = pl.resample('MS').agg(['mean', 'sum', 'count'])
    monthly.columns = ['reported_mean_kwh_d', 'sum_reported_daily_kwh', 'reported_days']
    monthly['expected_days'] = monthly.index.days_in_month
    monthly['complete'] = monthly.reported_days.eq(monthly.expected_days)
    monthly['reported_mean_gwh_d'] = monthly.reported_mean_kwh_d / 1e6
    monthly.to_csv(DIAG / 'poland_faxe_monthly_diagnostics.csv', index_label='month')
    stable_window = monthly.loc['2023-01':'2025-12', 'reported_mean_gwh_d']
    annual_rates = stable_window.groupby(stable_window.index.year).agg(['mean', 'std', 'min', 'max'])
    both = pd.DataFrame({'PL': pl, 'DK': dk}).dropna().loc['2023-01':'2025-12']
    monthly_pair = both.resample('MS').sum() / 1e9
    vintage_a, vintage_b = values('pl_faxe_physical_asof_2024-07-01'), values('pl_faxe_physical_asof_2025-07-01')
    poland = {'sid': flow_checks['PL']['sid'], 'physical_sid': r'ENTSOG\transport_point\PL-TSO-0002\Faxe\entry\Physical Flow',
        'n_days': len(pl), 'complete_months': int(monthly.complete.sum()), 'zero_days': int(pl.eq(0).sum()),
        'scope': 'Polish-side Baltic Pipe physical energy flow; not proof of exclusively Norwegian origin or commercial allocation',
        'monthly_rate_cv_2023_2025': float(stable_window.std() / stable_window.mean()),
        'annual_monthly_rate_stats_gwh_d': annual_rates.to_dict(orient='index'),
        'publisher_comparison': {'shared_days_after_ramp': len(both),
            'maximum_monthly_reported_energy_difference_twh': float((monthly_pair.PL - monthly_pair.DK).abs().max()),
            'maximum_monthly_relative_difference': float(((monthly_pair.PL - monthly_pair.DK).abs() / monthly_pair.PL).max()),
            'treatment': 'Separate publishers; not summed, averaged or stitched; provisional status and discrepancies remain'},
        'asof_revision': {'window': '2024-06', 'cutoffs': ['2024-07-01T23:59:59', '2025-07-01T23:59:59'],
            'changed_days': int(vintage_a.ne(vintage_b).sum()), 'max_abs_revision_kwh_d': float((vintage_b - vintage_a).abs().max()),
            'sum_revision_kwh': float((vintage_b - vintage_a).sum())}}

    matrix = []
    blockers = {
        'UK': 'St Fergus handover and physical/nominations break unresolved; Gassco benchmark omits/has different scope from all UK deliveries.',
        'DE': 'Emden+Dornum minus EPT1 requires aligned physical indicators, gas days and matched GCV; swaps/allocation are not inferred.',
        'NL': 'EPT1 physical kWh/d exists; gas-day and matched-GCV conversion unresolved; landing point is not commercial delivery.',
        'BE': 'Zeebrugge physical/nominations publication break; EA monthly workbook is a QA target with unresolved provenance.',
        'FR': 'Dunkerque physical/nominations break plus sparse PEG quote dates; EA monthly provenance unresolved.',
        'DK': 'Nybro is an import/transit corridor, not Danish final receipt; EA DK benchmark has six negative months; Baltic Pipe must not be double-counted.',
        'PL': 'Faxe provisional physical energy is usable descriptively; Norwegian origin, publisher discrepancies, gas-day/GCV volume conversion and shares unresolved.',
    }
    price_windows = {'UK': 'NBP-TTF: 2015-01..2025-12; see computed overlap count',
        'DE': 'THE-TTF: 2021-10..2025-12; pre-2021 NCG-era lineage not spliced',
        'NL': 'TTF: 2015-01..2025-12; reference hub', 'BE': 'Not needed for requested stability test; ZTP not retrieved',
        'FR': 'PEG-TTF: 2019-11..2025-12, sparse dates; see computed overlap count',
        'DK': 'Not required', 'PL': 'Not required'}
    for country in ['UK', 'DE', 'NL', 'BE', 'FR', 'DK', 'PL']:
        matrix.append({'destination': country, 'best_retained_monthly_sid': flow_checks[country]['sid'],
            'monthly_benchmark_period': flow_checks[country]['first'][:7] + '..2025-12',
            'monthly_unit': 'bcm; EA workbook QA benchmark',
            'missing_months': flow_checks[country]['missing_months'],
            'negative_months': flow_checks[country]['negative_months'],
            'independent_physical_period': '2022-10..2025-12; kWh/d at Faxe, see computed coverage' if country == 'PL' else 'Not yet validated for monthly regression',
            'price_overlap': price_windows[country], 'total_export_shares_ready': False,
            'readiness': 'Route-energy stability only' if country == 'PL' else 'QA descriptions only; flow-price regression blocked',
            'blocker': blockers[country]})
    pd.DataFrame(matrix).to_csv(DIAG / 'destination_readiness.csv', index=False)
    result = {'recorded_at': pd.Timestamp.now(tz='UTC').isoformat(),
        'scope': 'Read-only EA service/public evidence; latest-revised exploratory summaries, not fitted routing parameters',
        'price_checks': price_checks, 'spread_summary': spread_summary,
        'price_aggregation': 'Same-date available quotes/FX; arithmetic monthly mean of matched published dates. No price/FX filling, no weekend delivery weights; PEG sparse. THE restricted to post-merger. Retrospective monthly averages are not predictors available before that month.',
        'nbp_conversion': 'EUR/MWh = (pence_per_therm / 100) / 0.0293071 / GBP_per_EUR; same-date ECB observations only; not implemented in model inputs.',
        'flow_checks': flow_checks, 'benchmark_descriptive_stats': benchmark_stats,
        'public_2024_scope_crosscheck': {'gassco_rounded_bcm': {'UK': 30, 'BE': 16, 'FR': 16, 'total': 117.6},
            'retained_benchmark_bcm': {c: float(flows[c].loc['2024'].sum()) for c in ['UK', 'BE', 'FR', 'total']},
            'interpretation': 'BE/FR broadly agree at annual rounding precision; UK benchmark is about 2.24 bcm below rounded published UK deliveries. Annual agreement does not resolve monthly provenance. Gassco groups Germany/Denmark because of exchanged volumes; commercial destinations cannot be read off landing points.'},
        'share_reconciliation': shares, 'poland_physical_descriptive': poland,
        'controls': {'seasonality': 'Calendar month, days in month and trends available without retrieval',
            'production': 'Retained Norway total/Troll/Oseberg/non-flexible monthly history; current revision and definition risks, source accounting and LNG exclusion unresolved',
            'maintenance': 'Retained per-asset daily/monthly signed maintenance 2021-01..2030-12; asof supported, no baseline/asset scope inferred; avoid double-counting production outages',
            'breaks': ['Gassco nominations switch 2020-12-01', 'THE merger 2021-10-01', 'Baltic Pipe starts 2022-10-01 and full capacity 2022-11-30', 'PEG quote sparsity; capacity changes and effective dates unresolved']},
        'vintage': 'Date-based @asof verified previously for production/EA forecasts and now for Faxe/TTF. Faxe revisions recovered; TTF sample identical across cutoffs. Unit conversion uses contemporary FX observations but this report uses latest retrieved datasets. Public release time, deep retention and all-series vintage completeness remain unverified.',
        'regressions_run': False, 'reason_no_regressions': 'No requested destination yet has an independently resolved monthly Norwegian flow/share target paired with sufficiently validated prices.',
        'conclusion': 'Belgium QA benchmark is comparatively stable, but France is also relatively stable. Denmark/Poland baseload and UK/DE/NL/FR price responsiveness remain hypotheses; route variability is not commercial flexibility.',
        'sources': {
            'gassco_market_scope_2024': 'https://gassco.eu/en/record-delivery-of-natural-gas-through-the-gas-transport-system-to-europe-in-2024/',
            'baltic_pipe_start_and_ramp': 'https://www.gaz-system.pl/en/for-media/press-releases/2022/november/31-11-2022-baltic-pipe-has-reached-its-maximum-capacity.html',
            'danish_transit': 'https://en.energinet.dk/media/xlmiu5pq/report-on-security-of-gas-supply-2023.pdf',
            'the_merger': 'https://www.eex.com/fileadmin/EEX/Downloads/Customer_Information_older_than_2024/2021/20210917_EEX_Gas_Customer_Information_Launch_Information_related_to_the_German_Gas_Markets_Merger_on_1_October_2021.pdf',
            'nbp_therm': 'https://www.ice.com/products/910/UK-Natural-Gas',
            'ecb_quote_direction': 'https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.sl.html',
            'entsog_indicators': 'https://transparency.entsog.eu/pdf/TRA158_ENTSOG%20TP%20Data%20Publication%20Format_v3%2017052016.pdf'}}
    (DIAG / 'destination_readiness.json').write_text(json.dumps(result, indent=2, default=str) + '\n', encoding='utf-8')
    print('Produced seven-destination readiness matrix; no regressions or model changes.')
    print('Spread samples:', json.dumps(spread_summary))


if __name__ == '__main__':
    retrieve()
    analyse()
