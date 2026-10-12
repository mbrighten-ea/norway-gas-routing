"""Query fresh origin SIDs and identify blockers before a routing forecast replay."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.config import load_config
from norway_gas_routing.sid_backtest import inspect_origin


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin',default='2024-12-31')
    parser.add_argument('--months-ahead',type=int,default=12,help='Use 1 for a rolling next-month readiness check')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/routing_validation_readiness')
    args=parser.parse_args()
    model,registry=load_config(ROOT/'config/model.yaml',ROOT/'config/data_series.csv')
    manifest=inspect_origin(ROOT,model,registry,args.output,args.origin,months_ahead=args.months_ahead)
    print('Origin:',manifest['origin'],'Status:',manifest['status'])
    print('Readiness tables:',args.output)
    print('No routing forecast solved or ranked; blockers are in provenance/run_manifest.json.')


if __name__=='__main__':
    main()
