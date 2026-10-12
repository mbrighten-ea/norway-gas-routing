"""Read-only checks of saved evidence and frozen network constraints."""
import hashlib
import json
from pathlib import Path
import networkx as nx
import pandas as pd
import yaml
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.artifacts import first_solve_file, verify_first_solve, original_bytes
out=ROOT/'outputs/benchmark'
v=pd.read_csv(out/'provenance/forecast_verification.csv')
assert len(v)==120 and v.verified_future_forecast.all()
manifest=json.loads((out/'provenance/run_manifest.json').read_text())
archive=ROOT/'archive/20261008-01_first-solve'
verify_first_solve(ROOT)
for path,digest in manifest['protected_sha256'].items():
    assert hashlib.sha256(original_bytes(ROOT,path)).hexdigest()==digest,path
assert hashlib.sha256(original_bytes(ROOT,'scripts/build_initial_benchmark.py')).hexdigest()==manifest['code_sha256']
network=yaml.safe_load(first_solve_file(ROOT,'outputs/poc/network_definition.yaml').read_text())
graph=nx.DiGraph([(a['from'],a['to']) for a in network['arcs'] if a.get('kind')!='accounting'])
graph.add_nodes_from(network['nodes'])
cases=[('KARSTO_PROCESSING','KARSTO_FEED','DK'),('OGT','OSEBERG','UK'),
       ('EUROPIPE_II','KARSTO_FEED','DK'),('NORTH_SEA_ENTRY','KARSTO_FEED','PL'),
       ('BALTIC_PIPE','KARSTO_FEED','PL')]
checks={}
for arc,source,target in cases:
    candidate=graph.copy()
    entry=next(a for a in network['arcs'] if a['id']==arc)
    candidate.remove_edge(entry['from'],entry['to'])
    checks[arc]=not nx.has_path(candidate,source,target)
assert all(checks.values()),checks
print('120 forecast points, original hashes and constraint paths verified; saved evidence unchanged:',checks)
