"""Mock SID integration; the simplified fixture is NOT the live physical model.

Successful cases use a fixture-specific reviewed contract, three already selected
Kollsnes fields and manufactured responses. The unchanged full operational model
must still reject all 46 unresolved components before connecting or optimising.
"""
from copy import deepcopy
import json
import shutil

import pandas as pd
import pytest
import yaml

from norway_gas_routing.config import load_config
from norway_gas_routing import routing_sources as sources
from norway_gas_routing import routing_inputs as prep
from norway_gas_routing import operational as op


@pytest.fixture
def mock_workspace(repo_root, tmp_path, monkeypatch):
    for directory in ['config', 'src/norway_gas_routing', 'evidence/inputs/routing_sources_b1']:
        shutil.copytree(repo_root/directory, tmp_path/directory)
    (tmp_path/'scripts/run').mkdir(parents=True)
    shutil.copyfile(repo_root/'scripts/run/run_routing.py', tmp_path/'scripts/run/run_routing.py')
    model, registry = load_config(tmp_path/'config/model.yaml', tmp_path/'config/data_series.csv')
    # This is an explicit synthetic topology fixture, not an approved alternative
    # real-data route model. Known Kollsnes field memberships remain identical.
    remove = {n for n,e in model['routing']['nodes'].items() if e['kind']=='source' and n not in {'KOLLSNES_FEED', 'UNMAPPED'}}
    model['routing']['nodes'] = {n:e for n,e in model['routing']['nodes'].items() if n not in remove}
    model['routing']['nodes']['KOLLSNES_FEED'].pop('workbook_columns')
    model['routing']['arcs'] = [a for a in model['routing']['arcs'] if a['from'] not in remove and a['to'] not in remove]
    assets = {a['asset'] for a in model['routing']['arcs'] if a['asset']}
    model['routing']['assets'] = {a:e for a,e in model['routing']['assets'].items() if a in assets}
    model['routing'].update(start='2024-01', end='2024-12')
    (tmp_path/'config/model.yaml').write_text(yaml.safe_dump(model, sort_keys=False), encoding='utf-8')
    contract = sources.source_contract(tmp_path)
    contract['network'] = {k:model['routing'][k] for k in ['nodes', 'arcs']}
    contract['capacity_assumptions'] = model['routing']['assets']
    (tmp_path/sources.CONTRACT).write_text(json.dumps(contract), encoding='utf-8')
    monkeypatch.setattr('norway_gas_routing.data_functions.connect_shooju', lambda: object())
    return tmp_path, model, registry, contract


def response_factory(contract, calls, change=None):
    def retrieve(key, start, end, *, registry, client=None, asof=None):
        calls.append((key, start, end, asof))
        spec = contract['sources'][key]
        index = pd.date_range(start, end, freq='D' if spec['frequency']=='daily' else 'MS')
        value = 1. if key.endswith('_flow_qa') or spec['frequency']=='daily' else 1.05 if key=='norway_prod' else 2. if key=='snohvit_net_prod' else .2
        result = dict(registry={'key':key, 'sid':spec['sid']}, asof=asof, query=None,
            values=pd.Series(value, index=index), metadata=dict(unit=spec['metadata_unit'],
                frequency=spec['frequency'], source_file=spec['source_file'],
                lifecycle_stage='forecast', forecast_start_date='2025-10-01',
                api_obj={'snap_shooju_job_id':'mock-cohort'}, _mock_sid_response=True))
        if change:
            change(key, start, result)
        return result
    return retrieve


def prepare(mock_workspace, monkeypatch, change=None):
    root, model, registry, contract = mock_workspace
    calls = []
    monkeypatch.setattr(sources, 'get_registered_series', response_factory(contract, calls, change))
    result = prep.prepare_fresh_inputs(root, model, registry, provenance_dir=root/'provenance', client=object())
    return result, calls


def test_complete_mock_preparation_and_signed_capacity(mock_workspace, monkeypatch):
    def signed(key, start, response):
        if key=='kollsnes_maint_d':
            response['values'].iloc[0] = -2.
        if key=='snohvit_net_prod':
            response['values'].iloc[0] = -2.
        if key=='dk_flow_qa' and start.startswith('2023'):
            response['values'].iloc[0] = -1.
    result, calls = prepare(mock_workspace, monkeypatch, signed)
    month = pd.Period('2024-01', 'M')
    assert result['supply'].at[month, 'KOLLSNES_FEED'] == pytest.approx(.6)
    assert result['reconciliation'].at[month, 'snohvit_bcm'] == pytest.approx(-2*31/1000)
    assert result['supply'].at[month, 'UNMAPPED'] == pytest.approx(1.05+2*31/1000-.6)
    assert result['capacities'].at[month, 'KOLLSNES_EXPORT'] == pytest.approx((143*31-28)/1000)
    assert result['excluded_training_months'] == ['2023-01']
    assert sum(result['preferences'].values()) == pytest.approx(1.)
    assert all(asof is None and end<='2024-12-31' for _,_,end,asof in calls)
    assert all(r['sha256'] and r['metadata'] and r['retrieved_at'] for r in result['provenance'] if r['category']!='technical_capacity')
    assert all(r['source_url'] and r['effective_at'] is None for r in result['provenance'] if r['category']=='technical_capacity')
    assert len(result['months']) == 12


@pytest.mark.parametrize('case,message', [
    ('missing_month', 'incomplete'), ('duplicate', 'duplicate timestamp'),
    ('unit', 'inconsistent source units'), ('frequency', 'units/frequency'),
    ('origin', 'vintage substitution'), ('handover', 'forecast boundary'),
    ('sid', 'source identifier'), ('source_file', 'source-file identity'),
    ('negative', 'negative'), ('nan', 'missing/nonfinite'),
    ('maintenance_gap', 'incomplete'), ('mixed_cohort', 'Mixed production import vintages'),
    ('missing_boundary', 'missing historical/forecast'), ('source_error', 'No cached fallback'),
    ('small_total', 'source/residual supply'),
])
def test_bad_essential_sources_fail_without_fallback(mock_workspace, monkeypatch, case, message):
    def change(key, start, response):
        if case=='maintenance_gap' and key=='kollsnes_maint_d':
            response['values'] = response['values'].iloc[1:]
        if case=='small_total' and key=='norway_prod': response['values'].iloc[0]=.1
        if key != 'troll_prod':
            return
        if case=='missing_month': response['values'] = response['values'].iloc[1:]
        if case=='duplicate': response['values'] = pd.concat([response['values'], response['values'].iloc[:1]])
        if case=='unit': response['metadata']['unit'] = 'mcm_d'
        if case=='frequency': response['metadata']['frequency'] = 'daily'
        if case=='origin': response['asof'] = '2023-12-31'
        if case=='handover': response['metadata']['forecast_start_date'] = '2024-01-01'
        if case=='sid': response['registry']['sid'] = 'unverified-other'
        if case=='source_file': response['metadata']['source_file'] = 'Other.xlsx'
        if case=='negative': response['values'].iloc[0] = -.1
        if case=='nan': response['values'].iloc[0] = float('nan')
        if case=='mixed_cohort': response['metadata']['api_obj']['snap_shooju_job_id'] = 'other-import'
        if case=='missing_boundary': response['metadata'].pop('forecast_start_date')
        if case=='source_error': raise RuntimeError('SECRET-MUST-NOT-BE-LOGGED')
    with pytest.raises(ValueError, match=message) as caught:
        prepare(mock_workspace, monkeypatch, change)
    assert 'SECRET-MUST-NOT-BE-LOGGED' not in str(caught.value)


def test_optional_reference_failure_and_incompatible_definitions(mock_workspace, monkeypatch):
    def change(key, start, response):
        if key=='fr_be_flow_qa':
            response['values'] = response['values'].iloc[1:]
    result, _ = prepare(mock_workspace, monkeypatch, change)
    assert result['actual_comparisons']['FR+BE'].isna().all()
    assert result['comparison_status']['FR+BE'].startswith('Unavailable')
    assert 'Incompatible' in result['comparison_status']['DK']
    assert result['supply'].notna().all().all()


@pytest.mark.parametrize('case,message', [('missing_sid','missing SID'), ('unverified_sid','independently reviewed'),
    ('missing_record','missing verified SID'), ('duplicate_key','Duplicate production'), ('unmapped','unverified or aggregate')])
def test_registry_or_mapping_blockers_precede_retrieval(mock_workspace, monkeypatch, case, message):
    root, model, registry, _ = mock_workspace
    if case=='missing_sid': registry.at['troll_prod','sid']=''
    if case=='unverified_sid': registry.at['troll_prod','sid']='discovery-not-verified'
    if case=='missing_record': registry=registry.drop('troll_prod')
    if case=='duplicate_key': model['sources']['KOLLSNES']['series'].append('troll_prod')
    if case=='unmapped':
        model['sources']['KOLLSNES']['series'].append('unknown_component')
        # This also changes the reviewed group, deliberately fails closed.
        message='source-group components differ'
    monkeypatch.setattr(sources, 'get_registered_series', lambda *a,**k: pytest.fail('Retrieval before source-map approval'))
    with pytest.raises(ValueError, match=message):
        prep.prepare_fresh_inputs(root, model, registry, client=object())


def test_full_model_keeps_46_essential_blockers(repo_root, monkeypatch):
    model, registry = load_config(repo_root/'config/model.yaml', repo_root/'config/data_series.csv')
    requirements, _, _ = sources.source_requirements(repo_root, model, registry)
    assert len(requirements.loc[requirements.blocked & requirements.classification.eq('essential_optimisation')]) == 46
    monkeypatch.setattr(sources, 'get_registered_series', lambda *a,**k: pytest.fail('Full model must not retrieve'))
    with pytest.raises(ValueError, match='46 essential inputs unresolved'):
        prep.prepare_fresh_inputs(repo_root, model, registry)
    changed=deepcopy(model)
    changed['routing']['nodes']['KOLLSNES_FEED'].pop('workbook_columns')
    with pytest.raises(ValueError, match='do not remove essential inputs'):
        sources.source_requirements(repo_root, changed, registry)


def test_mock_operational_solve_and_failure_provenance(mock_workspace, monkeypatch):
    root, _, _, contract = mock_workspace
    calls=[]
    monkeypatch.setattr(sources, 'get_registered_series', response_factory(contract, calls))
    output, code=op.execute_run(root)
    assert code==0
    manifest=json.loads((output/'provenance/run_manifest.json').read_text())
    assert manifest['status']=='OPTIMAL' and manifest['inputs']
    assert 'MOCK SID' in manifest['analysis_type']
    assert (output/'results.xlsx').is_file()
    assert (output/'provenance/inputs/actual_comparisons.csv').is_file()
    comparisons=pd.read_csv(output/'details/comparisons.csv')
    assert comparisons.loc[comparisons.group.eq('UK'),'model_minus_actual_bcm'].notna().all()
    assert comparisons.loc[comparisons.group.isin(['DK','Baltic Pipe']),'model_minus_actual_bcm'].isna().all()
    assert comparisons.ea_legacy_forecast_bcm.isna().all()
    # Data failure retains the exact raw source response and prevents solving.
    def bad(key,start,response):
        if key=='troll_prod': response['values']=response['values'].iloc[1:]
    monkeypatch.setattr(sources, 'get_registered_series', response_factory(contract, calls, bad))
    monkeypatch.setattr(op, 'optimise', lambda *a,**k: pytest.fail('Bad source entered optimiser'))
    failed, code=op.execute_run(root)
    assert code==2
    failure=json.loads((failed/'provenance/run_manifest.json').read_text())
    assert failure['status']=='BLOCKED_INPUTS' and failure['inputs'][0]['status']=='REJECTED'
    assert (failed/failure['inputs'][0]['raw_file']).is_file()


def test_duplicate_sid_alias_is_rejected_before_query(mock_workspace, monkeypatch):
    root, model, registry, contract=mock_workspace
    registry.at['kvitebjorn_prod','sid']=registry.at['troll_prod','sid']
    contract['sources']['kvitebjorn_prod']['sid']=registry.at['troll_prod','sid']
    (root/sources.CONTRACT).write_text(json.dumps(contract),encoding='utf-8')
    monkeypatch.setattr(sources,'get_registered_series',lambda *a,**k:pytest.fail('Duplicate SID entered retrieval'))
    with pytest.raises(ValueError,match='Duplicate production SID'):
        prep.prepare_fresh_inputs(root,model,registry,client=object())


def test_missing_evidence_keeps_failure_package(mock_workspace, monkeypatch):
    root, _, _, _=mock_workspace
    (root/sources.CONTRACT).unlink()
    monkeypatch.setattr(op,'optimise',lambda *a,**k:pytest.fail('Missing evidence entered optimiser'))
    output,code=op.execute_run(root,validate_only=True)
    assert code==2
    manifest=json.loads((output/'provenance/run_manifest.json').read_text())
    assert 'Restore the committed evidence' in manifest['blocker']
    assert (output/'results.xlsx').is_file()
