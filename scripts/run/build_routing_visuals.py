"""Build graphics from saved routing results and fresh EA/Shooju reference queries."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from norway_gas_routing.reporting.dashboard import build_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='append', help='Saved run folder; repeat to include multiple runs')
    parser.add_argument('--scenario', action='append', help='Scenario for corresponding --run, in the same order')
    parser.add_argument('--legacy-source', action='append', help='sid:YYYY-MM-DD; fresh Shooju archive query at each origin')
    parser.add_argument('--legacy-workbook', type=Path)
    parser.add_argument('--legacy-archive', type=Path, help='Verified retained forecast export folder; default outputs/benchmark')
    parser.add_argument('--topology', type=Path, help='Retained topology YAML; must match diagnostic manifest hash')
    parser.add_argument('--start', help='First reporting month YYYY-MM')
    parser.add_argument('--end', help='Last reporting month YYYY-MM')
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/routing_graphics')
    parser.add_argument('--html', action='store_true', help='Also create an optional self-contained dashboard')
    args = parser.parse_args()
    paths = args.run or ['outputs/reconstruction', 'archive/20261009-13_snohvit-sensitivity']
    scenarios = args.scenario or ([None]*len(paths) if args.run else ['refined_broader_boundary', 'official-net-production'])
    if len(scenarios) != len(paths):
        parser.error('--scenario must be supplied once per --run when used')
    runs = [(ROOT/path if not Path(path).is_absolute() else Path(path), scenario) for path, scenario in zip(paths, scenarios)]
    output, _ = build_package(ROOT, runs, args.output,
        args.legacy_source or ['sid:2023-12-31', 'sid:2024-12-31'],
        args.legacy_workbook, args.start, args.end, args.topology, args.legacy_archive,
        include_html=args.html)
    print(f'Graphics: {output / "details"}')
    print(f'Main CSV: {output / "results.csv"}')
    print(f'Figure index: {output / "figures.csv"}')
    if args.html:
        print(f'Optional dashboard: {output / "report.html"}')


if __name__ == '__main__':
    main()
