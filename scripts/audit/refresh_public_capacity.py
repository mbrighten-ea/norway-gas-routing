"""Optional public retrieval only; never overwrite audit captures or build/import a DB.

Outputs require a separately reviewed ingestion manifest before offline use.
Only the three point identities and Firm Technical are retrieved. No live flows.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.capacity.public import PILOT,canonical,historical_window,validate_capture


def collect_pages(identity,start,end,get,page_size=100):
    """Fail closed on inconsistent totals, duplicates, or incomplete pagination.

    Raw pages are kept by caller. Never claim completeness from returned values.
    """
    historical_window(start,end)
    rows=[]; pages=[]; total=None; offset=0
    while True:
        params=dict(operatorKey=identity[0],pointKey=identity[1],directionKey=identity[2],
                    indicator='Firm Technical',periodType='day',periodize=0,limit=page_size,offset=offset)
        params.update({'from':start,'to':end})
        url='https://transparency.entsog.eu/api/v1/operationaldatas?'+urlencode(params)
        raw=get(url); payload=json.loads(raw); meta=payload['meta']; batch=payload['operationaldatas']
        if meta.get('count')!=len(batch) or not isinstance(meta.get('total'),int):
            raise ValueError('Invalid API pagination metadata')
        if total is None: total=meta['total']
        if total!=meta['total'] or meta.get('offset',offset)!=offset:
            raise ValueError('Changing/mismatched API pagination metadata')
        pages.append((url,raw)); rows.extend(batch)
        offset+=len(batch)
        if offset==total: break
        if not batch or offset>total: raise ValueError('Incomplete pagination')
    combined=dict(meta=dict(count=len(rows),total=len(rows),offset=0),operationaldatas=rows)
    checked=validate_capture(combined,identity)
    if len(checked)!=len(rows):
        raise ValueError('Duplicate records across pages; retrieval completeness unresolved')
    return pages,combined


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New directory under data/raw/public_capacity_refresh/')
    parser.add_argument('--from-day',default='2022-10-01'); parser.add_argument('--to-day',default='2025-12-31')
    args=parser.parse_args(); output=args.output.resolve()
    historical_window(args.from_day,args.to_day)
    if not output.is_relative_to(ROOT/'data/raw/public_capacity_refresh') or output.exists():
        raise ValueError('Use a new repository raw refresh directory; no overwrites')
    output.mkdir(parents=True); log=[]
    def get(url):
        with urlopen(url,timeout=45) as response: return response.read()
    for probe,identity in PILOT.items():
        pages,combined=collect_pages(identity[:3],args.from_day,args.to_day,get)
        for i,(url,raw) in enumerate(pages):
            name=f'{probe}_page_{i:03d}.json'; (output/name).write_bytes(raw)
            log.append(dict(probe=probe,url=url,raw_file=name,sha256=hashlib.sha256(raw).hexdigest(),
                            retrieved_at=datetime.now(timezone.utc).isoformat(),indicator='Firm Technical'))
        (output/(probe+'_assembled.json')).write_text(canonical(combined),encoding='utf-8')
    (output/'retrieval_manifest.json').write_text(json.dumps(dict(requests=log,
        status='Retrieved only; review source definitions and vintages before independent ingestion',
        holdout='No requested gas-day labels after 2025'),indent=2),encoding='utf-8')
    print(output)


if __name__=='__main__': main()
