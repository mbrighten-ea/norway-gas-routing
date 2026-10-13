"""Charts and a retained report from completed optional price experiments."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def retain_price_report(root, run, output, *, revise_draft=False):
    root, run, output = Path(root).resolve(), Path(run).resolve(), Path(output).resolve()
    if not run.is_relative_to(root/'.scratch/runs') or output.parent != root/'archive':
        raise ValueError('Use a scratch experiment and new archive milestone')
    manifest = json.loads((run/'manifest.json').read_bytes())
    if manifest['years'] != [2024] or manifest['holdout_loaded'] or manifest['baseline_max_difference_bcm'] > 1e-9:
        raise ValueError('Only verified 2024 comparisons may be reported')
    monthly = pd.read_csv(run/'monthly_results.csv')
    annual = pd.read_csv(run/'annual_results.csv')
    annual['DE_NL_price_delta_bcm'] = annual.DE_price_delta_bcm+annual.NL_price_delta_bcm
    monthly['priced_pool_reallocation_bcm'] = (monthly.UK_price_delta_bcm.abs()+monthly.FR_price_delta_bcm.abs()+
        monthly.DE_NL_price_delta_bcm.abs()+monthly.BE_price_delta_bcm.abs()+monthly.DK_price_delta_bcm.abs()+monthly.PL_price_delta_bcm.abs())/2
    pool_shift = monthly.groupby(['capacity','shock','responsiveness_label']).priced_pool_reallocation_bcm.sum()
    annual['priced_pool_reallocation_bcm'] = [pool_shift.loc[r.capacity,r.shock,r.responsiveness_label] for r in annual.itertuples()]
    constraints = pd.read_csv(run/'asset_constraints.csv')
    prices = pd.read_csv(run/'prices/monthly_prices.csv')
    if revise_draft:
        # Explicit QA iteration only, with exactly the same completed producer.
        if json.loads((output/'manifest.json').read_bytes()) != manifest:
            raise ValueError('Cannot revise a report from another producer')
    else:
        output.mkdir()
    for name in ['monthly_results.csv', 'annual_results.csv', 'asset_constraints.csv', 'arc_flows.csv', 'manifest.json']:
        shutil.copyfile(run/name, output/name)
    shutil.copytree(run/'prices', output/'prices', dirs_exist_ok=revise_draft)
    observed = annual.loc[annual.shock.eq('observed')].sort_values(['capacity','responsiveness'])
    observed.to_csv(output/'results.csv', index=False, float_format='%.15g')
    annual.to_csv(output/'grouped_annual_results.csv', index=False, float_format='%.15g')
    monthly.to_csv(output/'grouped_monthly_results.csv', index=False, float_format='%.15g')
    shock_sensitivity = []
    interactions = []
    indexed = monthly.set_index(['capacity','month','shock','responsiveness_label'])
    markets = ['UK','FR','DE_NL','BE','DK','PL']
    for row in monthly.itertuples():
        if row.shock != 'observed':
            own = indexed.loc[row.capacity,row.month,'observed',row.responsiveness_label]
            shock_size = float(row.shock.rsplit('_',1)[1])
            for market in markets:
                shift = getattr(row,market)-own[market]
                shock_sensitivity.append(dict(capacity=row.capacity,month=row.month,shock=row.shock,
                    responsiveness_label=row.responsiveness_label,destination=market,shock_delta_bcm=shift,
                    finite_difference_bcm_per_eur_mwh=shift/shock_size,
                    qualification='20-EUR/MWh finite shock difference, not a calibrated marginal elasticity'))
        if row.capacity == 'kollsnes-156':
            low = indexed.loc['baseline',row.month,row.shock,row.responsiveness_label]
            zero_low = indexed.loc['baseline',row.month,row.shock,'zero']
            zero_high = indexed.loc['kollsnes-156',row.month,row.shock,'zero']
            for market in markets:
                total = getattr(row,market)-low[market]
                physical = zero_high[market]-zero_low[market]
                interactions.append(dict(month=row.month,shock=row.shock,responsiveness_label=row.responsiveness_label,
                    destination=market,capacity_only_delta_bcm=physical,price_capacity_interaction_bcm=total-physical,
                    total_capacity_delta_at_same_price_bcm=total))
    pd.DataFrame(shock_sensitivity).to_csv(output/'shock_sensitivity.csv',index=False,float_format='%.15g')
    pd.DataFrame(interactions).to_csv(output/'capacity_price_interaction.csv',index=False,float_format='%.15g')
    binding = constraints.groupby(['capacity','shock','responsiveness_label','asset']).binding.sum().rename('binding_months').reset_index()
    binding.to_csv(output/'binding_months.csv', index=False)
    charts = []
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})

    def save(fig, name):
        fig.tight_layout()
        for ext in ['png','svg']:
            path = output/(name+'.'+ext)
            fig.savefig(path, dpi=150, facecolor='white')
            if ext == 'svg':
                path.write_text('\n'.join(x.rstrip() for x in path.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8')
        plt.close(fig)
        charts.append(name)

    fig, ax = plt.subplots(figsize=(11,4))
    for market in ['UK','FR','DE_NL']:
        ax.plot(prices.iloc[:,0], prices[market], marker='o', label=market)
    ax.set(title='Fresh 2024 realised quote spreads — monthly common-date means', ylabel='EUR/MWh versus TTF')
    ax.tick_params(axis='x',rotation=45)
    ax.legend(ncol=3)
    save(fig,'price_spreads')

    fig, axes = plt.subplots(2,3, figsize=(15,9), sharex=True)
    for row, capacity in enumerate(['baseline','kollsnes-156']):
        for col, market in enumerate(['UK','FR','DE_NL']):
            for strength in ['low','medium','high']:
                part = monthly.loc[monthly.capacity.eq(capacity)&monthly.shock.eq('observed')&monthly.responsiveness_label.eq(strength)]
                plotted = part[market+'_price_delta_bcm'].where(part[market+'_price_delta_bcm'].abs() >= 1e-9, 0.)
                axes[row,col].plot(part.month, plotted,label=strength)
            axes[row,col].set(title=f'{capacity}: {market}',ylabel='Price-only shift (bcm/month)')
            axes[row,col].axhline(0,color='grey',linewidth=.6)
            axes[row,col].tick_params(axis='x',rotation=60)
    axes[0,0].legend(ncol=3)
    save(fig,'monthly_destination_shifts')

    fig, axes = plt.subplots(1,2, figsize=(12,5),sharey=True)
    for ax, capacity in zip(axes,['baseline','kollsnes-156']):
        part = observed.loc[observed.capacity.eq(capacity)]
        ax.plot(part.responsiveness,part.priced_pool_reallocation_bcm,marker='o')
        ax.set(title=capacity,xlabel='Uncalibrated responsiveness λ',ylabel='Monthly reallocation summed (bcm; DE/NL pooled)')
    save(fig,'responsiveness')

    fig, axes = plt.subplots(1,2, figsize=(15,6),sharey=True)
    for ax, capacity in zip(axes,['baseline','kollsnes-156']):
        part = annual.loc[annual.capacity.eq(capacity)&annual.responsiveness_label.eq('high')].set_index('shock')
        part[['UK_price_delta_bcm','FR_price_delta_bcm','DE_NL_price_delta_bcm']].plot.bar(ax=ax)
        ax.set(title=f'{capacity}: ±20 EUR/MWh feature shocks at λ=4',ylabel='Annual price-only destination shift (bcm)',xlabel='')
        ax.tick_params(axis='x',rotation=35)
        ax.legend(['UK','France','DE/NL pool'],ncol=3,fontsize=9)
    save(fig,'synthetic_shocks')

    fig, ax = plt.subplots(figsize=(12,5))
    interaction = pd.DataFrame(interactions)
    selected = interaction.loc[interaction.shock.eq('observed')&interaction.responsiveness_label.eq('medium')]
    selected.groupby('destination')[['capacity_only_delta_bcm','price_capacity_interaction_bcm']].sum().plot.bar(ax=ax)
    ax.set(title='143 → hypothetical 156: capacity effect and price interaction at λ=1',ylabel='Annual destination change (bcm)',xlabel='')
    ax.tick_params(axis='x',rotation=0)
    ax.legend(['Capacity alone','Additional price/capacity interaction'])
    save(fig,'capacity_price_interaction')

    caveat = ('Optional empirical preference experiment: Stage 2 minimises L1 deviation minus λ × '
              'spread/10 EUR/MWh × allocated bcm. This is not revenue or a netback. Strengths 0, 0.25, 1 and 4 '
              'are illustrative, not calibrated. TTF represents the whole DE/NL pool; BE/DK/PL have zero price '
              'coefficients but may move indirectly. Fresh realised quote-date means do not represent delivery '
              'volume weights or information available before the month. Kollsnes 156 remains hypothetical. '
              'Stage 1 maximum exports and the combined Stage 2 optimum are preserved. No 2025/2026 scoring '
              'or default model activation occurred.')
    caveat += (' Any positive weight can resolve old L1 ties, so a jump from zero is expected; '
               'response need not scale smoothly with λ. Within-DE/NL changes are not separately '
               'price-identified. Grouped reallocation removes that internal-pool contribution; '
               'seven-country shifts remain available in CSVs.')
    body = '<h1>Optional 2024 price response</h1><p>'+html.escape(caveat)+'</p>'
    body += observed[['capacity','responsiveness_label','exports_bcm','priced_pool_reallocation_bcm',
                      'UK_price_delta_bcm','FR_price_delta_bcm','DE_NL_price_delta_bcm']].to_html(index=False,float_format=lambda x:f'{x:.6f}')
    for chart in charts:
        body += f'<img src="{chart}.png" alt="{chart.replace("_"," ")}" style="width:100%;max-width:1200px">'
    links = ['results.csv','monthly_results.csv','annual_results.csv','grouped_monthly_results.csv','grouped_annual_results.csv','shock_sensitivity.csv','capacity_price_interaction.csv','asset_constraints.csv','binding_months.csv',
             'arc_flows.csv','manifest.json','prices/monthly_prices.csv','prices/price_manifest.json']
    body += '<h2>CSV tables and provenance</h2><ul>'+''.join(f'<li><a href="{n}">{n}</a></li>' for n in links)+'</ul>'
    (output/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>2024 price response</title><style>body{font:16px Arial;color:#17334a;max-width:1300px;margin:30px auto;padding:20px}td,th{padding:8px;border:1px solid #ccd6df}table{border-collapse:collapse}</style>'+body,encoding='utf-8')
    return output
