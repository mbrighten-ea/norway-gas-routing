"""Synthetic reporting tests. No optimiser, services, real workbooks or holdout reads."""
import io
import json
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import pytest

from norway_gas_routing.visual_data import (COUNTRIES, aggregate_groups, annual_comparison,
    comparison, dated_csv, period_map, safe_percent, shares, strict_sum, validate_run)
from norway_gas_routing.visual_legacy import NS, SUFFIX, cached_cell, load_retained_forecast, selected_sheet, workbook_bytes


def solution():
    monthly = pd.DataFrame([{'month': month, **{c: 1.0 for c in COUNTRIES}, 'exports_bcm': 7.,
        'supply_bcm': 9., 'unrouted_bcm': 2., 'unmapped_bcm': .5, 'mapped_disposal_bcm': 1.5}
        for month in ['2024-01','2024-02']])
    definitions = [{'id': 'ROUTE_'+c, 'from': 'FEED', 'to': c, 'asset': 'POOL' if c in ['DE','NL'] else None} for c in COUNTRIES]
    definitions += [{'id': 'FEED_UNROUTED', 'from': 'FEED', 'to': 'UNROUTED', 'asset': None},
                    {'id': 'UNMAPPED_UNROUTED', 'from': 'UNMAPPED', 'to': 'UNROUTED', 'asset': None}]
    arcs = pd.DataFrame([{'month': m, 'arc': d['id'], 'from': d['from'], 'to': d['to'], 'asset': d['asset'],
        'flow_bcm': 1.5 if d['id']=='FEED_UNROUTED' else .5 if d['id']=='UNMAPPED_UNROUTED' else 1.}
        for m in monthly.month for d in definitions])
    assets = pd.DataFrame([{'month': '2024-01','asset': 'POOL','flow_bcm': 2.,'capacity_bcm': 2.},
                          {'month': '2024-02','asset': 'POOL','flow_bcm': 2.,'capacity_bcm': 4.}])
    return {'monthly': monthly, 'arcs': arcs, 'assets': assets, 'id':'synthetic', 'scenario':'test',
        'network': {'arcs': definitions, 'nodes': {**{c: {'kind':'destination'} for c in COUNTRIES},
            'FEED': {'kind':'source'}, 'UNMAPPED': {'kind':'source'}, 'UNROUTED': {'kind':'unrouted'}}}}


def legacy(kind='forecast'):
    return {'kind': kind, 'vintage':'synthetic-origin', 'data': pd.DataFrame([
        {'month':'2024-01','level':'groups','destination':'UK','value_bcm':0.,'compatible':True,'status':'real zero','cell':'D1'},
        {'month':'2024-02','level':'groups','destination':'UK','value_bcm':np.nan,'compatible':True,'status':'missing cache','cell':'D2'},
        {'month':'2024-01','level':'countries','destination':'PL','value_bcm':2.,'compatible':False,'status':'Nybro entry','cell':'L1'},
        {'month':'2024-01','level':'groups','destination':'DK','value_bcm':-.1,'compatible':False,'status':'signed net','cell':'O1'}])}


def test_groups_reconcile_without_double_counting():
    run=solution(); grouped=aggregate_groups(run['monthly'][COUNTRIES])
    assert grouped.iloc[0].to_dict()=={'UK':1.,'FR+BE':2.,'NL+DE':2.,'Baltic Pipe':1.,'DK':1.}
    assert grouped.sum(axis=1).tolist()==[7.,7.]


def test_missing_group_component_stays_missing():
    frame=solution()['monthly'][COUNTRIES].copy(); frame.loc[0,'FR']=np.nan
    assert np.isnan(aggregate_groups(frame).iloc[0]['FR+BE'])


@pytest.mark.parametrize('values', [[1.,np.nan],[],[np.inf,1.]])
def test_strict_sum_does_not_hide_missing(values):
    assert np.isnan(strict_sum(values))


def test_shared_asset_annual_denominator_is_monthly_sum():
    run=solution(); maps, caps=period_map(run,['2024-01','2024-02'])
    row=caps.iloc[0]
    assert row.asset_flow_bcm==4. and row.capacity_bcm==6.
    assert row.utilisation_pct==pytest.approx(100*4/6)
    assert row.binding_months==1
    assert maps.loc[maps.asset.eq('POOL'),'flow_bcm'].sum()==4.
    # Capacity is stored once in caps, not duplicated by DE and NL allocation links.
    assert len(caps)==1


def test_missing_annual_capacity_withholds_utilisation():
    run=solution();run['assets'].loc[1,'capacity_bcm']=np.nan
    _,caps=period_map(run,['2024-01','2024-02'])
    assert np.isnan(caps.iloc[0].capacity_bcm)
    assert np.isnan(caps.iloc[0].utilisation_pct)


@pytest.mark.parametrize('denominator',[0.,-1.,np.nan])
def test_invalid_denominator_has_no_percentage(denominator):
    assert np.isnan(safe_percent(1.,denominator))


@pytest.mark.parametrize('values',[[1.,np.nan],[1.,-.1],[0.,0.]])
def test_share_baskets_incomplete_negative_or_zero_are_withheld(values):
    assert shares(values).isna().all()


def test_export_shares_reconcile():
    assert shares([1.,3.]).tolist()==[25.,75.]


def test_true_zero_forecast_and_missing_are_distinct():
    frame=comparison(solution(),legacy())
    uk=frame.loc[frame.level.eq('groups') & frame.destination.eq('UK')]
    assert uk.iloc[0].legacy_model_bcm==0.
    assert uk.iloc[0].delta_bcm==1.
    assert np.isnan(uk.iloc[0].delta_pct)
    assert np.isnan(uk.iloc[1].delta_bcm)
    assert frame.legacy_vintage.eq('synthetic-origin').all()
    assert frame.unit.eq('bcm/month').all()


def test_incompatible_poland_is_not_plotted_as_country_export():
    frame=comparison(solution(),legacy('workbook_history'))
    pl=frame.loc[frame.level.eq('countries') & frame.destination.eq('PL')].iloc[0]
    assert pl.legacy_source_bcm==2.
    assert np.isnan(pl.workbook_history_bcm) and np.isnan(pl.legacy_model_bcm)


def test_signed_danish_history_is_retained_but_not_model_difference():
    frame=comparison(solution(),legacy('workbook_history'))
    dk=frame.loc[frame.level.eq('groups') & frame.destination.eq('DK')].iloc[0]
    assert dk.workbook_history_bcm==-.1
    assert np.isnan(dk.delta_bcm)


def test_annual_missing_legacy_month_is_not_a_partial_total():
    frame=comparison(solution(),legacy())
    annual=annual_comparison(frame,['2024-01','2024-02'])
    uk=annual.loc[annual.level.eq('groups') & annual.destination.eq('UK')].iloc[0]
    assert uk.model_bcm==2. and uk.matched_model_months==1
    assert np.isnan(uk.legacy_model_bcm)


def test_balances_capacity_and_disposal_validation():
    assert validate_run(solution())['country_and_group_totals']=='PASS'


@pytest.mark.parametrize('change',['country','arc','capacity','disposal','definition'])
def test_reconciliation_detects_corrupted_saved_data(change):
    run=solution()
    if change=='country': run['monthly'].loc[0,'UK']+=.1
    if change=='arc':run['arcs'].loc[0,'flow_bcm']+=.1
    if change=='capacity':run['assets'].loc[0,'capacity_bcm']=1.
    if change=='disposal':run['monthly'].loc[0,'unmapped_bcm']=.7
    if change=='definition':run['arcs'].loc[0,'to']='FR'
    with pytest.raises(ValueError):validate_run(run)


def test_holdout_csv_rejected_from_dates_before_numeric_load(tmp_path,monkeypatch):
    path=tmp_path/'outcomes.csv';path.write_text('month,value\n2026-01-01,123\n')
    original=pd.read_csv; calls=[]
    def read(*a,**k):calls.append(k);return original(*a,**k)
    monkeypatch.setattr(pd,'read_csv',read)
    with pytest.raises(ValueError,match='holdout'):dated_csv(path)
    assert calls==[{'usecols':['month']}]


def test_cached_xml_uses_exact_value_and_retains_missing():
    cell=ET.fromstring(f'<c xmlns="{NS["x"]}" r="D121"><f>INDEX(X,1)</f><v>2.8797531094202897</v></c>')
    assert cached_cell(cell,[])==2.8797531094202897
    missing=ET.fromstring(f'<c xmlns="{NS["x"]}" r="D122"><f>INDEX(X,2)</f></c>')
    assert cached_cell(missing,[]) is None


def test_workbook_date_selection_skips_unselected_outcome_decoding():
    xml=f'<worksheet xmlns="{NS["x"]}"><sheetData><row r="1"><c r="B1"><v>45292</v></c><c r="D1"><v>1.23456789</v></c></row><row r="2"><c r="B2"><v>46023</v></c><c r="D2"><v>not-a-number-reserved-cell</v></c></row></sheetData></worksheet>'
    content=io.BytesIO()
    with zipfile.ZipFile(content,'w') as archive:archive.writestr('sheet.xml',xml)
    with zipfile.ZipFile(io.BytesIO(content.getvalue())) as archive:
        result=selected_sheet(archive,'sheet.xml','B',{'2024-01'},['D'],[])
    assert result.cached.tolist()==[1.23456789]


def test_original_workbook_read_bytes_are_unchanged(tmp_path):
    content=io.BytesIO()
    with zipfile.ZipFile(content,'w') as archive:archive.writestr('proof.txt','synthetic')
    path=tmp_path/'book.xlsx';path.write_bytes(content.getvalue())
    data,status=workbook_bytes(path)
    assert data==path.read_bytes()==content.getvalue()
    assert status=='Original ZIP readable'


def forecast_fixture(path):
    raw=path/'provenance/raw';raw.mkdir(parents=True)
    rows,checks=[],[]
    for name,suffix in SUFFIX.items():
        value=1.234567890123
        record={'origin':'2023-12-31','retrieved_at_utc':'2026-10-09T00:00:00Z',
            'metadata':{'unit':'bcm','frequency':'monthly','lifecycle_stage':'forecast',
                'source_file':'Norwegian flows model.xlsx','forecast_start_date':'2024-01-01'},
            'points':[{'dt':'2024-01-01T00:00:00Z','val':value}]}
        (raw/(suffix+'.json')).write_text(json.dumps(record))
        if name!='total':
            rows.append({'method':'legacy_asof','origin':'2023-12-31','target_month':'2024-01',
                'destination':name,'prediction_bcm':round(value,9)})
            checks.append({'origin':'2023-12-31','target_month':'2024-01','group':name,
                'verified_future_forecast':True,'evidence_file':suffix+'.json'})
    pd.DataFrame(rows).to_csv(path/'results.csv',index=False)
    pd.DataFrame(checks).to_csv(path/'provenance/forecast_verification.csv',index=False)
    (path/'provenance/retrieval_manifest.json').write_text(json.dumps([
        {'origin':'2023-12-31','sid':'teams\\gassco_total','evidence_file':'total.json'}]))
    return path


def test_retained_forecasts_use_exact_unrounded_values_and_provenance(tmp_path):
    source=load_retained_forecast(forecast_fixture(tmp_path),'2023-12-31',['2024-01','2024-02'])
    assert source['data'].value_bcm.eq(1.234567890123).all()
    assert not source['data'].destination.isin(['FR','BE','NL','DE']).any()
    assert source['data'].month.eq('2024-01').all()
    assert source['ledger'].record_sha256.str.len().eq(64).all()
    assert source['ledger'].origin.eq('2023-12-31').all()


@pytest.mark.parametrize('field,value',[('unit','mcm/day'),('lifecycle_stage','actual'),('forecast_start_date',None)])
def test_unverified_forecast_semantics_are_rejected(tmp_path,field,value):
    root=forecast_fixture(tmp_path);path=root/'provenance/raw/UK.json';record=json.loads(path.read_text())
    record['metadata'][field]=value;path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='identity/unit/vintage'):
        load_retained_forecast(root,'2023-12-31',['2024-01'])


def test_changed_retained_export_fails_exact_match(tmp_path):
    root=forecast_fixture(tmp_path);frame=pd.read_csv(root/'results.csv');frame.loc[0,'prediction_bcm']+=.001
    frame.to_csv(root/'results.csv',index=False)
    with pytest.raises(ValueError,match='differs from retained export'):
        load_retained_forecast(root,'2023-12-31',['2024-01'])
