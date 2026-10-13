"""Few representative maximum-export-face checks, with preferences released."""
import pandas as pd
import pulp

from .routing import DESTINATIONS,build_month,validate_solution


def representative_ranges(inputs,results,network,solver):
    months=inputs['months']
    capacity_month=inputs['capacities'].KOLLSNES_EXPORT.idxmin()
    selected=sorted(set([months[0],capacity_month,months[-1]]))
    rows=[]
    for month in selected:
        supply=inputs['supply'].loc[month].to_dict(); capacities=inputs['capacities'].loc[month].to_dict()
        baseline=results[str(month)]
        # Same node/asset equations and export optimum. Deliberately do not lock
        # the preference objective: these are physical envelopes, not new forecasts.
        built=build_month(network,supply,capacities,inputs['preferences'],str(month)+'_physical_range')
        built['problem']+=built['unrouted']==baseline['unrouted'],'fix_maximum_exports'
        for d in DESTINATIONS:
            bounds={}
            for label,sign in [('minimum',1),('maximum',-1)]:
                built['problem'].setObjective(sign*built['destinations'][d])
                stats=built['problem'].solve(solver)
                if stats.status!=pulp.LpSolveStatus.Optimal: raise RuntimeError('Physical range solve failed.')
                values=dict(flows={k:float(v.varValue) for k,v in built['flows'].items()},
                    destinations={k:float(v.varValue) for k,v in built['destinations'].items()},
                    unrouted=float(pulp.value(built['unrouted'])))
                validate_solution(network,supply,capacities,values)
                bounds[label]=values['destinations'][d]
            if not bounds['minimum']-1e-7<=baseline['destinations'][d]<=bounds['maximum']+1e-7:
                raise RuntimeError('Reference allocation outside its physical range.')
            rows.append(dict(month=month.start_time,destination=d,model_bcm=baseline['destinations'][d],
                minimum_bcm=bounds['minimum'],maximum_bcm=bounds['maximum'],
                range_width_bcm=bounds['maximum']-bounds['minimum'],
                fixed_exports_bcm=sum(baseline['destinations'].values()),
                interpretation='Individual physical bounds at maximum exports; endpoints are not jointly attainable and are not scenarios'))
    return pd.DataFrame(rows)
