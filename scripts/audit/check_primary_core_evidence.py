"""Targeted retained-SID comparisons; diagnostic scaling never changes inputs."""

import html
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from norway_gas_routing.evaluation import read_parquet, check_dates


def main():
    audit = pd.read_csv(ROOT / 'evidence/inputs/data_series_audit.csv').set_index('sid')
    def values(sid):
        return read_parquet(ROOT / audit.loc[sid, 'raw_file']).value

    text = (ROOT / 'data/raw/series_audit/snohvit_sodir_primary_20261008.html').read_text(encoding='utf-8')
    official = {}
    # This one retained field page has separate net saleable and gross well tables.
    for caption, name in [('Production , saleable', 'nod_net_saleable_bcm'),
                          ('Production , sum wellbores', 'nod_gross_well_bcm')]:
        start = text.index('<caption>' + caption + '</caption>')
        block = text[start:text.index('</table>', start)]
        rows = {}
        year = None
        for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', block, re.S):
            cells = [html.unescape(re.sub('<[^>]+>', ' ', v)).strip()
                     for v in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.S)]
            if not cells:
                continue
            if re.fullmatch(r'\d{4}', cells[0]):
                year = int(cells[0])
            elif year and re.fullmatch(r'\d{1,2}', cells[0]):
                month = int(cells[0])
                assert 1 <= month <= 12
                rows[pd.Timestamp(year, month, 1)] = float(cells[2])
        official[name] = pd.Series(rows, name=name).sort_index()

    prefix = 'teams\\natural_gas\\EUR\\'
    field = values(prefix + 'NO_production_Snohvit_field')
    comparison = pd.concat(list(official.values()), axis=1)
    comparison['sid_reported_bcm_value'] = field
    comparison['sid_if_monthly_average_mcm_d_bcm'] = field * field.index.days_in_month / 1000
    comparison['sid_minus_nod_net_bcm'] = comparison.sid_if_monthly_average_mcm_d_bcm - comparison.nod_net_saleable_bcm
    comparison['sid_minus_nod_gross_bcm'] = comparison.sid_if_monthly_average_mcm_d_bcm - comparison.nod_gross_well_bcm
    comparison['sid_declared_forecast_period'] = comparison.index >= pd.Timestamp('2025-10-01')
    comparison.to_csv(ROOT / 'evidence/inputs/core_snohvit_primary_comparison.csv', index_label='month')
    negatives = comparison.loc[comparison.sid_reported_bcm_value.lt(0)].copy()
    negatives.to_csv(ROOT / 'evidence/inputs/core_snohvit_negative_primary_comparison.csv', index_label='month')

    def summary(series):
        s = series.dropna()
        return {'n': len(s), 'first': str(s.index.min()), 'last': str(s.index.max()),
                'mean': float(s.mean()), 'max_abs': float(s.abs().max()),
                'within_0_000001_bcm': int(s.abs().le(0.000001).sum()),
                'within_0_0000051_bcm': int(s.abs().le(0.0000051).sum())}

    historical = comparison.loc[~comparison.sid_declared_forecast_period]
    production = pd.read_csv(ROOT / 'evidence/inputs/core_production_comparison.csv', index_col='month', parse_dates=True)
    production = production.loc[:'2025-12']
    check_dates(production.index)
    total = values(prefix + 'NO_production')
    components = sum(values(prefix + s) for s in ['NO_production_Troll_field', 'NO_production_Oseberg_field', 'NO_production_non_flexible_fields'])
    result = {
        'policy': 'Diagnostic comparisons only. No configuration, input units or model transformations changed.',
        'primary_source': 'https://factpages.sodir.no/en/field/PageView/All/2053062',
        'snohvit_historical_net_residual': summary(historical.sid_minus_nod_net_bcm),
        'snohvit_historical_gross_residual': summary(historical.sid_minus_nod_gross_bcm),
        'negative_observations': len(negatives),
        'negative_observations_with_official_negative_net': int(negatives.nod_net_saleable_bcm.lt(0).sum()),
        'negative_net_matches_within_0_000001_bcm': int(negatives.sid_minus_nod_net_bcm.abs().le(0.000001).sum()),
        'negative_net_matches_within_0_0000051_bcm': int(negatives.sid_minus_nod_net_bcm.abs().le(0.0000051).sum()),
        'total_component_identity': summary(total - components),
        'exclusion_residual_2012_2021': summary(production.loc['2012':'2021', 'hypothesis_residual_bcm']),
        'exclusion_residual_2022_2025': summary(production.loc['2022':'2025', 'hypothesis_residual_bcm']),
    }

    days = read_parquet(ROOT / 'evidence/inputs/core_gassco_daily_samples.parquet', date_column='calendar_date')
    selected = days.loc[days.calendar_date.isin(pd.to_datetime(['2015-11-22', '2020-11-25', '2020-12-02', '2024-02-21']))].copy()
    selected.to_csv(ROOT / 'evidence/inputs/core_gassco_representative_dates.csv', index=False)
    # Route sample means are not gas-day totals or authorised monthly inputs.
    routes = ['Zeebrugge', 'Dunkerque', 'Emden', 'Dornum', 'Easington', 'Fields_Delivering_into_SEGAL']
    comparisons = []
    for date in selected.calendar_date.unique():
        names = routes + (['St_Fergus'] if date < pd.Timestamp('2020-12-01') else ['StFergus'])
        if date >= pd.Timestamp('2022-09-01'):
            names += ['Nybro']
        subset = selected.loc[selected.calendar_date.eq(date) & selected.sid.isin(['gassco\\' + n for n in names])]
        comparisons.append({'calendar_date': str(pd.Timestamp(date).date()), 'routes_present': len(subset),
                            'sum_of_route_sample_means_unverified': float(subset['mean'].sum()),
                            'min_samples_per_route': int(subset['count'].min()), 'max_samples_per_route': int(subset['count'].max())})
    result['gassco_representative_route_sums'] = comparisons
    result['gassco_external_scale_only'] = {'source': 'https://gassco.eu/en/about-us/who-we-are/our-history/',
        '2015_11_22_published_daily_production_million_Sm3': 365.3,
        '2024_published_pipeline_delivery_bcm': 117.6,
        '2024_annual_delivery_calendar_day_average_million_Sm3': 117.6 * 1000 / 366,
        'caution': 'Production and exit-route samples differ in scope and timing. These figures test magnitude only, not payload identity or gas-day alignment.'}

    ept = values(r'ENTSOG\transport_point\NL-TSO-0001\Emden (EPT1) (GTS)\entry\Physical Flow')
    diagnostic = ept.loc[pd.to_datetime(['2020-11-25', '2020-12-02', '2024-02-21'])].rename('reported_kWh_d').to_frame()
    diagnostic['if_0_095_m3_per_kWh_mcm_d'] = diagnostic.reported_kWh_d * 0.095 / 1e6
    emden = days.loc[days.sid.eq(r'gassco\Emden')].set_index('calendar_date')['mean']
    diagnostic['gassco_Emden_calendar_sample_mean_unverified'] = emden
    diagnostic.to_csv(ROOT / 'evidence/inputs/core_ept1_0095_diagnostic.csv', index_label='calendar_date')
    result['ept1_policy'] = '0.095 is diagnostic only, implying fixed gross calorific value 10.526315789 kWh/m3. Emden aggregate and EPT1 Dutch observation are not identical scopes.'
    (ROOT / 'evidence/inputs/core_primary_checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    print(comparison.loc[pd.to_datetime(['2019-02-01', '2021-01-01', '2025-01-01', '2025-05-01', '2025-07-01'])].to_string())
    print(diagnostic.to_string())


if __name__ == '__main__':
    main()
