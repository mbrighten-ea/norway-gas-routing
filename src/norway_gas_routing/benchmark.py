"""Archived forecast gates, seasonal baseline and scoring; no live retrieval."""
from pathlib import Path
import numpy as np
import pandas as pd
from .poc import DESTINATIONS
from .evaluation import check_dates, check_table, TRAIN_END, TRAIN_CUTOFF, EvaluationError

OUT=Path(__file__).resolve().parents[2]/'.scratch/benchmark-tables'

def csv(frame,name):
    check_table(frame)
    OUT.mkdir(parents=True,exist_ok=True)
    frame.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.9f')

SUFFIX = {'UK':'UK','FR+BE':'FR_and_BE','NL+DE':'NL_and_DE',
          'Baltic Pipe':'PL','DK':'DK','FR':'FR','BE':'BE','NL':'NL','DE':'DE','total':'total'}

GROUPS = {'UK':['UK'], 'FR+BE':['FR','BE'], 'NL+DE':['NL','DE'],
          'Baltic Pipe':['PL'], 'DK':['DK']}

def monthly(series):
    result = series.copy()
    result.index = pd.to_datetime(result.index, utc=True).tz_localize(None).to_period('M')
    check_dates(result.index)
    if not result.index.is_unique:
        raise ValueError('Duplicate monthly timestamps; no automatic aggregation')
    return result.astype(float)

def boundary(meta):
    value = meta.get('forecast_start_date')
    return pd.Period(pd.Timestamp(value),freq='M') if value else None

def verified_forecast(record, target, value):
    check_dates([str(target)], 'score')
    meta = record['metadata']
    cutoff = pd.Period(record['origin'],freq='M')
    first = boundary(meta)
    return (pd.notna(value) and np.isfinite(value) and target > cutoff and
            first is not None and target >= first and meta.get('unit') == 'bcm' and
            meta.get('lifecycle_stage') == 'forecast' and
            str(meta.get('source_file','')).endswith('Norwegian flows model.xlsx'))

def forecast_rows(latest,snapshots):
    for series in latest.values():
        check_dates(series.index, 'score')
    rows,training,verification=[],[],[]
    individual={'PL':'Baltic Pipe',**{d:d for d in DESTINATIONS if d!='PL'}}
    for origin,snapshot in snapshots.items():
        check_dates([origin], 'read')
        cutoff=pd.Period(origin,freq='M')
        targets=pd.period_range(cutoff+1,cutoff+12,freq='M')
        check_dates(targets, 'score')
        if pd.to_datetime(origin, utc=True) > TRAIN_CUTOFF:
            raise EvaluationError('Validation origins require a separately frozen training vintage through 2024-12; do not refit from validation snapshots')
        # Baseline uses only observed months already retained at origin, with a
        # one-month reporting lag and historical forecast boundaries enforced.
        hist=pd.DataFrame({d:snapshot[key][0] for d,key in individual.items()})
        check_dates(hist.index)
        accepted=hist.notna().all(axis=1)&hist.ge(0).all(axis=1)&(hist.index<cutoff)&(hist.index<=TRAIN_END)
        for d,key in individual.items():
            first=boundary(snapshot[key][1]['metadata'])
            if first is not None:accepted &= hist.index<first
        hist=hist.loc[accepted]
        check_dates(hist.index, 'fit')
        for month,values in hist.iterrows():
            training.append({'origin':origin,'month':str(month),**values.to_dict()})
        for target in targets:
            for name in GROUPS:
                series,record=snapshot[name];value=series.get(target,np.nan)
                valid=verified_forecast(record,target,value)
                actual=latest[name].get(target,np.nan)
                verification.append({'origin':origin,'target_month':str(target),'group':name,'archived_bcm':value,
                    'latest_bcm':actual,'revised_bcm':actual-value,'verified_future_forecast':valid,
                    'forecast_start_date':record['metadata'].get('forecast_start_date'),'evidence_file':record['evidence_file']})
                rows.append({'method':'legacy_asof','origin':origin,'target_month':str(target),'level':'five_groups','destination':name,
                    'prediction_bcm':value if valid else np.nan,'actual_bcm':actual,'status':'verified retained future forecast' if valid else 'missing/unverified forecast',
                    'analysis_type':'archived retained-state forecast; public release timing unverified'})
            seasonal=hist.loc[hist.index.month==target.month]
            if len(seasonal) and seasonal.sum().sum()>0:
                shares=seasonal.sum()/seasonal.sum().sum()
                # Total forecast is historical mean same-month export DAILY rate
                # times target calendar days, avoiding future actual totals.
                total_rate=(seasonal.sum(axis=1)/seasonal.index.days_in_month).mean()
                forecasts=shares*total_rate*target.days_in_month
                for level,mapping in [('seven_destinations',{d:[d] for d in DESTINATIONS}),('five_groups',GROUPS)]:
                    for name,ds in mapping.items():
                        actual_key=individual.get(name,name)
                        rows.append({'method':'seasonal_asof','origin':origin,'target_month':str(target),'level':level,'destination':name,
                            'prediction_bcm':forecasts[ds].sum(),'actual_bcm':latest[actual_key].get(target,np.nan),
                            'status':'earlier same-month complete nonnegative observations only',
                            'analysis_type':'archived seasonal forecast; public release timing unverified',
                            'training_n_same_month':len(seasonal),'training_last_month':str(seasonal.index.max())})
    csv(pd.DataFrame(training),'seasonal_training_vintages.csv')
    csv(pd.DataFrame(verification),'forecast_verification.csv')
    return rows

def metric_table(frame):
    check_table(frame, 'score')
    frame = frame.copy()
    frame['split'] = ['development' if m <= TRAIN_END else 'validation' for m in
                      check_dates(frame.target_month, 'score')]
    metrics=[]
    keys_columns = ['method','origin','level','destination','split']
    for keys,group in frame.groupby(keys_columns):
        good=group.dropna(subset=['prediction_bcm','actual_bcm'])
        denom=good.actual_bcm.abs().sum()
        metrics.append(dict(zip(keys_columns,keys)) | {
            'n':len(good),'wape_pct':100*good.error_bcm.abs().sum()/denom if denom else np.nan,
            'mae_bcm_month':good.error_bcm.abs().mean(),'bias_bcm_month':good.error_bcm.mean(),
            'bias_total_bcm':good.error_bcm.sum() if len(good) else np.nan,
            'bias_pct':100*good.error_bcm.sum()/denom if denom else np.nan,
            'share_mae_pp':good.share_error_pp.abs().mean(),'share_bias_pp':good.share_error_pp.mean(),
            'share_n':good.share_error_pp.notna().sum(),'negative_actual_months':int(good.actual_bcm.lt(0).sum())})
    return pd.DataFrame(metrics)

def scores(rows):
    frame=pd.DataFrame(rows)
    check_table(frame, 'score')
    frame['split'] = ['development' if m <= TRAIN_END else 'validation' for m in
                      check_dates(frame.target_month, 'score')]
    frame['error_bcm']=frame.prediction_bcm-frame.actual_bcm
    # Share denominator always the full matching five-group or seven-destination
    # vector, never legacy total or an incomplete basket. Negative net DK remains
    # in volume scores but the whole month's physical share score is withheld.
    frame['share_error_pp']=np.nan
    for _,group in frame.groupby(['method','origin','target_month','level']):
        expected=5 if group.level.iloc[0]=='five_groups' else 7
        if len(group)!=expected or group[['prediction_bcm','actual_bcm']].isna().any().any():continue
        if group[['prediction_bcm','actual_bcm']].lt(0).any().any():continue
        if min(group.prediction_bcm.sum(),group.actual_bcm.sum())<=0:continue
        frame.loc[group.index,'share_error_pp']=100*(group.prediction_bcm/group.prediction_bcm.sum()-group.actual_bcm/group.actual_bcm.sum())
    csv(frame,'comparisons.csv')
    metrics=metric_table(frame);csv(metrics,'metrics.csv')
    # Matched target sets only; reconstruction is intentionally separate.
    matched=frame.loc[frame.level.eq('five_groups')&frame.method.isin(['legacy_asof','seasonal_asof'])]
    pairs=matched.pivot(index=['origin','target_month','destination'],columns='method',values='prediction_bcm').reindex(columns=['legacy_asof','seasonal_asof']).dropna()
    selected=matched.set_index(['origin','target_month','destination']).loc[pairs.index].reset_index()
    csv(selected,'matched_forecast_comparisons.csv')
    csv(metric_table(selected),'matched_forecast_metrics.csv')
    return frame,metrics
