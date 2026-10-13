"""Common fixed schematic geometry, interactive Plotly figures and static exports."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .data import COLORS, COUNTRIES, GROUPS, NAMES, TOL, safe_percent, shares, strict_sum

# Layout coordinates, not surveyed coordinates. No GIS or physical geometry claim.
# North Sea sources sit between western UK and eastern Norwegian processing sites.
POSITIONS = {
    'NYHAMNA_FEED': (8.2, 11.25), 'NYHAMNA': (7.3, 10.75),
    'KOLLSNES_FEED': (9.4, 9.1), 'KOLLSNES': (8.2, 8.4),
    'KARSTO_FEED': (10.3, 6.8), 'KARSTO': (9.0, 6.1),
    'OSEBERG': (5.4, 10.2), 'HEIMDAL_BYPASS': (4.3, 9.0),
    'SLEIPNER': (5.3, 7.15), 'CORE': (6.2, 5.8),
    'UK_DIRECT': (1.4, 9.0), 'EKOFISK_FEED': (3.6, 5.6), 'EKOFISK': (4.5, 4.2),
    'EUROPIPE_II_SPLIT': (8.5, 4.0), 'EMDEN_POOL': (6.8, 2.3),
    'DANISH_TRANSIT': (10.5, 3.9), 'FAXE': (11.9, 2.25),
    'UK': (1.1, 6.3), 'FR': (2.5, .65), 'BE': (4.5, .65), 'NL': (6.6, .65),
    'DE': (8.8, .65), 'DK': (12.15, 4.8), 'PL': (12.15, .65),
    'UNMAPPED': (11.2, 10.7), 'UNROUTED': (11.2, 9.5)}
LABELS = {'NYHAMNA_FEED': 'Nyhamna fields', 'NYHAMNA': 'Nyhamna', 'KOLLSNES_FEED': 'Kollsnes fields',
    'KOLLSNES': 'Kollsnes', 'KARSTO_FEED': 'Kårstø fields', 'KARSTO': 'Kårstø',
    'OSEBERG': 'Oseberg', 'HEIMDAL_BYPASS': 'Heimdal', 'SLEIPNER': 'Sleipner fields',
    'CORE': 'Sleipner / Draupner', 'UK_DIRECT': 'UK-direct fields', 'EKOFISK_FEED': 'Ekofisk fields',
    'EKOFISK': 'Ekofisk', 'EUROPIPE_II_SPLIT': 'Europipe II shared split',
    'EMDEN_POOL': 'Shared DE / NL landing pool', 'DANISH_TRANSIT': 'North Sea Entry / Nybro',
    'FAXE': 'Faxe', **NAMES}
# Quadratic offsets separate parallel paths. Label positions keep essential routes readable.
OFFSETS = {'LANGELED_NORTH': -.55, 'LANGELED_SOUTH': -.6, 'VESTERLED': -.35,
    'ZEEPIPE_IIA': -.5, 'ZEEPIPE_IIB': .5, 'EUROPIPE_I': -.65,
    'CORE_EKOFISK': -.15, 'FRANPIPE': -.9, 'ZEEPIPE_EXPORT': .25,
    'EUROPIPE_II_DORNUM': -.25, 'NORPIPE': -.35, 'UK_DIRECT_PROXY': -.25}
LINE_LABELS = {
    'LANGELED_NORTH': (6.85, 9.0), 'LANGELED_SOUTH': (3.2, 6.65),
    'VESTERLED': (2.2, 7.7), 'ZEEPIPE_IIA': (6.45, 7.65), 'ZEEPIPE_IIB': (8.4, 7.3),
    'KARSTO_STATPIPE': (7.75, 5.75), 'EUROPIPE_II': (9.7, 5.1),
    'EUROPIPE_I': (6.5, 4.25), 'CORE_EKOFISK': (5.1, 4.95), 'NORPIPE': (4.55, 2.6),
    'ZEEPIPE_EXPORT': (5.15, 3.2), 'FRANPIPE': (3.0, 3.5),
    'NORTH_SEA_ENTRY': (10.0, 3.15), 'BALTIC_PIPE': (11.4, 1.4),
    'OGT': (4.35, 10.35), 'HEIMDAL_STATPIPE': (5.1, 8.15)}
ARC_NAMES = {'ZEEPIPE_EXPORT': 'Zeepipe', 'CORE_EKOFISK': 'Draupner–Ekofisk',
    'KARSTO_STATPIPE': 'Kårstø–Draupner', 'HEIMDAL_STATPIPE': 'Heimdal–Statpipe',
    'NORTH_SEA_ENTRY': 'North Sea Entry', 'ZEEPIPE_IIA': 'Zeepipe IIA',
    'ZEEPIPE_IIB': 'Zeepipe IIB', 'LANGELED_NORTH': 'Langeled North',
    'LANGELED_SOUTH': 'Langeled South', 'EUROPIPE_I': 'Europipe I',
    'EUROPIPE_II': 'Europipe II', 'BALTIC_PIPE': 'Baltic Pipe'}


def curve(row):
    x1, y1 = POSITIONS[row['from']]
    x2, y2 = POSITIONS[row['to']]
    bend = OFFSETS.get(row.arc, 0)
    length = max(np.hypot(x2-x1, y2-y1), .1)
    control = ((x1+x2)/2-(y2-y1)/length*bend, (y1+y2)/2+(x2-x1)/length*bend)
    t = np.linspace(0, 1, 35)
    x = (1-t)**2*x1+2*(1-t)*t*control[0]+t**2*x2
    y = (1-t)**2*y1+2*(1-t)*t*control[1]+t**2*y2
    return x, y


def utilisation_color(value):
    if pd.isna(value): return '#9ca7b2'
    if value >= 99.999: return '#b64c42'
    if value >= 95: return '#c58c38'
    return '#428b96'


def fmt(value, suffix='', digits=2):
    return f'{value:.{digits}f}{suffix}' if pd.notna(value) else 'Unavailable'


def style(fig, title, height=520):
    fig.update_layout(template='plotly_white', title=dict(text=title, x=.02, y=.98, yanchor='top',
        font=dict(size=20, color='#172f45')), font=dict(family='Arial, sans-serif', size=13, color='#33465a'),
        height=height, margin=dict(l=65, r=35, t=110, b=60), paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff', legend=dict(orientation='h', y=1.03, x=0, font=dict(size=12)),
        hoverlabel=dict(font_size=13), hovermode='closest')
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#e7edf2', zerolinecolor='#8d9ba8')
    return fig


def network_figure(run, map_data, assets, monthly, period):
    fig = go.Figure()
    totals = {col: strict_sum(monthly[col]) for col in ['supply_bcm', 'exports_bcm', 'unrouted_bcm', 'unmapped_bcm', 'mapped_disposal_bcm']}
    maximum = map_data.loc[map_data.kind.ne('accounting'), 'flow_bcm'].max()
    for _, row in map_data.loc[map_data.kind.ne('accounting')].iterrows():
        if row['from'] not in POSITIONS or row['to'] not in POSITIONS:
            raise ValueError('Topology changed: reviewed schematic positions are required for new nodes')
        x, y = curve(row)
        color = utilisation_color(row.utilisation_pct)
        hover = (f'<b>{ARC_NAMES.get(row.arc, row.arc.replace("_", " "))}</b><br>'
            f'{LABELS.get(row["from"], row["from"])} → {LABELS.get(row["to"], row["to"])}<br>'
            f'Flow: {fmt(row.flow_bcm)} bcm<br>Modelled capacity: {fmt(row.capacity_bcm)} bcm<br>'
            f'Utilisation: {fmt(row.utilisation_pct, "%", 1)}<br>Kind: {row.kind}<br>'
            'No capacity denominator assigned to an unconstrained allocation proxy.' if pd.isna(row.capacity_bcm) else
            f'<b>{ARC_NAMES.get(row.arc, row.arc.replace("_", " "))}</b><br>'
            f'Flow: {fmt(row.flow_bcm)} bcm<br>Modelled capacity: {fmt(row.capacity_bcm)} bcm<br>'
            f'Asset utilisation: {fmt(row.utilisation_pct, "%", 1)}<br>'
            f'Binding months: {int(row.binding_months)} of {len(monthly)}<br>Kind: {row.kind}')
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', showlegend=False,
            line=dict(color=color, width=1.5+6*max(row.flow_bcm, 0)/max(maximum, 1e-12),
                dash='dash' if row.kind == 'allocation proxy' else 'solid'),
            text=[hover]*len(x), hovertemplate='%{text}<extra></extra>', name=row.arc))
        if row.arc in LINE_LABELS:
            lx, ly = LINE_LABELS[row.arc]
            fig.add_annotation(x=lx, y=ly, text=f'<b>{ARC_NAMES.get(row.arc, row.arc.replace("_", " "))}</b><br>'
                f'{fmt(row.flow_bcm)} / {fmt(row.capacity_bcm)} bcm<br>{fmt(row.utilisation_pct, "% used", 1)}', showarrow=False,
                font=dict(size=11, color=color), bgcolor='rgba(255,255,255,.93)', borderpad=3)
    for node, definition in run['network']['nodes'].items():
        if node in ['UNMAPPED', 'UNROUTED']: continue
        x, y = POSITIONS[node]
        kind = definition['kind']
        volume = strict_sum(monthly[node]) if node in COUNTRIES else None
        label = LABELS.get(node, node)
        if volume is not None: label += f'<br><b>{volume:.2f} bcm</b>'
        if node in ['KOLLSNES', 'KARSTO', 'NYHAMNA']:
            key = {'KOLLSNES': 'KOLLSNES_EXPORT', 'KARSTO': 'KARSTO_PROCESSING', 'NYHAMNA': 'NYHAMNA_EXPORT'}[node]
            cap = assets.set_index('asset').loc[key]
            label += f'<br>{cap.asset_flow_bcm:.2f} / {cap.capacity_bcm:.2f} bcm'
        fig.add_trace(go.Scatter(x=[x], y=[y], mode='markers', showlegend=False,
            marker=dict(size=17 if node in COUNTRIES else 11, color=COLORS.get(node, '#173e56'),
                symbol='diamond' if kind == 'source' else 'circle', line=dict(color='white', width=2)),
            text=[definition.get('label', node)], hovertemplate='%{text}<extra></extra>'))
        offset = -29 if node in ['CORE', 'EMDEN_POOL', 'KARSTO', 'FAXE', 'DANISH_TRANSIT', 'EUROPIPE_II_SPLIT'] else 27
        fig.add_annotation(x=x, y=y, text=label, yshift=offset, showarrow=False,
            font=dict(size=12 if node in COUNTRIES else 11), bgcolor='rgba(255,255,255,.91)', borderpad=2)
    fig.add_annotation(x=11.6, y=10.85, text='<b>Supply reconciliation</b><br>'+
        '<br>'.join(f'{label}: {totals[col]:.2f} bcm' for label, col in
        [('Pipeline supply', 'supply_bcm'), ('Exported', 'exports_bcm'), ('Unrouted', 'unrouted_bcm'),
         ('Unclassified', 'unmapped_bcm'), ('Mapped disposal', 'mapped_disposal_bcm')]),
        showarrow=False, align='left', bgcolor='#edf3f6', borderpad=12, font=dict(size=12))
    for color, label in [('#428b96', '<95% utilisation'), ('#c58c38', '95–100% utilisation'),
                         ('#b64c42', 'Binding / 100%'), ('#9ca7b2', 'No model capacity')]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', name=label, line=dict(color=color, width=4)))
    style(fig, f'Norwegian gas routing network · {period}', 830)
    fig.update_layout(margin=dict(l=15, r=15, t=85, b=15), legend=dict(y=1.015, x=.025),
        annotations=list(fig.layout.annotations)+[dict(x=.02, y=.025, xref='paper', yref='paper',
            text='N ↑  Fixed North Sea schematic. Routes are approximate; dashed links are allocation proxies.<br>'
                 'Labels: flow / modelled capacity. Hover for utilisation. Accounting disposal is excluded from pipelines.',
            showarrow=False, align='left', font=dict(size=11, color='#5f7385'))])
    fig.update_xaxes(range=[.2, 13.2], visible=False)
    fig.update_yaxes(range=[-.35, 12.05], visible=False)
    return fig


def monthly_figure(comparison, level, title):
    names = COUNTRIES if level == 'countries' else list(GROUPS)
    columns, rows = (2, 4) if level == 'countries' else (2, 3)
    fig = make_subplots(rows=rows, cols=columns, subplot_titles=[NAMES.get(n, n) for n in names],
        vertical_spacing=.09, horizontal_spacing=.1)
    for index, destination in enumerate(names):
        data = comparison.loc[comparison.level.eq(level) & comparison.destination.eq(destination)]
        row, col = index//columns+1, index%columns+1
        for column, label, dash, color in [('model_bcm', 'Routing reconstruction / diagnostic', 'solid', COLORS[destination]),
            ('legacy_model_bcm', 'Legacy model forecast', 'dash', COLORS[destination]),
            ('actual_chart_bcm', 'EA historical actuals', 'solid', '#172f45'),
            ('ea_net_context_bcm', 'EA Denmark net actuals (context)', 'dot', '#a0a8b1')]:
            if column in data and data[column].notna().any():
                fig.add_trace(go.Scatter(x=data.month, y=data[column], mode='lines+markers', name=label,
                    legendgroup=column, showlegend=index == 0, connectgaps=False,
                    line=dict(color=color, width=2.7 if column == 'model_bcm' else 2, dash=dash),
                    marker=dict(size=5), customdata=data.status,
                    hovertemplate='%{x}<br>%{y:.3f} bcm/month<br>%{customdata}<extra>'+label+'</extra>'), row=row, col=col)
        if not data.legacy_model_bcm.notna().any():
            axis_id = index+1
            fig.add_annotation(x=.5, y=1.025, xref=f'x{axis_id if axis_id>1 else ""} domain',
                yref=f'y{axis_id if axis_id>1 else ""} domain', text='Legacy model output unavailable',
                showarrow=False, font=dict(size=10, color='#8c6b32'))
    style(fig, title, 980 if level == 'countries' else 780)
    fig.update_xaxes(tickangle=-30, nticks=6)
    fig.update_yaxes(title_text='bcm/month', rangemode='tozero')
    fig.update_layout(margin=dict(t=135), legend=dict(y=1.045))
    return fig


def annual_figure(annual, title):
    fig = make_subplots(rows=1, cols=2, subplot_titles=['Seven countries', 'Original five destination groups'], horizontal_spacing=.12)
    for col, level in [(1, 'countries'), (2, 'groups')]:
        names = COUNTRIES if level == 'countries' else list(GROUPS)
        data = annual.loc[annual.level.eq(level)].set_index('destination').reindex(names)
        for key, name, pattern, opacity in [('model_bcm', 'Routing model', '', 1),
            ('legacy_model_bcm', 'Legacy model forecast', '/', .55),
            ('actual_chart_bcm', 'EA historical actuals', '', 1)]:
            if key not in data: continue
            fig.add_trace(go.Bar(x=[NAMES.get(n, n) for n in names], y=data[key], name=name,
                legendgroup=key, showlegend=col == 1, marker=dict(color='#172f45' if key=='actual_chart_bcm' else [COLORS[n] for n in names],
                pattern_shape=pattern), opacity=opacity, hovertemplate='%{x}<br>%{y:.3f} bcm<extra>'+name+'</extra>'), row=1, col=col)
    style(fig, title, 560)
    fig.update_layout(barmode='group')
    fig.update_yaxes(title_text='bcm in stated period', rangemode='tozero')
    fig.update_xaxes(tickangle=-30)
    return fig


def totals_figure(model, allocated, named, title):
    fig=go.Figure(go.Bar(x=['Routing pipeline exports','Legacy five-group allocations','Legacy declared Gassco total'],
        y=[model,allocated,named],marker_color=['#285d7c','#809aab','#b7bec6'],
        text=[fmt(v) if pd.notna(v) else 'Unavailable' for v in [model,allocated,named]],textposition='outside',
        hovertemplate='%{x}<br>%{y:.3f} bcm<extra></extra>'))
    style(fig,title,350);fig.update_yaxes(title_text='bcm in selected period',rangemode='tozero')
    return fig


def difference_figure(comparison, title):
    groups = comparison.loc[comparison.level.eq('groups')]
    months = groups.month.unique().tolist()
    z = groups.pivot(index='destination', columns='month', values='delta_bcm').reindex(index=list(GROUPS), columns=months)
    maximum = z.abs().max().max()
    maximum = max(float(maximum), .1) if pd.notna(maximum) else 1
    fig = go.Figure(go.Heatmap(x=months, y=[NAMES.get(n, n) for n in GROUPS], z=z.to_numpy(),
        zmin=-maximum, zmax=maximum, colorscale=[[0, '#387eae'], [.5, '#f9fafb'], [1, '#c66648']],
        hoverongaps=False, colorbar=dict(title='bcm'), xgap=3, ygap=3,
        hovertemplate='%{y}<br>%{x}<br>Routing − legacy: %{z:.3f} bcm<extra></extra>'))
    style(fig, title, 390)
    if not z.notna().any().any():
        fig.add_annotation(x=.5, y=.5, xref='paper', yref='paper', text='No comparable legacy model outputs in this period', showarrow=False)
    return fig


def shares_figure(comparison, title):
    groups = comparison.loc[comparison.level.eq('groups')]
    months = groups.month.unique().tolist()
    fig = make_subplots(rows=2, cols=1, subplot_titles=['Routing model: shares of exported gas', 'Legacy: shares of allocated forecast gas'], vertical_spacing=.15)
    for row, column in [(1, 'model_bcm'), (2, 'legacy_model_bcm')]:
        values = groups.pivot(index='month', columns='destination', values=column).reindex(index=months, columns=list(GROUPS))
        fractions = values.apply(lambda v: shares(v), axis=1)
        for name in GROUPS:
            fig.add_trace(go.Bar(x=months, y=fractions[name], name=NAMES.get(name, name), legendgroup=name,
                showlegend=row == 1, marker_color=COLORS[name], hovertemplate='%{x}<br>%{y:.1f}%<extra>'+NAMES.get(name, name)+'</extra>'), row=row, col=1)
        fig.update_yaxes(range=[0, 100], title_text='% of allocated exports', row=row, col=1)
    style(fig, title, 620)
    fig.update_layout(barmode='stack')
    return fig


def supply_figure(monthly, title):
    fig = go.Figure()
    for key, label, color in [('exports_bcm', 'Exported gas', '#285d7c'), ('mapped_disposal_bcm', 'Mapped-source disposal', '#c88a44'),
                              ('unmapped_bcm', 'Unclassified / UNMAPPED', '#b6bec7')]:
        fig.add_trace(go.Bar(x=monthly.month, y=monthly[key], name=label, marker_color=color,
            hovertemplate='%{x}<br>%{y:.3f} bcm<extra>'+label+'</extra>'))
    fig.add_trace(go.Scatter(x=monthly.month, y=monthly.supply_bcm, name='Total pipeline supply', mode='markers',
        marker=dict(color='#172f45', symbol='line-ew', size=16), hovertemplate='%{x}<br>%{y:.3f} bcm<extra>Supply</extra>'))
    style(fig, title, 410)
    fig.update_layout(barmode='stack')
    fig.update_yaxes(title_text='bcm/month', rangemode='tozero')
    return fig


def capacity_figure(assets, title):
    data = assets.sort_values('utilisation_pct', ascending=True)
    fig = go.Figure(go.Bar(x=data.utilisation_pct, y=data.asset.str.replace('_', ' '), orientation='h',
        marker_color=[utilisation_color(v) for v in data.utilisation_pct],
        customdata=data[['asset_flow_bcm', 'capacity_bcm', 'binding_months', 'high_utilisation_months']],
        hovertemplate='%{y}<br>%{x:.1f}% utilisation<br>%{customdata[0]:.3f} bcm flow / %{customdata[1]:.3f} bcm modelled capacity<br>'
            '%{customdata[2]} binding months; %{customdata[3]} months ≥95%<extra></extra>'))
    style(fig, title, 690)
    fig.update_xaxes(range=[0, 105], title_text='% of saved modelled capacity')
    fig.update_layout(margin=dict(l=220, r=35, t=75, b=60), showlegend=False)
    return fig


def static_exports(run, monthly, maps, assets, comparison, annual, output, label, named_legacy_total=np.nan):
    """Matplotlib exports use the same prepared data as interactive figures."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'axes.titleweight': 'bold',
        'axes.spines.top': False, 'axes.spines.right': False, 'svg.fonttype': 'none'})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = []

    def save(fig, name, title, note):
        fig.suptitle(title, x=.04, ha='left', fontsize=18, color='#172f45', y=.98)
        fig.text(.04, .015, note, fontsize=10, color='#5f7080')
        for extension in ['png', 'svg']:
            path = output/f'{name}.{extension}'
            fig.savefig(path, dpi=200, facecolor='white', bbox_inches='tight')
            files.append(path)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(18, 13))
    fig.subplots_adjust(left=.035, right=.97, top=.91, bottom=.08)
    maximum = maps.loc[maps.kind.ne('accounting'), 'flow_bcm'].max()
    for _, edge in maps.loc[maps.kind.ne('accounting')].iterrows():
        x, y = curve(edge)
        ax.plot(x, y, color=utilisation_color(edge.utilisation_pct), linewidth=1.5+6*edge.flow_bcm/maximum,
            linestyle='--' if edge.kind == 'allocation proxy' else '-', solid_capstyle='round', alpha=.85)
        if edge.arc in LINE_LABELS:
            x, y = LINE_LABELS[edge.arc]
            ax.text(x, y, f'{ARC_NAMES.get(edge.arc, edge.arc.replace("_", " "))}\n{edge.flow_bcm:.2f} / {fmt(edge.capacity_bcm)} bcm\n{fmt(edge.utilisation_pct, "% used", 1)}',
                ha='center', va='center', fontsize=10, color=utilisation_color(edge.utilisation_pct),
                bbox=dict(facecolor='white', edgecolor='none', pad=2, alpha=.95))
    for node, definition in run['network']['nodes'].items():
        if node in ['UNMAPPED', 'UNROUTED']: continue
        x, y = POSITIONS[node]
        ax.scatter([x], [y], s=160 if node in COUNTRIES else 85, c=[COLORS.get(node, '#173e56')],
            marker='D' if definition['kind'] == 'source' else 'o', edgecolors='white', zorder=5)
        text = LABELS.get(node, node)
        if node in COUNTRIES: text += f'\n{monthly[node].sum():.2f} bcm'
        if node in ['KOLLSNES', 'KARSTO', 'NYHAMNA']:
            key = {'KOLLSNES': 'KOLLSNES_EXPORT', 'KARSTO': 'KARSTO_PROCESSING', 'NYHAMNA': 'NYHAMNA_EXPORT'}[node]
            cap = assets.set_index('asset').loc[key]
            text += f'\n{cap.asset_flow_bcm:.2f} / {cap.capacity_bcm:.2f} bcm'
        down = node in ['CORE', 'EMDEN_POOL', 'KARSTO', 'FAXE', 'DANISH_TRANSIT', 'EUROPIPE_II_SPLIT']
        ax.text(x, y+(-.29 if down else .26), text, ha='center', va='top' if down else 'bottom', fontsize=11,
            bbox=dict(facecolor='white', edgecolor='none', alpha=.9, pad=2), zorder=6)
    ax.text(10.3, 11.35, 'Pipeline supply  '+fmt(monthly.supply_bcm.sum())+' bcm\nExported gas     '+fmt(monthly.exports_bcm.sum())+
        ' bcm\nUnrouted supply  '+fmt(monthly.unrouted_bcm.sum())+' bcm\n  Unclassified  '+fmt(monthly.unmapped_bcm.sum())+
        ' bcm\n  Mapped disposal '+fmt(monthly.mapped_disposal_bcm.sum())+' bcm', ha='left', va='top', fontsize=11,
        bbox=dict(facecolor='#edf3f6', edgecolor='none', pad=12))
    ax.legend(handles=[Line2D([0], [0], color=c, linewidth=4, label=t) for c,t in
        [('#428b96', '<95% utilised'), ('#c58c38', '≥95% utilised'), ('#b64c42', 'Binding / 100%'),
         ('#9ca7b2', 'No capacity denominator')]], loc='upper left', ncol=4, frameon=False, fontsize=11)
    ax.set(xlim=(.15, 13.4), ylim=(-.15, 12.0)); ax.axis('off')
    save(fig, 'network_map', f'Norwegian gas routing network · {label}',
        'Fixed North Sea schematic; routes are not GIS geometry. Flow / modelled capacity in bcm. Dashed links: allocation proxies. Disposal is accounting, not proven curtailment.')

    for level, names, dims, filename in [('countries', COUNTRIES, (4, 2), 'monthly_seven_countries'),
        ('groups', list(GROUPS), (3, 2), 'monthly_five_groups')]:
        fig, axes = plt.subplots(*dims, figsize=(16, 12 if level == 'countries' else 10))
        fig.subplots_adjust(top=.86, bottom=.09, hspace=.58, wspace=.2)
        for ax, name in zip(axes.flat, names):
            part = comparison.loc[comparison.level.eq(level) & comparison.destination.eq(name)]
            x = np.arange(len(part))
            for column, legend, line, color in [('model_bcm', 'Routing model', '-', COLORS[name]),
                ('legacy_model_bcm', 'EA legacy forecast', '--', COLORS[name]),
                ('actual_chart_bcm', 'EA historical actuals', '-', '#172f45'),
                ('ea_net_context_bcm', 'EA signed DK net (context)', ':', '#9ba3ad')]:
                if column in part and part[column].notna().any(): ax.plot(x, part[column], line, color=color, linewidth=2.5, marker='o', markersize=3, label=legend)
            if not part.legacy_model_bcm.notna().any():
                ax.text(.5, 1.02, 'Legacy model output unavailable', transform=ax.transAxes, fontsize=10, color='#8c6b32', ha='center')
            if name in ['PL', 'Baltic Pipe'] and 'actual_chart_bcm' in part:
                ax.text(.5, -.22, 'EA Nybro history differs from Polish delivery', transform=ax.transAxes, fontsize=10, color='#8c6b32', ha='center')
            ax.set_title(NAMES.get(name, name), color=COLORS[name], y=1.14); ax.set_ylabel('bcm/month')
            ax.set_xticks(x[::2], part.month.str[5:][::2], rotation=0)
            low, high = ax.get_ylim(); ax.set_ylim(min(0, low), high)
            ax.grid(axis='y', alpha=.18)
        for ax in list(axes.flat)[len(names):]: ax.axis('off')
        axes.flat[0].legend(loc='upper left', bbox_to_anchor=(0, 1.43), ncol=3, frameon=False, fontsize=11)
        save(fig, filename, f'Monthly destination allocations · {label}',
             'Dark line: EA historical actuals. Country colour: reconstruction / diagnostic; dashed: EA archived forecast. DK is signed net context; Polish export actuals withheld.')

    if 'legacy_error_bcm' in comparison:
        fig, axes = plt.subplots(3, 2, figsize=(16, 10))
        fig.subplots_adjust(top=.84, bottom=.1, hspace=.6, wspace=.2)
        for ax, name in zip(axes.flat, GROUPS):
            part = comparison.loc[comparison.level.eq('groups') & comparison.destination.eq(name)]
            x = np.arange(len(part))
            ax.axhline(0, color='#657587', linewidth=1)
            ax.plot(x, part.legacy_error_bcm, color=COLORS[name], linewidth=2.5, marker='o', markersize=4)
            ax.set_title(NAMES[name], color=COLORS[name]); ax.set_ylabel('Forecast minus actual, bcm/month')
            ax.set_xticks(x[::2], part.month.str[5:][::2]); ax.grid(axis='y', alpha=.18)
            if not part.legacy_error_bcm.notna().any():
                ax.text(.5, .5, 'Export-error score withheld\n'+('Nybro / Polish boundary differs' if name=='Baltic Pipe' else 'Signed net / gross boundary differs'),
                    transform=ax.transAxes, ha='center', color='#8c6b32', fontsize=12)
        axes.flat[-1].axis('off')
        axes.flat[-1].text(.02, .8, 'Routing forecast accuracy: unavailable\n\nSaved routing results use revised inputs.\nA complete origin SID bundle is needed\nbefore comparing forecast accuracy.',
            transform=axes.flat[-1].transAxes, va='top', color='#33465a', fontsize=13)
        save(fig, 'legacy_forecast_errors_against_actuals', 'EA legacy forecast errors against EA historical actuals\n'+label,
            'Positive error: forecast above actual. EA allocation-series definitions and source vintages apply. No routing reconstruction is scored as a forecast.')

    fig, axes = plt.subplots(1, 2, figsize=(17, 6.5))
    fig.subplots_adjust(top=.78, bottom=.24, wspace=.2)
    for ax, level, names in [(axes[0], 'countries', COUNTRIES), (axes[1], 'groups', list(GROUPS))]:
        part = annual.loc[annual.level.eq(level)].set_index('destination').reindex(names)
        x = np.arange(len(names))
        ax.bar(x-.26, part.model_bcm, .25, color=[COLORS[n] for n in names], label='Routing model')
        ax.bar(x, part.legacy_model_bcm, .25, color=[COLORS[n] for n in names], alpha=.5, hatch='//', label='Legacy forecast')
        if 'actual_chart_bcm' in part:
            ax.bar(x+.26, part.actual_chart_bcm, .25, color='#172f45', label='EA historical actuals')
        for i, value in enumerate(part.legacy_model_bcm):
            if pd.isna(value): ax.text(i, .4, 'n/a', rotation=90, color='#8c6b32', fontsize=10)
        ax.set_xticks(x, [NAMES.get(n, n).replace(' + ', '\n+ ') for n in names], rotation=25, ha='right')
        ax.set_ylabel('bcm in stated period'); ax.grid(axis='y', alpha=.15)
    axes[0].legend(ncol=3, loc='upper left', bbox_to_anchor=(0, 1.22), frameon=False)
    save(fig, 'annual_destination_comparison', f'Destination allocations · {label}',
         'Full-period totals require every month. EA actuals use original definitions; DK/net and PL/Nybro are withheld from gross-export comparisons. No country forecast disaggregation.')

    fig,ax=plt.subplots(figsize=(14,6));fig.subplots_adjust(top=.76,bottom=.19)
    quantities=[monthly.exports_bcm.sum(),strict_sum(annual.loc[annual.level.eq('groups'),'legacy_model_bcm']),named_legacy_total]
    ax.bar(range(3),quantities,color=['#285d7c','#809aab','#b7bec6'],width=.55)
    for i,value in enumerate(quantities):
        ax.text(i,value+.7 if pd.notna(value) else .5,fmt(value),ha='center',fontsize=14,color='#172f45')
    ax.set_xticks(range(3),['Routing pipeline exports','Legacy five-group allocations','Legacy declared Gassco total'])
    ax.set_ylabel('bcm in selected period');ax.grid(axis='y',alpha=.15)
    low,high=ax.get_ylim();ax.set_ylim(0,high*1.1)
    save(fig,'annual_export_totals',f'Pipeline exports and legacy declared totals · {label}',
         'Legacy declared Gassco total has its original supply/accounting boundary. No adjustment forces group sums or model exports to match. Incomplete periods remain unavailable.')

    z = comparison.loc[comparison.level.eq('groups')].pivot(index='destination', columns='month', values='delta_bcm').reindex(list(GROUPS))
    fig, ax = plt.subplots(figsize=(16, 5.8))
    fig.subplots_adjust(top=.83, bottom=.14, left=.19)
    maximum = max(z.abs().max().max(), .1) if z.notna().any().any() else 1
    image = ax.imshow(np.ma.masked_invalid(z.to_numpy()), cmap='RdBu_r', vmin=-maximum, vmax=maximum, aspect='auto')
    ax.set_xticks(np.arange(len(z.columns)), z.columns, rotation=30, ha='right')
    ax.set_yticks(np.arange(len(z)), [NAMES.get(n, n) for n in z.index])
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            value = z.iloc[i,j]
            ax.text(j, i, f'{value:+.2f}' if pd.notna(value) else 'n/a', ha='center', va='center',
                color='white' if pd.notna(value) and abs(value) > maximum*.65 else '#273d50', fontsize=11)
    fig.colorbar(image, ax=ax, label='Routing − legacy (bcm)', pad=.02)
    save(fig, 'model_legacy_differences', f'Monthly routing model minus legacy model · {label}',
        'Same month and original destination group. A missing comparator remains blank. Signed percentage differences are in comparison CSVs; no forecast-error claim.')

    fig, ax = plt.subplots(figsize=(16, 5.7))
    fig.subplots_adjust(top=.8, bottom=.15)
    x = np.arange(len(monthly)); base = np.zeros(len(monthly))
    for column, legend, color in [('exports_bcm', 'Exports', '#285d7c'), ('mapped_disposal_bcm', 'Mapped disposal', '#c88a44'), ('unmapped_bcm', 'UNMAPPED', '#b6bec7')]:
        ax.bar(x, monthly[column], bottom=base, color=color, label=legend); base += monthly[column].to_numpy()
    ax.plot(x, monthly.supply_bcm, 'k_', markersize=16, label='Pipeline supply')
    ax.set_xticks(x, monthly.month, rotation=30, ha='right'); ax.set_ylabel('bcm/month')
    ax.legend(ncol=4, loc='upper left', bbox_to_anchor=(0, 1.21), frameon=False); ax.grid(axis='y', alpha=.15)
    save(fig, 'supply_export_unrouted', f'Pipeline supply reconciliation · {label}',
        'Exports + mapped-source disposal + unclassified supply = pipeline supply. Model disposal does not demonstrate actual Norwegian production curtailment.')

    part = assets.sort_values('utilisation_pct')
    fig, ax = plt.subplots(figsize=(15, 10))
    fig.subplots_adjust(top=.88, bottom=.1, left=.29, right=.9)
    bars = ax.barh(part.asset.str.replace('_', ' '), part.utilisation_pct, color=[utilisation_color(v) for v in part.utilisation_pct])
    for bar, (_, row) in zip(bars, part.iterrows()):
        ax.text(min(row.utilisation_pct+1, 101), bar.get_y()+bar.get_height()/2,
                f'{row.utilisation_pct:.1f}%  ({int(row.binding_months)} binding months)', va='center', fontsize=10)
    ax.set(xlim=(0, 130), xlabel='Flow / aggregated saved modelled capacity (%)'); ax.axvline(100, color='#c5ced7', linewidth=1)
    ax.grid(axis='x', alpha=.15)
    save(fig, 'capacity_bottlenecks', f'Modelled capacity utilisation · {label}',
        'Annual capacity sums the selected monthly bcm limits. Binding-month counts retain seasonal bottlenecks. Public-capacity audit data are not used.')

    fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
    fig.subplots_adjust(top=.86, bottom=.14, hspace=.3)
    for ax, column, heading in [(axes[0], 'model_bcm', 'Routing model'), (axes[1], 'legacy_model_bcm', 'Legacy model forecast')]:
        part = comparison.loc[comparison.level.eq('groups')].pivot(index='month', columns='destination', values=column).reindex(columns=list(GROUPS))
        part = part.apply(shares, axis=1); base = np.zeros(len(part)); x=np.arange(len(part))
        for name in GROUPS:
            ax.bar(x, part[name], bottom=base, color=COLORS[name], label=NAMES.get(name,name)); base += part[name].to_numpy()
        ax.set(ylim=(0,100), ylabel='% allocated exports', title=heading)
        for i, row in part.iterrows():
            if row.isna().any(): ax.text(list(part.index).index(i), 50, 'n/a', ha='center', color='#8c6b32')
    axes[0].legend(ncol=5, loc='upper left', bbox_to_anchor=(0,1.33), frameon=False, fontsize=10)
    axes[1].set_xticks(x, part.index, rotation=30, ha='right')
    save(fig, 'allocation_shares', f'Destination shares of allocated exports · {label}',
        'Original five-group order. Incomplete or negative baskets have no share calculation. These are export shares; supply shares are separately provided in CSV.')

    groups = comparison.loc[comparison.level.eq('groups')]
    available = groups.pivot(index='month',columns='destination',values='legacy_model_bcm').reindex(columns=list(GROUPS))
    matched = available.index[available.notna().all(axis=1)].tolist()
    if matched and len(matched)!=len(monthly):
        fig,ax=plt.subplots(figsize=(14,6.5));fig.subplots_adjust(top=.74,bottom=.19)
        part=groups.loc[groups.month.isin(matched)].groupby('destination')[['model_bcm','legacy_model_bcm']].sum().reindex(list(GROUPS))
        x=np.arange(len(part));colors=[COLORS[n] for n in part.index]
        ax.bar(x-.2,part.model_bcm,.38,color=colors,label='Routing diagnostic')
        ax.bar(x+.2,part.legacy_model_bcm,.38,color=colors,hatch='//',alpha=.5,label='Legacy forecast')
        ax.set_xticks(x,[NAMES.get(n,n) for n in part.index]);ax.set_ylabel('bcm in matched months')
        ax.legend(ncol=2,loc='upper left',bbox_to_anchor=(0,1.22),frameon=False);ax.grid(axis='y',alpha=.15)
        save(fig,'matched_period_destination_comparison',f'Matched destination allocations · {matched[0]} to {matched[-1]}\n{run["title"]}\n{label.splitlines()[-1]}',
             'Only months with all five original legacy forecasts. This partial-period total is not a full-year legacy forecast.')

    # A one-page visual briefing, using finished figures' datasets rather than new calculations.
    fig=plt.figure(figsize=(16,9.5)); grid=fig.add_gridspec(2,2,top=.74,bottom=.1,left=.07,right=.95,hspace=.44,wspace=.35)
    total=monthly[['supply_bcm','exports_bcm','unrouted_bcm','unmapped_bcm','mapped_disposal_bcm']].sum()
    for x,(key,title) in zip([.07,.29,.51,.73],[('supply_bcm','PIPELINE SUPPLY'),('exports_bcm','EXPORTED'),('unmapped_bcm','UNCLASSIFIED'),('mapped_disposal_bcm','MAPPED DISPOSAL')]):
        fig.text(x,.82,title,fontsize=11,color='#5f7385');fig.text(x,.775,f'{total[key]:.2f} bcm',fontsize=23,color='#172f45')
    ax=fig.add_subplot(grid[:,0]);part=annual.loc[annual.level.eq('groups')].set_index('destination').reindex(list(GROUPS));x=np.arange(len(part))
    ax.barh(x+.18,part.model_bcm,.34,color=[COLORS[n] for n in part.index],label='Routing model')
    ax.barh(x-.18,part.legacy_model_bcm,.34,color=[COLORS[n] for n in part.index],hatch='//',alpha=.5,label='Legacy forecast')
    ax.set_yticks(x,[NAMES.get(n,n) for n in part.index]);ax.set_xlabel('bcm in selected period');ax.set_title('Destination allocations',loc='left',fontsize=14)
    ax.invert_yaxis();fig.legend(*ax.get_legend_handles_labels(),frameon=False,ncol=2,loc='upper left',bbox_to_anchor=(.065,.91),fontsize=11)
    ax.grid(axis='x',alpha=.15)
    if part.legacy_model_bcm.isna().any():ax.text(.02,.02,'Full-period legacy values unavailable',transform=ax.transAxes,color='#8c6b32',fontsize=10)
    ax=fig.add_subplot(grid[0,1]);top=assets.nlargest(5,'utilisation_pct').sort_values('utilisation_pct')
    ax.barh(top.asset.str.replace('_',' '),top.utilisation_pct,color=[utilisation_color(v) for v in top.utilisation_pct]);ax.set_xlim(0,105)
    ax.set_title('Highest aggregate capacity utilisation',loc='left',fontsize=14);ax.set_xlabel('% of saved modelled capacity');ax.tick_params(axis='y',labelsize=10)
    ax=fig.add_subplot(grid[1,1]);x=np.arange(len(monthly));base=np.zeros(len(monthly))
    for key,legend,color in [('exports_bcm','Exports','#285d7c'),('mapped_disposal_bcm','Mapped disposal','#c88a44'),('unmapped_bcm','UNMAPPED','#b6bec7')]:
        ax.bar(x,monthly[key],bottom=base,color=color,label=legend);base+=monthly[key].to_numpy()
    ax.set_xticks(x[::2],monthly.month.str[5:][::2]);ax.set_ylabel('bcm/month');ax.set_title('Supply reconciliation',loc='left',fontsize=14)
    ax.legend(ncol=3,frameon=False,loc='upper left',bbox_to_anchor=(0,1.03),fontsize=9)
    save(fig,'visual_summary',f'Norwegian gas routing briefing · {label}',
        'Reconstruction / diagnostic versus earlier legacy forecast; differences are not forecast errors. Modelled capacities only. Disposal is not proof of actual curtailment.')
    return files
