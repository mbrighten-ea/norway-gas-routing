"""Build a fresh offline SQLite database and CSVs from verified audit captures."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from norway_gas_routing.artifacts import new_experiment
from norway_gas_routing.public_capacity import build_database


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Fresh repository-local directory; default new named experiment')
    parser.add_argument('--from-day',default='2022-10-01')
    parser.add_argument('--to-day',default='2025-12-31')
    args=parser.parse_args()
    output=args.output or new_experiment(ROOT,'public-capacity-database')/'database'
    manifest=build_database(ROOT,output,args.from_day,args.to_day)
    print(output.resolve())
    print(manifest['counts'])


if __name__=='__main__':
    main()
