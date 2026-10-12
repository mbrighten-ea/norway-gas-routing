"""Validate known NPD candidates with bounded 2024 queries; optionally register passes.

No discovery, workbook observations, forecast retrieval or solver is involved.
Raw responses and the pre-change registry/contracts/ledger are preserved locally.
Every subsequent operational run still makes fresh SID queries.
"""
import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
from uuid import uuid4

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from norway_gas_routing.config import load_config, load_series
from norway_gas_routing.data_functions import connect_shooju
from norway_gas_routing.routing_sources import (CONTRACT, MAPPING_LEDGER, retrieve_checked,
                                              source_contract, field_identity)


def activate(apply=False, references=None, start='2024-01', end='2024-12'):
    months=pd.period_range(start,end,freq='M')
    if months.empty or months.min()<pd.Period('2024-01','M') or months.max()>pd.Period('2024-12','M'):
        raise ValueError('Activation retrieval must remain within January-December 2024.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_'+uuid4().hex[:8]
    output=ROOT/'data/raw/npd_activation'/stamp
    output.mkdir(parents=True, exist_ok=False)
    model, registry=load_config(ROOT/'config/model.yaml', ROOT/'config/data_series.csv')
    ledger=pd.read_csv(ROOT/MAPPING_LEDGER, keep_default_na=False)
    contract=source_contract(ROOT)
    paths={'registry': ROOT/'config/data_series.csv', 'contract': ROOT/CONTRACT, 'ledger': ROOT/MAPPING_LEDGER}
    before={key:path.read_bytes() for key,path in paths.items()}
    for key,data in before.items():
        (output/(key+'_before'+paths[key].suffix)).write_bytes(data)
    client=connect_shooju()
    records, report, additions=[], [], []
    dates=months.to_timestamp()
    selected=ledger if not references else ledger.loc[ledger.reference.isin(references)]
    if references and set(selected.reference)!=set(references):
        raise ValueError('Use only references from the existing 46-row ledger.')
    for index,row in selected.iterrows():
        sid=row.candidate_sid
        parts=sid.split('\\')
        if len(parts)!=5 or parts[:3]!=['NPD','monthly_by_field','marketed_production'] or parts[-1]!='gas-saleable':
            raise ValueError('Expected one exact known candidate, not a discovery query: '+row.reference)
        slug=parts[-2]
        key=slug+'_net_actual'
        if field_identity(row.field)!=slug:
            raise ValueError('Candidate/field label mismatch: '+row.reference)
        spec=dict(sid=sid, category='production_npd', provider_contract='npd_historical',
            npd_field=slug, npd_field_label=row.field, raw_unit='bcm', metadata_unit='bcm',
            frequency='monthly', registry_role='supply', status='Historical identity/units/coverage validated on direct response',
            evidence=MAPPING_LEDGER, verified_history_start=start, verified_history_end=end)
        info={col:'' for col in registry.columns}
        info.update(sid=sid, description=row.field+' historical marketed gas production',
            custom_description='Monthly NPD net saleable gas production for '+row.field+' in bcm; existing '+row.node+' mapping.',
            country='Norway', country_iso='NO', balance_item='production', data_item='gas_production',
            category='production', asset_type='gas_field', asset='', status='CONFIRMED',
            model_role='supply', required_level='required', raw_unit='bcm', target_unit='bcm',
            source_frequency='monthly', lifecycle='actual', source_system='energy_aspects', display_source='NPD',
            economic_property='production', input_semantics='net_saleable_monthly_volume',
            history_required=True, forecast_required=False,
            notes='B2 direct '+start+' to '+end+' contract validation; workbook '+row.reference+' -> '+row.node+
                '. Monthly bcm used directly; no rate conversion, cached values, zero fill or forecast claim.')
        if key in registry.index and (registry.at[key,'sid']!=sid or registry.at[key,'model_role']!='supply'):
            raise ValueError('Existing registry record conflicts with proposed activation: '+key)
        proposed=registry.copy()
        proposed.loc[key]=info
        proposed_contract={**contract, 'sources': {**contract['sources'], key:spec}}
        try:
            values=retrieve_checked(ROOT,key,dates,proposed,proposed_contract,records,output,client=client)
            if values.lt(0).any():
                raise ValueError(key+': negative mapped field production; retain sign and review accounting, never clip.')
            record=records[-1]
            spec.update(source_metadata_file=(output/'source_metadata.json').relative_to(ROOT).as_posix(),
                source_response_sha256=record['sha256'], validated_at=record['retrieved_at'])
            contract['sources'][key]=spec
            contract.setdefault('historical_components',{})[row.reference]=dict(key=key,node=row.node)
            if key not in registry.index:
                additions.append((key,info))
                registry.loc[key]=info
            ledger.at[index,'verified_key']=key
            ledger.at[index,'verified_sid']=sid
            ledger.at[index,'candidate_status']='Direct response identity/measurement/units validated; historical coverage recorded separately'
            ledger.at[index,'retrieved_at']=record['retrieved_at']
            ledger.at[index,'mapping_status']='activated_historical' if len(months)==12 else 'registered_partial_2024_coverage'
            ledger.at[index,'availability']='Direct '+start+' to '+end+' query: '+str(len(months))+' finite nonnegative monthly observations; unqueried/absent months are not zero; queried fresh every run'
            ledger.at[index,'raw_unit']='bcm (API monthly volume)'
            ledger.at[index,'source_unit']='bcm / bill Sm3; marketed net saleable gas'
            ledger.at[index,'transformation']='Use monthly bcm directly; worksheet bcm / days * 1000 and old adapter reversal cancel'
            ledger.at[index,'validation_evidence']=spec['source_metadata_file']
            ledger.at[index,'response_sha256']=record['sha256']
            status,error='PASS',''
        except (ValueError,OSError,KeyError) as exc:
            status,error='BLOCKED',str(exc)
            ledger.at[index,'mapping_status']='blocked_returned_contract'
            ledger.at[index,'availability']=error
        report.append(dict(reference=row.reference,field=row.field,key=key,sid=sid,status=status,error=error))
        print(str(len(report))+'/'+str(len(selected))+' '+key+' '+status+((': '+error) if error else ''),flush=True)
    pd.DataFrame(report).to_csv(output/'validation.csv',index=False)
    headers=['key',*registry.columns]
    text=io.StringIO(newline='')
    writer=csv.DictWriter(text,fieldnames=headers,lineterminator='\n')
    for key,info in additions:
        info={**info, 'history_required':'true','forecast_required':'false'}
        writer.writerow({'key':key,**info})
    updated=before['registry']+(b'' if before['registry'].endswith(b'\n') else b'\n')+text.getvalue().encode('utf-8')
    candidate=output/'registry_candidate.csv'
    candidate.write_bytes(updated)
    load_series(candidate)
    load_config(ROOT/'config/model.yaml', candidate)
    (output/'contract_candidate.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
    ledger.to_csv(output/'ledger_candidate.csv',index=False,encoding='utf-8')
    if apply:
        if any(paths[key].read_bytes()!=data for key,data in before.items()):
            raise ValueError('Registry/contracts/ledger changed concurrently; candidates retained, no overwrite.')
        # Single writes to task-owned canonical files. A lock failure leaves the
        # checked candidates here; diagnose the exact Windows error, do not bypass.
        paths['registry'].write_bytes(updated)
        paths['contract'].write_bytes((output/'contract_candidate.json').read_bytes())
        paths['ledger'].write_bytes((output/'ledger_candidate.csv').read_bytes())
    print('Activation evidence:',output)
    print('Passed',sum(r['status']=='PASS' for r in report),'blocked',sum(r['status']!='PASS' for r in report),'applied',apply)
    return 0 if all(r['status']=='PASS' for r in report) else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Append passing canonical records and update existing source contract/ledger')
    parser.add_argument('--reference',action='append',help='Recheck only a known workbook reference; repeat as needed')
    parser.add_argument('--start',default='2024-01',help='First activation month, restricted to 2024')
    parser.add_argument('--end',default='2024-12',help='Last activation month, restricted to 2024')
    args=parser.parse_args()
    sys.exit(activate(args.apply,args.reference,args.start,args.end))
