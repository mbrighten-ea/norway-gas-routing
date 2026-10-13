"""Fresh, bounded F2.3 source evidence; no allocation certification or solver."""
from datetime import datetime, timezone
from pathlib import Path
import sys,json,hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.data_functions import connect_shooju,get_series,get_metadata
from norway_gas_routing.project_data import load_registry,get_registered_series,get_prospective_forecast


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def retrieve():
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    raw=ROOT/'data/raw/physical_contract_f23'/run
    raw.mkdir(parents=True,exist_ok=False)
    ledger=pd.read_csv(ROOT/'evidence/inputs/reconciled_supply_f22/production_population.csv',keep_default_na=False,dtype=str)
    registry=load_registry(); client=connect_shooju()
    origin=pd.Timestamp.now(tz='UTC').floor('s').isoformat()
    records=[]; values_by_sid={}; jobs={}
    def retain(name,sid,start,end,key=None,prospective=False,query_origin=None):
        requested_origin=query_origin or origin
        record=dict(name=name,sid=sid,start=start,end=end,origin=requested_origin if prospective else None,
            retrieved_at=datetime.now(timezone.utc).isoformat(),mode='prospective' if prospective else 'latest-revised 2024 accounting; not an origin forecast')
        try:
            if prospective:
                result=get_prospective_forecast(key,start,end,registry=registry,client=client,origin=requested_origin)
                values,meta=result['values'],result['metadata']; record['query']=result['query']
            elif key:
                result=get_registered_series(key,start,end,registry=registry,client=client)
                values,meta=result['values'],result['metadata']
            else:
                meta=get_metadata(sid,client=client)
                assert meta.get('unit')=='bcm' and meta.get('frequency')=='monthly','NPD monthly bcm contract not established'
                try:
                    values=get_series(sid,start,end,client=client)
                except KeyError:
                    # Existing helper raises 'points' for an empty native series.
                    # Confirm the empty bounded response, never replace it by zero.
                    frame=client.sj.get_df(query='sid="'+sid+'"',fields=None,max_points=-1,df=start,dt=end)
                    if not frame.empty: raise
                    record['native_empty_response_columns']=frame.columns.tolist()
                    values=pd.Series(dtype=float,index=pd.DatetimeIndex([]))
            record['metadata']=meta
            ix=pd.DatetimeIndex(values.index)
            plain=ix.tz_convert('UTC').tz_localize(None) if ix.tz is not None else ix
            assert not plain.hasnans and not plain.has_duplicates
            assert (plain>=pd.Timestamp(start)).all() and (plain<=pd.Timestamp(end)).all()
            values=pd.Series(values.to_numpy(),index=plain,name=name).sort_index()
            path=raw/(name+'.csv'); values.rename('value').rename_axis('date').to_csv(path,float_format='%.17g')
            record.update(raw_file=path.relative_to(ROOT).as_posix(),sha256=digest(path),points=len(values),
                first_date=str(values.index.min()) if len(values) else None,last_date=str(values.index.max()) if len(values) else None)
            expected=pd.date_range(start,end,freq='D' if meta.get('frequency')=='daily' else 'MS')
            record['missing_dates']=expected.difference(values.index).strftime('%Y-%m-%d').tolist()
            record['status']='EXACT_COVERAGE' if values.index.equals(expected) else 'PARTIAL_OR_EMPTY; no filling'
            try:
                updates=get_metadata(record.get('query',sid),fields=['meta.updated_at','meta.updated_by'],client=client)
                record['system_update_metadata']=updates
            except Exception as exc: record['update_error_type']=type(exc).__name__
            job=meta.get('api_obj',{}).get('snap_shooju_job_id')
            if job and job not in jobs:
                try:
                    found=client.get_active_jobs('id='+str(job),max_pages=1)
                    info=found.get(str(job),found.get(job,{})); jobs[job]={k:info.get(k) for k in ['description','created_at']}
                except Exception as exc: jobs[job]={'error_type':type(exc).__name__}
            record['import_job']=jobs.get(job)
            print(name,record['status'],len(values),flush=True)
            return values
        except Exception as exc:
            record.update(status='BLOCKED',error_type=type(exc).__name__)
            if isinstance(exc,(ValueError,AssertionError,KeyError)): record['validation_error']=str(exc)
            print(name,'BLOCKED',type(exc).__name__,flush=True)
        finally:
            records.append(record)
            (raw/'source_metadata.json').write_text(json.dumps(records,indent=2,default=str)+'\n',encoding='utf-8')
    # Reuse the existing exact SID identities. Never discover or zero-fill sources.
    for row in ledger.itertuples():
        if not row.sid or row.sid in values_by_sid: continue
        key=row.source_key if row.source_key in registry.index else None
        value=retain('historical_'+row.component_id,row.sid,'2024-01-01','2024-12-31',key=key)
        if value is not None: values_by_sid[row.sid]=value
    for key in ['norway_prod','norway_net_actual','norway_nonflex_prod','norway_prod_dashboard']:
        sid=registry.at[key,'sid']
        value=retain('historical_'+key,sid,'2024-01-01','2024-12-31',key=key)
        if value is not None: values_by_sid[sid]=value
    snohvit_native=r'NPD\monthly_by_field\marketed_production\snohvit\gas-saleable'
    retain('historical_snohvit_native',snohvit_native,'2024-01-01','2024-12-31')
    # Targeted ownership probes established in F2.3, not general SID discovery.
    for field in ['oseberg','oseberg_sor','oseberg_ost']:
        sid='NPD\\monthly_by_field\\marketed_production\\'+field+'\\gas-saleable'
        retain('historical_'+field+'_native',sid,'2024-01-01','2024-12-31')
    for key in ['norway_prod','norway_prod_dashboard','norway_nonflex_prod','snohvit_net_prod',
                'kollsnes_maint_d','kollsnes_maint_m','kollsnes_upstream_maint_d']:
        retain('prospective_'+key,registry.at[key,'sid'],'2026-11-01','2029-12-31',key=key,prospective=True)
    for key in ['snohvit_net_prod','norway_prod','norway_nonflex_prod','kollsnes_maint_d']:
        retain('october01_'+key,registry.at[key,'sid'],'2026-11-01','2029-12-31',key=key,
               prospective=True,query_origin='2026-10-01T00:00:00Z')
    manifest=dict(run_id=run,raw_directory=raw.relative_to(ROOT).as_posix(),origin=origin,
        historical_window='2024-01..2024-12',prospective_window='2026-11..2029-12',
        source_records=len(records),source_metadata_sha256=digest(raw/'source_metadata.json'),
        sid_discovery_performed=False,solver_runs=0,weights_frozen=False,operational_input_use=False,
        protected_sid_observations_read=False,
        source_search_incident='A web search preview surfaced protected 2026 production rows; none retained or consumed as numeric evidence, fitting or scoring inputs.',
        jobs=jobs)
    (raw/'manifest.json').write_text(json.dumps(manifest,indent=2,default=str)+'\n',encoding='utf-8')
    print('EVIDENCE',raw,flush=True)
    return raw


def summarise_capture(raw, output):
    """Post-process this audit's immutable capture, never prepare model inputs.

    Missing components are reported as missing. Only existing Hanz Jan/Feb
    structural-zero authority is reused. Trym observed sums are labelled partial.
    The caller must supply a new evidence directory; nothing is overwritten.
    """
    from norway_gas_routing.production_diagnostics import monthly_rate_diagnostic
    from norway_gas_routing.capacity.diagnostics import kollsnes_hypotheses
    from norway_gas_routing.routing_sources import verify_response,source_contract
    raw=Path(raw).resolve(); output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=False)
    months=pd.period_range('2024-01','2024-12',freq='M')
    def read(name):
        v=pd.read_csv(raw/(name+'.csv'),index_col='date',parse_dates=True)['value']
        if v.index.tz is not None: v.index=v.index.tz_convert('UTC').tz_localize(None)
        return v
    ledger=pd.read_csv(ROOT/'evidence/inputs/reconciled_supply_f22/production_population.csv',keep_default_na=False,dtype=str)
    metadata=json.loads((raw/'source_metadata.json').read_text())
    by_name={r['name']:r for r in metadata}
    original=ledger.loc[ledger.classification.isin(['1','3'])]
    values=[]
    for row in original.itertuples():
        v=read('historical_'+row.component_id)
        if row.source_key=='hanz_net_actual':
            spec=source_contract(ROOT)['sources'][row.source_key]
            response={'values':v,'metadata':by_name['historical_'+row.component_id]['metadata'],
                      'registry':{'key':row.source_key,'sid':row.sid}}
            v=verify_response(row.source_key,response,spec,months.to_timestamp(),'monthly')
        assert len(v)==12 and v.notna().all()
        v.index=months; values.append(v)
    extra=[]; inventory=[]
    for row in ledger.itertuples():
        record=by_name.get('historical_'+row.component_id,{})
        path=raw/('historical_'+row.component_id+'.csv')
        v=read('historical_'+row.component_id) if path.exists() else pd.Series(dtype=float)
        complete=len(v)==12 and v.notna().all()
        if row.classification in {'2','5'} and complete: extra.append(v.set_axis(months))
        category={'1':'explicit_forecast_mapped','3':'historically_observed_mapped_residual',
                  'LNG':'outside_pipeline_boundary_LNG'}.get(row.classification,'unresolved_component_candidate')
        candidate_node=''; decision='Existing evidence only; no prospective certification'
        if row.component_id=='CL':
            category='observed_export_eligible_mapping_candidate'; candidate_node='KARSTO_FEED'
            decision='Statpipe gas path verified; rich-to-saleable boundary requires approval'
        if row.component_id=='ER':
            category='observed_export_eligible_mapping_candidate'; candidate_node='OSEBERG'
            decision='Corresponding Oseberg sales-gas entitlement; overlap/ownership not yet certified'
        if row.component_id=='FD':
            category='signed_export_accounting_candidate'; candidate_node='UK_DIRECT'
            decision='Alvheim/SAGE path verified; signed May accounting requires owner explanation'
        if row.component_id=='EQ':
            category='verified_outside_existing_network'; candidate_node='OUTSIDE Harald/Tyra'
            decision='Norwegian field marketed gas through Danish network; Jan-Oct unavailable, no zero fill'
        if row.classification=='2':
            category='group_or_calculation_slot_not_independent_source'
            decision='Do not sum independently; complete child memberships/overlap still unresolved'
        inventory.append(dict(component_id=row.component_id,field=row.field,sid=row.sid,
            existing_classification=row.classification,existing_node=row.node,
            evidence_category=category,candidate_node=candidate_node,decision=decision,
            observed_months=len(v),coverage_complete=complete,
            observed_sum_bcm=float(v.sum()) if len(v) and row.classification!='LNG' else None,
            raw_unit=record.get('metadata',{}).get('unit',''),
            missing_months=';'.join(months.to_timestamp().difference(v.index).strftime('%Y-%m')) if len(v) else ';'.join(map(str,months)),
            activated=False))
    pd.DataFrame(inventory).to_csv(output/'component_inventory.csv',index=False)
    if (raw/'historical_oseberg_native.csv').exists():
        ownership=pd.DataFrame({'ea_oseberg_group_bcm':read('historical_Q'),
            'npd_oseberg_bcm':read('historical_oseberg_native'),
            'npd_oseberg_sor_bcm':read('historical_oseberg_sor_native'),
            'npd_oseberg_ost_bcm':read('historical_oseberg_ost_native'),
            'npd_tune_separate_bcm':read('historical_ER')})
        ownership['oseberg_owner_discrepancy_bcm']=ownership.ea_oseberg_group_bcm-ownership[
            ['npd_oseberg_bcm','npd_oseberg_sor_bcm','npd_oseberg_ost_bcm']].sum(axis=1)
        ownership.to_csv(output/'oseberg_component_ownership_2024.csv',index_label='month')
    converted=monthly_rate_diagnostic(read('historical_GD'),months)
    native=read('historical_snohvit_native').set_axis(months)
    assert (converted-native.round(5)).abs().max()<1e-12
    national=read('historical_norway_prod').set_axis(months)
    accounting=pd.DataFrame({'ea_national_bcm':national,
        'npd_national_bcm':read('historical_norway_net_actual').set_axis(months),
        'original62_bcm':pd.concat(values,axis=1).sum(axis=1),
        'additional28_complete_bcm':pd.concat(extra,axis=1).sum(axis=1),
        'snohvit_legacy_converted_bcm':converted,'snohvit_native_bcm':native,
        'trym_observed_bcm':read('historical_EQ').set_axis(read('historical_EQ').index.to_period('M'))})
    accounting['f22_gap_bcm']=national-accounting.original62_bcm-accounting.additional28_complete_bcm-converted
    accounting['snohvit_precision_difference_bcm']=converted-native
    accounting['native_basis_remaining_before_trym_bcm']=national-accounting.original62_bcm-accounting.additional28_complete_bcm-native
    accounting['observed_trym_month_discrepancy_bcm']=accounting.native_basis_remaining_before_trym_bcm-accounting.trym_observed_bcm
    accounting['ea_minus_npd_total_bcm']=national-accounting.npd_national_bcm
    accounting.to_csv(output/'monthly_accounting_2024.csv',index_label='month',float_format='%.12g')
    future=pd.period_range('2026-11','2029-12',freq='M')
    sn=monthly_rate_diagnostic(read('prospective_snohvit_net_prod'),future)
    sn_table=pd.DataFrame({'raw_hypothesised_mcmd':read('prospective_snohvit_net_prod').set_axis(future),
        'calendar_days':future.days_in_month,'diagnostic_converted_bcm':sn,
        'national_bcm':read('prospective_norway_prod').set_axis(future),
        'hypothetical_national_minus_LNG_bcm':read('prospective_norway_prod').set_axis(future)-sn,
        'operationally_approved':False})
    sn_table.to_csv(output/'snohvit_conversion_diagnostic.csv',index_label='month')
    capacity_summary={}
    for label,prefix in [('current_capture','prospective'),('october01_archive','october01')]:
        if not (raw/(prefix+'_kollsnes_maint_d.csv')).exists(): continue
        daily,monthly=kollsnes_hypotheses(read(prefix+'_kollsnes_maint_d'),'2026-11-01','2029-12-31')
        daily.to_csv(output/(label+'_capacity_daily.csv'),index_label='date')
        monthly.to_csv(output/(label+'_capacity_monthly.csv'),index_label='month')
        capacity_summary[label]=monthly.select_dtypes('number').sum().to_dict()
    result=dict(status='BLOCKED_INPUTS',forecast_activated=False,weights_frozen=False,
        historical_allocation_certified=False,dual_capacity_activated=False,
        target_start='2026-11',target_end='2029-12',months=38,
        annual_observed_subtotals_bcm=accounting.sum().to_dict(),
        annual_sn_diagnostic_bcm=sn.groupby(sn.index.year).sum().to_dict(),
        capacity_diagnostics=capacity_summary,
        interpretation='Observed partial sums are not complete annual source volumes; no missing-to-zero.',
        capture=raw.relative_to(ROOT).as_posix(),capture_metadata_sha256=digest(raw/'source_metadata.json'))
    (output/'assessment.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    capture=retrieve()
    summarise_capture(capture,capture/'diagnostics')
