"""F2.4 approved technical availability and proportional conservative stress."""
import pandas as pd


def approved_capacities(model,months,unavailable,scenario):
    if scenario not in {'core_f24_156','core_f24_proportional_143'}:
        raise ValueError('Explicit Core F2.4 capacity scenario required.')
    dates=pd.date_range(months.min().start_time,months.max().end_time.normalize())
    if (not unavailable.index.equals(dates) or not unavailable.map(
            lambda x: pd.notna(x) and 0<=x<=156).all()):
        raise ValueError('Kollsnes requires every daily unavailable observation in [0,156]; no filling/clipping.')
    factor=143/156 if scenario=='core_f24_proportional_143' else 1.
    capacities={}; all_daily=[]; all_monthly=[]
    for asset,entry in model['routing']['assets'].items():
        rate=entry['mcm_d'] if 'mcm_d' in entry else entry['annual_bcm']*1000/365
        loss=unavailable if asset=='KOLLSNES_EXPORT' else pd.Series(0.,index=dates)
        if entry.get('maintenance_series') and asset!='KOLLSNES_EXPORT':
            raise ValueError('Unapproved maintenance source.')
        if asset=='KOLLSNES_EXPORT': rate=156.
        scale=factor if asset=='KOLLSNES_EXPORT' else 1.
        daily=pd.DataFrame(dict(technical_mcm_d=rate,unavailable_mcm_d=loss,
            available_mcm_d=(rate-loss)*scale,stress_factor=scale),index=dates)
        monthly=daily.groupby(dates.to_period('M')).agg(
            available_capacity_bcm=('available_mcm_d',lambda x:x.sum()/1000))
        monthly['month']=monthly.index; monthly['asset']=asset
        capacities[asset]=monthly.available_capacity_bcm
        all_daily.append(daily.rename_axis('date').reset_index().assign(asset=asset,
            availability_status='Core-approved provisional technical availability' if asset=='KOLLSNES_EXPORT' else 'Existing provisional envelope; future availability unverified'))
        all_monthly.append(monthly.reset_index(drop=True))
    return pd.DataFrame(capacities),pd.concat(all_daily,ignore_index=True),pd.concat(all_monthly,ignore_index=True)
