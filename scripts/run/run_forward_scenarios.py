"""Four-scenario implementation called by the supported run_routing command."""
from datetime import datetime,timezone
from pathlib import Path
import json,sys,os
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.scratch/cache/matplotlib'))
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.operational import execute_run,load_run_config
from norway_gas_routing.reporting.assessment import STYLE,table


def write_summary_workbook(summary,manifest):
    """One analyst workbook over existing saved scenario tables; no new solves."""
    from norway_gas_routing.reporting.operational import write_workbook
    def read(path):
        if not path.exists(): return pd.DataFrame()
        try: frame=pd.read_csv(path)
        except pd.errors.EmptyDataError: return pd.DataFrame()
        if 'month' in frame: frame['month']=pd.to_datetime(frame.month)
        return frame
    frames={'Monthly scenarios':read(summary/'results.csv'),
        'Annual scenarios':read(summary/'details/annual_allocations.csv'),
        'Scenario differences':read(summary/'details/scenario_differences.csv')}
    monthly=frames['Monthly scenarios']
    if not monthly.empty:
        columns=['month','scenario']+[d+'_volume_bcm' for d in ['UK','FR','BE','NL','DE','DK','PL']]+[
            'total_exports_bcm','unrouted_supply_bcm','network_coverage_pct']
        frames['Monthly scenarios']=monthly[columns]
    notes=[('Status',manifest['status']),('Origin UTC',manifest['origin']),
        ('Interpretation',manifest['interpretation']),
        ('Units','Monthly bcm; annual totals cover only the included delivery months.'),
        ('Country definitions','UK/FR/BE are modelled exits; DE/NL are shared landing-pool proxies; DK/PL are corridor allocations, not signed DK net/Nybro legacy deliveries.'),
        ('Country codes','UK United Kingdom; FR France; BE Belgium; NL Netherlands; DE Germany; DK Denmark; PL Poland. Coverage is conditional on frozen residual assumptions, not independent physical verification.'),
        ('Supply','Frozen 2024 residual weights approximate future mix; external Trym excluded; UNMAPPED is unrouted. Mixed Snøhvit/national vintages accepted provisionally.'),
        ('Capacity','156 minus net unavailability once; stress is 143/156 times that availability. Other envelopes provisional; monthly feasibility does not prove daily dispatch.'),
        ('Scenarios','A reference: no extra domestic deduction. B: forecast Heidrun outside-network bound. C: proportional capacity stress. D: both bounds.'),
        ('Validation-only','No country forecast is produced when status is VALIDATED_ONLY.')]
    if manifest.get('snohvit_method')=='seasonal_two_year':
        notes=[(key,value.replace('Mixed Snøhvit/national vintages accepted provisionally.','Seasonal Snøhvit is a historical assumption.')) for key,value in notes]
        notes.append(('Snøhvit','Explicit two-year seasonal net-saleable historical assumption, not the EA field forecast. See each case provenance for archived observations, rates and selected years.'))
    for label,relative in manifest['outputs'].items():
        notes.append((label+' detailed Excel','../../'+relative.removeprefix('outputs/')+'/results.xlsx'))
    frames['Read me']=pd.DataFrame(notes,columns=['item','meaning'])
    for sheet,file in [('Accounting','provenance/inputs/reconciliation.csv'),
        ('Source nodes','provenance/inputs/supply.csv'),
        ('Capacity utilisation','details/binding_constraints.csv')]:
        tables=[]
        for label,relative in manifest['outputs'].items():
            frame=read(ROOT/relative/file)
            if not frame.empty:
                if sheet=='Capacity utilisation':
                    frame['utilisation_pct']=100*frame.flow_bcm/frame.available_capacity_bcm.mask(frame.available_capacity_bcm.eq(0))
                frame.insert(0,'scenario',label); tables.append(frame)
        if tables: frames[sheet]=pd.concat(tables,ignore_index=True)
    write_workbook(summary/'results.xlsx',frames,dict(status=manifest['status'],
        analysis_type='Provisional physical-routing scenario comparison; snapshot, not commercial forecast'))


def render_summary(summary,manifest):
    """Present this completed batch's saved solves; never query or rerun models."""
    def read_table(file):
        try: return pd.read_csv(file)
        except pd.errors.EmptyDataError: return pd.DataFrame()
    annual=read_table(summary/'details/annual_allocations.csv')
    differences=read_table(summary/'details/scenario_differences.csv')
    links=''.join('<li>'+label+': <a href="../../'+rel.removeprefix('outputs/')+'/report.html">scenario report and Excel/CSV/charts</a></li>' for label,rel in manifest['outputs'].items())
    content='<h1>Provisional physical-routing POC: four scenarios</h1><p>'+manifest['interpretation']+'</p><p><a href="results.xlsx">Scenario workbook</a> | <a href="results.csv">Monthly scenarios</a> | <a href="details/scenario_differences.csv">Monthly bcm and percentage differences</a>. Annual 2026 rows cover November-December only.</p><ul>'+links+'</ul>'+table(annual)
    if not differences.empty:
        ranked=differences.loc[differences.measure.str.endswith('_volume_bcm')].copy()
        ranked['magnitude']=ranked.difference_bcm.abs()
        content+='<h2>Largest monthly country sensitivities</h2>'+table(ranked.sort_values('magnitude',ascending=False).head(8).drop(columns='magnitude'))
    a=ROOT/manifest['outputs']['A']
    if (a/'details/historical_share_comparison.csv').exists():
        shares=pd.read_csv(a/'details/historical_share_comparison.csv')
        flows=pd.read_csv(a/'results.csv')
        moved=shares.model_minus_share_bcm.abs().sum()/2
        proxy=flows.residual_bcm.sum()/flows.pipeline_supply_bcm.sum()*100
        content+='<h2>What the network explains</h2><p>On the identical modelled export-volume basis, constraints require '+f'{moved:.3f}'+' bcm ('+f'{moved/flows.total_exports_bcm.sum()*100:.2f}'+'%) to move away from naive 2023 destination shares. The country totals below show signed changes against that baseline, not forecast errors.</p>'
        content+=table(shares.groupby('destination',sort=False).model_minus_share_bcm.sum().reset_index())
        content+='<p>Binding limits are reported below. A zero slack alone does not prove an economically important bottleneck: parallel arc flows can be nonunique. France/Belgium have physical corridor upper bounds; some high-supply UK allocations sit at their physical minimum. Individual DE/NL and DK/PL splits are principally preference/proxy allocations. Representative bounds release the preference objectives at the same maximum exports; their endpoints are not jointly attainable.</p>'
        binding=pd.read_csv(a/'details/binding_constraints.csv')
        content+=table(binding.loc[binding.binding].groupby('asset').size().rename('binding_months').reset_index())
        content+=table(pd.read_csv(a/'details/physical_ranges.csv'))
        weights=pd.read_csv(a/'provenance/frozen_residual_weights.csv')
        content+='<h2>Accounting and coverage</h2><p>Every month closes nationally. Frozen 2024 denominator: 18.785806 bcm. The following mutually exclusive node numerators include separate external Trym. Unknown owners remain UNMAPPED. '+f'{proxy:.2f}'+'% of forward pipeline supply is allocated through this residual proxy, not individual field forecast SIDs. Zero UNMAPPED under the approved annual certificate does not certify the future project mix. Heidrun remains explicit; B/D are outside-network boundary bounds, not modelled offtakes or estimated domestic consumption.</p>'
        content+=table(weights.groupby('node')[['annual_bcm','weight']].sum().reset_index())
        sn_definition='Snøhvit uses the explicit two-year seasonal historical assumption, not the EA field forecast. ' if manifest.get('snohvit_method')=='seasonal_two_year' else 'Snøhvit uses the approved calendar-day rate conversion, with older LNG versus newer national/component vintage disclosed. '
        content+='<p>'+sn_definition+'Kollsnes is 156 minus net unavailability once, or its proportional 143 stress. Other envelopes and prospective availability remain provisional; monthly feasibility is not daily dispatch. DE/NL are shared landing-pool allocation proxies. DK/PL are corridor outputs, not comparable signed DK-net or Nybro-entry observations. UK legacy comparison removes only evidenced non-Gassco UK packets once; legacy duplicate Rev is disclosed without changing operational supply.</p>'
        content+='<p><a href="provenance/manifest.json">Batch provenance</a> | <a href="provenance/validation.json">Accounting, raw-data, workbook and output verification</a>. No protected 2026 actuals loaded; no commercial validation.</p>'
    (summary/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><style>'+STYLE+'</style>'+content+'</html>',encoding='utf-8')


def main(config, *, validate_only=False, solver_name=None):
    settings,_,_,_=load_run_config(ROOT,config)
    if settings.get('physical_input_contract')!='core_f24':
        raise ValueError('Four-scenario comparison requires core_f24.')
    if solver_name: settings['solver']=solver_name
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    scratch=ROOT/'.scratch/runs'/(run[:8]+'-01_forward-scenarios_'+run)
    scratch.mkdir(parents=True,exist_ok=False)
    outputs={}; frames=[]; failures={}
    for label,heidrun,capacity in [('A','export_eligible','core_f24_156'),
        ('B','domestic_bound','core_f24_156'),('C','export_eligible','core_f24_proportional_143'),
        ('D','domestic_bound','core_f24_proportional_143')]:
        scenario_config={**settings,'compare_scenarios':False,'heidrun_treatment':heidrun,'capacity_scenario':capacity}
        path=scratch/(label+'.yaml'); path.write_text(yaml.safe_dump(scenario_config,sort_keys=False),encoding='utf-8')
        output,code=execute_run(ROOT,path.relative_to(ROOT).as_posix(),validate_only=validate_only)
        outputs[label]=output.relative_to(ROOT).as_posix()
        if code: failures[label]=json.loads((output/'provenance/run_manifest.json').read_text())['blocker']
        elif not validate_only:
            frame=pd.read_csv(output/'results.csv',parse_dates=['month']); frame['scenario']=label; frames.append(frame)
    summary=ROOT/'outputs/forward_scenarios'/run
    (summary/'details').mkdir(parents=True,exist_ok=False)
    (summary/'provenance').mkdir()
    results=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    results.to_csv(summary/'results.csv',index=False)
    countries=[d+'_volume_bcm' for d in ['UK','FR','BE','NL','DE','DK','PL']]
    annual=pd.DataFrame(); differences=[]
    if frames:
        results['year']=results.month.dt.year
        annual=results.groupby(['scenario','year'],sort=True)[countries+['total_exports_bcm','unrouted_supply_bcm',
            'national_production_bcm','snohvit_bcm','external_trym_bcm','hypothetical_domestic_bcm']].sum().reset_index()
        reference=results.loc[results.scenario.eq('A')].set_index('month')
        for label in ['B','C','D']:
            alternative=results.loc[results.scenario.eq(label)].set_index('month')
            if reference.empty or alternative.empty: continue
            for month,row in alternative.iterrows():
                for col in countries+['total_exports_bcm','unrouted_supply_bcm']:
                    base=reference.at[month,col]; delta=row[col]-base
                    differences.append(dict(month=month,scenario=label,measure=col,
                        reference_bcm=base,scenario_bcm=row[col],difference_bcm=delta,
                        difference_pct=delta/base*100 if abs(base)>1e-12 else None))
    annual.to_csv(summary/'details/annual_allocations.csv',index=False)
    differences=pd.DataFrame(differences)
    differences.to_csv(summary/'details/scenario_differences.csv',index=False)
    # Fresh queries occurred in each scenario at the same information origin.
    # Compare frozen owners and prospective points to detect revisions mid-batch.
    comparable={}
    import hashlib
    for label,rel in outputs.items():
        p=ROOT/rel
        comparable[label]={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'provenance/raw').glob('*')}
    consistent=bool(comparable) and all(v==next(iter(comparable.values())) for v in comparable.values())
    if not consistent: failures['consistency']='Fresh raw sources changed between scenarios; do not interpret differences as controlled sensitivities.'
    manifest=dict(origin=settings['origin'],snohvit_method=settings.get('snohvit_method','sid_forecast'),outputs=outputs,failures=failures,controlled_sources_identical=consistent,
        status=('VALIDATED_ONLY' if validate_only else 'PROVISIONAL_PARTIAL_COVERAGE_PHYSICAL_ROUTING') if not failures else 'PARTIAL_SCENARIO_RESULTS',
        interpretation='No commercial validation. A/C no additional domestic deduction; B/D hypothetical whole-Heidrun outside-network boundary, not an offtake or domestic forecast. Unknown future field mix approximated by Core-approved frozen 2024 residual weights.',
        holdout_actuals_loaded=False,source_query_policy='Every scenario freshly queried 2024 owners, 2023 preferences and prospective origin-matched SIDs; no workbook numerical inputs')
    if settings.get('snohvit_method')=='seasonal_two_year':
        manifest['interpretation']+=' Snøhvit uses the explicitly selected two-year seasonal historical assumption, not the EA field forecast.'
    (summary/'provenance/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    write_summary_workbook(summary,manifest)
    if not failures and not validate_only:
        sys.path.insert(0,str(ROOT/'scripts/verify'))
        from verify_forward_scenarios import main as verify_packages
        verify_packages([summary.relative_to(ROOT).as_posix(),'--write-validation'])
    render_summary(summary,manifest)
    manifest['files_sha256']={p.relative_to(summary).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in summary.rglob('*') if p.is_file() and p!=summary/'provenance/manifest.json'}
    (summary/'provenance/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(manifest['status']+' | '+settings['start']+' to '+settings['end']+' | A/B/C/D')
    print('Excel: '+str(summary/'results.xlsx'))
    print(manifest['interpretation'],flush=True)
    return 0 if not failures else 2


if __name__=='__main__':
    sys.exit('Use scripts/run/run_routing.py --config config/run.yaml with compare_scenarios: true.')
