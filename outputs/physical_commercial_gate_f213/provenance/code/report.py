"""Retain the bounded F2.13 decision from diagnostics and captured origin prices.

Run from repository root after physical_checks.py. No source query, forecast,
commercial objective, calibration or protected-actual read occurs here.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import sys
import pandas as pd

R = Path.cwd()
sys.path.insert(0, str(R/'src'))
from norway_gas_routing.reporting.assessment import STYLE, table, artifact_links

out = R/'outputs/physical_commercial_gate_f213'
scratch = R/'.scratch/runs/20261014-01_physical-commercial-gate'
raw = R/'data/raw/physical_commercial_gate_f213/20261014T142207141301Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['feasibility.csv', 'source_witnesses.csv', 'physical_witnesses.json', 'two_route_domains.csv']:
    shutil.copyfile(scratch/name, out/'details'/name)
physical = pd.read_csv(out/'details/feasibility.csv')
assert len(physical)==48 and physical.status.eq('Optimal').all()
assert physical.max_mass_balance_residual_bcm.max()<1e-7
assert physical.max_capacity_violation_bcm.max()<1e-7
domains = pd.read_csv(out/'details/two_route_domains.csv')
assert len(domains)==12 and domains.physical_optimal_width_bcm.ge(-1e-7).all()

records = json.loads((raw/'source_metadata.json').read_text())
prices = []
view = pd.DataFrame({'month':pd.period_range('2025-01','2025-12',freq='M').astype(str)})
for record in records:
    assert record['asof']=='2024-12-31T23:59:59Z'
    assert record['start']=='2025-01-01' and record['end']=='2025-12-31'
    path=R/record['raw_file']
    assert sha(path)==record['sha256']
    metadata=record['metadata']
    complete = record['complete_monthly_grid'] in (True, 'True')
    prices.append(dict(key=record['key'],points=record['points'],complete_monthly_grid=complete,
        unit=metadata.get('unit','Unknown'),role=metadata.get('lifecycle_stage','Unknown'),
        forecast_start_date=metadata.get('forecast_start_date','Not supplied'),
        origin=record['asof'],sid=record['sid'],missing_months=','.join(record['missing_months']),
        qualification='Service as-of view; independent publication/FX/energy basis not certified'))
    if record['key'].endswith('forecast') or record['key']=='nbp_forecast_eur':
        assert complete and record['points']==12 and metadata['lifecycle_stage']=='forecast'
        frame=pd.read_csv(path)
        assert pd.DatetimeIndex(frame.date).equals(pd.date_range('2025-01-01','2025-12-01',freq='MS'))
        view[record['key']+'_eur_MWh']=frame.value
view['NBP_minus_PEG_break_even_incremental_cost_gap_eur_MWh']=view.nbp_forecast_eur_eur_MWh-view.peg_forecast_eur_MWh
view.to_csv(out/'details/origin_price_view.csv',index=False)
price_table=pd.DataFrame(prices)
price_table.to_csv(out/'details/price_availability.csv',index=False)

gates=pd.DataFrame([
    ['2025 ratings / dates','UNRESOLVED; boundary contradiction',
     '14 pipes match retained 2024 map; Kollsnes upgrade evidenced; Nyhamna 84 export.',
     '2025 effective dates/reference conditions unverified. Karsto 95 is rich inlet, not certified net dry export; Kollsnes 143/144.5/156 differ in date/boundary.',
     'Obtain dated dry/export definitions or approve declared sensitivity; no numeric correction justified.'],
    ['Maintenance compatibility','UNRESOLVED',
     'Historical pilot explicitly assumes no planned deductions; live 156-minus-unavailable is unchanged.',
     'No origin-available 2025 outage contract; net UMM effects, overlapping revisions and volume bases not fully reconciled.',
     'Retain full-availability planning assumption, not observed availability; no synthetic outages.'],
    ['Shared plant / corridor / terminal constraints','PARTIAL PASS; unresolved coverage',
     'Asset users summed once; Europipe II shared before DK/PL split; Zeepipe IIA/IIB not additional exits.',
     'Collapsed CORE lacks separate Sleipner-Draupner segment; receiver cluster/end-terminal limits not independently validated.',
     'Do not add terminal/pipe capacities or Faxe sides. Validate material UK/France end-to-end limits before commercial certification.'],
    ['Connections / destination boundaries','PARTIAL PASS; proxy limits',
     'Existing supported routes and accounting retained; UK scope correction explicit.',
     'DE/NL split is accounting, not independently tradable routing; DK/PL boundaries and Sm3/Nm3/GCV basis incomplete.',
     'Restrict initial choice to physical Easington versus Dunkerque; hold proxy and Nordic allocations fixed.'],
    ['Observed 2025 joint feasibility','PARTIAL PASS, not full certification',
     '48/48 physical-only monthly cases optimal under 156 and 143, with no preference or maximum-export optimum restriction.',
     'Only UK, FR+BE, DE+NL jointly imposed; no observed node ledger, DK/PL, individual terminal or daily feasibility claim.',
     'No observed aggregate topology contradiction. Keep full physical-validation gate unresolved.'],
],columns=['Gate','Decision','Verified evidence','Remaining limit','Required action'])
gates.to_csv(out/'results.csv',index=False)

refs=[
 'evidence/inputs/public_capacity_findings.md','evidence/inputs/public_capacity_database.md',
 'evidence/inputs/capacity_integration_recommendation.md','evidence/inputs/capacity_integration_contract.json',
 'evidence/inputs/physical_contract_f23/README.md','evidence/inputs/physical_contract_f23/assessment.json',
 'evidence/inputs/price_response_feasibility.md','evidence/inputs/price_response_experiment.md',
 'config/data_series.csv','src/norway_gas_routing/routing.py',
 'scripts/run/run_routing_flexibility.py',
 'outputs/revision_tolerant_2025/provenance/manifest.json',
 'outputs/routing_error_attribution_2025/provenance/manifest.json']
prior_files=0
for folder in ['revision_tolerant_2025','routing_error_attribution_2025']:
    manifest=json.loads((R/'outputs'/folder/'provenance/manifest.json').read_text())
    for name,digest in manifest['files_sha256'].items():
        assert sha(R/name)==digest, name
        prior_files+=1

content='''<p class="note"><strong>Decision: physical validation remains unresolved; the smallest economic pilot is designed, not implemented.</strong>
Observed aggregate deliveries are feasible under the declared envelopes, but that does not verify capacity definitions, actual source injections or commercial access.
No active model, preferences, weights, capacities, forecasts or historical scoring changed. F2.12 cleanup was completed first at <code>1e88049</code>.</p>
<h2>Physical-validation gate</h2>'''+table(gates)+'''
<p>Evidence: <a href="../../evidence/inputs/public_capacity_findings.md">retained capacity findings</a>,
<a href="../../evidence/inputs/public_capacity_database.md">capacity database assessment</a>,
<a href="../../evidence/inputs/physical_contract_f23/README.md">physical input contract evidence</a>.
No network-wide audit or new infrastructure search was performed. The older findings' detailed public-audit CSVs/raw archive are not part of this tracked checkout;
this gate relies on the retained findings and their operator citations, not a new independent verification of those absent files.</p>
<p><strong>Material definition issue:</strong> Karsto's 95 mcm/day rich inlet rating is not a certified dry-gas export limit.
The 97 generic processing figure does not correct that mismatch. Obtain an operator-supported rich/dry conversion or net-export rating before changing it.
F2.10 peak Karsto utilisation is 86.004% of the assumed ceiling (about 81.704 mcm/day), so the current cap does not bind that reference.
Any sensitivity must use independently evidenced conversion bounds, not a capacity chosen to fit observed country flows.</p>
<p>Kollsnes' autumn-2023 upgrade was documented in a report published in 2024; the explicit 144.5-to-156 announcement is dated 6 January 2025.
Exact effective day, baseline and upgraded dry-export boundary remain unresolved. Retain the predeclared 156 planning and 143 sensitivity cases without claiming either was a verified December-2024 rating.
No independent correction to the live approved capacity or maintenance formula is justified here.</p>
<h2>Observed-flow feasibility, without routing preferences</h2>
<p>All twelve months pass jointly for UK, France+Belgium and Germany+Netherlands: two declared Kollsnes envelopes times two source treatments = 48 feasible cases.
The objective is zero/existence; neither destination preferences nor a maximum-export optimum is imposed.
The first case allows unknown nonnegative injections at existing Gassco feeds, with UK_DIRECT and UNMAPPED set to zero, bounded by retained revised actual national production minus Snøhvit.
Those injections are existence witnesses, not reconstructed actual sources or calibrated weights.</p>
<p>The second case fixes the original forecast source vector and adds its forecast non-Gassco UK scope packet to the observed UK target.
That packet is not an observed reconstruction. DK/PL and the within-group country splits remain free in both cases; aggregate month feasibility does not prove daily or terminal feasibility.
Observed 2025 production is used only as a physical-diagnostic upper bound, never a forecast input. No protected 2026 actuals were read.</p>
<h2>Smallest fourth-stage experiment</h2>
<p>Allow only a CORE-feed exchange between Langeled South → Easington → UK/NBP and Franpipe → Dunkerque → France/PEG.
Hold all upstream flows, source weights, UK_DIRECT, Vesterled, Belgium/Zeepipe, DE/NL and Nordic allocations fixed.
This deliberately tests a subset of optimal routing freedom, not the full UK/France-Belgium range found in F2.11.</p>
<p>First preserve export/disposal optimum, absolute destination-preference deviation optimum, and minimax fractional-shortfall optimum.
Then propose the fourth criterion, with δ the additional UK bcm and equal reduction in France:</p>
<p><code>max δ × [(NBP_origin − PEG_origin) − (incremental_UK_cost − incremental_FR_cost)]</code></p>
<p>Prices and incremental costs are EUR/MWh for the same delivery month. A common positive MWh/bcm factor cancels for selection only under an explicit compatible energy/volume assumption;
no calorific value, realised FX or numerical profit is invented. δ must satisfy the saved three optima, physical envelopes and separately approved commercial switching rights.
If the net difference is zero, retain δ=0 deterministically. No commercial objective was solved in this task.</p>
<p>The analytic forecast-input-only domains below preserve all three optima and every physical constraint at both endpoints (1e-7 bcm verification tolerance).
They are not commercial availability. September has no such exchange freedom.</p>'''+table(domains[['month','UK_increment_min_bcm','UK_increment_max_bcm']])+'''
<h2>December-2024 commercial input availability</h2>
<p>Seven existing registered candidates were queried once with <code>@asof:2024-12-31T23:59:59</code>, delivery dates January–December 2025.
The four EA monthly price forecasts have 12/12 observations in the archived service view, labelled EUR/MWh and forecast start December 2024.
These are provider forecasts, not demonstrated traded forward settlement strips. As-of service availability is evidenced; independent publication/import time and NBP EUR conversion/FX/therm and energy-reference conventions remain uncertified.</p>'''+table(price_table[['key','points','complete_monthly_grid','unit','role','forecast_start_date']])+'''
<p>The EEX candidates supply only 5 NBP, 6 PEG and 3 ZTP points; their delivery-strip valuation/freshness contract is incomplete.
Do not fill missing months or substitute them silently. Full SIDs, queries, dates, source metadata and byte hashes are retained.
The minimal pilot needs only NBP-EUR and PEG. Belgium is fixed; extending it requires a separate ZTP contract, not a France+Belgium invented price.
TTF may only be an explicitly approved common landing-pool value proxy later; DE/NL accounting arcs cannot be treated as separately tradable routes.</p>
<h2>Incremental costs and commercial access</h2>
<p>Required costs are the route-dependent offshore transport/commodity or fuel charges, receiving entry/hub/balancing costs and genuinely incremental capacity-acquisition or independently supported opportunity costs.
Retain their delivery period, currency, energy basis, effective date and origin availability. Exclude unavoidable sunk/precontracted payments from marginal cash selection;
capacity rights still constrain the switch. Do not deduct physical fuel volumes again or equate a published average/full tariff with a marginal cost.</p>
<p>No retained twelve-month UK/France end-to-end incremental-tariff or shipper-rights contract was established.
Spare engineering headroom and unsold technical/firm capacity do not prove a producer can switch nominated gas between markets.
Document held rights, receiving entry access, resale/nomination flexibility and relevant portfolio ownership, or obtain explicit Core approval for hypothetical bounds.
Unknown rights imply no verified switch. A δ=0 no-access case and full-physical-access upper case may be declared assumptions, never certified commercial forecasts.</p>
<p>Unknown costs must not silently become zero. The saved NBP-minus-PEG value gap is a break-even incremental-cost difference, not net profit.
Core must approve any cost assumption before allocation; do not select tariffs or access fractions using 2025 errors.</p>
<h2>Twelve-month historical testing specification</h2>
<ol><li>Preserve the unchanged <a href="../revision_tolerant_2025/results.xlsx">F2.10 genuine forecast-volume output</a> and its revision-tolerant provenance.</li>
<li>Keep conditional allocation scoring separate: normalise forecast shares to common observed export volume after forecasting only. Actual totals are not commercial-forecast LP inputs.</li>
<li>After freezing the origin price, cost, rights and unit contract, produce the optional economic tie-selection forecast for all twelve 2025 months using December-2024 information only.
It retains revision-tolerant pre-origin production histories, so is not a fully vintage-correct real-time backtest.</li></ol>
<p>Use the existing UK, FR+BE, DE+NL and comparable-total boundaries and MAE, WAPE, signed bias and share diagnostics.
Total export volume stays unchanged in this two-route experiment. Do not retrieve realised 2025 hub prices or tune the commercial score to deliveries.
The examined 2025 sample is development evidence; it is not untouched validation. Preserve the locked January–September 2026 holdout.
No UK regression is introduced, and no ex-ante UK accuracy improvement is promised. A negative result does not authorise retuning physics or historical preferences.</p>
<h2>Minimum Core decision and next task</h2>
<p><strong>Design ready; implementation conditional, commercially verified forecast not ready.</strong>
Approve the narrowly declared physical envelopes and common energy/provider-EUR basis, plus a documented or explicitly hypothetical UK/France rights and incremental-cost contract.
Then implement one optional fourth-stage selector in the existing workflow, preserving the three existing optima and retaining a δ=0 baseline and qualifications.
Do not reuse the old realised-price experiment that alters stage two; no new framework, grouped-market price, general commercial optimiser or capacity calibration is needed.</p>
<p>Focused regression checks: 123 passed. Physical-only cases: 48/48 optimal; analytic domains: 12 months with endpoint checks.
F2.10 independent accounting/scoring verification and both original-package hash checks pass. Inputs and original forecasts are unchanged.</p>
'''
content+=artifact_links(out)
(out/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Physical gate and commercial-choice design</title><style>'+STYLE+'</style><h1>Physical gate and commercial-choice design</h1>'+content+'</html>',encoding='utf-8')

validation=dict(focused_tests='123 passed in 12.55s',physical_cases=48,optimal_cases=48,
    maximum_balance_residual_bcm=float(physical.max_mass_balance_residual_bcm.max()),
    maximum_capacity_violation_bcm=float(physical.max_capacity_violation_bcm.max()),
    analytic_domains=12,all_three_objectives_preserved=True,
    prior_manifest_files_verified=prior_files,original_forecasts_changed=False,
    commercial_optimisation_implemented=False,protected_actuals_queried=False)
(out/'provenance/validation.json').write_text(json.dumps(validation,indent=2)+'\n')
files=[p for p in out.rglob('*') if p.is_file() and p.name!='manifest.json']+list(raw.iterdir())
manifest=dict(base_revision='1e8804979b424302863515333ebaf40d81ddc586',
    created_at=datetime.now(timezone.utc).isoformat(),assessment='F2.13 physical gate and pilot design only',
    forecast_origin='2024-12-31T23:59:59Z',physical_gate='UNRESOLVED',
    commercial_pilot_status='Design ready; rights/cost/basis assumptions require Core approval',
    input_policy='Retained F2.10/F2.11 evidence; fresh bounded origin-matched price candidates only',
    actual_usage='Retained 2025 delivery constraints and production upper bound for physical existence only; no forecast inputs or commercial score',
    protected_actuals_queried=False,model_changes=False,commercial_optimisation_implemented=False,
    reproduction='From repository root run provenance/code/physical_checks.py, then report.py with approved workspace interpreter. Diagnostics go to ignored .scratch. query_prices.py records the bounded acquisition, not required for saved-data replay.',
    evidence_sha256={n:sha(R/n) for n in refs},
    files_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(files)})
(out/'provenance/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(validation,indent=2))
