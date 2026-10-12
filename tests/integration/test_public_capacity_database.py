"""Explicit offline public-evidence integration tests; no private data or network."""
import json
from pathlib import Path
import sqlite3

import pytest

from norway_gas_routing.capacity.public import build_database, sha256


@pytest.fixture(scope='module')
def capacity_db(tmp_path_factory):
    root=Path(__file__).resolve().parents[2]
    output=tmp_path_factory.mktemp('public-capacity')/'database'
    manifest=build_database(root,output)
    db=sqlite3.connect(output/'capacity.sqlite');db.row_factory=sqlite3.Row
    yield root,output,manifest,db
    db.close()


def test_exact_model_assets_and_foundation_separate(capacity_db):
    root,output,manifest,db=capacity_db
    assert manifest['counts']['assets']==37 and manifest['counts']['assumption_comparison']==19
    assert db.execute("SELECT count(*) FROM assets WHERE scope='foundation_retained'").fetchone()[0]==15
    assert db.execute("SELECT count(*) FROM assets WHERE scope='public_point' AND active=1").fetchone()[0]==0
    assert db.execute("SELECT count(*) FROM ratings WHERE source_id='G_MAP'").fetchone()[0]==14
    assert db.execute("SELECT count(*) FROM ratings WHERE source_id='G_MAP' AND (valid_from IS NOT NULL OR valid_to IS NOT NULL)").fetchone()[0]==0


def test_coverage_matches_audit(capacity_db):
    root,output,manifest,db=capacity_db
    assert manifest['counts']['daily']==3564 and manifest['counts']['monthly']==117
    assert len(manifest['audit_coverage_comparison'])==12
    assert all(r['covered_days']==r['audit_covered_days'] for r in manifest['audit_coverage_comparison'])
    assert db.execute('SELECT count(*) FROM daily WHERE technical_kwh_per_gas_day IS NULL').fetchone()[0]==0
    assert db.execute("SELECT count(*) FROM daily WHERE gas_day LIKE '2026%'").fetchone()[0]==0


def test_original_observations_and_lineage_exact(capacity_db):
    root,output,manifest,db=capacity_db
    for probe in ['north_sea_technical','faxe_dk_technical','faxe_pl_technical']:
        original=json.loads((root/'data/raw/public_capacity_audit'/(probe+'.json')).read_bytes())['operationaldatas']
        stored=[json.loads(r[0]) for r in db.execute('SELECT raw_record_json FROM ratings WHERE asset_key=?',('point:'+probe,))]
        assert sorted(original,key=lambda r:r['id'])==sorted(stored,key=lambda r:r['id'])
        lookup={r['id']:r for r in original}
        for day in db.execute('SELECT * FROM daily WHERE asset_key=?',('point:'+probe,)):
            matching=[lookup[k] for k in json.loads(day['source_record_ids_json'])]
            assert matching and all(r['value']==day['technical_kwh_per_gas_day'] for r in matching)
            assert day['technical_gwh_per_gas_day']==day['technical_kwh_per_gas_day']/1e6


def test_faxe_sides_and_commissioning_zero(capacity_db):
    db=capacity_db[3]
    values=dict(db.execute("SELECT asset_key,technical_kwh_per_gas_day FROM daily WHERE gas_day='2023-10-02'"))
    assert values['point:faxe_dk_technical']==321864000
    assert values['point:faxe_pl_technical']==201480000
    zero=db.execute("SELECT quality,technical_kwh_per_gas_day FROM daily WHERE asset_key='point:north_sea_technical' AND gas_day='2022-10-01'").fetchone()
    assert tuple(zero)==('reported_zero',0)


def test_actual_dst_days_and_monthly_quantities(capacity_db):
    db=capacity_db[3]
    for day,hours,value in [('2024-03-30',23,308453000),('2024-10-26',25,335275000),('2024-02-29',24,321864000)]:
        row=db.execute("SELECT gas_day_hours,technical_kwh_per_gas_day FROM daily WHERE asset_key='point:north_sea_technical' AND gas_day=?",(day,)).fetchone()
        assert tuple(row)==(hours,value)
    row=db.execute("SELECT technical_kwh,covered_gas_days FROM monthly WHERE asset_key='point:north_sea_technical' AND month='2024-02'").fetchone()
    assert tuple(row)==(29*321864000,29)


def test_unknown_availability_no_events_no_volume_conversion(capacity_db):
    db=capacity_db[3]
    assert db.execute('SELECT count(*) FROM events').fetchone()[0]==0
    assert db.execute('SELECT count(*) FROM daily WHERE capacity_bcm IS NOT NULL OR engineering_available_kwh IS NOT NULL OR commercial_available_kwh IS NOT NULL').fetchone()[0]==0
    assert db.execute('SELECT count(*) FROM monthly WHERE capacity_bcm IS NOT NULL').fetchone()[0]==0
    assert db.execute("SELECT count(*) FROM ratings WHERE capacity_category='commercial_available'").fetchone()[0]==0


def test_plant_conflicts_preserved(capacity_db):
    db=capacity_db[3]
    values={r[0] for r in db.execute("SELECT value FROM specification_register WHERE asset_id='KOLLSNES_EXPORT' AND value IS NOT NULL")}
    assert {143,144.5,156}<=values
    assert db.execute("SELECT comparison_status FROM assets WHERE asset_key='poc_active:KARSTO_PROCESSING'").fetchone()[0]=='definition_incompatible'
    assert db.execute("SELECT count(*) FROM ratings WHERE effective_change_window IS NOT NULL AND valid_from IS NOT NULL").fetchone()[0]==0


def test_publication_vintage_provenance(capacity_db):
    root,output,manifest,db=capacity_db
    for source in db.execute("SELECT * FROM sources WHERE source_id IN ('TP_north_sea_technical','TP_faxe_dk_technical','TP_faxe_pl_technical')"):
        assert source['raw_sha256']==sha256(root/source['raw_capture_path'])
        assert source['retrieved_precision']=='timestamp' and source['first_published_at'] is None
        assert source['vintage_status']=='latest_revised_origin_unverified'
        assert 'operatorKey' in json.loads(source['request_parameters_json'])
    assert db.execute('SELECT count(*) FROM ratings WHERE revision_timestamp IS NOT NULL AND first_published_at IS NOT NULL').fetchone()[0]==0


def test_rebuild_deterministic_idempotent_and_no_overwrite(capacity_db):
    root,output,manifest,db=capacity_db
    second=output.parent/'second'
    again=build_database(root,second)
    assert manifest==again
    assert sha256(output/'capacity.sqlite')==sha256(second/'capacity.sqlite')
    with pytest.raises(FileExistsError): build_database(root,output)


def test_partial_requested_month_not_full_month(capacity_db):
    root,output,manifest,db=capacity_db
    clipped=output.parent/'clipped'
    build_database(root,clipped,'2024-02-29','2024-02-29')
    with sqlite3.connect(clipped/'capacity.sqlite') as connection:
        rows=connection.execute('SELECT requested_gas_days,calendar_gas_days,technical_kwh,known_subtotal_kwh,quality FROM monthly').fetchall()
    assert all(r[0:3]==(1,29,None) and r[3]>0 and r[4]=='partial_requested_month' for r in rows)


def test_unknown_day_cannot_become_complete_month_or_bcm(capacity_db):
    copy=sqlite3.connect(':memory:');capacity_db[3].backup(copy)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            copy.execute("UPDATE daily SET capacity_bcm=1 WHERE asset_key='point:north_sea_technical' AND gas_day='2023-01-01'")
        copy.execute("UPDATE daily SET technical_kwh_per_gas_day=NULL,technical_gwh_per_gas_day=NULL,quality='missing' WHERE asset_key='point:north_sea_technical' AND gas_day='2023-01-01'")
        row=copy.execute("SELECT technical_kwh,unknown_gas_days,quality,known_subtotal_kwh FROM monthly WHERE asset_key='point:north_sea_technical' AND month='2023-01'").fetchone()
        assert row[:3]==(None,1,'incomplete_unknown') and row[3]>0
    finally:
        copy.close()
