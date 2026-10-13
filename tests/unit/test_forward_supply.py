"""Synthetic ownership and conservation checks for the approved provisional path."""
import pandas as pd
import pytest

from norway_gas_routing.forward_supply import residual_weights,allocate_forward
from norway_gas_routing.capacity.forward import approved_capacities
from norway_gas_routing.config import load_config


@pytest.mark.parametrize('case',['unchanged','node','sid','identity','class','missing','duplicate'])
def test_evidence_cannot_reassign_reviewed_physical_owner(repo_root,case):
    from norway_gas_routing.forward_supply import verify_original_owners
    from norway_gas_routing.routing_sources import source_requirements
    model,registry=load_config(repo_root/'config/model.yaml',repo_root/'config/data_series.csv')
    _,components,contract=source_requirements(repo_root,model,registry)
    ledger=pd.read_csv(repo_root/'evidence/inputs/reconciled_supply_f22/production_population.csv',dtype=str,keep_default_na=False)
    selected=ledger.loc[ledger.classification.isin(['1','3'])].reset_index(drop=True)
    if case=='node': selected.loc[0,'node']='UK_DIRECT'
    if case=='sid': selected.loc[0,'sid']='other'
    if case=='identity': selected.loc[0,'component_id']='FAKE'
    if case=='class': selected.loc[0,'classification']='3'
    if case=='missing': selected=selected.iloc[:-1]
    if case=='duplicate': selected.loc[1,'source_key']=selected.loc[0,'source_key']
    if case=='unchanged': verify_original_owners(selected,components,registry,contract)
    else:
        with pytest.raises(ValueError): verify_original_owners(selected,components,registry,contract)


def test_representative_physical_ranges_keep_export_basis(repo_root):
    from norway_gas_routing.operational import synthetic_inputs,optimise
    from norway_gas_routing.routing import network_definition,available_solver
    from norway_gas_routing.forward_diagnostics import representative_ranges
    model,_=load_config(repo_root/'config/model.yaml',repo_root/'config/data_series.csv')
    model['routing'].update(start='2026-11',end='2026-11')
    inputs=synthetic_inputs(model); network=network_definition(model['routing'])
    selected,results,_=optimise(inputs,network,None)
    _,solver=available_solver(selected)
    ranges=representative_ranges(inputs,results,network,solver)
    assert len(ranges)==7
    assert ranges.range_width_bcm.gt(0).all()
    assert (ranges.minimum_bcm<=ranges.model_bcm+1e-8).all()
    assert (ranges.maximum_bcm>=ranges.model_bcm-1e-8).all()
    assert ranges.fixed_exports_bcm.to_numpy()==pytest.approx([sum(results['2026-11']['destinations'].values())]*7)


@pytest.fixture
def fixture(repo_root):
    model,registry=load_config(repo_root/'config/model.yaml',repo_root/'config/data_series.csv')
    import json
    contract=json.loads((repo_root/'evidence/inputs/routing_sources_b1/verified_sources.json').read_text())
    membership={k:next(row.node for row in pd.read_csv(repo_root/'evidence/inputs/reconciled_supply_f22/production_population.csv').itertuples() if row.source_key==k)
                for k in contract['component_columns']}
    owners=pd.DataFrame([dict(component_id=contract['component_columns'][k],sid=k,node=n,role='explicit',annual_bcm=1.) for k,n in membership.items()]+
        [dict(component_id='RES',sid='residual',node='KARSTO_FEED',role='residual',annual_bcm=2.),
         dict(component_id='EQ',sid='trym',node='EXTERNAL_TRYM',role='residual',annual_bcm=.001)])
    weights=residual_weights(owners,18.701,.7)
    months=pd.period_range('2026-11','2029-12',freq='M')
    fields=pd.DataFrame(.1,index=months,columns=membership)
    fields.heidrun_prod=pd.Series([.1+i/1000 for i in range(38)],index=months)
    snohvit=pd.Series(.2,index=months); national=fields.sum(axis=1)+snohvit+2.001
    nodes=[n for n,e in model['routing']['nodes'].items() if e['kind']=='source']
    return model,owners,weights,fields,national,snohvit,membership,nodes


def test_all38_national_balances_and_heidrun_independent_of_residual(fixture):
    _,_,weights,fields,national,snohvit,membership,nodes=fixture
    a,ra=allocate_forward(fields,national,snohvit,weights,membership,nodes,'export_eligible')
    b,rb=allocate_forward(fields,national,snohvit,weights,membership,nodes,'domestic_bound')
    assert len(a)==38 and ra.national_balance_residual_bcm.abs().max()<1e-12
    assert rb.national_balance_residual_bcm.abs().max()<1e-12
    assert (ra.residual_bcm-rb.residual_bcm).abs().max()<1e-12
    assert (ra.external_trym_bcm-rb.external_trym_bcm).abs().max()<1e-12
    assert (a.KARSTO_FEED-b.KARSTO_FEED-fields.heidrun_prod).abs().max()<1e-12
    assert (rb.hypothetical_domestic_bcm-fields.heidrun_prod).abs().max()<1e-12
    assert a.UNMAPPED.eq(0).all() and a.ge(0).all().all()


@pytest.mark.parametrize('case',['duplicate_sid','duplicate_owner','heidrun_residual','negative_annual','unclosed'])
def test_invalid_frozen_ownership_cannot_allocate(fixture,case):
    _,owners,*_=fixture; owners=owners.copy()
    if case=='duplicate_sid': owners.loc[16,'sid']=owners.loc[0,'sid']
    if case=='duplicate_owner': owners.loc[16,'component_id']=owners.loc[0,'component_id']
    if case=='heidrun_residual': owners.loc[owners.component_id.eq('AQ'),'role']='residual'
    if case=='negative_annual': owners.loc[16,'annual_bcm']=-2
    if case=='unclosed': owners.loc[16,'annual_bcm']=3
    with pytest.raises(ValueError): residual_weights(owners,18.701,.7)


def test_unknown_production_stays_unmapped_and_unrouted(fixture):
    _,_,weights,fields,national,snohvit,membership,nodes=fixture
    weights=weights.copy(); weights.loc[weights.component_id.eq('RES'),'node']='UNMAPPED'
    supply,r=allocate_forward(fields,national,snohvit,weights,membership,nodes,'export_eligible')
    assert supply.UNMAPPED.to_numpy()==pytest.approx([2.]*38)
    assert r.network_coverage_pct.lt(100).all()


def test_negative_monthly_residual_not_clipped(fixture):
    _,_,weights,fields,national,snohvit,membership,nodes=fixture
    national.iloc[0]=.1
    with pytest.raises(ValueError): allocate_forward(fields,national,snohvit,weights,membership,nodes,'export_eligible')


def test_reference_and_stress_apply_unavailability_once(fixture):
    model,*_=fixture; months=pd.period_range('2027-09',periods=1,freq='M')
    u=pd.Series(0.,index=pd.date_range('2027-09-01','2027-09-30')); u.iloc[:13]=156
    a,_,_=approved_capacities(model,months,u,'core_f24_156')
    c,_,_=approved_capacities(model,months,u,'core_f24_proportional_143')
    assert a.KOLLSNES_EXPORT.iloc[0]==pytest.approx(17*156/1000)
    assert c.KOLLSNES_EXPORT.iloc[0]==pytest.approx(17*143/1000)
    for col in a.columns.drop('KOLLSNES_EXPORT'): assert a[col].equals(c[col])


@pytest.mark.parametrize('case',['gap','negative','above156','nan'])
def test_invalid_maintenance_blocks(fixture,case):
    model,*_=fixture; months=pd.period_range('2027-09',periods=1,freq='M')
    u=pd.Series(0.,index=pd.date_range('2027-09-01','2027-09-30'))
    if case=='gap': u=u.iloc[:-1]
    else: u.iloc[0]={'negative':-1,'above156':157,'nan':float('nan')}[case]
    with pytest.raises(ValueError): approved_capacities(model,months,u,'core_f24_156')
