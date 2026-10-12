"""Export the read-only capacity adapter without production data or solver runs."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import pandas as pd
import yaml
from norway_gas_routing.capacity_contract import IDENTITIES
from norway_gas_routing.capacity_inputs import DATABASE, SCENARIOS, baseline_rate, database_candidates, dated_daily_rates
from norway_gas_routing.public_capacity import sha256


def export_candidates(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT): raise ValueError('Output must be in this repository')
    output.mkdir()  # No overwrite.
    model=yaml.safe_load((ROOT/'config/model.yaml').read_text(encoding='utf-8'))
    observations=database_candidates(ROOT,model,pd.period_range('2021-01','2025-12',freq='M'))
    observations.to_csv(output/'database_candidates.csv',index=False)
    mappings=[]
    for key,(operator,point,direction,arc) in IDENTITIES.items():
        mappings.append(dict(database_asset=key,operator=operator,point=point,direction=direction,
            model_arc=arc,model_asset='NORTH_SEA_ENTRY' if arc=='NORTH_SEA_ENTRY' else 'BALTIC_PIPE',
            affected_flows='DK plus PL' if arc=='NORTH_SEA_ENTRY' else 'PL only',
            shared_upstream='EUROPIPE_II: DE plus DK plus PL',
            point_identity_status='VERIFIED_COMPATIBLE',model_limit_status='CONDITIONAL',
            conversion_status='INSUFFICIENT_EVIDENCE',optimiser_eligible=False,
            combination='separate serial inequalities; never sum/average; preserve each side'))
    pd.DataFrame(mappings).to_csv(output/'physical_mapping_matrix.csv',index=False)
    months=pd.period_range('2024-01','2025-12',freq='M')
    tables=[]
    for scenario,schedules in SCENARIOS.items():
        for asset,entry in model['poc']['assets'].items():
            base=baseline_rate(entry)
            rates=dated_daily_rates(schedules[asset],months) if asset in schedules else pd.Series(base,index=pd.date_range('2024-01-01','2025-12-31'))
            monthly=rates.groupby(rates.index.to_period('M')).sum()/1000
            for month,value in monthly.items():
                maintenance=bool(entry.get('maintenance_series'))
                tables.append(dict(month=str(month),scenario=scenario,asset=asset,
                    original_rate=base,original_unit='model mcm/day',
                    baseline_technical_bcm=base*month.days_in_month/1000,
                    selected_technical_bcm=value,technical_delta_bcm=value-base*month.days_in_month/1000,
                    candidate_available_bcm=None if maintenance else value,
                    available_status='MISSING_DATA: fresh signed maintenance required' if maintenance else 'baseline/sensitivity assumption; operational history unknown',
                    evidence_status='DEFINITION_MISMATCH' if asset=='KARSTO_PROCESSING' else 'CONDITIONAL' if asset in schedules else 'INSUFFICIENT_EVIDENCE',
                    public_candidate_eligible=False,
                    solver_ready_without_production=False,
                    input_class='assumption_sensitivity' if asset in schedules else 'baseline_assumption',
                    maintenance_policy='do not add new outage deductions; apply original signed adjustment once after fresh retrieval'))
    pd.DataFrame(tables).to_csv(output/'monthly_capacity_preparation.csv',index=False)
    with sqlite3.connect((ROOT/DATABASE).resolve().as_uri()+'?mode=ro',uri=True) as db:
        for view in ('specification_register','assumption_comparison','daily','monthly','coverage'):
            pd.read_sql_query('SELECT * FROM '+view,db).to_csv(output/(view+'.csv'),index=False)
        counts={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('assets','ratings','daily','events')}
    (output/'manifest.json').write_text(json.dumps(dict(database=DATABASE,database_sha256=sha256(ROOT/DATABASE),
        config_sha256=sha256(ROOT/'config/model.yaml'),counts=counts,
        production_inputs_consumed=False,solver_runs=0,holdout_loaded=False,holdout_scored=False,
        forecast_effective=False,scenario_definitions=SCENARIOS),indent=2),encoding='utf-8')
    print(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    export_candidates(parser.parse_args().output)
