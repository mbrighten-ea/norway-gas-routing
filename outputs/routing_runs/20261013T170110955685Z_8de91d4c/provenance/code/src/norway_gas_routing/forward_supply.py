"""Core-approved F2.4 annual ownership and partial-coverage physical supplies."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from .routing import DESTINATIONS, finite_nonnegative, historical_preferences
from .routing_sources import retrieve_checked, field_identity
from .project_data import get_registered_series
from .data_functions import get_series, get_metadata
from .evaluation import check_dates
from .production_diagnostics import monthly_rate_diagnostic

CONTRACT = 'core_f24'
EXTRA = {'CL': ('brage_net_actual', 'KARSTO_FEED'),
         'ER': ('tune_net_actual', 'OSEBERG'),
         'FD': ('vilje_net_actual', 'UK_DIRECT'),
         'EQ': ('trym_net_actual', 'EXTERNAL_TRYM')}
APPROVED = {'national':126.231133, 'original62':119.377524,
            'additional28':.426406, 'trym':.020461, 'snohvit':6.406742}


def verify_original_owners(selected,components,registry,contract):
    """A mutable evidence row cannot move a field to another physical entry."""
    assigned={key:node for node,keys in components.items() for key in keys}
    columns={**contract['component_columns'],**{v['key']:c for c,v in contract['historical_components'].items()}}
    if len(selected)!=62 or selected.source_key.duplicated().any() or set(selected.source_key)!=set(assigned):
        raise ValueError('Original owner population changed or duplicates sources.')
    for row in selected.itertuples():
        expected_class='1' if row.source_key in contract['component_columns'] else '3'
        if (row.node!=assigned[row.source_key] or row.sid!=registry.at[row.source_key,'sid']
                or row.component_id!=columns[row.source_key] or row.classification!=expected_class):
            raise ValueError(row.component_id+': original physical ownership differs from reviewed source contract.')


def residual_weights(owners, national, snohvit):
    """Annual signed accounting, one owner per SID; no monthly missing-to-zero.

    The approved annual certificate accepts Trym's observed two-month subtotal.
    It does not declare missing monthly observations to be zero. Unknown/group
    slots outside this certificate are never independent addends or mapped fields.
    """
    if owners.sid.duplicated().any() or owners.component_id.duplicated().any():
        raise ValueError('Duplicate production ownership.')
    explicit=owners.loc[owners.role.eq('explicit')]
    if len(explicit)!=16 or 'AQ' not in set(explicit.component_id):
        raise ValueError('Exactly sixteen explicit owners including Heidrun required.')
    denominator=national-snohvit-explicit.annual_bcm.sum()
    residual=owners.loc[owners.role.eq('residual')].copy()
    finite_nonnegative(residual.annual_bcm,'Signed annual residual owners')
    if denominator<=0: raise ValueError('Nonpositive matching residual denominator.')
    unexplained=denominator-residual.annual_bcm.sum()
    if abs(unexplained)>1e-9:
        raise ValueError('Approved annual residual identity does not close; no balancing adjustment.')
    residual['denominator_bcm']=denominator
    residual['weight']=residual.annual_bcm/denominator
    return residual


def allocate_forward(fields, national, snohvit, weights, membership, nodes, heidrun):
    """R uses all 16 fields before the independent domestic boundary scenario."""
    if (set(fields.columns)!=set(membership) or len(fields.columns)!=16
            or not fields.index.equals(national.index) or not snohvit.index.equals(national.index)):
        raise ValueError('Exact explicit field/month ownership required.')
    finite_nonnegative(fields.to_numpy().ravel(),'Forward explicit fields')
    finite_nonnegative(snohvit,'Converted forward LNG')
    pipeline=national-snohvit
    residual=pipeline-fields.sum(axis=1)
    finite_nonnegative(residual,'Forward residual; no clipping or unexplained negative residual')
    if heidrun not in {'export_eligible','domestic_bound'}:
        raise ValueError('Explicit Heidrun boundary treatment required.')
    if weights.weight.lt(0).any() or abs(weights.weight.sum()-1)>1e-9:
        raise ValueError('Frozen residual weights must be nonnegative and sum to one.')
    supply=pd.DataFrame(0.,index=fields.index,columns=list(nodes))
    for key,node in membership.items():
        supply[node]+=fields[key]
    outside=pd.Series(0.,index=fields.index)
    for row in weights.itertuples():
        packet=residual*row.weight
        if row.node=='EXTERNAL_TRYM': outside+=packet
        elif row.node in supply: supply[row.node]+=packet
        else: raise ValueError('Unsupported physical residual assignment: '+row.node)
    domestic=fields.heidrun_prod if heidrun=='domestic_bound' else pd.Series(0.,index=fields.index)
    supply[membership['heidrun_prod']]-=domestic
    finite_nonnegative(supply.to_numpy().ravel(),'Physical injection; annual signed weights only')
    mapped=supply.drop(columns='UNMAPPED').sum(axis=1)
    reconciliation=pd.DataFrame(dict(national_production_bcm=national,snohvit_bcm=snohvit,
        pipeline_supply_bcm=pipeline,explicit16_bcm=fields.sum(axis=1),residual_bcm=residual,
        heidrun_forecast_bcm=fields.heidrun_prod,hypothetical_domestic_bcm=domestic,
        external_trym_bcm=outside,mapped_supply_bcm=mapped,unmapped_supply_bcm=supply.UNMAPPED,
        export_eligible_bcm=pipeline-outside-domestic))
    reconciliation['national_balance_residual_bcm']=national-snohvit-outside-domestic-supply.sum(axis=1)
    if reconciliation.national_balance_residual_bcm.abs().max()>1e-9:
        raise ValueError('Forward national accounting does not close.')
    reconciliation['network_coverage_pct']=mapped/reconciliation.export_eligible_bcm*100
    reconciliation['pipeline_boundary_coverage_pct']=mapped/pipeline*100
    return supply,reconciliation


def prepare_approved_inputs(root,model,registry,request,candidates,records,components,contract,client):
    """Consume fresh SID responses within this run; no workbook/cache fallback."""
    root=Path(root); output=Path(request['_provenance_dir'])
    months=pd.period_range(request['start'],request['end'],freq='M')
    historical=pd.period_range('2024-01','2024-12',freq='M')
    ledger=pd.read_csv(root/'evidence/inputs/reconciled_supply_f22/production_population.csv',dtype=str,keep_default_na=False)
    selected=ledger.loc[ledger.classification.isin(['1','3'])]
    verify_original_owners(selected,components,registry,contract)
    owners=[]; original={}
    for row in selected.itertuples():
        v=retrieve_checked(root,row.source_key,historical.to_timestamp(),registry,contract,records,output,client=client)
        original[row.component_id]=v
        owners.append(dict(component_id=row.component_id,field=row.field,sid=row.sid,node=row.node,
            role='explicit' if row.classification=='1' else 'residual',annual_bcm=float(v.sum()),
            observed_months=12-len(records[-1].get('structural_zero_dates',[])),
            approved_structural_zero_months=len(records[-1].get('structural_zero_dates',[])),
            accounting='Oseberg aggregate owns Oseberg/Sor/Ost; Tune separate' if row.component_id=='Q' else
            'Explicit Heidrun owner; never residual' if row.component_id=='AQ' else 'Existing approved independent owner'))
    def native(component,key=None,sid=None,partial=False):
        check_dates(historical,'read')
        try:
            if key:
                response=get_registered_series(key,'2024-01-01','2024-12-31',registry=registry,client=client)
                v,meta=response['values'],response['metadata']; sid=registry.at[key,'sid']
            else:
                v=get_series(sid,'2024-01-01','2024-12-31',client=client); meta=get_metadata(sid,client=client)
        except Exception as exc:
            raise ValueError(component+': approved historical source unavailable ('+type(exc).__name__+'); no fallback or missing-to-zero.') from None
        dates=pd.DatetimeIndex(v.index)
        if dates.tz is not None: dates=dates.tz_convert('UTC').tz_localize(None)
        v=pd.Series(v.to_numpy(),index=dates).sort_index()
        check_dates(v.index,'read')
        if (meta.get('unit')!='bcm' or meta.get('frequency')!='monthly'
                or meta.get('lifecycle_stage') not in {'actual','historical'}
                or meta.get('country_iso')!='NO'
                or meta.get('ea_production_type')!='marketed_production'
                or meta.get('source_obj',{}).get('aspect')!='gas-saleable'
                or meta.get('source_obj',{}).get('units')!='bill Sm3'):
            raise ValueError(component+': incompatible native saleable definition.')
        expected=historical.to_timestamp()
        if partial: expected=pd.to_datetime(['2024-11-01','2024-12-01'])
        if not v.index.equals(expected) or not v.map(lambda x: pd.notna(x) and abs(x)!=float('inf')).all():
            raise ValueError(component+': approved observed coverage changed; no filling.')
        expected_field=field_identity(sid.split('\\')[-2])
        if field_identity(meta.get('ea_field_name_standardised',''))!=expected_field:
            raise ValueError('Native production ownership changed.')
        path=output/'raw'/('owner_'+component+'_2024.csv')
        if path.exists(): raise ValueError('Historical raw capture already exists.')
        v.rename('value').rename_axis('date').to_csv(path,float_format='%.17g')
        records.append(dict(key=key or component,sid=sid,kind='frozen_2024_owner',metadata=meta,
            status='CORE_APPROVED_ANNUAL_OBSERVED_SUBTOTAL' if partial else 'VERIFIED_2024_OWNER',
            raw_file=path.relative_to(output.parent).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            observed_months=len(v),missing_months=historical.to_timestamp().difference(v.index).strftime('%Y-%m').tolist(),
            transformation='Signed monthly bcm; annual net sum. No missing-to-zero.',available_at=None))
        return v
    for component,(key,node) in EXTRA.items():
        row=ledger.loc[ledger.component_id.eq(component)].iloc[0]
        v=native(component,key if key in registry.index else None,sid=row.sid,partial=component=='EQ')
        owners.append(dict(component_id=component,field=row.field,sid=row.sid,node=node,
            role='residual',annual_bcm=float(v.sum()),observed_months=len(v),
            accounting='Approved observed annual subtotal; missing Trym months not filled' if component=='EQ' else 'Unique signed annual owner; Vilje May negative retained'))
    # Refresh the 25 complete zero-response owners too. Empty sources are never
    # inserted here: this cohort had twelve explicit 2024 zero observations.
    complete_extra=ledger.loc[ledger.classification.eq('5') & ledger.coverage_verified.eq('True')
                             & ~ledger.component_id.isin(EXTRA)]
    if len(complete_extra)!=25: raise ValueError('Approved additional zero-owner cohort changed.')
    for row in complete_extra.itertuples():
        v=native(row.component_id,sid=row.sid)
        if v.ne(0).any(): raise ValueError('Approved zero-response owner changed: '+row.field)
        owners.append(dict(component_id=row.component_id,field=row.field,sid=row.sid,node='UNMAPPED',
            role='residual',annual_bcm=0.,observed_months=12,accounting='Twelve explicit source zeros; unknown entry not routed'))
    snohvit_native=native('GD',sid=r'NPD\monthly_by_field\marketed_production\snohvit\gas-saleable')
    total=retrieve_checked(root,'norway_prod',historical.to_timestamp(),registry,contract,records,output,client=client)
    owners=pd.DataFrame(owners)
    observed=dict(national=float(total.sum()),original62=float(sum(v.sum() for v in original.values())),
        additional28=float(owners.loc[owners.component_id.isin(['CL','ER','FD']),'annual_bcm'].sum()),
        trym=float(owners.loc[owners.component_id.eq('EQ'),'annual_bcm'].iloc[0]),snohvit=float(snohvit_native.sum()))
    for key,value in APPROVED.items():
        if abs(observed[key]-value)>1e-9:
            raise ValueError('Core-approved annual '+key+' ledger changed; no revised reallocation.')
    weights=residual_weights(owners,observed['national'],observed['snohvit'])
    all_owners=pd.concat([owners,pd.DataFrame([dict(component_id='GD',field='Snohvit',
        sid=r'NPD\monthly_by_field\marketed_production\snohvit\gas-saleable',node='OUTSIDE_LNG',
        role='LNG',annual_bcm=observed['snohvit'],observed_months=12,
        accounting='Single LNG owner; prospective driver is selected converted SID, not additional supply')])],ignore_index=True)
    all_owners.to_csv(output/'frozen_2024_owners.csv',index=False)
    weights.to_csv(output/'frozen_residual_weights.csv',index=False)
    omitted=ledger.loc[~ledger.component_id.isin(owners.component_id) & ledger.component_id.ne('GD')].copy()
    omitted['accounting']='Outside approved annual summation; empty/partial/zero/group slots not independent new supply. No missing observations filled.'
    omitted.to_csv(output/'population_scope.csv',index=False)
    membership={key:node for node,keys in components.items() for key in keys
                if contract['sources'][key].get('provider_contract')!='npd_historical'}
    fields=pd.DataFrame({key:candidates[key].set_axis(months) for key in membership})
    national=candidates['norway_prod'].set_axis(months)
    snohvit=monthly_rate_diagnostic(candidates['snohvit_net_prod'],months)
    next(r for r in records if r['key']=='snohvit_net_prod').update(
        status='CORE_APPROVED_FORECAST_CONVERSION',target_unit='bcm/month',
        transformation='Core-approved monthly-average mcm/day * calendar days / 1000; declared bcm label retained in raw metadata; mixed vintage disclosed')
    nodes=[n for n,e in model['routing']['nodes'].items() if e['kind']=='source']
    supply,reconciliation=allocate_forward(fields,national,snohvit,weights,membership,nodes,request['heidrun_treatment'])
    excluded_uk_ids=['EB','FD','FF','CK','FS','CG']
    reconciliation['legacy_excluded_uk_direct_bcm']=fields.martin_linge_prod+reconciliation.residual_bcm*weights.loc[weights.component_id.isin(excluded_uk_ids),'weight'].sum()
    reconciliation['legacy_duplicate_rev_proxy_bcm']=reconciliation.residual_bcm*weights.loc[weights.component_id.eq('EB'),'weight'].sum()
    from .capacity.forward import approved_capacities
    capacities,daily,monthly=approved_capacities(model,months,candidates['kollsnes_maint_d'],request['capacity_scenario'])
    training=pd.period_range(model['routing']['baseline_start'],model['routing']['baseline_end'],freq='M')
    observations=pd.DataFrame({d:retrieve_checked(root,d.lower()+'_flow_qa',training.to_timestamp(),registry,
        contract,records,output,client=client).set_axis(training) for d in DESTINATIONS})
    preferences,excluded=historical_preferences(observations)
    # Optional future forecast comparisons use the prospective adapter, never the
    # guarded historical actual-reference reader. Their absence is not supply.
    from .forecast_inputs import inspect_forecast_source
    legacy={}; legacy_status={}
    for group,key in {'UK':'uk_flow_qa','FR+BE':'fr_be_flow_qa','NL+DE':'nl_de_flow_qa','total':'norway_exports_qa'}.items():
        try:
            legacy[group]=inspect_forecast_source(root,key,months.to_timestamp(),registry,contract,
                records,output,request['origin'],client).set_axis(months)
            legacy_status[group]='Origin-matched legacy Gassco group; boundary-adjusted descriptive comparison, not forecast scoring'
            if group=='UK': legacy_status[group]+='; exclude only lineage-supported non-Gassco UK packets once. Legacy duplicate Rev deduction is disclosed, never applied to operational supply.'
        except (ValueError,OSError,KeyError) as exc:
            legacy_status[group]='Unavailable: '+str(exc)
    records.append(dict(key='core_f24',kind='approved_provisional_contract',status='CORE_APPROVED_PROVISIONAL',
        historical_accounting=observed,raw_unit='selected Snohvit mislabelled bcm; approved interpretation monthly-average mcm/day',
        transformation='Snohvit rate*calendar_days/1000; frozen annual mutually exclusive residual owners; external Trym separate; no NPD national adjustment',
        mixed_vintage_limitation='Selected LNG October-2025 import versus current national/component forecast snapshot; Core-approved provisional compatibility, not identical publication vintages',
        heidrun_treatment=request['heidrun_treatment'],capacity_scenario=request['capacity_scenario'],
        capacity_status='156 provisional technical availability; dry-export reference not fully verified; other envelopes unchanged; no upstream subtraction',
        boundary_status='Partial-coverage physical routing experiment; frozen residual proxy is not field-specific future certification'))
    if 'total' in legacy: reconciliation['legacy_gassco_total_bcm']=legacy['total']
    result=dict(months=months,supply=supply,capacities=capacities,capacity_daily=daily,capacity_monthly=monthly,
        training_observations=observations,preferences=preferences,excluded_training_months=excluded,
        reconciliation=reconciliation,provenance=records,approved_contract=CONTRACT,
        legacy_forecasts=pd.DataFrame(legacy,index=months),legacy_status=legacy_status)
    return result
