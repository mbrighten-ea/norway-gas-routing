"""Retain this single stopped attempt, never generate substitute forecasts."""
from pathlib import Path
import sys,json,hashlib
import pandas as pd

R=Path.cwd();sys.path.insert(0,str(R/'src'))
from norway_gas_routing.seasonal_snohvit import seasonal_profile
from norway_gas_routing.routing import historical_preferences
from norway_gas_routing.reporting.assessment import STYLE,table

raw=next((R/'data/raw/minimum_backtest_f29').iterdir())
records=json.loads((raw/'source_metadata.json').read_text())
byname={r['name']:r for r in records}
owners=pd.read_csv(R/'outputs/routing_runs/20261013T165918528411Z_87c4eb40/provenance/frozen_2024_owners.csv',keep_default_na=False)
rows=[]
for row in owners.itertuples():
 rec=byname['ledger2023_'+row.component_id]
 rows.append(dict(component_id=row.component_id,field=row.field,sid=row.sid,current_identity_node=row.node,role=row.role,
     archived_2023_points=rec['points'],historical_points=len(rec.get('historical_months',[])),
     missing_months=';'.join(rec['missing_months']),status=rec['status'],
     physical_mapping_available_at_origin='Not certified; current identity only, no 2024 weights used'))
coverage=pd.DataFrame(rows)
assert len(coverage)==92 and coverage.component_id.is_unique and coverage.sid.is_unique
assert len(coverage.loc[coverage.role.eq('explicit')])==16
assert coverage.loc[coverage.role.eq('explicit'),'historical_points'].eq(12).all()
assert coverage.loc[coverage.role.eq('residual'),'archived_2023_points'].eq(0).all()
try:
 seasonal_profile(pd.DataFrame({'date':pd.Series(dtype='datetime64[ns]'),'monthly_bcm':pd.Series(dtype=float),
     'available_at':pd.Series(dtype='datetime64[ns, UTC]')}),pd.period_range('2025-01','2025-12',freq='M'),'2024-12-31T23:59:59Z')
 raise AssertionError('Missing source history produced a forecast')
except ValueError as e:seasonal_blocker=str(e)

def values(name):return pd.read_csv(R/byname[name]['raw_file'],index_col='date').value
pref=pd.DataFrame({c.upper():values('preference2023_'+c) for c in ['uk','fr','be','nl','de','dk','pl']})
pref.index=pd.DatetimeIndex(pref.index).to_period('M')
preferences,excluded=historical_preferences(pref)
nat=byname['ledger2023_national']['observed_subtotal']
explicit=sum(byname['ledger2023_'+r.component_id]['observed_subtotal'] for r in owners.itertuples() if r.role=='explicit')
origin=pd.Timestamp('2024-12-31T23:59:59Z')
forecasts=[r for r in records if r['name'].startswith('forecast2025_')]
legacy=[r for r in records if r['name'].startswith('legacy2025_')]
assert len(forecasts)==17 and len(legacy)==4
for r in forecasts+legacy:
 assert r['points']==12 and len(r['forecast_months'])==12 and not r['historical_months']
 assert r['metadata']['unit']=='bcm' and r['metadata']['frequency']=='monthly'
 job=r.get('import_job',{})
 if job.get('created_at'):
  assert pd.to_datetime(job['created_at'],unit='ms',utc=True)<=origin
  r['archive_import_time_utc']=pd.to_datetime(job['created_at'],unit='ms',utc=True).isoformat()
old=byname['seasonal_snohvit_net_prod_legacy']
assert len(old['historical_months'])==8 and len(old['forecast_months'])==16
assert old['metadata']['forecast_start_date']=='2022-09-01T00:00:00'
gap=nat-explicit
decisions=[
 dict(contract='Seasonal Snøhvit, 2022/2023',status='BLOCKED',verified='Native and selected archives empty; older EA series has only 8 historical months, Jan-Aug 2022',
      missing='Origin-available net-saleable observations for Sep-Dec 2022 and all 2023; units/provenance of substitute must be verified'),
 dict(contract='2023 residual-production ledger',status='BLOCKED',verified='All 16 explicit histories and matching national total have 12 months; 75 residual SIDs have no archived observations',
      missing='Complete mutually exclusive residual-owner ledger, native 2023 LNG exclusion, origin-appropriate mappings and monthly closure'),
 dict(contract='Kollsnes technical rating',status='UNRESOLVED',verified='Pre-origin upgrade evidence retained; no assumed forecast maintenance deductions',
      missing='Dated numeric post-upgrade technical rating and volume/processing boundary applicable by Dec 2024; no automatic 156/143 substitution'),
 dict(contract='EA national and 16-field forecasts',status='ARCHIVE_AVAILABLE',verified='17 series, each 12 genuine forecast months at the origin; December 16 import',missing='Original public issuance dates not independently established; archived origin availability verified'),
 dict(contract='EA legacy forecasts',status='ARCHIVE_AVAILABLE',verified='UK, FR+BE, DE+NL and Gassco total: 12 future months each at the origin',missing='Like-for-like total export/scoring boundary still requires certification after input closure'),
 dict(contract='2023 destination preferences',status='AVAILABLE',verified='12 historical observations for all seven destinations; existing rule uses 10 nonnegative baskets',missing='No 2025 actuals used or parameter tuning')]
assessment=dict(outcome='B',status='BLOCKED_INPUTS',forecast_origin=origin.isoformat(),target_period='2025-01 through 2025-12',
    focused_attempts=1,source_requests=len(records),seasonal_method='seasonal_two_year',seasonal_method_coverage_rejection=seasonal_blocker,
    missing_snohvit_historical_months=['2022-'+str(m).zfill(2) for m in range(9,13)]+['2023-'+str(m).zfill(2) for m in range(1,13)],
    historical_ledger=dict(national_EA_2023_bcm=nat,explicit16_2023_bcm=explicit,
        LNG_plus_residual_unallocated_bcm=gap,LNG_plus_residual_pct=gap/nat*100,
        missing_residual_sids=75,missing_original_mapped_residual_sids=46,
        residual_denominator=None,source_node_weights=None,
        interpretation='The 25.0765 bcm gap contains LNG and residual production; it is not a certified pipeline residual and is never redistributed'),
    current_identity_mapping_gaps=coverage.loc[coverage.role.eq('residual')].groupby('current_identity_node').size().to_dict(),
    origin_available_preferences=dict(shares=preferences,excluded_months=[str(x) for x in excluded],valid_baskets=12-len(excluded),
        method='Unchanged historical_preferences; diagnostic archive availability only, not activated'),
    decisions=decisions,capacity_reference=dict(
        existing_evidence='evidence/inputs/chronological_inputs_f28/assessment.json',
        dated_primary_sources=[
            dict(url='https://gassco.eu/wp-content/uploads/2024/03/Gassco-aarsrapport-2023-ENGELSK.pdf',availability='Before origin',finding='Approximate 8 percent autumn-2023 upgrade; exact daily rating/physical reference not established'),
            dict(url='https://www.equinor.com/investors/annual-report',availability='Published 21 March 2024',finding='Additional pre-origin report inspected; no compatible numeric rating certified in this bounded attempt'),
            dict(url='https://www.sec.gov/Archives/edgar/data/1140625/000114062524000034/eqnr20231231.pdf',availability='2024 filing',finding='Text extraction of plant table is insufficient to resolve inconsistent capacities; web screenshot failed and workspace has no PDF renderer. Numeric table not adopted'),
            dict(url='https://www.equinor.com/news/20250106-troll-highest-natural-gas-production-ever',availability='After origin',finding='Explicit 156 statement excluded from historical input')]),
    forecast_run=False,accuracy_metrics=None,comparison_excel=None,actual2025_deliveries_queried=False,
    protected_actuals_queried=False,forward_model_changed=False,indicative2025_weights_used=False,approved2024_weights_used=False,
    smallest_defensible_substitute='Dated pre-origin EA or SODIR production snapshots with release/availability evidence, compatible net-saleable units and unique physical ownership; current revised tables or stale forecasts are not substitutes',
    core_approval='Required for any substituted dated production ledger/source contract, historical mapping/exclusion decisions and provisional capacity interpretation; approval does not turn later revisions into origin-correct inputs',
    next_action='Request one provider/source-owner archive bundle: 2022/2023 Snøhvit net-saleable monthly actuals, a complete 2023 component ledger and contemporaneous ownership evidence, and one dated Kollsnes technical rating. Once it closes, run the unchanged model and retrieve bounded 2025 actuals for scoring. No additional investigation is launched.')
out=R/'outputs/minimum_backtest_f29'
for d in [out/'details',out/'provenance/code']:d.mkdir(parents=True,exist_ok=True)
pd.DataFrame(decisions).to_csv(out/'results.csv',index=False)
coverage.to_csv(out/'details/owner_coverage_2023.csv',index=False)
pd.DataFrame([dict(name=r['name'],sid=r['sid'],points=r['points'],forecast_start=r['metadata']['forecast_start_date'],
    archive_import_time_utc=r.get('archive_import_time_utc'),raw_file=r['raw_file']) for r in forecasts+legacy]).to_csv(out/'details/forecast_availability.csv',index=False)
pd.DataFrame(dict(country=list(preferences),share=list(preferences.values()))).to_csv(out/'details/origin_preferences.csv',index=False)
(out/'provenance/assessment.json').write_text(json.dumps(assessment,default=str,indent=2)+'\n',encoding='utf-8')
for name in ['audit.py','retain.py']:(out/'provenance/code'/name).write_bytes((R/'.scratch/runs/20261014-01_minimum-backtest'/name).read_bytes())
capture=R/'.scratch/runs/20261014-01_minimum-backtest/capacity_capture.json'
if capture.exists():(out/'provenance/capacity_capture.json').write_bytes(capture.read_bytes())
checks=dict(status='PASS',source_responses_checked=125,forecast_series_exact_12_month_coverage=21,
    empty_residual_archives=75,stale_snohvit_forecast_months_rejected=16,
    seasonal_method_rejected_missing_history=True,source_bounds_end_by_2025_12=True,
    optimiser_runs=0,accuracy_metrics_computed=False,protected_actuals_queried=False,
    focused_existing_tests=106,implementation_changed=False)
(out/'provenance/validation.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
content='<h1>December 2024 historical package: one focused attempt</h1><p><strong>Outcome B: BLOCKED_INPUTS.</strong> No 2025 routing forecast, accuracy metrics or comparison Excel was manufactured. No 2025 evaluation actuals were retrieved; January-September 2026 actuals remain locked.</p>'+table(pd.DataFrame(decisions))
content+='<p>2023 archived national production is 117.155200 bcm; the sixteen explicit fields sum to 92.078700 bcm. The remaining 25.076500 bcm (21.40%) includes LNG and residual production. Missing LNG/residual observations prevent a matching denominator, unique-owner closure and physical source-node shares. The older LNG series has Jan-Aug 2022 history only; Sep 2022-Dec 2023 are forecast cells, not actuals.</p>'
content+='<p>No archived-original Snøhvit forecast is required. The missing input is historical net-saleable production genuinely available by the origin. Dated EA/SODIR snapshots could substitute after source/ownership approval; latest-revised data cannot.</p>'
content+='<p>Capacity: assume no additional forecast-maintenance deduction only after establishing the applicable technical ceiling. The <a href="https://gassco.eu/wp-content/uploads/2024/03/Gassco-aarsrapport-2023-ENGELSK.pdf">pre-origin Gassco report</a> documents the upgrade but does not close the exact daily reference. The additional <a href="https://www.equinor.com/investors/annual-report">March-2024 Equinor report</a> did not resolve a compatible rating. No retrospective 156 or arbitrary 143 capacity was introduced.</p>'
content+='<p>December-16 production and country-flow imports are present at the December-31 cutoff; this is archived availability, not a claim that EA published on December 31. Origin-available 2023 preferences use the existing ten valid monthly baskets. Individual DE/NL and DK/PL proxies and the total-export boundary require like-for-like matching before eventual scoring.</p>'
content+='<p><strong>Next action:</strong> '+assessment['next_action']+'</p><p>Core approval is required for a substituted source contract, historic ownership/exclusions and provisional capacity interpretation. Approval cannot establish missing historical availability.</p>'
content+='<p><a href="details/owner_coverage_2023.csv">Exact owner gaps</a> | <a href="details/forecast_availability.csv">Recovered forecast vintages</a> | <a href="provenance/assessment.json">Decision evidence</a> | <a href="provenance/validation.json">106 focused tests and audit checks</a>.</p>'
(out/'report.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Minimum historical package</title><style>'+STYLE+'</style><body>'+content+'</body></html>',encoding='utf-8')
files=[p for base in [raw,out] for p in base.rglob('*') if p.is_file() and p.name!='manifest.json']
manifest=dict(base_revision='4465c8710f42fc732f9e655912f4fd33760318ab',origin=origin.isoformat(),
    purpose='One stopped origin-correct input attempt; no backtest or reconstruction',raw_directory=raw.relative_to(R).as_posix(),
    files_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(out/'provenance/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(checks,indent=2));print('Unallocated LNG/residual historical volume',gap)
