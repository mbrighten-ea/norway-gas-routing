"""Run a configured price-free routing package, or validate without constructing an LP."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.scratch/cache/matplotlib'))

# Keep the historical verifier's save_csv import compatible.
from norway_gas_routing.operational import execute_run, save_csv


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/run.yaml', help='Repository-relative historical/current-forecast YAML; current horizon defaults to 12 next-complete-month deliveries')
    parser.add_argument('--validate-only', action='store_true', help='Prepare/check inputs and write an unsolved analyst package; never construct or solve an LP')
    parser.add_argument('--solver', help='Override configured installed solver name')
    args = parser.parse_args(argv)
    try:
        _, code = execute_run(ROOT, args.config, validate_only=args.validate_only, solver_name=args.solver)
        return code
    except (ValueError, OSError, RuntimeError) as exc:
        print('BLOCKED: '+str(exc)+'\nReview config/run.yaml and README.md operator guide.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
