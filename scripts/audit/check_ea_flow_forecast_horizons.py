"""Check fresh EA archived horizons and rolling one-month errors within 2025."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.forecast_horizons import inspect_horizons


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start',default='2025-01')
    parser.add_argument('--end',default='2025-12')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/ea_flow_walk_forward')
    args=parser.parse_args()
    manifest=inspect_horizons(ROOT,args.output,args.start,args.end)
    print('Finite future values beyond one month:',manifest['future_values_beyond_one_month'])
    print('Graphics and CSVs:',args.output)


if __name__=='__main__':main()
