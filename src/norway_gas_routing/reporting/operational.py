"""Excel-first immutable run packages; reporting never retrieves or solves.

Use the project's existing openpyxl dependency so the Python operator command
does not require a second language runtime or an artifact-authoring service.
The workbook is a labelled snapshot, not an editable alternative optimiser.
"""
from datetime import datetime
from html import escape
import math

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..operational import save_csv, save_current_forecast_table
from ..routing import DESTINATIONS, draw_network
from .assessment import STYLE, artifact_links, table
from .data import COLORS, GROUPS


DEFINITIONS = [
    ('Monthly flows', 'One target month. Seven nonnegative physical/allocation sinks in bcm; exports exclude unrouted gas. Unclassified supply is included in unrouted, never added twice.'),
    ('Capacities', 'One asset/month. Monthly available capacity is the calendar-day sum of technical minus signed maintenance mcm/day, divided by 1000. Shared asset limits apply to the sum of its arcs; monthly feasibility is not daily scheduling.'),
    ('Comparisons', 'One month/group. UK; FR+BE; NL+DE; Baltic Pipe (PL); DK. These overlap country rows and must not be added to them. Unavailable references and errors are missing, never zero.'),
    ('Network flows', 'One month/arc, including explicit disposal arcs. Arc flows can be nonunique. DE/NL are landing-pool allocation proxies; these are not observed nominations.'),
    ('Diagnostics', 'Independent solver mass balance/capacity residuals in bcm; not forecast accuracy. Unrouted gas is accounting disposal, not demonstrated curtailment.'),
    ('Input sources', 'Every required or consumed source and explicit assumption, with identifier, dates, units, transformation and availability status. Exact tables and source metadata are under provenance/inputs and provenance/source_metadata.json.'),
    ('Preferences', 'Static soft routing shares from earlier complete nonnegative seven-destination baskets; capacity constraints can force rerouting. Price-free objective: maximum exports, minimum L1 deviation, then smallest worst fractional shortfall.'),
    ('Settings', 'Resolved run request. Canonical model, registry, fixed evaluation policy and source code snapshots are in provenance; manifest records hashes and Git identity.'),
    ('Missing values', 'Unavailable means not retrieved, unsupported, incompatible or unsolved. It is never an assumed zero. Synthetic references are not invented.'),
    ('Boundaries', 'UK United Kingdom; FR France; BE Belgium; NL Netherlands; DE Germany; DK Danish gross sink; PL Poland delivery. Historical DK signed net allocation and Poland-labelled Nybro entry are incompatible gross-export comparisons.'),
    ('Country interpretation', 'UK combines receiving routes; FR/BE represent modelled Dunkerque/Zeebrugge corridors; DE/NL are country-allocation proxies in a shared landing pool; DK/PL are modelled corridor allocations. These seven sinks are not seven independently validated terminal forecasts. Combined comparison groups overlap them.'),
    ('Evaluation', 'Development through 2024-12; validation 2025 only for fixed candidate comparison. 2026 holdout locked. No forecast or revised-data fallback is implemented.'),
]


def result_tables(inputs, results, manifest):
    rows, comparisons, arcs = [], [], []
    months = pd.period_range(manifest['settings']['start'], manifest['settings']['end'], freq='M')
    for month in months:
        result = results.get(str(month))
        row = dict(month=month.start_time, **{d+'_volume_bcm': result['destinations'][d] if result else None for d in DESTINATIONS},
            total_exports_bcm=sum(result['destinations'].values()) if result else None,
            unrouted_supply_bcm=result['unrouted'] if result else None,
            pipeline_supply_proxy_bcm=float(inputs['supply'].loc[month].sum()) if inputs else None,
            unclassified_supply_bcm=float(inputs['supply'].at[month, 'UNMAPPED']) if inputs else None,
            solver_status=manifest['status'])
        rows.append(row)
        if manifest['settings']['mode']=='current_forecast':
            row['forecast_origin']=manifest['settings']['origin']
        for group, countries in GROUPS.items():
            actual = inputs['actual_comparisons'].at[month, group] if inputs and 'actual_comparisons' in inputs else None
            compatible = actual is not None and pd.notna(actual) and group not in {'DK', 'Baltic Pipe'}
            modelled = sum(result['destinations'][d] for d in countries) if result else None
            comparisons.append(dict(month=month.start_time, group=group, unit='bcm/month',
                model_bcm=modelled,
                ea_actual_bcm=actual, ea_legacy_forecast_bcm=None,
                model_minus_actual_bcm=modelled-actual if result and compatible else None,
                model_minus_ea_forecast_bcm=None,
                status='Unavailable: prospective run does not retrieve actuals or score forecasts' if manifest['settings']['mode']=='current_forecast' else
                    inputs['comparison_status'][group] if inputs and 'comparison_status' in inputs else
                    'Unavailable: synthetic run has no EA references' if manifest['settings']['input_source']=='synthetic_demo'
                    else 'Unavailable: complete fresh SID inputs and compatible comparison definitions required'))
        for arc in manifest['network']['arcs']:
            asset = arc['asset']
            arcs.append(dict(month=month.start_time, arc_id=arc['id'], from_node=arc['from'], to_node=arc['to'],
                asset=asset, arc_type=arc.get('kind', 'physical_or_allocation_proxy'),
                flow_bcm=result['flows'][arc['id']] if result else None,
                available_capacity_bcm=float(inputs['capacities'].at[month, asset]) if inputs and asset else None))
    return pd.DataFrame(rows), pd.DataFrame(comparisons), pd.DataFrame(arcs)


def excel_value(value):
    if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)):
        return 'Unavailable'
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, pd.Period):
        return value.start_time.to_pydatetime()
    if hasattr(value, 'item'):
        value = value.item()
    if isinstance(value, (dict, list)):
        return str(value)
    # Source identifiers must never be interpreted as spreadsheet formulas.
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return "'"+value
    return value


def write_workbook(path, frames, manifest):
    book = Workbook()
    book.remove(book.active)
    for name, frame in frames.items():
        sheet = book.create_sheet(name)
        sheet.sheet_view.showGridLines = False
        sheet.append([name+' — '+manifest['analysis_type']])
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(2, len(frame.columns)))
        sheet.cell(1, 1).font = Font(name='Calibri', size=15, bold=True, color='FFFFFF')
        sheet.cell(1, 1).fill = PatternFill('solid', fgColor='193B50')
        sheet.cell(1, 1).alignment = Alignment(wrap_text=True, vertical='center')
        sheet.row_dimensions[1].height = 42
        sheet.append(['Status: '+manifest['status']+' | Price-free | Snapshot; edits do not rerun the model'])
        sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(2, len(frame.columns)))
        sheet.cell(2, 1).alignment = Alignment(wrap_text=True)
        sheet.row_dimensions[2].height = 32
        sheet.append(list(frame.columns))
        for row in frame.itertuples(index=False, name=None):
            sheet.append([excel_value(v) for v in row])
        sheet.freeze_panes = 'B4'
        if len(frame):
            sheet.auto_filter.ref = f'A3:{get_column_letter(len(frame.columns))}{sheet.max_row}'
        for cell in sheet[3]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='356079')
            cell.alignment = Alignment(wrap_text=True, vertical='center')
        sheet.row_dimensions[3].height = 45
        for column, label in enumerate(frame.columns, 1):
            long_text = label in {'meaning', 'transformation', 'status', 'source', 'identifier', 'value'}
            sheet.column_dimensions[get_column_letter(column)].width = 76 if label=='meaning' else 46 if long_text else 25
        for row in sheet.iter_rows(min_row=4):
            height = 22
            for cell in row:
                cell.font = Font(name='Calibri', size=11, color='865600' if cell.value=='Unavailable' else '193B50')
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                if isinstance(cell.value, datetime):
                    cell.number_format = 'yyyy-mm-dd'
                elif isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool):
                    cell.number_format = '0.000000'
                if cell.row % 2 == 0:
                    cell.fill = PatternFill('solid', fgColor='EFF4F7')
                width = sheet.column_dimensions[cell.column_letter].width
                height = max(height, 16*math.ceil(len(str(cell.value))/max(1, width-3))+6)
            sheet.row_dimensions[row[0].row].height = height
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = 'landscape'
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.print_title_rows = '1:3'
    if manifest['status']=='OPTIMAL':
        sheet = book['Monthly flows']
        chart = BarChart()
        chart.title = 'Monthly routed destination volumes — '+manifest['analysis_type']
        chart.type = 'col'
        chart.grouping = 'stacked'
        chart.overlap = 100
        chart.y_axis.title = 'Monthly volume (bcm)'
        chart.x_axis.title = 'Target month'
        chart.add_data(Reference(sheet, min_col=2, max_col=8, min_row=3, max_row=sheet.max_row), titles_from_data=True)
        chart.set_categories(Reference(sheet, min_col=1, min_row=4, max_row=sheet.max_row))
        chart.width, chart.height = 26, 12
        sheet.add_chart(chart, 'A'+str(sheet.max_row+3))
    book.save(path)
    # Export check: typed numbers/dates and visible missing values survive OOXML.
    reopened = load_workbook(path, read_only=True, data_only=True)
    try:
        if reopened.sheetnames != list(frames):
            raise ValueError('Excel export lost required sheets.')
        for name, frame in frames.items():
            if reopened[name].max_row < len(frame)+3:
                raise ValueError('Excel export lost data rows: '+name)
    finally:
        reopened.close()


def report_run(output, manifest, inputs, results, inventory, network):
    monthly, comparisons, arcs = result_tables(inputs, results, manifest)
    def save_delivery(frame,path):
        return save_current_forecast_table(frame,path,manifest['settings']) if manifest['settings']['mode']=='current_forecast' else save_csv(frame,path)
    save_delivery(monthly, output/'results.csv')
    save_delivery(comparisons, output/'details/comparisons.csv')
    save_delivery(arcs, output/'details/network_flows.csv')
    diagnostics = pd.read_csv(output/'details/solver_checks.csv')
    if diagnostics.empty:
        diagnostics = pd.DataFrame([dict(check='Optimisation', status=manifest['status'],
            action=manifest['blocker'] or 'Not requested: validation-only does not construct or solve an LP.')])
    capacities = inputs['capacity_monthly'] if inputs else pd.DataFrame([dict(status='Unavailable: preparation blocked; no capacity inputs consumed')])
    preferences = pd.DataFrame([dict(destination=d, share=inputs['preferences'][d]) for d in DESTINATIONS]) if inputs else pd.DataFrame([dict(status='Unavailable: preparation blocked')])
    forecast=manifest['settings']['mode']=='current_forecast'
    definitions=[(key,'Prospective only: no actuals or scores; historical date guards and 2026 holdout remain locked.' if forecast and key=='Evaluation' else value) for key,value in DEFINITIONS]
    forecast_guide=[('Forecast origin (UTC)',manifest['settings']['origin']),
        ('Delivery horizon',manifest['settings']['start']+' to '+manifest['settings']['end']+'; '+str(manifest['settings']['horizon_months'])+' monthly deliveries'),
        ('Prospective assumptions',manifest['settings']['capacity_scenario']+'; F2.2 provisional capacities approved, complete population and Snøhvit inputs still gated; synthetic fixtures are manufactured')] if forecast else []
    guide = pd.DataFrame([('Run identity', manifest['run_id']), ('Git commit', manifest['git']['commit']),
        ('Action required', manifest['blocker'] or 'Open Monthly flows; read definitions below before using results.'),
        *forecast_guide,*definitions], columns=['item', 'meaning'])
    frames = {'Read me': guide, 'Monthly flows': monthly, 'Comparisons': comparisons,
        'Capacities': capacities, 'Network flows': arcs, 'Preferences': preferences,
        'Input sources': inventory, 'Settings': pd.DataFrame(list(manifest['settings'].items()), columns=['setting', 'value']),
        'Diagnostics': diagnostics}
    write_workbook(output/'results.xlsx', frames, manifest)
    if results:
        month = inputs['months'][0]
        draw_network(network, output/'details/network_flows.png', capacities=inputs['capacities'].loc[month].to_dict(),
            result=results[str(month)], title=f'{manifest["analysis_type"]}: {month} monthly flows (bcm)')
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(11, 5))
        plotted = monthly.set_index(monthly.month.dt.to_period('M').astype(str))[[d+'_volume_bcm' for d in DESTINATIONS]]
        plotted.rename(columns={d+'_volume_bcm': d for d in DESTINATIONS}).plot.bar(
            stacked=True, ax=ax, color=[COLORS[d] for d in DESTINATIONS], rot=45)
        ax.set(title=manifest['analysis_type']+' — monthly destination volumes', ylabel='bcm/month', xlabel='Target month')
        ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1))
        fig.tight_layout()
        fig.savefig(output/'details/monthly_flows.png', dpi=140)
        fig.savefig(output/'details/monthly_flows.svg')
        plt.close(fig)
    else:
        draw_network(network, output/'details/network_topology.png',
            title=manifest['status']+' — unsolved topology; no flows inferred')
    content = f'<h1>{escape(manifest["analysis_type"])}</h1><p>Status: {escape(manifest["status"])}. Run {escape(manifest["run_id"])}.</p>'
    content += '<p><a href="results.xlsx">Open primary analyst workbook</a> · <a href="results.csv">Monthly CSV</a> · <a href="input_sources.csv">Input-source inventory</a></p>'
    if manifest['blocker']:
        content += '<p class="note">Action required: '+escape(manifest['blocker'])+'</p>'
    content += table(guide)+table(monthly)+table(comparisons)
    if results:
        content += '<img alt="Monthly flows snapshot" src="details/monthly_flows.png"><img alt="Solved network snapshot" src="details/network_flows.png">'
    else:
        content += '<img alt="Unsolved topology" src="details/network_topology.png">'
    content += artifact_links(output)
    (output/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Routing run</title><style>'+STYLE+'</style>'+content+'</html>', encoding='utf-8')
