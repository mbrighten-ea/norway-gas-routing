"""Retain an offline capacity comparison with charts; never retrieve or solve."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ['baseline', 'evidence-backed', 'kollsnes-144.5', 'kollsnes-156',
             'kollsnes-autumn-early', 'kollsnes-autumn-late', 'karsto-97-proxy',
             'kollsnes-156-karsto-97-proxy']


def retain(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    if not run.is_relative_to(ROOT/'.scratch/runs') or output.parent != ROOT/'archive':
        raise ValueError('Use a scratch experiment and a new archive milestone')
    manifest = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    if manifest['years'] != [2024] or manifest['baseline_max_difference_bcm'] > 1e-9:
        raise ValueError('Only verified frozen 2024 capacity comparisons are supported')
    if manifest['holdout_loaded'] or manifest['public_capacity_replacements']:
        raise ValueError('Holdout access and unsupported public replacements are forbidden')
    monthly = pd.read_csv(run/'monthly_results.csv')
    annual = pd.read_csv(run/'annual_results.csv').set_index('scenario').loc[SCENARIOS]
    deltas = pd.read_csv(run/'annual_differences.csv').set_index('scenario').loc[SCENARIOS]
    constraints = pd.read_csv(run/'asset_constraints.csv')
    if len(monthly) != 96 or set(monthly.year) != {2024}:
        raise ValueError('Expected eight complete 2024 scenarios')
    output.mkdir()  # Never overwrite an existing milestone.
    for name in ['annual_results', 'annual_differences', 'monthly_results',
                 'monthly_differences', 'asset_constraints', 'arc_flows', 'node_balances',
                 'selected_capacity_inputs', 'baseline_replay']:
        shutil.copyfile(run/(name+'.csv'), output/(name+'.csv'))
    shutil.copyfile(run/'manifest.json', output/'manifest.json')
    shutil.copyfile(run/'annual_results.csv', output/'results.csv')
    binding = constraints.groupby(['scenario', 'asset']).binding.sum().unstack(fill_value=0).loc[SCENARIOS]
    binding.to_csv(output/'binding_months.csv')
    candidates = pd.read_csv(run/'database_candidates.csv')
    candidates.groupby(['asset_id', 'status', 'optimiser_eligible'], dropna=False).size().rename('observations').to_csv(output/'candidate_status_counts.csv')
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    charts = []

    def save(fig, name):
        fig.tight_layout()
        for extension in ['png', 'svg']:
            path = output/(name+'.'+extension)
            fig.savefig(path, dpi=160, facecolor='white')
            if extension == 'svg':
                path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8')
        plt.close(fig)
        charts.append(name)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for scenario in ['baseline', 'kollsnes-144.5', 'kollsnes-156', 'karsto-97-proxy']:
        part = monthly.loc[monthly.scenario.eq(scenario)].set_index('month')
        axes[0].plot(part.index, part.total_exports_bcm, marker='o', label=scenario)
        axes[1].plot(part.index, part.total_unrouted_bcm, marker='o', label=scenario)
    axes[0].set(title='Frozen 2024 capacity sensitivities — hypothetical plant assumptions', ylabel='Exports (bcm/month)')
    axes[1].set(ylabel='Unrouted (bcm/month)')
    axes[0].legend(ncol=2)
    axes[1].tick_params(axis='x', rotation=45)
    save(fig, 'monthly_exports_unrouted')

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, metric, title in zip(axes, ['total_exports_bcm', 'total_unrouted_bcm'], ['Export change', 'Unrouted change']):
        ax.barh(SCENARIOS, deltas[metric], color='#246b91')
        ax.set(title=title, xlabel='Annual difference from baseline (bcm)')
        ax.axvline(0, color='grey', linewidth=.8)
    save(fig, 'annual_impacts')

    fig, ax = plt.subplots(figsize=(12, 6))
    deltas[['UK', 'FR', 'BE', 'NL', 'DE', 'DK', 'PL']].plot.bar(ax=ax)
    ax.set(title='Seven-destination changes — fixed baseline preferences', ylabel='Annual difference (bcm)', xlabel='')
    ax.tick_params(axis='x', rotation=25)
    ax.legend(ncol=7)
    save(fig, 'destination_changes')

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    for column, asset in enumerate(['KOLLSNES_EXPORT', 'KARSTO_PROCESSING']):
        for scenario in ['baseline', 'kollsnes-144.5', 'kollsnes-156', 'karsto-97-proxy']:
            part = monthly.loc[monthly.scenario.eq(scenario)].set_index('month')
            axes[0, column].plot(part.index, part[asset+'_flow_bcm'], label=scenario)
            axes[1, column].plot(part.index, part[asset+'_utilisation_pct'], label=scenario)
        axes[0, column].set(title=asset, ylabel='Throughput (bcm/month)')
        axes[1, column].set(ylabel='Capacity utilisation (%)')
        axes[1, column].tick_params(axis='x', rotation=45)
    axes[0, 0].legend(fontsize=9)
    save(fig, 'plant_throughput_utilisation')

    caveat = ('One-off authorised frozen 2024 model-to-model comparison, not forecasting or validation. '
              'Evidence-backed mode retains baseline: no public candidate is eligible. Kollsnes 144.5/156 and '
              'Kårstø 97 are hypothetical dry-boundary assumptions. Signed Kollsnes maintenance is preserved once. '
              'Autumn endpoints both give 156 throughout 2024; they cannot identify the commissioning date. '
              'ENTSOG energy conversions remain inactive. Default settings and 2026 holdout remain unchanged.')
    body = '<h1>2024 capacity sensitivity</h1><p>'+html.escape(caveat)+'</p>'
    body += '<p>Maximum baseline replay difference: '+str(manifest['baseline_max_difference_bcm'])+' bcm.</p>'
    body += '<h2>Annual results</h2>'+annual[['total_exports_bcm', 'total_unrouted_bcm', 'mapped_disposal_bcm', 'UNMAPPED_bcm']].to_html(float_format=lambda v: f'{v:.6f}')
    body += '<h2>Binding months</h2>'+binding.loc[:, binding.sum().gt(0)].to_html()
    for name in charts:
        body += f'<img src="{name}.png" alt="{name.replace("_", " ")}" style="width:100%;max-width:1100px">'
    links = [p.name for p in output.iterdir() if p.suffix in ['.csv', '.json', '.svg']]
    body += '<h2>Data and provenance</h2><ul>'+''.join(f'<li><a href="{n}">{n}</a></li>' for n in sorted(links))+'</ul>'
    (output/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>2024 capacity sensitivity</title><style>body{font:16px Arial;max-width:1200px;margin:32px auto;padding:20px;color:#17334a}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccd6df}</style>'+body, encoding='utf-8')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}
    (output/'report_artifact_hashes.json').write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    retain(args.run, args.output)
