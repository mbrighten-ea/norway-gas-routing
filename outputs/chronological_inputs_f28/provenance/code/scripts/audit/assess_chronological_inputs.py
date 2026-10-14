"""Bounded F2.8 archive audit of existing owners, not field discovery or scoring."""
from pathlib import Path
from datetime import datetime, timezone
import sys, json, hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.data_functions import connect_shooju,get_metadata,get_series
from norway_gas_routing.evaluation import check_dates
from norway_gas_routing.seasonal_snohvit import retrieve_seasonal_snohvit
from norway_gas_routing.project_data import load_registry, get_prospective_forecast
from norway_gas_routing.production_diagnostics import monthly_rate_diagnostic


def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    raw=ROOT/'data/raw/chronological_inputs_f28'/stamp
    raw.mkdir(parents=True,exist_ok=False)
    retained=ROOT/'outputs/routing_runs/20261013T165918528411Z_87c4eb40/provenance'
    owners=pd.read_csv(retained/'frozen_2024_owners.csv',keep_default_na=False)
    registry=load_registry(); client=connect_shooju(); records=[]
    national_sid=registry.at['norway_prod','sid']
    origins={'current':'2026-10-13T16:59:13Z','historical':'2024-12-31T23:59:59Z'}
    values={}; origin_records={}
    def retrieve(name,sid,start,end,origin):
        check_dates([start,end],'read')
        q='sid="'+sid+'"@asof:'+pd.Timestamp(origin).strftime('%Y-%m-%dT%H:%M:%S')
        r=dict(name=name,sid=sid,query=q,asof=origin,start=start,end=end,
            retrieved_at=datetime.now(timezone.utc).isoformat(),information_date_basis='Exact archived service state, not later-revised observations')
        try:
            try:m=get_metadata(q,client=client)
            except KeyError:
                f=client.sj.get_df(query=q,fields=['series_id'],max_points=-1,df=start,dt=end)
                r.update(empty_archive_confirmed=f.empty,response_rows=len(f),response_columns=f.columns.tolist())
                raise ValueError('No archived source metadata/points at the information origin; no later-revised substitution') from None
            r['metadata']=m
            try:v=get_series(q,start,end,client=client)
            except KeyError:
                f=client.sj.get_df(query=q,fields=['series_id'],max_points=-1,df=start,dt=end)
                if len(f):raise ValueError('Unexpected point schema; response not confirmed empty')
                v=pd.Series(dtype=float,index=pd.DatetimeIndex([]))
                r['empty_response_columns']=f.columns.tolist()
            ix=pd.DatetimeIndex(pd.to_datetime(v.index,utc=True)).tz_localize(None)
            check_dates(ix,'read')
            if ix.has_duplicates or ((ix<pd.Timestamp(start)) | (ix>pd.Timestamp(end))).any():
                raise ValueError('Unexpected/duplicate archived dates')
            v=pd.Series(v.to_numpy(),index=ix,name='value').sort_index()
            p=raw/(name+'.csv');v.rename_axis('date').to_csv(p,float_format='%.17g')
            expected=pd.date_range(start,end,freq='MS')
            r.update(raw_file=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                points=len(v),missing_months=expected.difference(ix).strftime('%Y-%m').tolist(),
                negative_months=v.loc[v.lt(0)].index.strftime('%Y-%m').tolist(),observed_sum_bcm=float(v.sum()) if len(v) else None,
                status='EXACT_COVERAGE' if ix.equals(expected) and v.notna().all() else 'PARTIAL_OR_EMPTY; no filling')
            values[name]=v
        except Exception as e:
            r.update(status='BLOCKED',error_type=type(e).__name__)
            if isinstance(e,ValueError):r['validation_error']=str(e)
        records.append(r)
        (raw/'source_metadata.json').write_text(json.dumps(records,default=str,indent=2)+'\n',encoding='utf-8')
        print(name,r['status'],r.get('points'),flush=True)
        return r
    for case,origin in origins.items():
        start,end=('2025-01-01','2025-12-31') if case=='current' else ('2023-01-01','2024-11-30')
        rr=[]
        for row in owners.itertuples():
            rr.append(retrieve(case+'_'+row.component_id,row.sid,start,end,origin))
        rr.append(retrieve(case+'_national',national_sid,start,end,origin))
        # Three known children verify EA Oseberg aggregate ownership; never add
        # them independently to the owner ledger.
        for field in ['oseberg','oseberg_sor','oseberg_ost']:
            rr.append(retrieve(case+'_'+field,'NPD\\monthly_by_field\\marketed_production\\'+field+r'\gas-saleable',start,end,origin))
        if case=='current':
            population=pd.read_csv(ROOT/'evidence/inputs/reconciled_supply_f22/production_population.csv',keep_default_na=False)
            # Existing named 2025 developments only: diagnose the missing
            # annual boundary; their observations are not activated as weights.
            for cid in ['GK','GR','GT']:
                row=population.loc[population.component_id.eq(cid)].iloc[0]
                rr.append(retrieve('priority_'+cid,row.sid,start,end,origin))
            rr.append(retrieve('priority_norne_native',r'NPD\monthly_by_field\marketed_production\norne\gas-saleable',start,end,origin))
            rr.append(retrieve('priority_national_native',registry.at['norway_net_actual','sid'],start,end,origin))
        origin_records[case]=rr
        directory=raw/(case+'_seasonal'); directory.mkdir()
        sr=[]
        try:
            months=pd.period_range('2026-11','2029-12',freq='M') if case=='current' else pd.period_range('2025-01','2025-12',freq='M')
            seasonal=retrieve_seasonal_snohvit(months,origin,sr,directory,client)
            if case=='current':
                response=get_prospective_forecast('snohvit_net_prod','2026-11-01','2029-12-31',registry=registry,client=client,origin=origin)
                response['values'].rename('value').rename_axis('date').to_csv(directory/'sid_forecast_raw.csv',float_format='%.17g')
                sid_forecast=monthly_rate_diagnostic(response['values'],months)
                table=pd.DataFrame(dict(seasonal_bcm=seasonal,sid_forecast_bcm=sid_forecast))
                table['difference_bcm']=table.seasonal_bcm-table.sid_forecast_bcm
                table.rename_axis('month').to_csv(directory/'comparison.csv')
                (directory/'sid_forecast_metadata.json').write_text(json.dumps({k:v for k,v in response.items() if k!='values'},default=str,indent=2)+'\n',encoding='utf-8')
        except Exception as e:
            print(case,'seasonal BLOCKED',type(e).__name__,flush=True)
        origin_records[case+'_seasonal']=sr
    summary=dict(origins=origins,owner_certificate='F2.4 physical ownership reused for feasibility only; historical availability of mappings not certified',
        protected_actuals_queried=False,forecasts_scored=False,records=origin_records)
    (raw/'audit.json').write_text(json.dumps(summary,default=str,indent=2)+'\n',encoding='utf-8')
    summarise(raw)
    print('RAW',raw.relative_to(ROOT).as_posix(),flush=True)


def summarise(raw):
    """Summarise this captured audit; incomplete subtotals never become weights."""
    from norway_gas_routing.reporting.assessment import STYLE, table
    raw=Path(raw).resolve()
    if not raw.is_relative_to(ROOT/'data/raw/chronological_inputs_f28'):
        raise ValueError('Use this task\'s bounded raw audit directory.')
    evidence=ROOT/'evidence/inputs/chronological_inputs_f28'
    output=ROOT/'outputs/chronological_inputs_f28'
    for directory in [evidence,output/'details',output/'provenance']:
        directory.mkdir(parents=True,exist_ok=True)
    retained=ROOT/'outputs/routing_runs/20261013T165918528411Z_87c4eb40'
    owners=pd.read_csv(retained/'provenance/frozen_2024_owners.csv',keep_default_na=False)
    old=pd.read_csv(retained/'provenance/frozen_residual_weights.csv')
    audit=json.loads((raw/'audit.json').read_text())
    def points(name):return pd.read_csv(raw/(name+'.csv'),index_col='date').value
    owner_rows=[]
    for row in owners.itertuples():
        v=points('current_'+row.component_id)
        rec=next(r for r in audit['records']['current'] if r['name']=='current_'+row.component_id)
        meta=rec.get('metadata',{})
        origin_contract=(meta.get('unit')=='bcm' and meta.get('frequency')=='monthly' and
            (meta.get('lifecycle_stage') in {'actual','historical'} or
             (meta.get('lifecycle_stage')=='forecast' and pd.Period(meta.get('forecast_start_date'),'M')>pd.Period('2025-12','M'))))
        owner_rows.append(dict(component_id=row.component_id,field=row.field,sid=row.sid,node=row.node,role=row.role,
            approved_2024_bcm=row.annual_bcm,observed_2025_subtotal_bcm=float(v.sum()),observed_months=len(v),
            complete=rec['status']=='EXACT_COVERAGE',origin_available_historical_definition=origin_contract,
            missing_months=';'.join(rec.get('missing_months',[])),negative_months=';'.join(rec.get('negative_months',[]))))
    ownership=pd.DataFrame(owner_rows)
    if not ownership.origin_available_historical_definition.all():
        raise ValueError('Historical component definitions require review; do not label these ratios eligible.')
    national,lng=points('current_national'),points('current_GD')
    explicit=pd.DataFrame({r.component_id:points('current_'+r.component_id) for r in owners.itertuples() if r.role=='explicit'})
    residual=national-lng-explicit.sum(axis=1)
    components=pd.DataFrame({r.component_id:points('current_'+r.component_id) for r in owners.itertuples() if r.role=='residual'})
    monthly=pd.DataFrame(dict(national_EA_bcm=national,snohvit_native_bcm=lng,explicit16_bcm=explicit.sum(axis=1),
        residual_denominator_bcm=residual,observed_owner_subtotal_bcm=components.sum(axis=1),
        missing_owner_count=components.isna().sum(axis=1)))
    monthly['unassigned_boundary_difference_bcm']=residual-monthly.observed_owner_subtotal_bcm
    halten=points('priority_GK')
    monthly['halten_ost_observed_bcm']=halten
    # Only compare dates actually returned; absent months remain NaN.
    compatible=monthly.halten_ost_observed_bcm.notna()
    max_gap=float((monthly.loc[compatible,'unassigned_boundary_difference_bcm']-halten).abs().max())
    denominator=float(residual.sum())
    future=pd.read_csv(retained/'results.csv')
    future_residual=float(future.residual_bcm.sum())
    node_rows=[]
    for node,g in ownership.loc[ownership.role.eq('residual')].groupby('node'):
        subtotal=float(g.observed_2025_subtotal_bcm.sum())
        old_weight=float(old.loc[old.node.eq(node),'weight'].sum())
        node_rows.append(dict(node=node,approved_2024_weight=old_weight,observed_2025_subtotal_bcm=subtotal,
            indicative_2025_share=subtotal/denominator,complete_owner_coverage=bool(g.complete.all()),
            implied_delta_on_retained_residual_bcm=(subtotal/denominator-old_weight)*future_residual,
            status='Diagnostic observed-subtotal ratio only; not certified rolling weights'))
    node_rows.append(dict(node='UNMAPPED_HALTEN_OST',approved_2024_weight=0.,observed_2025_subtotal_bcm=float(halten.sum()),
        indicative_2025_share=float(halten.sum())/denominator,complete_owner_coverage=False,
        implied_delta_on_retained_residual_bcm=float(halten.sum())/denominator*future_residual,
        status='Known group SID matches missing EA boundary; membership/coverage/physical entry require Core approval; unrouted'))
    nodes=pd.DataFrame(node_rows)
    if abs(nodes.indicative_2025_share.sum()-1)>1e-9:
        raise ValueError('Indicative subtotal identity does not close; no normalization adjustment.')
    sn=pd.read_csv(raw/'current_seasonal/comparison.csv')
    if not pd.to_datetime(future.month).dt.to_period('M').astype(str).equals(sn.month):
        raise ValueError('Retained forward plausibility basis differs from the captured seasonal delivery grid.')
    seasonal_pipeline=future.national_production_bcm-sn.seasonal_bcm
    seasonal_residual=seasonal_pipeline-future.explicit16_bcm
    if seasonal_pipeline.lt(0).any() or seasonal_residual.lt(0).any():
        raise ValueError('Seasonal assumption produces negative supply on the unchanged retained forecast basis.')
    annual=sn.groupby(sn.month.str[:4])[['seasonal_bcm','sid_forecast_bcm','difference_bcm']].sum().rename_axis('year').reset_index()
    decision=pd.DataFrame([
        dict(contract='Seasonal Snøhvit / October 2026',decision='PASS: 2024 and 2025 archived net-saleable history; 38 positive forecast months',remaining='Optional historical assumption; SID forecast remains default'),
        dict(contract='Seasonal Snøhvit / December 2024',decision='BLOCKED: native and selected SID archives unavailable',remaining='Origin-available complete net-saleable observations for latest eligible two years, expected 2022/2023'),
        dict(contract='Kollsnes / December 2024',decision='FALLBACK RULE READY; numeric post-upgrade rating not certified',remaining='Dated pre-origin numeric technical rating/boundary; no assumed maintenance; no later 156 applied'),
        dict(contract='Rolling 2025 weights / October 2026',decision='NOT ACTIVATION-READY',remaining='Rev Oct-Dec missing; Halten Øst Jan missing/group ownership/entry unresolved; Balder/Urd unmapped; separate Verdande/NPD revision bridge'),
        dict(contract='Earlier rolling weights / December 2024',decision='BLOCKED: native residual owner archives unavailable',remaining='Origin-correct ledger and mapping evidence; candidate window Dec 2023-Nov 2024 not certified')])
    assessment=dict(status='Historical comparison not ready; seasonal current-origin assumption verified',
        origins=audit['origins'],protected_actuals_queried=False,forecasts_scored=False,operational_weights_changed=False,
        current_seasonal_years=[2024,2025],seasonal_totals=sn[['seasonal_bcm','sid_forecast_bcm','difference_bcm']].sum().to_dict(),
        retained_input_plausibility_check=dict(basis='Immutable F2.7 national/16-field forecasts at the same origin; diagnostic only, no new routing forecast',
            pipeline_min_bcm=float(seasonal_pipeline.min()),residual_min_bcm=float(seasonal_residual.min()),
            forecast_min_bcm=float(sn.seasonal_bcm.min()),forecast_max_bcm=float(sn.seasonal_bcm.max())),
        annual_2025_accounting=dict(national_EA_bcm=float(national.sum()),native_lng_bcm=float(lng.sum()),explicit16_bcm=float(explicit.sum().sum()),
            residual_denominator_bcm=denominator,observed_residual_owners_bcm=float(components.sum().sum()),
            unassigned_before_halten_bcm=float(monthly.unassigned_boundary_difference_bcm.sum()),halten_ost_observed_bcm=float(halten.sum()),
            halten_monthly_match_max_bcm=max_gap,complete_monthly_ledger=False),
        indicative_share_sum=float(nodes.indicative_2025_share.sum()),retained_future_residual_basis_bcm=future_residual,
        limitations=['Observed subtotals are not complete annual observations. Missing values remain missing; no operational shares are written.',
            'The 2024 physical certificate is used to audit known identities, not certified as historically available in December 2024.',
            'Verdande observed December volume is 0.017290 bcm. EA Norne equals native Norne, not Norne plus Verdande. Adding Verdande breaks the matching EA identity; earlier/newer revisions require a bridge.',
            'NPD national 2025 is 121.839 bcm, EA is 121.771800; the 0.067200 bcm difference is documented only and never redistributed.'],
        historical_owner_archive_counts=pd.Series([r['status'] for r in audit['records']['historical'][:len(owners)]]).value_counts().to_dict(),
        kollsnes=dict(status='Numeric historical rating pending; approved live contract unchanged',candidate_rule='Applicable origin-known technical rating * calendar days / 1000; no additional assumed forecast maintenance',
            availability_assumption='Full technical availability, not actual observed availability',
            evidence=[dict(url='https://gassco.eu/wp-content/uploads/2024/03/Gassco-aarsrapport-2023-ENGELSK.pdf',page=2,known_before_origin=True,
                fact='Autumn-2023 compressor upgrade completed; approximately 8 percent/46 TWh annual increase. No exact numeric daily post-upgrade rating in the report.'),
                dict(url='https://gassco.eu/wp-content/uploads/2023/04/091540-Kollsnes_NORSK_spreads_22.10.2019-1-1.pdf',known_before_origin=True,
                    fact='2019 brochure: 144.5 MSm3/day export capacity; predates upgrade, not proof of December-2024 applicable technical ceiling.'),
                dict(url='https://www.equinor.com/news/20250106-troll-highest-natural-gas-production-ever',known_before_origin=False,
                    fact='6 January 2025 explicitly states increase from 144.5 to 156; after December-2024 information origin, so not used retrospectively.')],
            minimum_missing_fact='An origin-available numeric post-upgrade technical daily rating and applicable gas/processing boundary; do not infer an exact rating from rounded 8 percent.'),
        minimum_next_action='Obtain one December-2024 archived net-saleable Snøhvit/owner ledger bundle (candidate Dec2023-Nov2024 owners and two complete LNG years) with contemporaneous ownership/definition evidence and one dated Kollsnes technical rating; Core approves the chronological-weight contract before an untuned 2025 comparison.')
    ownership.to_csv(evidence/'component_coverage.csv',index=False)
    monthly.rename_axis('month').to_csv(evidence/'monthly_accounting_2025.csv')
    nodes.to_csv(evidence/'indicative_node_shares.csv',index=False)
    (evidence/'assessment.json').write_text(json.dumps(assessment,default=str,indent=2)+'\n',encoding='utf-8')
    sn.to_csv(output/'results.csv',index=False)
    annual.to_csv(output/'details/snohvit_annual.csv',index=False)
    report='<!doctype html><html><meta charset="utf-8"><title>Chronological input readiness</title><style>'+STYLE+'</style><body><h1>Seasonal Snøhvit and chronological allocation readiness</h1>'
    report+='<p>F2.8 input assumptions and readiness only. No accuracy scoring, weight activation, protected actual retrieval or optimisation changes.</p>'+table(decision)
    report+='<h2>Current-origin seasonal assumption</h2><p>Two complete archived years: 2024/2025. Signed historical values are retained in daily-rate averages. November 2026–December 2029: seasonal 16.855625 bcm versus SID 17.555713 bcm, difference −0.700088 bcm (−3.99%). This is an assumption comparison.</p>'+table(annual)
    report+='<h2>2025 accounting and indicative shares</h2><p>121.771800 = 4.113131 LNG + 97.648351 explicit fields + 18.842866 observed residual owners + 1.167452 observed Halten Øst bcm. Observed-subtotal identity closes but missing Rev/Halten Øst months are not zero-filled. Balder 0.047496 and Urd 0.000079 bcm stay unmapped. Verdande 0.017290 is not added; native/EA national revisions remain separate. Oseberg aggregate matches its three native members.</p>'+table(nodes)
    report+='<p>The indicated UK-direct change (−5.782919 bcm on the retained 95.915535 bcm residual basis) is a source-input sensitivity, not a solver forecast or change in actual UK deliveries. No complete candidate weights are approved.</p>'
    report+='<h2>December 2024</h2><p>Sixteen explicit EA field archives and national history cover January 2023–November 2024. Native residual and LNG archives are unavailable. December 2023–November 2024 is only a candidate window; latest common eligible 12 months cannot be certified. Earlier routing mappings/weights require contemporaneous evidence; the 2026-certified 2024 ledger is not origin-correct.</p>'
    report+='<h2>Historical Kollsnes</h2><p>Fallback: use the origin-known technical ceiling with no additional forecast-maintenance deduction, labelled assumed full technical availability. The <a href="'+assessment['kollsnes']['evidence'][0]['url']+'">2023 Gassco report</a> establishes a pre-origin upgrade but not its exact daily rating. The explicit 156 statement is January 2025. One dated numeric post-upgrade contract is required; the live model is unchanged.</p>'
    report+='<h2>Smallest next step</h2><p>'+assessment['minimum_next_action']+'</p><p><a href="results.csv">Monthly Snøhvit comparison</a>; <a href="../../evidence/inputs/chronological_inputs_f28/assessment.json">Evidence assessment</a>; <a href="provenance/manifest.json">Capture hashes</a>.</p></body></html>'
    (output/'report.html').write_text(report,encoding='utf-8')
    for name in ['src/norway_gas_routing/seasonal_snohvit.py','scripts/audit/assess_chronological_inputs.py']:
        target=output/'provenance/code'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    files=[p for base in [raw,evidence,output] for p in base.rglob('*') if p.is_file() and p.name!='manifest.json']
    manifest=dict(purpose='Immutable fresh archive input-readiness evidence; no operational cache fallback',raw_directory=raw.relative_to(ROOT).as_posix(),
        origins=audit['origins'],protected_actuals_queried=False,base_git_revision='d4e3f57a961588077bb67f1ff9af24acc2d8f61b',
        implementation_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/norway_gas_routing/seasonal_snohvit.py','scripts/audit/assess_chronological_inputs.py']},
        files_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (output/'provenance/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
