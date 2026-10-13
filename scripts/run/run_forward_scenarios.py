"""Fresh four-scenario F2.4 run, preserving the existing operational packages."""
from datetime import datetime,timezone
from pathlib import Path
import json,sys
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.operational import execute_run
from norway_gas_routing.reporting.assessment import STYLE,table


def main():
    settings=yaml.safe_load((ROOT/'config/run_f24.yaml').read_text(encoding='utf-8'))
    settings['origin']=pd.Timestamp.now(tz='UTC').floor('s').isoformat()
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    scratch=ROOT/'.scratch/runs'/(run[:8]+'-01_forward-scenarios_'+run)
    scratch.mkdir(parents=True,exist_ok=False)
    outputs={}; frames=[]; failures={}
    for label,heidrun,capacity in [('A','export_eligible','core_f24_156'),
        ('B','domestic_bound','core_f24_156'),('C','export_eligible','core_f24_proportional_143'),
        ('D','domestic_bound','core_f24_proportional_143')]:
        config={**settings,'heidrun_treatment':heidrun,'capacity_scenario':capacity}
        path=scratch/(label+'.yaml'); path.write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
        output,code=execute_run(ROOT,path.relative_to(ROOT).as_posix())
        outputs[label]=output.relative_to(ROOT).as_posix()
        if code: failures[label]=json.loads((output/'provenance/run_manifest.json').read_text())['blocker']
        else:
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
    if frames:
        from norway_gas_routing.reporting.operational import write_workbook
        write_workbook(summary/'results.xlsx',{'Monthly scenarios':results,'Annual scenarios':annual,
            'Scenario differences':differences},dict(status='SCENARIO_COMPARISON',
                analysis_type='Provisional partial-coverage physical-routing POC; bcm over included deliveries, 2026 Nov-Dec only'))
    # Fresh queries occurred in each scenario at the same information origin.
    # Compare frozen owners and prospective points to detect revisions mid-batch.
    comparable={}
    import hashlib
    for label,rel in outputs.items():
        p=ROOT/rel
        comparable[label]={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'provenance/raw').glob('*')}
    consistent=bool(comparable) and all(v==next(iter(comparable.values())) for v in comparable.values())
    if not consistent: failures['consistency']='Fresh raw sources changed between scenarios; do not interpret differences as controlled sensitivities.'
    manifest=dict(origin=settings['origin'],outputs=outputs,failures=failures,controlled_sources_identical=consistent,
        status='PROVISIONAL_PARTIAL_COVERAGE_PHYSICAL_ROUTING' if not failures else 'PARTIAL_SCENARIO_RESULTS',
        interpretation='No commercial validation. A/C no additional domestic deduction; B/D hypothetical whole-Heidrun outside-network boundary, not an offtake or domestic forecast. Unknown future field mix approximated by Core-approved frozen 2024 residual weights.',
        holdout_actuals_loaded=False,source_query_policy='Every scenario freshly queried 2024 owners, 2023 preferences and prospective origin-matched SIDs; no workbook numerical inputs')
    (summary/'provenance/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    links=''.join('<li>'+label+': <a href="../../'+rel.removeprefix('outputs/')+'/report.html">scenario report</a></li>' for label,rel in outputs.items())
    content='<h1>Provisional physical-routing POC: four scenarios</h1><p>'+manifest['interpretation']+'</p><p><a href="results.xlsx">Scenario workbook</a> | <a href="results.csv">Monthly scenarios</a> | <a href="details/scenario_differences.csv">Monthly bcm and percentage differences</a>. Annual 2026 rows cover November-December only.</p><ul>'+links+'</ul>'+table(annual)
    (summary/'report.html').write_text('<!doctype html><html><meta charset="utf-8"><style>'+STYLE+'</style>'+content,encoding='utf-8')
    print('SUMMARY',summary,flush=True)
    return 0 if not failures else 2


if __name__=='__main__': sys.exit(main())
