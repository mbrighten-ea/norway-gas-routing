"""Local orchestration: configuration, input gates, solve, then analyst reporting.

Synthetic demonstration is explicit and cannot act as a fallback for EA inputs.
Current forecasts have bounded origins/deliveries and explicit physical-input
gates. No cached numerical input reader or walk-forward engine is called here.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pandas as pd
import yaml

from .config import UniqueKeyLoader, load_config
from .evaluation import (check_dates, check_table, load_policy,
                         reconstruction_evaluation, validate_manifest)
from .routing import (DESTINATIONS, available_solver, build_month,
                      finite_nonnegative, historical_preferences,
                      monthly_available_capacity, network_definition,
                      solve_month, validate_solution)
from .validation import check_keys


class RunBlocked(ValueError):
    """A prerequisite needs analyst action, with no numerical substitution."""


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, default=str, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def local_path(root, value):
    if not isinstance(value, str) or not value:
        raise RunBlocked('Configuration paths must be nonempty repository-relative strings.')
    path = (root/value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RunBlocked('Path leaves the authorised repository: '+value)
    return path


def load_run_config(root, path):
    """Resolve one run request without changing canonical model assumptions."""
    path = local_path(root, str(path))
    try:
        request = yaml.load(path.read_text(encoding='utf-8-sig'), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise RunBlocked('Invalid run YAML: '+str(exc)+'; fix the indicated line in '+str(path)) from exc
    keys = {'model', 'registry', 'evaluation', 'mode', 'input_source', 'start',
            'end', 'origin', 'solver', 'capacity_scenario', 'price_enabled'}
    check_keys(request, 'run configuration', keys, {'horizon_months','forecast_end_month','physical_input_contract','heidrun_treatment'})
    if not isinstance(request['mode'], str) or request['mode'] not in {'historical_reconstruction', 'retrospective_forecast', 'latest_forecast', 'current_forecast'}:
        raise RunBlocked('Unsupported mode. Use historical_reconstruction; forecast modes require a verified origin bundle.')
    if not isinstance(request['input_source'], str) or request['input_source'] not in {'fresh_sid', 'synthetic_demo'}:
        raise RunBlocked('Unsupported input_source. Use fresh_sid or explicit synthetic_demo; cached/frozen inputs are not authorised.')
    if not isinstance(request['price_enabled'], bool):
        raise RunBlocked('price_enabled must be a YAML boolean.')
    if request['price_enabled']:
        raise RunBlocked('Experimental price routing is not exposed in Milestone A. Set price_enabled: false; use the separately authorised price experiment.')
    current=request['mode']=='current_forecast'
    core=request.get('physical_input_contract')=='core_f24'
    if request.get('physical_input_contract') not in (None,'core_f24'):
        raise RunBlocked('Unknown physical input contract.')
    if core and (not current or request['input_source']!='fresh_sid' or
                 request.get('heidrun_treatment') not in ('export_eligible','domestic_bound')):
        raise RunBlocked('Core F2.4 requires fresh current forecasts and an explicit Heidrun treatment.')
    if not core and request.get('heidrun_treatment') is not None:
        raise RunBlocked('Heidrun treatment requires the Core F2.4 contract.')
    if not isinstance(request['capacity_scenario'],str):
        raise RunBlocked('capacity_scenario must be a named string.')
    approved_capacities={'core_f24_156','core_f24_proportional_143'}
    if core != (request['capacity_scenario'] in approved_capacities):
        raise RunBlocked('Core F2.4 supply and capacity contracts must be selected together.')
    if current and request['capacity_scenario'] not in {'baseline_prospective','provisional_kollsnes_143','provisional_kollsnes_156','synthetic_fixture'} | approved_capacities:
        raise RunBlocked('Current forecast requires provisional_kollsnes_143 / provisional_kollsnes_156 or explicit synthetic_fixture capacities.')
    if current and ((request['input_source']=='synthetic_demo') != (request['capacity_scenario']=='synthetic_fixture')):
        raise RunBlocked('synthetic_fixture capacities require synthetic_demo inputs, and vice versa; never mix manufactured and EA inputs.')
    if not current and request['capacity_scenario'] != 'baseline':
        raise RunBlocked('Milestone A supports baseline capacity only. Sensitivity assumptions need their separately authorised command.')
    if request['solver'] is not None and not isinstance(request['solver'], str):
        raise RunBlocked('solver must be an installed solver name or null.')
    model_path = local_path(root, request['model'])
    registry_path = local_path(root, request['registry'])
    policy_path = local_path(root, request['evaluation'])
    if policy_path != (root/'config/evaluation.yaml').resolve():
        raise RunBlocked('Use config/evaluation.yaml: the locked evaluation policy cannot be replaced.')
    load_policy(policy_path)
    model, registry = load_config(model_path, registry_path)
    if current:
        from .forecast_inputs import forecast_window
        request['horizon_months']=request.get('horizon_months',12)
        request['forecast_end_month']=request.get('forecast_end_month')
        request['origin'],months=forecast_window(request['origin'],request['horizon_months'],request['forecast_end_month'])
        request['horizon_months']=len(months)
        for name,value in [('start',str(months.min())),('end',str(months.max()))]:
            if request[name] is not None and request[name]!=value:
                raise RunBlocked('Current forecast '+name+' must be null or '+value+'; deliveries derive from origin and forecast_end_month or horizon_months.')
            request[name]=value
    elif request.get('forecast_end_month') is not None:
        raise RunBlocked('forecast_end_month is only supported for current_forecast; historical reconstruction uses start/end.')
    for name in ('start', 'end'):
        value = request[name]
        if not isinstance(value, str) or len(value) != 7 or str(pd.Period(value, 'M')) != value:
            raise RunBlocked(name+' must be a quoted YYYY-MM month.')
    if request['start'] > request['end']:
        raise RunBlocked('start must precede or equal end.')
    if not current:
        check_dates([request['start'], request['end']], 'analysis')
    if request['origin'] is not None:
        origin = pd.Timestamp(request['origin'])
        if pd.isna(origin):
            raise RunBlocked('origin must be a valid explicit timestamp.')
        if not current: check_dates([origin], 'read')
        if pd.Period(request['start'], 'M') <= pd.Period(origin.tz_localize(None) if origin.tzinfo else origin, 'M'):
            raise RunBlocked('Forecast targets must follow the origin; revised values cannot substitute for origin forecasts.')
    if request['mode'] == 'historical_reconstruction' and request['origin'] is not None:
        raise RunBlocked('A reconstruction has origin: null. Do not label revised inputs as an origin forecast.')
    model = deepcopy(model)
    model['routing'].update(start=request['start'], end=request['end'])
    training = pd.period_range(model['routing']['baseline_start'], model['routing']['baseline_end'], freq='M')
    check_dates(training, 'fit')
    if training.empty or training.max() >= pd.Period(request['start'], 'M'):
        raise RunBlocked('Baseline training months must be nonempty and precede the run; adjust reviewed canonical settings.')
    return request, model, registry, path


def input_inventory(model, registry, request):
    """Enumerate current consumers, including unresolved workbook-only fields."""
    rows = []
    start, end = request['start'], request['end']
    def add(key, consumer, transformation, begin=start, finish=end):
        info = registry.loc[key].to_dict() if key in registry.index else {}
        rows.append(dict(key=key, identifier=info.get('sid', ''), consumer=consumer,
            start=begin, end=finish, raw_unit=info.get('raw_unit', ''),
            model_unit='bcm/month', transformation=transformation,
            status='SID identified; values and semantics require fresh validation' if info.get('sid') else 'BLOCKED: missing SID',
            source=info.get('display_source', ''), lifecycle=info.get('lifecycle', ''),
            origin=request['origin'], available_at=None, metadata_file=None))
    for node, entry in model['routing']['nodes'].items():
        if entry.get('source_group'):
            for key in model['sources'][entry['source_group']]['series']:
                add(key, node, 'Sum distinct monthly field bcm into source node')
        for column in entry.get('workbook_columns', []):
            rows.append(dict(key='unresolved_component_'+column, identifier='', consumer=node,
                start=start, end=end, raw_unit='monthly-average mcm/day reference',
                model_unit='bcm/month', transformation='rate * calendar days / 1000; individual SID required',
                status='BLOCKED: workbook column is lineage only, never a numerical input',
                source='Production mcm_d!'+column, lifecycle='unverified', origin=request['origin']))
    add('norway_prod', 'supply boundary', 'National total minus Snøhvit once; residual remains UNMAPPED')
    add('snohvit_net_prod', 'LNG exclusion', 'Validated historical rate * calendar days / 1000; July 2025 guard retained')
    for asset, entry in model['routing']['assets'].items():
        rows.append(dict(key=asset, identifier='config/model.yaml:routing.assets.'+asset,
            consumer='asset capacity', start=start, end=end, raw_unit='mcm/day or bcm/year',
            model_unit='bcm/month', transformation='Calendar-day sum / 1000; annual envelope / 365',
            status='Provisional envelope; effectiveness/maintenance compatibility unverified',
            source=model['routing']['capacity_sources'][entry['source']], origin=None))
        if entry.get('maintenance_series'):
            add(entry['maintenance_series'], asset, 'Signed daily technical minus maintenance; sum / 1000')
    for d in DESTINATIONS:
        add(d.lower()+'_flow_qa', 'historical preference '+d, 'Earlier complete nonnegative baskets -> volume-weighted shares',
            model['routing']['baseline_start'], model['routing']['baseline_end'])
    return pd.DataFrame(rows)


def prepare_run_inputs(root, model, registry, request):
    """Return the existing monthly table contract; never substitute another mode."""
    if request['mode']=='current_forecast':
        if request['input_source']=='synthetic_demo':
            inputs=synthetic_inputs(model)
            inputs['provenance'][0].update(kind='synthetic_forecast_fixture',asof=request['origin'])
            inputs['provenance'][0]['transformation']+='; fixture LNG 0.2 bcm/month; national equals pipeline source sum plus fixture LNG, never EA observations'
            inputs['reconciliation']=pd.DataFrame(dict(
                national_production_bcm=inputs['supply'].sum(axis=1)+.2,
                snohvit_bcm=.2,pipeline_supply_bcm=inputs['supply'].sum(axis=1),
                mapped_supply_bcm=inputs['supply'].drop(columns='UNMAPPED').sum(axis=1),
                unmapped_supply_bcm=inputs['supply'].UNMAPPED))
            return inputs
        from .forecast_inputs import prepare_current_inputs
        return prepare_current_inputs(root,model,registry,request)
    if request['mode'] != 'historical_reconstruction':
        raise RunBlocked('Forecast mode unavailable: identify every component SID and verify origin Snøhvit, Kollsnes maintenance, capacity effectiveness and training release dates. Supply a complete origin bundle before implementing forecast preparation; no revised fallback.')
    if request['input_source'] == 'fresh_sid':
        from .routing_inputs import prepare_fresh_inputs
        return prepare_fresh_inputs(root, model, registry, provenance_dir=request.get('_provenance_dir'))
    return synthetic_inputs(model)


def synthetic_inputs(model):
    """Deterministic manufactured fixtures, never observations or forecasts."""
    settings = model['routing']
    months = pd.period_range(settings['start'], settings['end'], freq='M')
    training = pd.period_range(settings['baseline_start'], settings['baseline_end'], freq='M')
    network = network_definition(settings)
    # Deliberately exercise shared processing, transit and unmapped disposal.
    base = {'KOLLSNES_FEED': 1.6, 'NYHAMNA_FEED': 1.2, 'KARSTO_FEED': 1.5,
            'OSEBERG': .3, 'SLEIPNER': .4, 'UK_DIRECT': .2, 'EKOFISK_FEED': .3, 'UNMAPPED': .1}
    if set(base) != {n for n, e in network['nodes'].items() if e['kind'] == 'source'}:
        raise RunBlocked('Synthetic fixture topology changed; update and review fixture source identities.')
    supply = pd.DataFrame([{k: v*(1+i/100) for k, v in base.items()} for i in range(len(months))], index=months)
    observations = pd.DataFrame(1., index=training, columns=DESTINATIONS)
    preferences, excluded = historical_preferences(observations)
    capacities, daily_rows, monthly_rows = {}, [], []
    # Manufactured 100 mcm/d envelopes, including a genuine fixture bottleneck.
    for asset in settings['assets']:
        rate = 30. if asset == 'KARSTO_PROCESSING' else 100.
        technical = pd.Series([rate], index=pd.DatetimeIndex([months.min().start_time]))
        monthly, daily = monthly_available_capacity(technical, months)
        capacities[asset] = monthly.available_capacity_bcm
        daily_rows.append(daily.rename_axis('date').reset_index().assign(asset=asset))
        monthly_rows.append(monthly.rename_axis('month').reset_index().assign(asset=asset))
    return dict(months=months, supply=supply, capacities=pd.DataFrame(capacities),
        capacity_daily=pd.concat(daily_rows, ignore_index=True),
        capacity_monthly=pd.concat(monthly_rows, ignore_index=True),
        training_observations=observations, preferences=preferences,
        excluded_training_months=excluded,
        provenance=[dict(key='synthetic_demo_v1', category='synthetic', source='operational.synthetic_inputs',
            transformation='Manufactured monthly source base * (1 + month offset / 100); capacities 100 mcm/day except Karsto 30; zero fixture derates; equal earlier training observations',
            target_months=months.astype(str).tolist(), unit='bcm/month', asof=None)])


def validate_prepared_inputs(inputs, network, request):
    """Validation boundary also usable by a future one-target-month adapter."""
    months = pd.period_range(request['start'], request['end'], freq='M')
    if request['mode']=='current_forecast':
        from .forecast_inputs import forecast_window
        _,expected=forecast_window(request['origin'],request['horizon_months'],request.get('forecast_end_month'))
        if not months.equals(expected) or len(expected)!=request['horizon_months']:
            raise RunBlocked('Current forecast deliveries differ from origin/horizon contract.')
    else:
        check_dates(months, 'analysis')
    if not inputs['months'].equals(months):
        raise RunBlocked('Prepared target months do not match the run request.')
    sources = {n for n, e in network['nodes'].items() if e['kind'] == 'source'}
    assets = {a['asset'] for a in network['arcs'] if a['asset']}
    for name, expected in [('supply', sources), ('capacities', assets)]:
        frame = inputs[name]
        if not frame.index.equals(months) or not frame.columns.is_unique or set(frame.columns) != expected:
            raise RunBlocked(name+': require exact unique target months and network identifiers; no filling.')
        finite_nonnegative(frame.to_numpy().ravel(), name)
    preferences = inputs['preferences']
    if set(preferences) != set(DESTINATIONS) or abs(sum(preferences.values())-1.) > 1e-10:
        raise RunBlocked('Preferences require seven destinations and shares summing to one.')
    finite_nonnegative(preferences.values(), 'preferences')
    training = inputs['training_observations']
    if training.empty or not training.index.is_unique or set(training.columns) != set(DESTINATIONS):
        raise RunBlocked('Training observations require nonempty unique earlier months and seven destinations.')
    check_dates(training.index, 'fit')
    if training.index.max() >= months.min():
        raise RunBlocked('Training overlaps targets; use earlier verified training inputs.')
    if not inputs.get('provenance'):
        raise RunBlocked('Missing input provenance; preserve source metadata before solving.')


def optimise(inputs, network, solver_name):
    """Only this phase constructs/solves LPs; validation-only never calls it."""
    selected, solver = available_solver(solver_name)
    results, checks = {}, []
    for month in inputs['months']:
        supply = inputs['supply'].loc[month].to_dict()
        capacities = inputs['capacities'].loc[month].to_dict()
        result = solve_month(build_month(network, supply, capacities, inputs['preferences'], str(month)), solver)
        checks.append(dict(month=str(month), **validate_solution(network, supply, capacities, result)))
        results[str(month)] = result
    return selected, results, pd.DataFrame(checks)


def git_identity(root):
    def git(*args):
        return subprocess.check_output(['git', '-c', 'safe.directory='+str(root.resolve()), '-C', str(root), *args], encoding='utf-8', stderr=subprocess.PIPE).strip()
    try:
        return dict(branch=git('branch', '--show-current'), commit=git('rev-parse', 'HEAD'),
            tracked_status=git('status', '--porcelain', '--untracked-files=no'),
            status=git('status', '--porcelain'),
            diff_sha256=hashlib.sha256(git('diff', 'HEAD').encode()).hexdigest())
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RunBlocked('Cannot record Git identity; run inside the authorised Git checkout: '+str(exc)) from exc


def csv_frame(frame, monthly_index=False):
    frame = frame.copy()
    if monthly_index:
        frame = frame.rename_axis('month').reset_index()
    for col in frame:
        if isinstance(frame[col].dtype, pd.PeriodDtype):
            frame[col] = frame[col].dt.to_timestamp()
    return frame


def save_csv(frame, path, *, monthly_index=False):
    frame=csv_frame(frame,monthly_index)
    check_table(frame)
    frame.to_csv(path, index=False, encoding='utf-8-sig', date_format='%Y-%m-%d', float_format='%.17g')


def save_current_forecast_table(frame,path,request,*,monthly_index=False):
    """Export declared prospective delivery tables, never historical actuals.

    A separate publication contract; historical save_csv/check_table are unchanged.
    Numeric operational inputs remain gated by preparation and fixture provenance.
    """
    from .forecast_inputs import forecast_window
    if request['mode']!='current_forecast': raise RunBlocked('Prospective table export requires current_forecast.')
    _,months=forecast_window(request['origin'],request['horizon_months'],request.get('forecast_end_month'))
    if request['start']!=str(months.min()) or request['end']!=str(months.max()) or len(months)!=request['horizon_months']:
        raise RunBlocked('Prospective export window differs from declared forecast horizon.')
    frame=csv_frame(frame,monthly_index)
    for column in ('month','target_month','date','calendar_date','timestamp'):
        if column in frame:
            dates=pd.DatetimeIndex(pd.to_datetime(frame[column],utc=True)).tz_localize(None)
            if dates.hasnans or (dates<months.min().start_time).any() or (dates>months.max().end_time).any():
                raise RunBlocked('Prospective export contains dates outside its delivery contract; locked actuals cannot be exported.')
    frame.to_csv(path,index=False,encoding='utf-8-sig',date_format='%Y-%m-%d',float_format='%.17g')


def execute_run(root, config='config/run.yaml', *, validate_only=False, solver_name=None):
    """Return (package directory, process exit code); failed runs stay traceable."""
    root = Path(root).resolve()
    request, model, registry, config_path = load_run_config(root, config)
    def save_target(frame,path,**kwargs):
        return save_current_forecast_table(frame,path,request,**kwargs) if request['mode']=='current_forecast' else save_csv(frame,path,**kwargs)
    if solver_name:
        request['solver'] = solver_name
    network = network_definition(model['routing'])
    identity = git_identity(root)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_'+uuid4().hex[:8]
    output = root/'outputs/routing_runs'/run_id
    output.mkdir(parents=True, exist_ok=False)
    details, provenance = output/'details', output/'provenance'
    details.mkdir()
    provenance.mkdir()
    prepared = provenance/'inputs'
    prepared.mkdir()
    manifest = dict(schema_version=1, run_id=run_id, run_at_utc=datetime.now(timezone.utc).isoformat(),
        status='PREPARING', phase='preparation', blocker=None, settings=request,
        analysis_type=('SYNTHETIC CURRENT-FORECAST WORKFLOW — manufactured data, not an EA forecast' if request['input_source']=='synthetic_demo' else 'Norwegian Gas Routing: Provisional Physical and Historical-Preference Allocation Forecast') if request['mode']=='current_forecast' else
            'SYNTHETIC DEMONSTRATION — not EA data or a forecast' if request['input_source']=='synthetic_demo' else 'Latest revised reconstruction',
        asof=request['origin'], unit='bcm/month', git=identity,
        config_sha256={str(p.relative_to(root)): digest(p) for p in [config_path,
            local_path(root, request['model']), local_path(root, request['registry']), local_path(root, request['evaluation'])]},
        code_sha256={str(p.relative_to(root)): digest(p) for p in (root/'src/norway_gas_routing').rglob('*') if p.suffix in {'.py', '.html'}},
        network=network, inputs=[], solver=None, holdout_scored=False,
        interpreter=sys.executable, package_versions={name: version(name) for name in
            ['pandas', 'pulp', 'openpyxl', 'matplotlib', 'networkx', 'PyYAML']})
    if request['mode']=='current_forecast':
        manifest.update(operational_forecast_available=False,physical_supply_contract='F2.2: complete historical population and compatible Snøhvit required; allocation and capacities provisionally approved, no EA commercial validation')
    manifest['code_sha256']['scripts/run/run_routing.py'] = digest(root/'scripts/run/run_routing.py')
    # Preserve dirty code itself, not only a hash which cannot reconstruct it.
    code = provenance/'code'
    for name in manifest['code_sha256']:
        target = code/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root/name).read_bytes())
    for name in manifest['config_sha256']:
        target = provenance/'configuration'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root/name).read_bytes())
    (provenance/'resolved_settings.yaml').write_text(yaml.safe_dump(dict(run=request, model=model), sort_keys=False), encoding='utf-8')
    inventory = input_inventory(model, registry, request)
    inventory_error = None
    if request['input_source'] == 'fresh_sid':
        from .routing_sources import source_requirements, CONTRACT, MAPPING_LEDGER
        try:
            if request['mode']=='current_forecast':
                from .forecast_inputs import forecast_requirements
                inventory,_,_=forecast_requirements(root,model,registry,request)
            else:
                inventory, _, _ = source_requirements(root, model, registry)
            inventory['start'], inventory['end'] = request['start'], request['end']
            mask = inventory.classification.eq('essential_training')
            inventory.loc[mask, 'start'] = model['routing']['baseline_start']
            inventory.loc[mask, 'end'] = model['routing']['baseline_end']
            mask=inventory.classification.eq('essential_population')
            inventory.loc[mask,'start']='2024-01'
            inventory.loc[mask,'end']='2024-12'
        except (ValueError, OSError) as error:
            inventory_error = str(error)
        for name in [CONTRACT, MAPPING_LEDGER, 'evidence/inputs/routing_sources_b1/hanz_preproduction.json']:
            target = provenance/name
            target.parent.mkdir(parents=True, exist_ok=True)
            if (root/name).is_file():
                target.write_bytes((root/name).read_bytes())
            else:
                inventory_error = 'Reviewed source evidence missing: '+name+'. Restore the committed evidence; never infer replacement mappings.'
        if request['mode']=='current_forecast':
            from .production_population import POPULATION, LINEAGE
            for name in [POPULATION, LINEAGE, 'evidence/inputs/reconciled_supply_f22/assessment.json']:
                target=provenance/name
                target.parent.mkdir(parents=True,exist_ok=True)
                if (root/name).is_file(): target.write_bytes((root/name).read_bytes())
    inputs, results, checks = None, {}, pd.DataFrame(columns=['month', 'max_mass_balance_residual_bcm', 'max_capacity_violation_bcm'])
    try:
        if inventory_error:
            raise RunBlocked(inventory_error)
        preparation_request = {**request, '_provenance_dir': provenance}
        inputs = prepare_run_inputs(root, model, registry, preparation_request)
        validate_prepared_inputs(inputs, network, request)
        manifest['inputs'] = inputs['provenance']
        if request.get('physical_input_contract')=='core_f24':
            inventory=pd.DataFrame(columns=['key','classification','status'])
        metadata = [r['metadata'] for r in inputs['provenance'] if r.get('metadata')]
        if any(m.get('_mock_sid_response') is True for m in metadata):
            if not all(m.get('_mock_sid_response') is True for m in metadata):
                raise RunBlocked('Mixed mock/live responses cannot be presented as real data.')
            manifest['analysis_type'] = 'MOCK SID DEMONSTRATION — manufactured responses, not live EA observations'
        if request['input_source'] == 'synthetic_demo':
            # Replace unresolved real-source inventory with exactly what was consumed.
            inventory = pd.DataFrame([dict(key=name, identifier='synthetic_demo_v1:'+name,
                consumer=name, start=str(frame.index.min()), end=str(frame.index.max()),
                raw_unit='mcm/day' if name == 'capacities' else unit, model_unit=unit,
                transformation=inputs['provenance'][0]['transformation'],
                status='SYNTHETIC — manufactured, not provider data', source='operational.synthetic_inputs',
                origin=request['origin'] if request['mode']=='current_forecast' else None, metadata_file='provenance/source_metadata.json') for name, frame, unit in [
                    ('source_supply', inputs['supply'], 'bcm/month'),
                    ('capacities', inputs['capacities'], 'bcm/month'),
                    ('training_observations', inputs['training_observations'], 'bcm/month')]])
        for key in ['supply', 'capacities', 'training_observations']:
            writer=save_csv if key=='training_observations' else save_target
            writer(inputs[key], prepared/(key+'.csv'), monthly_index=True)
        for key in ['capacity_daily', 'capacity_monthly']:
            save_target(inputs[key], prepared/(key+'.csv'))
        if 'reconciliation' in inputs:
            save_target(inputs['reconciliation'], prepared/'reconciliation.csv', monthly_index=True)
        if 'actual_comparisons' in inputs:
            save_csv(inputs['actual_comparisons'], prepared/'actual_comparisons.csv', monthly_index=True)
            write_json(prepared/'comparison_status.json', inputs['comparison_status'])
        write_json(prepared/'preferences.json', inputs['preferences'])
        write_json(provenance/'source_metadata.json', inputs['provenance'])
        if request['input_source'] == 'synthetic_demo':
            for index, row in inventory.iterrows():
                key = {'source_supply': 'supply', 'capacities': 'capacities',
                       'training_observations': 'training_observations'}[row['key']]
                file = prepared/(key+'.csv')
                inventory.at[index, 'model_ready_file'] = file.relative_to(output).as_posix()
                inventory.at[index, 'sha256'] = digest(file)
                inventory.at[index, 'raw_file'] = 'provenance/inputs/capacity_daily.csv' if key == 'capacities' else file.relative_to(output).as_posix()
        if request['mode']=='current_forecast':
            manifest['evaluation']=dict(split=load_policy(),experiment_id=run_id,analysis_mode='current_forecast',
                forecast_origin=request['origin'],target_start=request['start'],target_end=request['end'],
                period_role='prospective workflow; no scoring',holdout_loaded=False,holdout_scored=False,
                model_parameters=dict(historical_routing_shares=inputs['preferences'],price_response=dict(enabled=False),
                    training_start=model['routing']['baseline_start'],training_end=model['routing']['baseline_end'],
                    training_vintage_status='Synthetic fixture; no EA forecast claim'))
        else:
            manifest['evaluation'] = reconstruction_evaluation(root, inputs, model['routing'], run_id)
        if request['input_source'] == 'synthetic_demo':
            manifest['evaluation']['model_parameters']['training_vintage_status'] = 'synthetic fixture; not observed training data'
        parameters = manifest['evaluation']['model_parameters']
        manifest['evaluation']['parameters_sha256'] = hashlib.sha256(json.dumps(parameters, sort_keys=True, default=str).encode()).hexdigest()
        if request['mode']=='current_forecast':
            if request.get('physical_input_contract')=='core_f24' and inputs.get('approved_contract')=='core_f24':
                manifest.update(operational_forecast_available=True,
                    commercial_validated=False,production_ready=False,
                    analysis_type='PROVISIONAL PARTIAL-COVERAGE PHYSICAL-ROUTING POC - price-free historical-preference allocation',
                    physical_supply_contract='Core F2.4 approved provisional annual ownership, LNG conversion and technical availability; external routes and hypothetical domestic supply excluded explicitly')
                parameters['training_vintage_status']='Fresh latest-revised 2023 destination preferences; not a historical forecast backtest'
            elif request['input_source']!='synthetic_demo':
                raise RunBlocked('Approved complete physical forecast adapter required; no partial EA vector can be solved.')
            if request['input_source']=='synthetic_demo' and any(r.get('kind')!='synthetic_forecast_fixture' for r in inputs['provenance']):
                raise RunBlocked('Mixed/unlabelled forecast fixture provenance.')
        else:
            validate_manifest(manifest)
        manifest['evaluation']['parameters_sha256']=hashlib.sha256(json.dumps(parameters,sort_keys=True,default=str).encode()).hexdigest()
        if validate_only:
            manifest['status'] = 'VALIDATED_ONLY'
        else:
            manifest['phase'] = 'optimisation'
            selected, results, checks = optimise(inputs, network, request['solver'])
            manifest.update(status='OPTIMAL', solver=selected)
            if request.get('physical_input_contract')=='core_f24' and request['heidrun_treatment']=='export_eligible' and request['capacity_scenario']=='core_f24_156':
                from .forward_diagnostics import representative_ranges
                _,diagnostic_solver=available_solver(selected)
                inputs['physical_ranges']=representative_ranges(inputs,results,network,diagnostic_solver)
                save_target(inputs['physical_ranges'],details/'physical_ranges.csv')
                manifest['physical_range_diagnostics']='Individual maximum-export-face bounds for three representative months; historical preferences released, not additional forecasts'
    except (ValueError, RuntimeError, OSError) as exc:
        manifest.update(status='BLOCKED_INPUTS' if manifest['phase']=='preparation' else 'FAILED_OPTIMISATION', blocker=str(exc))
        if (provenance/'source_metadata.json').exists():
            manifest['inputs'] = json.loads((provenance/'source_metadata.json').read_text(encoding='utf-8'))
    if request['input_source'] == 'fresh_sid' and manifest['inputs']:
        if request['mode']=='current_forecast' and any(r.get('metadata',{}).get('_mock_sid_response') for r in manifest['inputs']):
            manifest['analysis_type']='MOCK CURRENT-FORECAST INPUT CHECK — manufactured responses, not an operational EA forecast'
            manifest['operational_forecast_available']=False
        rows = [{**{k:v for k,v in r.items() if k not in {'metadata', 'registry'}},
                 'metadata_file': 'provenance/source_metadata.json'} for r in manifest['inputs']]
        inventory = pd.concat([inventory, pd.DataFrame(rows)], ignore_index=True)
    save_csv(inventory, output/'input_sources.csv')
    if not (provenance/'source_metadata.json').exists():
        write_json(provenance/'source_metadata.json', {'status': 'Unavailable: no numerical inputs consumed', 'blocker': manifest['blocker']})
    write_json(provenance/'solver_results.json', results)
    save_target(checks, details/'solver_checks.csv')
    write_json(provenance/'run_manifest.json', manifest)
    from .reporting.operational import report_run
    try:
        manifest['phase'] = 'reporting'
        report_run(output, manifest, inputs, results, inventory, network)
    except (ValueError, RuntimeError, OSError) as exc:
        manifest.update(status='FAILED_REPORTING', blocker='Reporting failed: '+str(exc))
    manifest['phase'] = 'complete'
    # Ledger covers every file except the manifest itself (no recursive self-hash).
    manifest['files_sha256'] = {p.relative_to(output).as_posix(): digest(p) for p in output.rglob('*')
                               if p.is_file() and p != provenance/'run_manifest.json'}
    write_json(provenance/'run_manifest.json', manifest)
    print(manifest['status']+': '+str(output))
    if manifest['blocker']:
        print('Action required: '+manifest['blocker'])
    return output, 0 if manifest['status'] in {'OPTIMAL', 'VALIDATED_ONLY'} else 2
