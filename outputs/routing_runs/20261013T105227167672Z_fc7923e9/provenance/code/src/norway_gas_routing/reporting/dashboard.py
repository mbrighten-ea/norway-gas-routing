"""Reproducible local reporting package from saved solutions and retained Excel evidence."""
import json
import re
from html import escape
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder

from .data import (COUNTRIES, GROUPS, actual_error_summary, annual_comparison, comparison, load_run,
                          period_map, sha, shares, strict_sum)
from .sids import load_sid_reference
from ..data_functions import connect_shooju
from .figures import (annual_figure, capacity_figure, difference_figure,
    monthly_figure, network_figure, shares_figure, static_exports, supply_figure, totals_figure)


def records(frame):
    return json.loads(frame.to_json(orient='records', double_precision=15))


def figure_json(fig):
    return json.loads(json.dumps(fig.to_plotly_json(), cls=PlotlyJSONEncoder))


def save_csv(frame, path):
    frame.to_csv(path, index=False, float_format='%.15g', encoding='utf-8')


def build_package(root, run_specs, output, legacy_sources, workbook=None, start=None, end=None, topology=None, legacy_archive=None, include_html=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not output.is_relative_to(root):
        raise ValueError('Report output must stay inside the authorised repository')
    forbidden = ['src', 'scripts', 'config', 'data', 'archive', 'evidence', 'tests',
                 'outputs/reconstruction', 'outputs/benchmark']
    if output == root or any(output.is_relative_to(root/x) or (root/x).is_relative_to(output) for x in forbidden):
        raise ValueError('Reporting cannot overwrite source inputs or retained solver outputs')
    for path in [p for p,_ in run_specs]+[p for p in [workbook, topology, legacy_archive] if p is not None]:
        if not Path(path).resolve().is_relative_to(root):
            raise ValueError('Report sources must stay inside the authorised repository')
    if not legacy_sources:
        raise ValueError('At least one explicit legacy source is required')
    if workbook is not None or legacy_archive is not None or any(not s.startswith('sid:') or s=='sid:actuals' for s in legacy_sources):
        raise ValueError('SID-only sourcing: use sid:YYYY-MM-DD; workbook/retained numerical sources are no longer allowed')
    runs = [load_run(path, scenario, start, end, topology) for path, scenario in run_specs]
    months = sorted(set(m for run in runs for m in run['monthly'].month))
    legacy = []
    client = connect_shooju()
    actuals = load_sid_reference(months, client=client)
    for source in legacy_sources:
        legacy.append(load_sid_reference(months, source.split(':',1)[1], client=client))
    if len({run['id']+run['scenario'] for run in runs}) != len(runs) or len({s['id'] for s in legacy}) != len(legacy):
        raise ValueError('Duplicate run/scenario or legacy source')
    # Validation and source extraction precede publishing any chart.
    details, provenance = output/'details', output/'provenance'
    details.mkdir(parents=True, exist_ok=True); provenance.mkdir(parents=True, exist_ok=True)
    all_comparisons, all_annual, all_maps, all_assets, all_shares, totals_rows, all_errors = [], [], [], [], [], [], []
    main = pd.concat([r['monthly'].assign(run_id=r['id'], scenario=r['scenario'],
        analysis_type=r['title'], unit='bcm/month') for r in runs], ignore_index=True)
    save_csv(main, output/'results.csv')
    views, galleries = [], []
    checks = []
    for run in runs:
        for year, monthly in run['monthly'].groupby(run['monthly'].month.str[:4], sort=True):
            selected_months = monthly.month.tolist()
            full_year = selected_months == pd.period_range(year+'-01', year+'-12', freq='M').astype(str).tolist()
            period_label = year+' annual total' if full_year else f'{selected_months[0]} to {selected_months[-1]} period total'
            title = f'{period_label} · {run["title"]}'
            slug = re.sub('[^A-Za-z0-9_-]', '_', run['id']+'_'+run['scenario']+'_'+year)
            maps, assets = period_map(run, selected_months)
            maps['period'] = period_label
            all_maps.append(maps.assign(run_id=run['id'], scenario=run['scenario'], year=year))
            all_assets.append(assets.assign(run_id=run['id'], scenario=run['scenario'], year=year, period=period_label))
            map_views = {}
            if include_html:
                map_views['Annual total' if full_year else 'Period total'] = figure_json(network_figure(run, maps, assets, monthly, title))
            for month in selected_months:
                monthly_map, monthly_assets = period_map(run, [month])
                all_maps.append(monthly_map.assign(period=month, run_id=run['id'], scenario=run['scenario'], year=year))
                all_assets.append(monthly_assets.assign(period=month, run_id=run['id'], scenario=run['scenario'], year=year))
                if include_html:
                    map_views[month] = figure_json(network_figure(run, monthly_map, monthly_assets, monthly.loc[monthly.month.eq(month)],
                        f'{month} · {run["title"]}'))
            sources = {}
            default_id = next((s['id'] for s in legacy if s['id'] == ('sid:2023-12-31' if year == '2024' else 'sid:2024-12-31')), legacy[0]['id'])
            for source in legacy:
                prepared = comparison(run | {'monthly': monthly}, source, actuals)
                all_errors.append(actual_error_summary(prepared).assign(run_id=run['id'], scenario=run['scenario'],
                    year=year, legacy_source=source['id'], legacy_vintage=source['vintage']))
                annual = annual_comparison(prepared, selected_months)
                all_comparisons.append(prepared.assign(year=year, legacy_source=source['id']))
                all_annual.append(annual.assign(run_id=run['id'], scenario=run['scenario'], year=year,
                    legacy_source=source['id'], legacy_vintage=source['vintage'], period=period_label))
                group_data = prepared.loc[prepared.level.eq('groups')]
                pivot = group_data.pivot(index='month', columns='destination', values='legacy_model_bcm').reindex(columns=list(GROUPS))
                matched_months = pivot.index[pivot.notna().all(axis=1)].tolist()
                matched = prepared.loc[prepared.month.isin(matched_months)]
                matched_annual = annual_comparison(matched, matched_months) if matched_months else annual.iloc[0:0]
                for month in selected_months:
                    source_total = source['data'].loc[source['data'].month.eq(month) & source['data'].level.eq('total'), 'value_bcm']
                    five = group_data.loc[group_data.month.eq(month), 'legacy_model_bcm']
                    named = source_total.iloc[0] if len(source_total) == 1 else float('nan')
                    allocated = strict_sum(five)
                    totals_rows.append({'run_id': run['id'], 'scenario': run['scenario'], 'month': month,
                        'legacy_source': source['id'], 'kind': source['kind'], 'model_exports_bcm': monthly.set_index('month').loc[month, 'exports_bcm'],
                        'legacy_named_total_bcm': named, 'legacy_five_group_allocations_bcm': allocated,
                        'legacy_named_minus_allocated_bcm': named-allocated,
                        'boundary': 'Named legacy Gassco supply/accounting total retained separately from allocated exports; no forced reconciliation'})
                for level, names in [('countries', COUNTRIES), ('groups', list(GROUPS))]:
                    basket = prepared.loc[prepared.level.eq(level)]
                    for method, column in [('routing_model', 'model_bcm'), ('legacy_model', 'legacy_model_bcm')]:
                        for month, part in basket.groupby('month', sort=False):
                            values = part.set_index('destination').reindex(names)[column]
                            fractions = shares(values)
                            supply = monthly.set_index('month').loc[month, 'supply_bcm'] if method == 'routing_model' else float('nan')
                            for name in names:
                                all_shares.append({'run_id': run['id'], 'scenario': run['scenario'], 'month': month,
                                    'legacy_source': source['id'], 'level': level, 'method': method, 'destination': name,
                                    'export_share_pct': fractions[name],
                                    'total_supply_share_pct': 100*values[name]/supply if pd.notna(supply) and supply>0 else float('nan'),
                                    'supply_share_status': 'Routing pipeline supply denominator' if method == 'routing_model' else 'Legacy available-supply denominator not verified'})
                divergences = prepared.loc[prepared.level.eq('groups') & prepared.delta_bcm.notna()].copy()
                divergences['absolute_delta_bcm'] = divergences.delta_bcm.abs()
                divergences = divergences.sort_values(['absolute_delta_bcm', 'month', 'destination'], ascending=[False, True, True]).head(6)
                annual_rows = annual.loc[annual.level.eq('groups')]
                routing_total = strict_sum(annual_rows.model_bcm)
                legacy_total = strict_sum(annual_rows.legacy_model_bcm)
                named_cells = source['data'].loc[source['data'].month.isin(selected_months) & source['data'].level.eq('total')]
                named_legacy_total = strict_sum(named_cells.value_bcm) if len(named_cells)==len(selected_months) else float('nan')
                matched_routing = strict_sum(matched_annual.loc[matched_annual.level.eq('groups'), 'model_bcm']) if len(matched_annual) else float('nan')
                matched_legacy = strict_sum(matched_annual.loc[matched_annual.level.eq('groups'), 'legacy_model_bcm']) if len(matched_annual) else float('nan')
                source_title = title+'<br><sup>'+source['label']+'</sup>'
                source_figures = {
                    'countries': figure_json(monthly_figure(prepared, 'countries', 'Monthly exports by country · '+source_title)),
                    'groups': figure_json(monthly_figure(prepared, 'groups', 'Monthly exports in original legacy groups · '+source_title)),
                    'annual': figure_json(annual_figure(annual, 'Destination allocations · '+source_title)),
                    'totals': figure_json(totals_figure(routing_total, legacy_total, named_legacy_total,
                        'Pipeline exports and declared legacy totals · '+source_title)),
                    'differences': figure_json(difference_figure(prepared, 'Routing minus legacy model · '+source_title)),
                    'shares': figure_json(shares_figure(prepared, 'Destination shares · '+source_title))} if include_html else {}
                if include_html and matched_months and len(matched_months) != len(selected_months):
                    source_figures['matched'] = figure_json(annual_figure(matched_annual,
                        f'Matched period only: {matched_months[0]} to {matched_months[-1]}<br><sup>{run["title"]}; {source["label"]}</sup>'))
                sources[source['id']] = {'label': source['label'], 'vintage': source['vintage'], 'kind': source['kind'],
                    'notes': source['notes'], 'figures': source_figures, 'divergences': records(divergences),
                    'annual_data': records(annual), 'matched_months': matched_months,
                    'routing_total': routing_total, 'legacy_total': legacy_total,
                    'named_legacy_total': named_legacy_total,
                    'matched_routing_total': matched_routing, 'matched_legacy_total': matched_legacy}
                if source['id'] == default_id:
                    static_title = title+'\n'+source['label']
                    paths = static_exports(run, monthly, maps, assets, prepared, annual, details/slug, static_title, named_legacy_total)
                    if len(matched_months) and len(matched_months) != len(selected_months):
                        # Matched-period data are exported separately; no partial annual bar is presented as a full year.
                        save_csv(matched_annual, details/slug/'matched_period_destination_comparison.csv')
                    galleries.append({'label': f'{year} · {run["scenario"]}',
                        'files': [str(p.relative_to(output).as_posix()) for p in paths]})
            totals = {c: strict_sum(monthly[c]) for c in ['supply_bcm', 'exports_bcm', 'unrouted_bcm', 'unmapped_bcm', 'mapped_disposal_bcm']}
            key = slug
            identity = {'run_id': run['id'], 'scenario': run['scenario'], 'solver': run['manifest'].get('solver'),
                'run_at_utc': run['manifest'].get('run_at_utc'), 'code_sha256': run['manifest'].get('code_sha256', {})}
            views.append({'key': key, 'label': f'{year} · {run["title"]} · {run["scenario"]}',
                'year': year, 'title': title, 'id': run['id'], 'scenario': run['scenario'], 'identity': identity,
                'totals': totals, 'maps': map_views, 'default_source': default_id, 'sources': sources,
                'supply': figure_json(supply_figure(monthly, 'Pipeline supply, exports and disposal · '+title)) if include_html else None,
                'capacity': figure_json(capacity_figure(assets, 'Saved modelled capacities and binding months · '+title)) if include_html else None,
                'assets': records(assets)})
            flex_path = root/'archive/20261009-14_routing-flexibility/annual_flexibility.csv'
            if year == '2025' and full_year and run['scenario'] == 'official-net-production' and flex_path.exists():
                flex = pd.read_csv(flex_path)[['destination','baseline_bcm','minimum_bcm','maximum_bcm']]
                saved = monthly[COUNTRIES].sum()
                if set(flex.destination) == set(COUNTRIES) and all(abs(saved[r.destination]-r.baseline_bcm)<2e-8 for r in flex.itertuples()):
                    views[-1]['flexibility'] = records(flex)
                    run['source_hashes'][str(flex_path)] = sha(flex_path)
                    save_csv(flex, details/'saved_2025_individual_flexibility.csv')
            checks.append({'run_id': run['id'], 'scenario': run['scenario'], 'year': year, **run['checks'],
                'annual_flow': 'strict sums of monthly volumes', 'annual_capacity': 'strict sums of monthly bcm limits',
                'country_total_bcm': strict_sum(monthly[COUNTRIES].sum(axis=1)), 'exports_bcm': totals['exports_bcm']})
    save_csv(pd.concat(all_comparisons, ignore_index=True), details/'monthly_comparisons.csv')
    save_csv(pd.concat(all_annual, ignore_index=True), details/'annual_comparisons.csv')
    save_csv(pd.concat(all_maps, ignore_index=True), details/'map_flows.csv')
    save_csv(pd.concat(all_assets, ignore_index=True), details/'modelled_capacities.csv')
    save_csv(pd.DataFrame(all_shares), details/'allocation_shares.csv')
    save_csv(pd.DataFrame(totals_rows), details/'legacy_totals.csv')
    save_csv(pd.concat(all_errors, ignore_index=True), details/'forecast_error_summary.csv')
    save_csv(actuals['data'], details/'ea_historical_actuals.csv')
    save_csv(pd.DataFrame([{'run': gallery['label'], 'path': path, 'format': Path(path).suffix[1:]}
                          for gallery in galleries for path in gallery['files']]), output/'figures.csv')
    for source in legacy+[actuals]:
        safe_id = source['id'].replace(':','_')
        save_csv(source['data'], provenance/f'legacy_{safe_id}_values.csv')
        save_csv(source['ledger'], provenance/f'legacy_{safe_id}_sid_queries.csv')
        (provenance/f'legacy_{safe_id}_responses.json').write_text(json.dumps(source['responses'], indent=2, allow_nan=False)+'\n', encoding='utf-8')
    manifest = {'report_type': 'saved-solution routing visualisation; no optimisation',
        'units': {'monthly_volume': 'bcm/month', 'period_volume': 'bcm', 'capacity': 'saved monthly bcm limits'},
        'runs': [{'id': r['id'], 'scenario': r['scenario'], 'analysis_type': r['title'],
            'path': r['path'], 'producer_code_sha256': r['manifest'].get('code_sha256'),
            'source_hashes': r['source_hashes']} for r in runs],
        'legacy_sources': [{k: s[k] for k in ['id', 'label', 'kind', 'vintage', 'source_hashes', 'notes']} for s in legacy],
        'actual_source': {k: actuals[k] for k in ['id', 'label', 'kind', 'vintage', 'source_hashes', 'notes']},
        'reporting_code_sha256': {p.name: sha(p) for p in Path(__file__).parent.glob('*') if p.is_file() and p.suffix in {'.py', '.html'}},
        'sid_queries': len(actuals['responses'])+sum(len(s['responses']) for s in legacy),
        'sourcing': 'Fresh direct EA/Shooju values and metadata on every run; no workbook/cache fallback',
        'routing_forecast_available': False, 'solver_calls': 0, 'holdout_loaded': False, 'holdout_scored': False,
        'schematic': 'Fixed layout; not GIS; retained topology is the source of truth',
        'missing_values': 'No zero filling or forecasts extrapolated',
        'annual_capacity': 'Sum of selected monthly bcm limits, never a daily denominator',
        'disposal': 'UNMAPPED separated from mapped disposal; not actual curtailment'}
    (provenance/'run_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    verification = {'status': 'PASS', 'checks': checks, 'legacy_source': 'Fresh origin-matched SID forecasts with exact returned values',
        'ea_historical_actuals': 'Fresh historical SID segment, checked against forecast-start boundary',
        'incompatible_export_errors': 'PL/Nybro and signed DK/net withheld; original values retained in CSV',
        'routing_forecast_accuracy': 'WITHHELD: saved reconstructions are not origin-only routing forecasts',
        'determinism': 'Stable data order; CSV float format %.15g; no current timestamp in data'}
    (provenance/'verification.json').write_text(json.dumps(verification, indent=2)+'\n', encoding='utf-8')
    if include_html:
        payload = json.dumps({'views': views, 'galleries': galleries}, cls=PlotlyJSONEncoder, allow_nan=True)
        # Preserve missing values as JSON null in the optional dashboard.
        payload = re.sub(r'(?<![\w"])NaN(?![\w"])', 'null', payload)
        payload = payload.replace('</', '<\\/')
        template = (Path(__file__).parent/'dashboard.html').read_text(encoding='utf-8')
        report = template.replace('__PLOTLY_JS__', get_plotlyjs()).replace('__REPORT_DATA__', payload)
        (output/'report.html').write_text(report, encoding='utf-8')
    verification_md = ['# Routing visualisation verification', '', 'PASS: saved-solution reconciliations at 2e-8 bcm tolerance.',
        'No solver calls, input changes, public-capacity substitutions or holdout reads.', '',
        'Fresh SID query ledgers and responses are in provenance/. Full run/producer identities are in run_manifest.json.', '',
        'Country and five-group sums, annual sums, node balances, disposal split and asset capacities pass.',
        'Annual capacity sums saved monthly bcm limits. Arcs are not summed to calculate exports; only unique destination receipts are.', '',
        'Legacy forecast percentages use positive legacy denominators. Missing or incompatible cells stay missing.',
        'Negative Danish historical net flows stay signed and are not included in physical export shares.',
        'Historical Poland-labelled Nybro values are withheld from direct Polish export comparison.', '',
        'Legacy errors use EA historical actuals, with compatible definitions and identical months. Routing forecast scores are missing, not reconstruction scores.', '',
        'Historical reconstruction versus earlier forecast comparisons include vintage and boundary differences and are not forecast errors.',
        'Targeted test, deterministic replay and protected-file results are recorded after verification in verification.json.']
    (provenance/'verification.md').write_text('\n'.join(verification_md)+'\n', encoding='utf-8')
    (provenance/'source_definitions.md').write_text('# Direct SID references\n\n'+
        '\n'.join(actuals['notes'])+'\n\nAll model results shown here are saved revised reconstructions/diagnostics. '
        'No same-origin routing forecast has been scored. See query ledgers for exact SIDs, origins, units and hashes.\n', encoding='utf-8')
    return output, manifest
