"""Fresh monthly EA archive horizons and fixed-window walk-forward references."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..data_functions import connect_shooju
from ..evaluation import check_dates
from .data import GROUPS, NAMES, safe_percent
from .sids import load_sid_reference


def horizon_rows(source, origin):
    data = source['data'].loc[source['data'].level.eq('groups')].copy()
    data['origin'] = origin
    origin_month = pd.Period(origin,'M')
    data['lead_months'] = [pd.Period(m,'M').ordinal-origin_month.ordinal for m in data.month]
    if not data.lead_months.ge(1).all():
        raise ValueError('Walk-forward targets must follow the origin')
    return data.rename(columns={'month':'target_month','value_bcm':'prediction_bcm'})[
        ['origin','target_month','destination','lead_months','prediction_bcm','status']]


def add_updates(frame):
    """Compare overlapping targets across consecutive snapshots without filling."""
    result = frame.sort_values(['destination','target_month','origin']).copy()
    grouped = result.groupby(['destination','target_month'],sort=False)
    result['previous_origin'] = grouped.origin.shift()
    result['previous_prediction_bcm'] = grouped.prediction_bcm.shift()
    result['forecast_update_bcm'] = result.prediction_bcm-result.previous_prediction_bcm
    return result.sort_values(['origin','destination','lead_months']).reset_index(drop=True)


def walk_forward_rows(frame, actuals):
    one = frame.loc[frame.lead_months.eq(1)].copy()
    references = actuals['data'].loc[actuals['data'].level.eq('groups')].rename(
        columns={'month':'target_month','value_bcm':'ea_actual_bcm','compatible':'definition_compatible',
                 'status':'actual_status'})
    one = one.merge(references[['target_month','destination','ea_actual_bcm','definition_compatible','actual_status']],
        on=['target_month','destination'],how='left',validate='one_to_one')
    one['legacy_error_bcm'] = (one.prediction_bcm-one.ea_actual_bcm).where(one.definition_compatible.eq(True))
    one['legacy_error_pct'] = [safe_percent(e,a) for e,a in zip(one.legacy_error_bcm,one.ea_actual_bcm)]
    one['routing_forecast_bcm'] = np.nan
    one['routing_error_bcm'] = np.nan
    one['routing_status'] = 'Missing origin-matched routing solution; no revised reconstruction substitution'
    one['unit'] = 'bcm/month'
    return one


def inspect_horizons(root, output, start='2025-01', end='2025-12', *, client=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not (output.is_relative_to(root/'outputs') or output.is_relative_to(root/'.scratch')):
        raise ValueError('Horizon output must stay in repository outputs/ or .scratch/')
    if any(output.is_relative_to(root/p) for p in ['outputs/reconstruction','outputs/benchmark']):
        raise ValueError('Cannot overwrite historical assessments')
    months = pd.period_range(start,end,freq='M')
    check_dates(months,'score')
    if months.empty:
        raise ValueError('Nonempty validation months required')
    origins = [(m-1).end_time.normalize().strftime('%Y-%m-%d') for m in months]
    check_dates(origins,'read')
    client = connect_shooju() if client is None else client
    output.mkdir(parents=True,exist_ok=True)
    provenance = output/'provenance';provenance.mkdir(exist_ok=True)
    frames, coverage = [], []
    for index, origin in enumerate(origins):
        selected = [str(m) for m in months[index:]]
        source = load_sid_reference(selected,origin,client=client)
        data = horizon_rows(source,origin)
        frames.append(data)
        for destination, part in data.groupby('destination',sort=False):
            good = part.loc[part.prediction_bcm.notna()]
            coverage.append({'origin':origin,'destination':destination,'queried_target_months':len(part),
                'finite_forecast_months':len(good),'furthest_available_lead_months':good.lead_months.max() if len(good) else np.nan,
                'finite_values_beyond_one_month':int(good.lead_months.gt(1).sum()),
                'forecast_start':source['ledger'].loc[source['ledger'].destination.eq(destination),'forecast_start'].iloc[0],
                'qualification':'Numeric archived future values; intended published horizon and release timing not independently verified'})
        (provenance/f'forecast_{origin}.json').write_text(json.dumps(source['responses'],indent=2,allow_nan=False)+'\n',encoding='utf-8')
        print('Inspected EA flow origin',origin,flush=True)
    frame = add_updates(pd.concat(frames,ignore_index=True))
    actuals = load_sid_reference([str(m) for m in months],client=client)
    one = walk_forward_rows(frame,actuals)
    frame.to_csv(output/'archived_forecast_horizons.csv',index=False,float_format='%.15g')
    pd.DataFrame(coverage).to_csv(output/'horizon_coverage.csv',index=False)
    one.to_csv(output/'one_month_walk_forward.csv',index=False,float_format='%.15g')
    summaries = []
    for destination,part in one.groupby('destination',sort=False):
        good = part.dropna(subset=['legacy_error_bcm'])
        error = good.legacy_error_bcm
        denominator = good.ea_actual_bcm.abs().sum()
        summaries.append({'destination':destination,'matched_months':len(good),'target_months':','.join(good.target_month),
            'legacy_mae_bcm_month':error.abs().mean(),'legacy_rmse_bcm_month':np.sqrt((error**2).mean()),
            'legacy_bias_bcm_month':error.mean(),'legacy_wape_pct':100*error.abs().sum()/denominator if denominator>0 else np.nan,
            'routing_mae_bcm_month':np.nan,'routing_status':'No complete origin-matched routing inputs/solutions',
            'comparison':'EA historical actual allocation series; PL/DK physical export errors withheld'})
    pd.DataFrame(summaries).to_csv(output/'walk_forward_error_summary.csv',index=False,float_format='%.15g')
    (provenance/'ea_actual_responses.json').write_text(json.dumps(actuals['responses'],indent=2,allow_nan=False)+'\n',encoding='utf-8')
    monthly_updates = frame.dropna(subset=['forecast_update_bcm']).groupby(['destination','lead_months'],sort=False).agg(
        comparable_updates=('forecast_update_bcm','size'),
        changed_updates=('forecast_update_bcm',lambda s:int(s.abs().gt(1e-8).sum())),
        mean_absolute_update_bcm=('forecast_update_bcm',lambda s:s.abs().mean())).reset_index()
    monthly_updates.to_csv(output/'forecast_update_summary.csv',index=False,float_format='%.15g')
    export_horizon_figures(frame,one,output)
    manifest = {'targets':[str(m) for m in months],'origins':origins,'origin_convention':'Previous calendar month-end at 23:59:59 UTC',
        'sourcing':'Fresh exact SID queries at every origin; no workbook/cache input fallback',
        'future_values_beyond_one_month':int(frame.loc[frame.lead_months.gt(1),'prediction_bcm'].notna().sum()),
        'independent_publication_horizon_verified':False,'routing_backtest_completed':False,
        'parameter_fitting':False,'solver_calls':0,'holdout_loaded':False,'holdout_scored':False,
        'later_horizons':'2026 targets were not queried; grey figure cells are outside the evaluation window',
        'walk_forward_interpretation':'Legacy one-month archived forecast versus EA actuals; routing comparison remains incomplete'}
    (provenance/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


def export_horizon_figures(frame,one,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from .data import COLORS
    fig,axes=plt.subplots(3,2,figsize=(16,12))
    fig.subplots_adjust(top=.9,bottom=.08,hspace=.48,wspace=.2)
    origins=sorted(frame.origin.unique())
    for ax,name in zip(axes.flat,GROUPS):
        part=frame.loc[frame.destination.eq(name)]
        matrix=part.pivot(index='origin',columns='lead_months',values='prediction_bcm').reindex(index=origins,columns=range(1,13))
        available=part.assign(queried=True).pivot(index='origin',columns='lead_months',values='queried').reindex(index=origins,columns=range(1,13))
        # Grey = outside selected window, white = missing queried value, colour = returned value.
        z=np.where(available.eq(True),np.where(matrix.notna(),2,1),0)
        ax.imshow(z,aspect='auto',vmin=0,vmax=2,cmap=ListedColormap(['#e8edf1','#ffffff',COLORS[name]]))
        ax.set_title(NAMES[name],color=COLORS[name]);ax.set_xticks(range(12),range(1,13));ax.set_xlabel('Months ahead of origin')
        ax.set_yticks(range(len(origins)),[o[:7] for o in origins]);ax.set_ylabel('Forecast origin')
    axes.flat[-1].axis('off')
    axes.flat[-1].text(.02,.9,'Coloured: finite archived future value\nWhite: missing within queried window\nGrey: outside 2025; not queried\n\nValues beyond one month establish\navailable forecast tails, not the publisher’s\nintended forecast horizon.\n\nMonthly origins use month-end cutoffs.\nRouting model parameters stay fixed.',
        transform=axes.flat[-1].transAxes,va='top',fontsize=13,color='#33465a',linespacing=1.5)
    fig.suptitle('EA flow forecast coverage by origin and lead time — 2025 targets',x=.045,ha='left',fontsize=19,color='#172f45')
    for extension in ['png','svg']:fig.savefig(Path(output)/f'forecast_horizon_coverage.{extension}',dpi=200,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(16,10));fig.subplots_adjust(top=.88,bottom=.09,hspace=.45,wspace=.2)
    for ax,name in zip(axes.flat,GROUPS):
        part=one.loc[one.destination.eq(name)];x=np.arange(len(part))
        ax.axhline(0,color='#8996a3',linewidth=1);ax.plot(x,part.legacy_error_bcm,marker='o',color=COLORS[name],linewidth=2.4)
        ax.set_title(NAMES[name],color=COLORS[name]);ax.set_ylabel('Forecast minus actual, bcm/month')
        ax.set_xticks(x[::2],part.target_month.str[5:][::2]);ax.grid(axis='y',alpha=.18)
        if not part.legacy_error_bcm.notna().any():
            ax.text(.5,.5,'Export-error comparison withheld\nNybro / net-flow boundary differs',transform=ax.transAxes,ha='center',fontsize=12,color='#8c6b32')
    axes.flat[-1].axis('off');axes.flat[-1].text(.02,.9,'Legacy forecast from the preceding\nmonth-end snapshot, compared with\nEA historical actuals.\n\nRouting forecast errors remain missing\nuntil complete same-origin SID inputs\nand frozen-model solutions are available.',transform=axes.flat[-1].transAxes,va='top',fontsize=13,color='#33465a',linespacing=1.5)
    fig.suptitle('One-month walk-forward legacy forecast errors — 2025 validation',x=.045,ha='left',fontsize=19,color='#172f45')
    fig.text(.045,.018,'EA allocation-series definitions apply. No 2026 outcomes or forecasts queried; no model refitting.',fontsize=11,color='#5f7080')
    for extension in ['png','svg']:fig.savefig(Path(output)/f'one_month_walk_forward_errors.{extension}',dpi=200,bbox_inches='tight',facecolor='white')
    plt.close(fig)
