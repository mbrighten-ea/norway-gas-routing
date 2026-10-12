"""Offline, read-only point mapping diagnostics; no solver integration."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from norway_gas_routing.capacity_contract import inspect_contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path,
                        help='New diagnostic directory; never overwrites an experiment')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error('Output must be inside this repository')
    output.mkdir(parents=True, exist_ok=False)
    contract = ROOT/'evidence/inputs/capacity_integration_contract.json'
    coverage, differences = inspect_contract(ROOT, contract)
    for name, rows in [('coverage',coverage), ('faxe_differences',differences)]:
        with (output/(name+'.csv')).open('w',encoding='utf-8',newline='') as handle:
            writer = csv.DictWriter(handle,fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    proposal = json.loads(contract.read_text(encoding='utf-8'))
    inputs = [contract, ROOT/'config/model.yaml', ROOT/proposal['database']]
    result = dict(transformation='capacity-contract-v1', activation=False,
        inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        coverage_rows=len(coverage),faxe_different_days=len(differences),
        missing_days=sum(r['missing_days'] for r in coverage),
        model_volume_comparisons='withheld: unsupported conversion and partial boundary')
    (output/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
