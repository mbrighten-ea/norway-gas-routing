from copy import deepcopy
from datetime import date
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

from norway_gas_routing.public_capacity import (
    CATEGORIES, SCHEMA, expand_intervals, gas_boundary, historical_window,
    instant, validate_capture,
)

IDENTITY=('DK-TSO-0001','ITP-00630','entry')


def record(start='2024-01-01',end='2024-01-03',value=100,identifier='r1',**changes):
    row=dict(id=identifier,operatorKey=IDENTITY[0],pointKey=IDENTITY[1],directionKey=IDENTITY[2],
             indicator='Firm Technical',unit='kWh/d',periodType='day',value=value,isNA=None,isUnlimited='0',
             periodFrom=gas_boundary(date.fromisoformat(start)).isoformat(),
             periodTo=gas_boundary(date.fromisoformat(end)).isoformat(),
             lastUpdateDateTime='2024-01-01T12:00:00+01:00')
    row.update(changes); return row


def payload(rows):
    return dict(meta=dict(count=len(rows),total=len(rows),offset=0),operationaldatas=rows)


def test_half_open_clipping_no_carry_forward():
    days=expand_intervals([record()], '2024-01-02','2024-01-04')
    assert [d['value'] for d in days]==[100,None,None]
    assert [d['quality'] for d in days]==['complete','missing','missing']
    assert days[0]['gwh']==.0001


@pytest.mark.parametrize('day,hours',[('2024-03-30',23),('2024-10-26',25),('2024-02-29',24)])
def test_dst_elapsed_time_and_leap_days(day,hours):
    rows=expand_intervals([record('2024-01-01','2025-01-01')],day,day)
    assert rows[0]['gas_day_hours']==hours
    assert rows[0]['value']==100  # already a source-day quantity; no 24 multiplication


def test_full_leap_year():
    assert len(expand_intervals([], '2024-01-01','2024-12-31'))==366


def test_genuine_zero_and_na_and_missing_are_different():
    rows=[record('2024-01-01','2024-01-02',0),record('2024-01-02','2024-01-03',0,'na',isNA=True)]
    days=expand_intervals(rows,'2024-01-01','2024-01-03')
    assert [d['quality'] for d in days]==['reported_zero','missing','missing']
    assert [d['value'] for d in days]==[0,None,None]
    assert days[1]['source_record_ids']==['na']


def test_partial_validity_not_prorated_without_rate_definition():
    row=record(periodFrom='2024-01-01T12:00:00+01:00')
    days=expand_intervals([row],'2024-01-01','2024-01-01')
    assert days[0]['quality']=='partial_unknown' and days[0]['covered_hours']==18
    assert days[0]['value'] is None


def test_identical_overlaps_not_added_and_conflicts_unknown():
    first=record(); same=record(identifier='r2'); different=record(value=200,identifier='r3')
    assert expand_intervals([first,same],'2024-01-01','2024-01-01')[0]['value']==100
    conflict=expand_intervals([first,different],'2024-01-01','2024-01-01')[0]
    assert conflict['value'] is None and conflict['quality']=='conflicting_overlap'
    assert conflict['source_record_ids']==['r1','r3']


def test_exact_duplicates_collapse_conflicting_identity_fails():
    first=record()
    assert len(validate_capture(payload([first,deepcopy(first)]),IDENTITY))==1
    with pytest.raises(ValueError,match='Conflicting duplicate'):
        validate_capture(payload([first,record(value=200)]),IDENTITY)


@pytest.mark.parametrize('change',[dict(operatorKey='PL-TSO-0002'),dict(pointKey='ITP-10009'),dict(directionKey='exit')])
def test_identity_includes_three_keys(change):
    with pytest.raises(ValueError,match='identity'):
        validate_capture(payload([record(**change)]),IDENTITY)


@pytest.mark.parametrize('change',[dict(value=True),dict(value=-1),dict(value=float('nan')),dict(unit='m3/d'),dict(periodType='hour')])
def test_invalid_capacity_inputs(change):
    with pytest.raises(ValueError): validate_capture(payload([record(**change)]),IDENTITY)


def test_pagination_fails_closed():
    obj=payload([record()]);obj['meta']['total']=2
    with pytest.raises(ValueError,match='Pagination'): validate_capture(obj,IDENTITY)


def test_technical_commercial_classification():
    assert CATEGORIES['Firm Technical']=='point_technical'
    assert CATEGORIES['Firm Available']=='commercial_available'
    commercial=payload([record(indicator='Firm Available')])
    with pytest.raises(ValueError,match='indicator'): validate_capture(commercial,IDENTITY)
    assert validate_capture(commercial,IDENTITY,'Firm Available')[0]['indicator']=='Firm Available'


@pytest.mark.parametrize('start,end',[('2025-12-31','2026-01-01'),('2020-12-31','2021-01-01'),('2024-02-02','2024-02-01')])
def test_window_guard(start,end):
    with pytest.raises(ValueError): historical_window(start,end)


def test_naive_times_rejected():
    with pytest.raises(ValueError,match='timezone'): instant('2024-01-01T06:00:00')


def test_refresh_pages_fail_on_missing_page_and_duplicates():
    module_path=Path(__file__).resolve().parents[2]/'scripts/audit/refresh_public_capacity.py'
    spec=importlib.util.spec_from_file_location('refresh_public_capacity',module_path)
    refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)
    pages=[payload([record()]),payload([record(identifier='r2')])]
    for i,page in enumerate(pages): page['meta'].update(total=2,offset=i)
    queue=iter(pages)
    captures,combined=refresh.collect_pages(IDENTITY,'2024-01-01','2024-01-02',lambda url:json.dumps(next(queue)).encode(),page_size=1)
    assert len(captures)==2 and len(combined['operationaldatas'])==2
    pages[1]['operationaldatas']=[record()];queue=iter(pages)
    with pytest.raises(ValueError,match='Duplicate'):
        refresh.collect_pages(IDENTITY,'2024-01-01','2024-01-02',lambda url:json.dumps(next(queue)).encode(),page_size=1)
    pages[1]['operationaldatas']=[];pages[1]['meta']['count']=0;queue=iter(pages)
    with pytest.raises(ValueError,match='Incomplete'):
        refresh.collect_pages(IDENTITY,'2024-01-01','2024-01-02',lambda url:json.dumps(next(queue)).encode(),page_size=1)


def test_database_has_five_tables_and_volume_guard():
    db=sqlite3.connect(':memory:');db.executescript(SCHEMA)
    assert {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}=={'assets','ratings','events','daily','sources'}
    assert 'CHECK(capacity_bcm IS NULL)' in SCHEMA
    db.close()
