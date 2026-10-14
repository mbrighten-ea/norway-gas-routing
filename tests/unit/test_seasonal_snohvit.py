"""Synthetic seasonal chronology/units; never retrieve protected actuals."""
import json
import pandas as pd
import pytest
from norway_gas_routing import seasonal_snohvit as sn


def history(years=(2023,2024),origin='2025-01-15T00:00:00Z'):
    dates=pd.date_range(f'{min(years)}-01-01',f'{max(years)}-12-01',freq='MS')
    return pd.DataFrame(dict(date=dates,monthly_bcm=dates.month*dates.days_in_month/1000,
                            available_at=origin))


def test_month_matching_repeated_profile_and_leap_units():
    h=history()
    # February's 2024 leap-day volume still represents the same daily rate.
    forecast, selected, rates, years, gaps=sn.seasonal_profile(h,pd.period_range('2025-02','2028-03',freq='M'),'2025-01-15T00:00:00Z')
    assert years==[2023,2024] and not gaps and len(selected)==24
    assert rates.to_list()==pytest.approx(list(range(1,13)))
    assert forecast.loc['2025-02']==pytest.approx(.056)
    assert forecast.loc['2028-02']==pytest.approx(.058)
    assert forecast.loc['2028-03']==pytest.approx(.093)


def test_future_revision_is_ineligible_not_substituted():
    h=history();h.loc[23,'available_at']='2025-01-16T00:00:00Z'
    with pytest.raises(ValueError,match='2024-12'):
        sn.seasonal_profile(h,pd.period_range('2025-02','2025-03',freq='M'),'2025-01-15T00:00:00Z')


def test_latest_two_complete_available_years():
    h=history((2022,2023,2024))
    h.loc[h.date.eq('2024-12-01'),'available_at']='2025-02-01T00:00:00Z'
    _,selected,_,years,gaps=sn.seasonal_profile(h,pd.period_range('2025-02','2025-02',freq='M'),'2025-01-15T00:00:00Z')
    assert years==[2022,2023] and len(selected)==24 and gaps['2024']==['2024-12']


@pytest.mark.parametrize('problem',['missing','nan','inf','duplicate','midmonth','missing_information'])
def test_bad_history_fails_without_filling(problem):
    h=history()
    if problem=='missing':h=h.iloc[:-1]
    if problem in {'nan','inf'}:h.loc[23,'monthly_bcm']=float(problem)
    if problem=='duplicate':h.loc[23,'date']=h.loc[22,'date']
    if problem=='midmonth':h.loc[23,'date']=pd.Timestamp('2024-12-02')
    if problem=='missing_information':h.loc[23,'available_at']=None
    with pytest.raises(ValueError):sn.seasonal_profile(h,pd.period_range('2025-02','2025-03',freq='M'),'2025-01-15T00:00:00Z')


def test_signed_history_is_preserved_and_negative_profile_rejected():
    h=history();h.loc[0,'monthly_bcm']=-.01
    f,selected,rates,_,_=sn.seasonal_profile(h,pd.period_range('2025-02','2026-01',freq='M'),'2025-01-15T00:00:00Z')
    assert selected.iloc[0].monthly_bcm==-.01
    assert rates.loc[1]==pytest.approx((-.01*1000/31+1)/2)
    h.loc[12,'monthly_bcm']=-.02
    with pytest.raises(ValueError,match='signed history retained'):
        sn.seasonal_profile(h,f.index,'2025-01-15T00:00:00Z')


def test_holdout_read_rejected():
    h=history((2025,2026),'2026-10-01T00:00:00Z')
    with pytest.raises(ValueError,match='holdout is locked'):
        sn.seasonal_profile(h,pd.period_range('2026-11','2026-12',freq='M'),'2026-10-01T00:00:00Z')


def test_origin_month_is_not_a_completed_calendar_year():
    with pytest.raises(ValueError,match='two complete'):
        sn.seasonal_profile(history(),pd.period_range('2025-01','2025-12',freq='M'),'2024-12-31T23:59:59Z')


def test_fresh_archive_request_and_provenance(tmp_path,monkeypatch):
    h=history((2024,2025),'2026-10-01T00:00:00Z')
    calls=[]
    meta=dict(unit='bcm',frequency='monthly',lifecycle_stage='actual',country_iso='NO',
        ea_field_name_standardised='snohvit',ea_production_type='marketed_production',
        source_obj={'aspect':'gas-saleable','units':'bill Sm3'})
    monkeypatch.setattr(sn,'get_metadata',lambda q,client:meta)
    def get(q,start,end,client):
        calls.append((q,start,end));return pd.Series(h.monthly_bcm.to_numpy(),index=h.date)
    monkeypatch.setattr(sn,'get_series',get)
    records=[];f=sn.retrieve_seasonal_snohvit(pd.period_range('2026-11','2029-12',freq='M'),'2026-10-01T00:00:00Z',records,tmp_path,object())
    assert len(f)==38 and calls[0][2]=='2025-12-31' and '@asof:2026-10-01T00:00:00' in calls[0][0]
    record=json.loads((tmp_path/'source_metadata.json').read_text())[0]
    assert record['selected_years']==[2024,2025] and record['status']=='VERIFIED_SEASONAL_ASSUMPTION'
    assert len(record['selected_observations'])==24 and len(record['seasonal_rates_mcmd'])==12
    assert len(record['monthly_forecast_bcm'])==38


def test_incompatible_source_rejected_before_point_io(tmp_path,monkeypatch):
    monkeypatch.setattr(sn,'get_metadata',lambda *a,**k:{'unit':'mcm/day'})
    monkeypatch.setattr(sn,'get_series',lambda *a,**k:pytest.fail('Read incompatible points'))
    with pytest.raises(ValueError,match='net-saleable source contract'):
        sn.retrieve_seasonal_snohvit(pd.period_range('2026-11','2026-12',freq='M'),'2026-10-01T00:00:00Z',[],tmp_path,object())


def test_recorded_seasonal_package_recomputed_and_cutoff_guarded(tmp_path,monkeypatch,repo_root):
    monkeypatch.syspath_prepend(str(repo_root/'scripts/verify'))
    from verify_forward_scenarios import seasonal_snohvit_snapshot
    h=history((2024,2025),'2026-10-01T00:00:00Z')
    months=pd.period_range('2026-11','2029-12',freq='M');origin='2026-10-01T00:00:00Z'
    f,_,rates,years,_=sn.seasonal_profile(h,months,origin)
    raw=tmp_path/'history.csv';pd.Series(h.monthly_bcm.to_numpy(),index=h.date).rename('value').rename_axis('date').to_csv(raw)
    record=dict(key='snohvit_seasonal_baseline',sid=sn.HISTORICAL_SID,status='VERIFIED_SEASONAL_ASSUMPTION',
        query=f'sid="{sn.HISTORICAL_SID}"@asof:2026-10-01T00:00:00',asof=origin,start='2021-01-01',end='2025-12-31',
        raw_file='history.csv',selected_years=years,seasonal_rates_mcmd={str(k):v for k,v in rates.items()},
        monthly_forecast_bcm={str(k):v for k,v in f.items()})
    manifest={'inputs':[record]}
    assert seasonal_snohvit_snapshot(tmp_path,manifest,origin,months).to_numpy()==pytest.approx(f.to_numpy())
    record['end']='2026-09-30';raw.unlink()
    with pytest.raises(ValueError,match='holdout is locked'):
        seasonal_snohvit_snapshot(tmp_path,manifest,origin,months)


def test_revision_tolerant_partial_seasonal_counts_and_imputation():
    h=pd.DataFrame(dict(date=pd.to_datetime(['2022-01-01','2023-01-01','2023-02-01']),
        monthly_bcm=[.031,.093,.056],available_at=['2026-10-01T00:00:00Z']*3))
    f,selected,rates,years,_=sn.seasonal_profile(h,pd.period_range('2025-01','2025-12',freq='M'),
        '2024-12-31T23:59:59Z',allow_partial=True,revision_tolerant=True)
    assert years==[2022,2023] and len(selected)==3
    assert rates.loc[1]==2 and rates.loc[2]==2 and rates.loc[3]==2
    assert rates.attrs['observation_counts'][1]==2 and rates.attrs['observation_counts'][2]==1
    assert rates.attrs['imputed_calendar_months']==list(range(3,13))
    assert f.loc['2025-02']==pytest.approx(.056)
    with pytest.raises(ValueError):
        sn.seasonal_profile(h,f.index,'2024-12-31T23:59:59Z')


def test_revision_tolerant_profile_rejects_target_actuals():
    h=history((2023,2024),'2026-10-01T00:00:00Z')
    h.loc[len(h)]=[pd.Timestamp('2025-01-01'),1.,'2026-10-01T00:00:00Z']
    with pytest.raises(ValueError,match='pre-origin production'):
        sn.seasonal_profile(h,pd.period_range('2025-01','2025-12',freq='M'),'2024-12-31T23:59:59Z',
            allow_partial=True,revision_tolerant=True)


def test_partial_profile_preserves_signed_values_and_needs_observations():
    h=pd.DataFrame(dict(date=pd.to_datetime(['2022-01-01','2023-01-01']),monthly_bcm=[-.031,.093],
        available_at=['2026-10-01T00:00:00Z']*2))
    _,selected,rates,_,_=sn.seasonal_profile(h,pd.period_range('2025-01','2025-12',freq='M'),
        '2024-12-31T23:59:59Z',allow_partial=True,revision_tolerant=True)
    assert selected.iloc[0].monthly_bcm==-.031 and rates.loc[1]==pytest.approx(1.)
    h.monthly_bcm=float('nan')
    with pytest.raises(ValueError,match='some genuine'):
        sn.seasonal_profile(h,pd.period_range('2025-01','2025-12',freq='M'),'2024-12-31T23:59:59Z',
            allow_partial=True,revision_tolerant=True)


def test_partial_profile_can_use_completed_months_in_origin_year():
    h=pd.DataFrame(dict(date=pd.to_datetime(['2022-01-01','2023-12-01','2024-11-01']),
        monthly_bcm=[.031,.031,.09],available_at=['2026-10-01T00:00:00Z']*3))
    _,selected,rates,years,_=sn.seasonal_profile(h,pd.period_range('2025-01','2025-12',freq='M'),
        '2024-12-31T23:59:59Z',allow_partial=True,revision_tolerant=True)
    assert years==[2023,2024] and len(selected)==2
    assert rates.loc[11]==pytest.approx(3.) and rates.loc[12]==pytest.approx(1.)


def test_partial_profile_selects_years_with_genuine_observations():
    h=pd.DataFrame(dict(date=pd.to_datetime(['2021-01-01','2022-01-01','2023-01-01']),
        monthly_bcm=[.031,.093,float('nan')],available_at=['2026-10-01T00:00:00Z']*3))
    _,selected,rates,years,_=sn.seasonal_profile(h,pd.period_range('2025-01','2025-12',freq='M'),
        '2024-12-31T23:59:59Z',allow_partial=True,revision_tolerant=True)
    assert years==[2021,2022] and len(selected)==2
    assert rates.loc[1]==pytest.approx(2.) and rates.attrs['observation_counts'][1]==2
