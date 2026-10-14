"""One report from frozen F2.10 and bounded diagnostics; no data I/O service."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,shutil
import pandas as pd,numpy as np
R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.reporting.assessment import STYLE,table,artifact_links
base=R/'outputs/revision_tolerant_2025';scratch=R/'.scratch/runs/20261014-01_routing-error-attribution'
out=R/'outputs/routing_error_attribution_2025'
for folder in ['details','provenance/code']:(out/folder).mkdir(parents=True,exist_ok=True)
read=lambda name:pd.read_csv(base/name)
errors=pd.read_csv(scratch/'errors.csv');ranges=pd.read_csv(scratch/'ranges.csv')
selection=json.loads((scratch/'selected.json').read_text());selected=selection['months']
pred=read('results.csv');flows=read('details/frozen_forecasts.csv').set_index(['scenario','month'])
obs=read('details/observations.csv').set_index('month');account=read('provenance/inputs/reconciliation.csv').set_index('month')
sources=read('provenance/inputs/supply.csv').set_index('month');caps=read('provenance/inputs/capacities.csv').set_index('month')
prefs=json.loads((base/'provenance/inputs/preferences.json').read_text())
groups={'UK':['UK'],'FR+BE':['FR','BE'],'NL+DE':['NL','DE']}
metrics=[]
for (method,group),f in errors.groupby(['method','group']):
 metrics.append(dict(method=method,group=group,n=len(f),share_MAE_pp=f.share_error_pp.abs().mean(),
  conditional_MAE_bcm=f.conditional_error_bcm.abs().mean(),conditional_bias_bcm=f.conditional_error_bcm.sum()))
metrics=pd.DataFrame(metrics)
score_view=metrics.pivot(index='group',columns='method',values='share_MAE_pp')[['Physical156','EA legacy','2023 shares']].reset_index()
score_view=score_view.rename(columns={'Physical156':'Model share MAE pp','EA legacy':'EA share MAE pp','2023 shares':'2023 share MAE pp'})
monthly=[]
for month in obs.index:
 f=flows.loc[('Physical156',month)];cap=caps.loc[month];correction=account.at[month,'legacy_excluded_uk_direct_bcm']
 z=dict(month=month)
 for method in errors.method.unique():
  e=errors.loc[errors.month.eq(month)&errors.method.eq(method)]
  assert len(e)==3 and abs(e.share.sum()-1)<1e-12
  assert abs(e.conditional_error_bcm.sum())<1e-10
  z[method+'_misallocated_bcm']=e.conditional_error_bcm.abs().sum()/2
  z[method+'_L1_share_pp']=e.share_error_pp.abs().sum()
 z['model_minus_EA_bcm']=z['Physical156_misallocated_bcm']-z['EA legacy_misallocated_bcm']
 z['common_volume_error_bcm']=f['Common total']-obs.at[month,'Common total']
 for group in groups:
  e=errors.loc[errors.month.eq(month)&errors.method.eq('Physical156')&errors.group.eq(group)].iloc[0]
  forecast=pred.loc[pred.target_month.eq(month)&pred.method.eq('Physical156')&pred.destination.eq(group)].iloc[0]
  z[group+'_routing_error_bcm']=e.conditional_error_bcm
  z[group+'_volume_error_bcm']=e.share*z['common_volume_error_bcm']
  assert abs(z[group+'_routing_error_bcm']+z[group+'_volume_error_bcm']-forecast.error_bcm)<1e-10
 cut=cap[['EUROPIPE_I','EUROPIPE_II','NORPIPE','FRANPIPE','ZEEPIPE_EXPORT']].sum()
 z['UK_cut_lower_bound_bcm']=max(sources.at[month,'UK_DIRECT']-correction,f.exports_bcm-cut-correction)
 z['UK_above_cut_lower_bound_bcm']=f.UK_comparable_bcm-z['UK_cut_lower_bound_bcm']
 z['DE_NL_ceiling_given_saved_DK_PL_bcm']=cap[['EUROPIPE_I','EUROPIPE_II','NORPIPE']].sum()-f.DK-f.PL
 assert f['NL+DE']<=z['DE_NL_ceiling_given_saved_DK_PL_bcm']+1e-7
 for g,ds in groups.items():
  z[g+'_unconstrained_operational_bcm']=sum(prefs[d] for d in ds)*f.exports_bcm-(correction if g=='UK' else 0)
 monthly.append(z)
monthly=pd.DataFrame(monthly)
assert monthly.sort_values('model_minus_EA_bcm',ascending=False).month.iloc[:3].tolist()==selected
overall=[]
for method in errors.method.unique():
 f=monthly[method+'_misallocated_bcm'];overall.append(dict(method=method,n=12,
  mean_misallocated_bcm=f.mean(),annual_misallocated_bcm=f.sum(),
  mean_half_L1_share_pp=monthly[method+'_L1_share_pp'].mean()/2))
overall=pd.DataFrame(overall)
case=[];node_rows=[]
for month in selected:
 f=flows.loc[('Physical156',month)];correction=account.at[month,'legacy_excluded_uk_direct_bcm']
 for group in groups:
  p=pred.loc[pred.target_month.eq(month)&pred.destination.eq(group)].set_index('method')
  case.append(dict(month=month,group=group,actual_bcm=obs.at[month,group],model_bcm=p.at['Physical156','prediction_bcm'],
   EA_bcm=p.at['EA legacy','prediction_bcm'],
   historical_share_on_actual_total_bcm=selection['shares_2023'][group]*obs.at[month,'Common total'],
   model_on_actual_total_bcm=errors.loc[errors.month.eq(month)&errors.method.eq('Physical156')&errors.group.eq(group)].iloc[0].share*obs.at[month,'Common total'],
   EA_on_actual_total_bcm=errors.loc[errors.month.eq(month)&errors.method.eq('EA legacy')&errors.group.eq(group)].iloc[0].share*obs.at[month,'Common total'],
   unconstrained_operational_target_bcm=monthly.set_index('month').at[month,group+'_unconstrained_operational_bcm']))
 node_rows.append(dict(month=month,**sources.loc[month].to_dict(),excluded_UK_bcm=correction,
  UK_direct_comparable_floor_bcm=sources.at[month,'UK_DIRECT']-correction,
  model_UK_comparable_bcm=f.UK_comparable_bcm,
  UK_cut_lower_bound_bcm=monthly.set_index('month').at[month,'UK_cut_lower_bound_bcm']))
case=pd.DataFrame(case);nodes=pd.DataFrame(node_rows)
binding=read('details/binding_constraints.csv')
binding_counts=binding.loc[binding.binding].groupby(['asset','scenario']).size().unstack('scenario',fill_value=0)
binding_counts=binding_counts.reindex(columns=['Physical156','Capacity143'],fill_value=0).reset_index()
binding_changed=binding_counts.loc[binding_counts.Physical156.ne(binding_counts.Capacity143)]
changes=flows.loc['Capacity143'].select_dtypes('number')-flows.loc['Physical156'].select_dtypes('number')
change_summary=pd.DataFrame(dict(quantity=['UK comparable','FR+BE','NL+DE','All modelled exports','Disposal'],
  stress_minus_reference_bcm=[changes[c].sum() for c in ['UK_comparable_bcm','FR+BE','NL+DE','exports_bcm','disposal_bcm']]))
assert np.max(np.abs(changes['NL+DE']))<1e-10
face=ranges.loc[ranges.face.eq('all saved objective optima')].pivot(index=['month','group'],columns='bound',values='comparable_bcm').reset_index()
face['saved_bcm']=[case.set_index(['month','group']).at[(r.month,r.group),'model_bcm'] for r in face.itertuples()]
face['width_bcm']=face.maximum-face.minimum
for r in face.itertuples():assert r.minimum-1e-7<=r.saved_bcm<=r.maximum+1e-7
assert ranges.max_mass_balance_residual_bcm.max()<1e-7 and ranges.max_capacity_violation_bcm.max()<1e-7
for name,frame in [('share_metrics',metrics),('normalised_group_errors',errors),('representative_months',case),
  ('source_nodes',nodes),('feasible_ranges',ranges),('binding_counts',binding_counts),('capacity_changes',changes.reset_index()),
  ('capacity_summary',change_summary)]:frame.to_csv(out/'details'/f'{name}.csv',index=False)
monthly.to_csv(out/'results.csv',index=False)
main=monthly[['month','Physical156_misallocated_bcm','EA legacy_misallocated_bcm','2023 shares_misallocated_bcm',
 'model_minus_EA_bcm','common_volume_error_bcm','UK_routing_error_bcm','FR+BE_routing_error_bcm','NL+DE_routing_error_bcm']]
main=main.rename(columns={'Physical156_misallocated_bcm':'Model shifted bcm','EA legacy_misallocated_bcm':'EA shifted bcm',
 '2023 shares_misallocated_bcm':'2023 shifted bcm','model_minus_EA_bcm':'Model minus EA',
 'common_volume_error_bcm':'Common-volume error','UK_routing_error_bcm':'UK routing error',
 'FR+BE_routing_error_bcm':'FR/BE routing error','NL+DE_routing_error_bcm':'DE/NL routing error'})
html='''<h1>Why 2025 destination allocation underperformed EA</h1>
<p>December 2024 origin; twelve 2025 deliveries. This uses immutable F2.10 forecasts and evaluation data, not fresh source queries or a new backtest. It remains a revision-tolerant reconstruction. The forward model and all F2.10 files are unchanged. The common basket is boundary-adjusted UK plus France/Belgium plus Germany/Netherlands; it excludes non-Gassco UK packets and DK/PL, and is not the full Norwegian export total.</p>
<p><strong>Conclusion:</strong> the network modestly improves on static 2023 shares overall, but EA allocates the common volume substantially better. The largest errors reflect static historical preferences and weak identification of flexible UK/France allocation, alongside continental corridor constraints. UK-direct supply and Kollsnes alone do not explain them.</p>
<p><a href="../revision_tolerant_2025/results.xlsx">Original F2.10 Excel</a> | <a href="results.csv">Monthly attribution CSV</a></p>
<h2>Volume-independent allocation accuracy</h2>
<p>For group g, forecast share p = forecast_g / forecast_common. Share error is 100(p - actual_g/actual_common), in percentage points. The conditional prediction p × actual_common is a post-forecast diagnostic only. Volume shifted = ½ Σ |p × actual_common − actual_g|; the division by two prevents counting both origin and destination of a shift. It is an error distance, not physically observed gas movement.</p>'''
html+=table(overall.loc[overall.method.isin(['Physical156','EA legacy','2023 shares','Capacity143'])].rename(columns={
 'method':'Method','n':'Months','mean_misallocated_bcm':'Mean allocation error bcm/month',
 'annual_misallocated_bcm':'Sum over 2025 bcm','mean_half_L1_share_pp':'Mean allocation error pp'}))+table(score_view.rename(columns={'group':'Group'}))
html+='''<p>Both issued forecasts use their own predicted shares; 2023 benchmark shares use all twelve retained positive compatible-group observations: UK 22.259%, FR/BE 28.821%, DE/NL 48.920%. The unchanged optimiser uses ten valid seven-market months, excluding July/August for negative Danish net accounting. Its normalised common-group shares are 22.798%, 28.442%, 48.760%. This sample choice changes mean shifted error by only about 0.01 bcm/month; it does not explain the EA gap.</p>
<p>Raw common-total MAE remains 0.360 bcm/month for the model versus 0.382 for EA. The model's NL/DE raw advantage partly cancels conditional underallocation against total overprediction. After normalisation EA has lower group MAE for every destination.</p>
<h2>Monthly error attribution</h2><p>All volumes below are bcm. Routing errors sum to zero each month; common-volume error is shown separately. Full group forecast error = routing error + predicted group share × common-volume error.</p>'''+table(main)
html+='''<h2>Largest model-versus-EA routing gaps: December, May and June</h2>
<p>Selected by largest model minus EA shifted-volume error, not by raw total errors. These three gaps total 1.131 bcm, about half the annual difference. Model/EA columns retain issued volumes. The 2023 column uses actual common total for post-forecast normalisation only. The unconstrained operational target is the original seven-market preference × gross model exports, with the UK boundary packet removed once.</p>'''+table(case[['month','group','actual_bcm','model_bcm','EA_bcm','historical_share_on_actual_total_bcm','unconstrained_operational_target_bcm']].rename(columns={
 'month':'Month','group':'Group','actual_bcm':'Actual bcm','model_bcm':'Model issued bcm','EA_bcm':'EA issued bcm',
 'historical_share_on_actual_total_bcm':'2023 share on actual total bcm','unconstrained_operational_target_bcm':'Unconstrained model target bcm'}))
html+='''<p><strong>May/June:</strong> actual UK shares were 16.52%/14.76%, while the annual benchmark assumes 22.26% and the model allocates 24.02%/22.90%. France/Belgium was 33.62%/34.34% of the actual common basket, versus model 29.15%/29.45%. France remains approximately at its static gross preference target while UK absorbs surplus. This is a preference outcome; it is not evidence of an unavoidable UK-direct delivery floor.</p>
<p><strong>December:</strong> actual UK share was 31.19%, model 26.26%, EA 28.76%. UK was at its forecast-supply cut minimum; France/Belgium was at both outlet ceilings, but those outlets need not be full. There is substantial spare Langeled capacity to divert core gas from France to UK. Actual shares are used for comparison only, not to choose a new optimal point.</p>'''
html+=table(nodes[['month','KOLLSNES_FEED','KARSTO_FEED','UK_DIRECT','excluded_UK_bcm','UK_direct_comparable_floor_bcm','model_UK_comparable_bcm','UK_cut_lower_bound_bcm']])
html+='''<p>UK-direct comparable floor is only 0.65–0.69 bcm/month, well below the saved UK allocation. Frozen 2023 residual ownership, revised histories, missing Tommeliten/Hanz/Trym observations, retrospective routes and unknown new-field mix remain limitations. They may alter routing pressure but this audit has no evidence that they are the leading explanation. UNMAPPED remains unrouted.</p>
<h2>What the constraints actually identify</h2>
<p>Europipe I (48), Europipe II (73.5) and Norpipe (34) together bound DE/NL plus DK/PL at 155.5 mcm/day in this network. The saved DK/PL allocation consumes 0.752 bcm in May/December and 0.728 in June, leaving DE/NL at 4.068/3.937 bcm. All three corridors bind in these months. The DE/NL maximum over physically feasible maximum-export solutions is higher: 4.821/4.665 bcm, by reducing Nordic allocation. Thus the reported DE/NL ceiling mixes physical corridor limits with preference-selected DK/PL deliveries. Individual DE/NL splits are proxies.</p>
<p>France/Belgium jointly has a 96.4 mcm/day envelope (Franpipe 54.2 + Zeepipe 42.2). At fixed forecast supply, minimum UK follows total exports minus these five continental capacities, corrected for non-Gassco UK production. Those cuts are mathematically necessary in the stated model; their capacity vintages and common gas-volume conditions remain provisional. No retained evidence here proves a wrong topology or a real operating bottleneck in 2025.</p>
<p><strong>Non-unique final allocations:</strong> the ranges below preserve maximum exports, minimum L1 deviation and the saved minimax-shortfall optimum. UK/France-Belgium can exchange 0.351 bcm in December, 0.364 in May and 0.263 in June without worsening any objective or violating physical limits. Saved UK is at the minimum in December and near/at the maximum in May/June. The numerical solver selects a point that the approved objectives do not uniquely identify. No alternative point is scored or selected as a forecast.</p><details><summary>Equally optimal destination ranges (bcm)</summary>'''+table(face.rename(columns={'month':'Month','group':'Group','minimum':'Minimum bcm','maximum':'Maximum bcm','saved_bcm':'Saved forecast bcm','width_bcm':'Range width bcm'}))+'</details>'
html+='''<p>Ranges are individual extrema, not a rectangular joint feasible set. Fifty-four small bound queries use unchanged source supplies/capacities and the existing optimal-face diagnostic pattern. No target actual enters an LP, and no forecast is reissued. Zeepipe IIB alone being full is not proof of a joint bottleneck: its parallel IIA route retains headroom. UK-direct injection is necessary; additional Langeled/Vesterled allocations depend on other constraints and preferences.</p>
<h2>Predeclared Kollsnes sensitivity</h2>'''+table(change_summary)+table(binding_changed)
html+='''<p>The 143 planning case binds Kollsnes in January, February, April, October, November and December (the 156 case never binds there). May/June forecasts are identical. In December it disposes of an additional 0.154 bcm and reduces UK by that amount, leaving both continental groups unchanged and worsening the UK underallocation. Across the year it reduces exports 1.100 bcm and adds the same disposal. DE/NL absolute volumes never change; their better conditional score comes from a smaller comparable denominator. Overall misallocated volume worsens from 0.463 to 0.480 bcm/month. This is not evidence to select either rating from realised accuracy.</p>
<h2>Recommendation to Core</h2>
<p><strong>Investigate first the assumption that the annual 2023 preference rule meaningfully identifies the flexible UK-versus-France allocation.</strong> It misses the observed seasonal share pattern and permits materially different, equally optimal final allocations. Establish what pre-origin physical or historical evidence should determine that allocation and how unresolved ties should be disclosed. Do not fit a preferred point to 2025, change weights or pick a Kollsnes rating from this sample.</p>
<p>Priorities by evidence: (1) static monthly preferences and unresolved final-objective ties; (2) the combined continental envelope and preference-selected Nordic diversion; (3) revision-tolerant production/source mix and missing maintenance information. The last two remain provisional inputs, not demonstrated specification errors. This audit cannot attribute realised outages or demand changes without new evidence, and does not initiate such an investigation.</p>
<p>Validation: F2.10 hashes and all frozen accounting checks pass; 54 bound queries are optimal and satisfy node/capacity checks. Independent share/error identities, monthly ordering, baseline derivation and selected-month ranking are checked. Focused regression results are retained in provenance. No code, configuration, network, objective, weights or protected 2026 actuals changed.</p>'''
for name in ['analyse.py','ranges.py','report.py']:
 source=Path(__file__).resolve().parent/name;destination=out/'provenance/code'/name
 if source.resolve()!=destination.resolve():shutil.copyfile(source,destination)
manifest=dict(base_revision='a676910e1447e1383fdbb68735a7d932d6c45b51',
 created_at=datetime.now(timezone.utc).isoformat(),analysis_type='Frozen 2025 routing-error attribution; not forecast calibration',
 frozen_input_manifest='outputs/revision_tolerant_2025/provenance/manifest.json',
 input_manifest_sha256=hashlib.sha256((base/'provenance/manifest.json').read_bytes()).hexdigest(),
 raw_data_retrieval=False,protected_actuals_queried=False,model_changes=False,diagnostic_bound_queries=len(ranges),
 actual_total_usage='Post-forecast share scoring only; no actuals enter bound-query LPs',
 baseline_policy='All twelve retained compatible 2023 group observations; unchanged ten-month operational shares shown separately',
 selected_months=selected,selection_metric='Largest conditional half-L1 volume-error gap Physical156 minus EA',
 range_policy='Existing optimal-face pattern; sources/capacities fixed; saved stage optima preserved with 1e-8 bcm tolerance; individual extrema')
if (scratch/'tests.log').exists():
 log=(scratch/'tests.log').read_text(encoding='utf-16') if (scratch/'tests.log').read_bytes().startswith(b'\xff\xfe') else (scratch/'tests.log').read_text()
 manifest['focused_regression_result']=log.strip().splitlines()[-1]
else:
 manifest['focused_regression_result']=json.loads((out/'provenance/manifest.json').read_text())['focused_regression_result']
manifest['reproduction']='Run retained provenance/code/analyse.py, then ranges.py, then report.py from repository root with approved interpreter; no source services are called. Diagnostics regenerate in ignored .scratch; recorded focused tests remain recorded unless explicitly rerun.'
(out/'provenance/validation.json').write_text(json.dumps(dict(status='PASS',F210_frozen_package='PASS',
  diagnostic_queries=len(ranges),max_balance_bcm=ranges.max_mass_balance_residual_bcm.max(),
  max_capacity_violation_bcm=ranges.max_capacity_violation_bcm.max(),share_identities=True,
  saved_solution_in_ranges=True,no_actual_LP_inputs=True,focused_tests=manifest['focused_regression_result']),indent=2)+'\n')
html+=artifact_links(out)
(out/'report.html').write_text('<!doctype html><html><meta charset="utf-8"><title>2025 routing-error attribution</title><style>'+STYLE+'</style><body>'+html+'</body></html>',encoding='utf-8')
manifest['files_sha256']={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json'}
(out/'provenance/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(overall.to_string(index=False));print('CAPACITY',change_summary.to_string(index=False));print('BINDING CHANGE',binding_changed.to_string(index=False));print('TESTS',manifest['focused_regression_result'])
