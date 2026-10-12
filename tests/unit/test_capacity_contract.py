"""Inactive mapping checks use synthetic database identities and real proposal."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest
import yaml

from norway_gas_routing.capacity.contract import IDENTITIES, inspect_contract, validate_contract

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT/'evidence/inputs/capacity_integration_contract.json'


@pytest.fixture
def proposal():
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    model = yaml.safe_load((ROOT/'config/model.yaml').read_text(encoding='utf-8'))
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE assets(asset_key,operator_key,point_key,direction)')
    db.executemany('INSERT INTO assets VALUES(?,?,?,?)',
                   [(key,*value[:3]) for key,value in IDENTITIES.items()])
    yield contract,model,db
    db.close()


def test_valid_inactive_identity(proposal):
    assert validate_contract(*proposal)


@pytest.mark.parametrize('field,value',[
    ('operator','PL-TSO-0002'),('point','ITP-10009'),('direction','exit'),
    ('candidate_arc','EUROPIPE_II'),('category','commercial_available'),
    ('replace_existing',True),('status','ready'),('original_unit','bcm/month'),
])
def test_identity_category_and_replacement_fail_closed(proposal,field,value):
    contract,model,db=proposal
    contract['mappings'][0][field]=value
    with pytest.raises(ValueError): validate_contract(contract,model,db)


@pytest.mark.parametrize('change',['factor','approval','active','shared_sum','duplicate','holdout','topology'])
def test_unsupported_derivations_and_shared_constraints(proposal,change):
    contract,model,db=proposal
    if change=='factor': contract['mappings'][0]['conversion']['capacity_basis_kwh_per_model_m3']=12.1
    if change=='approval': contract['mappings'][0]['conversion']['approved']=True
    if change=='active': contract['enabled']=True
    if change=='shared_sum': contract['shared_constraints']['faxe']['combination']='sum'
    if change=='duplicate': contract['mappings'][2]=deepcopy(contract['mappings'][1])
    if change=='holdout': contract['window'][1]='2026-01-01'
    if change=='topology': next(a for a in model['routing']['arcs'] if a['id']=='DK_OFFTAKE')['from']='FAXE'
    with pytest.raises(ValueError): validate_contract(contract,model,db)


def test_database_operator_not_inferred_from_point(proposal):
    contract,model,db=proposal
    db.execute("UPDATE assets SET operator_key='DK-TSO-0001' WHERE asset_key='point:faxe_pl_technical'")
    with pytest.raises(ValueError): validate_contract(contract,model,db)


def test_retained_history_lineage_and_no_volume_comparison():
    coverage,differences=inspect_contract(ROOT,CONTRACT)
    assert len(coverage)==9
    assert [r['known_days'] for r in coverage]==[365,366,365]*3
    assert all(r['missing_days']==0 and r['comparable_bcm'] is None and r['numerical_model_difference'] is None for r in coverage)
    assert len(differences)==4
    assert {r['gas_day'] for r in differences}=={'2023-10-02','2023-10-09','2024-07-31','2024-08-01'}
    assert all(r['dk_record_ids'] and r['pl_record_ids'] and r['dk_revisions'] and r['pl_revisions'] for r in differences)
    assert all(r['vintage_status']=='latest_revised_origin_unverified' for r in differences)
    assert all(r['gas_day_end']>r['gas_day_start'] for r in differences)


@pytest.mark.parametrize('change', ['capacity', 'migration_hash', 'missing_migration'])
def test_structure_migration_does_not_accept_other_changes(tmp_path, change):
    import shutil
    for name in ['config/model.yaml', 'evidence/inputs/project_structure_migration.json']:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    contract['input_sha256'] = {'config/model.yaml': contract['input_sha256']['config/model.yaml']}
    path = tmp_path/'contract.json'
    path.write_text(json.dumps(contract), encoding='utf-8')
    migration_path = tmp_path/'evidence/inputs/project_structure_migration.json'
    if change == 'capacity':
        model = yaml.safe_load((tmp_path/'config/model.yaml').read_text(encoding='utf-8'))
        model['routing']['assets']['KOLLSNES_EXPORT']['mcm_d'] = 156.
        (tmp_path/'config/model.yaml').write_text(yaml.safe_dump(model), encoding='utf-8')
    elif change == 'migration_hash':
        migration = json.loads(migration_path.read_text(encoding='utf-8'))
        migration['model_config']['before_sha256'] = '0'*64
        migration_path.write_text(json.dumps(migration), encoding='utf-8')
    else:
        migration_path.unlink()
    with pytest.raises(ValueError, match='Proposal input changed'):
        inspect_contract(tmp_path, path)
