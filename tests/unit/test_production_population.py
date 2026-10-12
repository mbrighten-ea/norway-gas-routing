"""Population ownership, full-year partition and provisional-capacity safeguards."""
from copy import deepcopy

import pandas as pd
import pytest

from norway_gas_routing.config import load_config
from norway_gas_routing.forecast_inputs import provisional_capacities
from norway_gas_routing.production_population import reconcile_population,validate_ownership,population_blockers


@pytest.fixture
def population():
    rows=[('A','1','FEED','a',''),('B','3','FEED','b',''),('C','5','UNMAPPED','c',''),
          ('D','4','OUTSIDE','d',''),('GD','LNG','LNG','lng',''),('E','2','FEED','a','A')]
    ledger=pd.DataFrame(rows,columns=['component_id','classification','node','sid','represented_by'])
    ledger['classification_verified']='True'; ledger['coverage_verified']='True'
    months=pd.period_range('2024-01','2024-12',freq='M')
    observations=pd.DataFrame(1.,index=months,columns=['A','B','C','D'])
    return ledger,observations,pd.Series(4.2,index=months),pd.Series(.2,index=months)


def test_complete_partition_keeps_unmapped_outside_and_alias_separate(population):
    ledger,values,total,lng=population
    result=reconcile_population(ledger,values,total,lng,ledger.component_id,{'FEED','UNMAPPED'})
    assert result.mapped_bcm.eq(2).all()
    assert result.unmapped_bcm.eq(1).all() and result.outside_boundary_bcm.eq(1).all()
    assert result.discrepancy_bcm.abs().max()<1e-12
    total.iloc[0]+=.1
    result=reconcile_population(ledger,values,total,lng,ledger.component_id,{'FEED','UNMAPPED'})
    assert result.discrepancy_bcm.iloc[0]==pytest.approx(.1)  # not silently assigned


@pytest.mark.parametrize('case,message',[
    ('duplicate','duplicates'),('omitted','incomplete'),('sid','Duplicate production SID'),
    ('node','existing physical'),('unmapped','remain UNMAPPED'),('alias','invalid'),('calculation','ownership')])
def test_invalid_ownership_stops_before_values(population,case,message):
    ledger,_,_,_=population; expected=list(ledger.component_id)
    if case=='duplicate': ledger=pd.concat([ledger,ledger.iloc[:1]])
    if case=='omitted': ledger=ledger.iloc[:-1]
    if case=='sid': ledger.loc[1,'sid']='a'
    if case=='node': ledger.loc[1,'node']='CONVENIENT_NEW_NODE'
    if case=='unmapped': ledger.loc[2,'node']='FEED'
    if case=='alias': ledger.loc[5,'represented_by']='E'
    if case=='calculation': ledger.loc[5,'represented_by']=''
    with pytest.raises(ValueError,match=message): validate_ownership(ledger,expected,{'FEED','UNMAPPED'})


@pytest.mark.parametrize('case,message',[('gap','missing'),('negative','Signed/negative'),
    ('coverage','Unverified'),('extra','unique component owners'),('year','complete 2024')])
def test_incomplete_or_incompatible_partition_cannot_make_weights(population,case,message):
    ledger,values,total,lng=population
    if case=='gap': values.iloc[0,0]=float('nan')
    if case=='negative': values.iloc[0,0]=-.1
    if case=='coverage': ledger.loc[0,'coverage_verified']='False'
    if case=='extra': values['E']=1.
    if case=='year': values=values.iloc[:-1]
    with pytest.raises(ValueError,match=message): reconcile_population(ledger,values,total,lng,ledger.component_id,{'FEED','UNMAPPED'})


def test_real_population_explicitly_blocks_without_old_five_node_weights(repo_root,tmp_path):
    model,_=load_config(repo_root/'config/model.yaml',repo_root/'config/data_series.csv')
    nodes={node for node,entry in model['routing']['nodes'].items() if entry['kind']=='source'}
    blockers=population_blockers(repo_root,nodes,tmp_path)
    assert '41 components' in blockers[0] and 'TRYM' in blockers[0]
    ledger=pd.read_csv(tmp_path/'production_population.csv')
    assert len(ledger)==132 and ledger.component_id.nunique()==132


def test_capacity_sensitivity_keeps_19_envelopes_and_signed_maintenance_once(repo_root):
    model,_=load_config(repo_root/'config/model.yaml',repo_root/'config/data_series.csv')
    original=deepcopy(model)
    months=pd.period_range('2026-11','2027-10',freq='M')
    days=pd.date_range(months.min().start_time,months.max().end_time.normalize())
    maintenance=pd.Series(10.,index=days); maintenance.iloc[0]=-2.
    central,_=provisional_capacities(model,months,maintenance,'provisional_kollsnes_143')
    sensitivity,_=provisional_capacities(model,months,maintenance,'provisional_kollsnes_156')
    assert len(central.columns)==19 and model==original
    assert (sensitivity.KOLLSNES_EXPORT-central.KOLLSNES_EXPORT).to_numpy()==pytest.approx(months.days_in_month*13/1000)
    assert central.KOLLSNES_EXPORT.iloc[0]==pytest.approx((30*143-29*10+2)/1000)
    assert central.drop(columns='KOLLSNES_EXPORT').equals(sensitivity.drop(columns='KOLLSNES_EXPORT'))
    with pytest.raises(ValueError,match='coverage'): provisional_capacities(model,months,maintenance.iloc[1:],'provisional_kollsnes_143')
    maintenance.iloc[:13]=156.
    with pytest.raises(ValueError,match='No clipping'): provisional_capacities(model,months,maintenance,'provisional_kollsnes_143')
    provisional_capacities(model,months,maintenance,'provisional_kollsnes_156')
