"""Reader-facing reports generated from saved tables, without data retrieval."""
from html import escape
import json
from pathlib import Path
import pandas as pd
from ..evaluation import check_table, validate_manifest

STYLE = '''body{font:16px/1.55 system-ui;margin:40px auto;max-width:1100px;padding:0 24px;color:#192c38}
h1,h2{line-height:1.2}table{border-collapse:collapse;font-size:14px;width:100%;margin:20px 0}
th,td{padding:8px 12px;border-bottom:1px solid #ccd6dd;text-align:left}th{background:#eef3f6}
img{max-width:100%;height:auto}a{color:#17659b}.scroll{overflow:auto}.note{background:#fff3da;padding:16px}
details{margin:20px 0}code{background:#edf2f5;padding:2px 5px}'''


def artifact_links(base):
    links = []
    for folder in ('details','provenance'):
        for path in sorted((base / folder).rglob('*')):
            if path.is_file():
                name = path.relative_to(base).as_posix()
                links.append(f'<li><a href="{escape(name, quote=True)}">{escape(name)}</a></li>')
    return '<details><summary>Technical tables and reproduction evidence</summary><ul>' + ''.join(links) + '</ul></details>'


def table(frame):
    return '<div class="scroll">' + frame.to_html(index=False, border=0, na_rep='Unavailable',
        float_format=lambda x: f'{x:.3f}', escape=True) + '</div>'


def render_report(base, assessment):
    base = Path(base)
    manifest = json.loads((base/'provenance/run_manifest.json').read_text())
    if 'evaluation' in manifest:
        validate_manifest(manifest)
    check_table(pd.read_csv(base/'results.csv'), 'plot')
    if assessment == 'reconstruction':
        results = pd.read_csv(base/'results.csv')
        title = 'Norwegian gas routing: historical reconstruction'
        content = '<p>Latest-revised 2024 inputs; this is a historical reconstruction, not an out-of-sample forecast.</p>'
        date = manifest.get('run_at_utc', 'See provenance')
        content += f'<p>Recorded execution: {escape(str(date))}. Solver status: {escape(manifest.get("status","unknown"))}.</p>'
        columns = ['total_exports_bcm','unrouted_supply_bcm','unclassified_supply_bcm']
        totals = pd.DataFrame({'Quantity':['Exports','Unrouted supply','Unclassified supply'],
            '2024 volume (bcm)':[results[name].sum(min_count=1) for name in columns]})
        content += '<h2>Supply and destination results</h2>' + table(totals)
        content += '<p class="note">A feasible optimal solve does not establish production readiness. Supply/target boundaries, domestic allocations and capacity bases remain unresolved. Unrouted gas is not proof of real curtailment.</p>'
        metrics = base/'details/metrics.csv'
        if metrics.exists():
            scores=pd.read_csv(metrics)
            selected=scores.loc[scores['case'].eq('refined_broader_boundary') & scores.destination.isin(['UK','FR','BE','NL','DE','DK','PL'])]
            content += '<h2>Destination accuracy against EA reference proxies</h2>' + table(selected[['destination','WAPE_pct','MAE_bcm_month','bias_bcm_month','n_months']] if 'n_months' in selected else selected[[c for c in ['destination','WAPE_pct','MAE_bcm_month','bias_bcm_month','months'] if c in selected]])
        for image, heading in [('monthly_destination_comparison.png','Monthly destination comparisons'),
                              ('before_after_wape.png','Original and refined reconstruction'),
                              ('network_flows.png','Representative-month solved network')]:
            if (base/'details'/image).exists():
                content += f'<h2>{heading}</h2><img alt="{heading}" src="details/{image}">'
        content += '<p>UK = United Kingdom; FR = France; BE = Belgium; NL = Netherlands; DE = Germany; DK = Danish net offtake; PL = Poland delivery. Nybro includes DK + PL transit: do not count Poland twice.</p>'
        content += '<p><a href="details/diagnosis.md">Full scope, scenario and capacity explanation</a></p>' if (base/'details/diagnosis.md').exists() else ''
    else:
        title='Norwegian gas: archived forecast evaluation'
        content='<p>Legacy forecasts retained at 31 December 2023 and 30 June 2024, compared with a historical seasonal baseline and latest revised EA workbook proxies.</p>'
        content+='<p class="note">This assessment retains the original first-solve reconstruction, not the refined current model. EA reference values are proxies; public release timing and physical/commercial definitions are unresolved.</p>'
        scores=pd.read_csv(base/'details/matched_forecast_metrics.csv')
        labels={'legacy_asof':'Legacy forecast','seasonal_asof':'Historical seasonal baseline'}
        view=scores[['origin','destination','method','wape_pct','mae_bcm_month','bias_bcm_month','n']].copy()
        view['method']=view.method.map(labels)
        content+='<h2>Fair comparison: shared available months</h2>'+table(view)
        for origin in ('20231231','20240630'):
            image=f'forecast_comparison_{origin}.png'
            if (base/'details'/image).exists():
                content+=f'<h2>Forecast origin {origin[:4]}-{origin[4:6]}-{origin[6:]}</h2><img src="details/{image}" alt="Monthly forecast comparison">'
        content+='<p>Blue: legacy forecast retained at the stated origin. Orange: seasonal baseline built from earlier same-calendar-month observations available at that origin. Black: latest revised EA reference. Seasonal July/August gaps mean unavailable, not zero. The baseline has ten scoreable months per origin. The new routing model is not a line in this forecast comparison.</p>'
        content+='<p>FR+BE combines France/Belgium; NL+DE combines Netherlands/Germany because separate country forecasts were unavailable. Baltic Pipe is Poland delivery; DK is Danish net allocation, excluding Poland transit. The Danish reference can be negative.</p>'
    content+='<h2>Keys, units and downloads</h2><p>bcm = billion cubic metres; bcm/month is monthly volume. WAPE = total absolute error divided by total absolute reference volume, as a percentage. MAE = mean absolute monthly error in bcm. Bias = signed prediction minus reference; positive means overprediction. Lower WAPE/MAE is better. n/months is score coverage. Share errors are percentage points and exclude incomplete or negative baskets.</p>'
    content+='<p>Blank numeric values mean unavailable, never assumed zero. Main table grain/fields: '+('one target month, seven destination volume columns and supply totals; solver_status records completion.' if assessment=='reconstruction' else 'method + origin + target_month + level + destination; prediction_bcm/actual_bcm are monthly volumes, error_bcm is prediction minus reference. Five-group and seven-destination rows overlap and must not be added together.')+'</p>'
    content+='<p><a href="results.csv">Download main results CSV</a> · <a href="../README.md">All assessments and retained milestones</a></p>'
    if 'evaluation' in manifest:
        content += '<h2>Chronological evaluation protocol</h2><p>Development through December 2024; validation January–December 2025 for candidate comparison only. Parameters are not fitted to validation outcomes. January–September 2026 is locked and has not been scored. Current results use revised inputs and unverified historical availability, so they remain historical reconstructions.</p>'
    content+=artifact_links(base)
    html=f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{escape(title)}</title><style>{STYLE}</style><h1>{escape(title)}</h1>{content}</html>'
    (base/'report.html').write_text(html,encoding='utf-8')


def forecast_charts(base):
    """Relabel saved predictions without recalculating forecasts or scores."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    base=Path(base)
    frame=pd.read_csv(base/'results.csv')
    check_table(frame, 'plot')
    groups=['UK','FR+BE','NL+DE','Baltic Pipe','DK']
    for origin,selection in frame.loc[frame.level.eq('five_groups') & frame.method.isin(['legacy_asof','seasonal_asof'])].groupby('origin'):
        fig,axes=plt.subplots(3,2,figsize=(12,10),layout='constrained')
        targets=pd.period_range(pd.Period(origin,'M')+1,periods=12,freq='M').astype(str)
        for ax,name in zip(axes.flat,groups):
            data=selection.loc[selection.destination.eq(name)]
            for method,label,color in [('legacy_asof',f'Legacy forecast - {origin}','#17669b'),
                                       ('seasonal_asof','Historical seasonal baseline','#dd7900')]:
                part=data.loc[data.method.eq(method)].set_index('target_month').reindex(targets)
                ax.plot(pd.to_datetime(part.index),part.prediction_bcm,label=label,color=color)
            actual=data.drop_duplicates('target_month').set_index('target_month').reindex(targets)
            ax.plot(pd.to_datetime(actual.index),actual.actual_bcm,color='black',label='EA reference - latest revised')
            ax.set_title(name);ax.set_ylabel('bcm/month');ax.tick_params(axis='x',rotation=30);ax.grid(alpha=.2)
        axes.flat[-1].axis('off');axes.flat[0].legend(fontsize=8)
        fig.suptitle(f'Forecasts retained at {origin}; seasonal July/August unavailable')
        fig.savefig(base/'details'/f'forecast_comparison_{origin.replace("-","")}.png',dpi=150)
        plt.close(fig)
