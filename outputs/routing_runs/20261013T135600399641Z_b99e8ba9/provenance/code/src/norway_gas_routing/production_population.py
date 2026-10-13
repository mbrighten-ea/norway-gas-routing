"""Complete production-population gate; workbook lineage is never numerical input.

Classification 5 remains UNMAPPED. A residual identity alone cannot certify that
omitted, overlapping or unavailable components have a defensible physical boundary.
"""
from pathlib import Path

import pandas as pd

POPULATION = 'evidence/inputs/reconciled_supply_f22/production_population.csv'
LINEAGE = 'evidence/inputs/production_forecast_lineage/all_field_components.csv'
CLASSES = {'1', '2', '3', '4', '5', 'LNG'}


def validate_ownership(ledger, expected_components, nodes):
    """Validate exhaustive identity and ownership before inspecting observations."""
    if ledger.component_id.duplicated().any() or set(ledger.component_id) != set(expected_components):
        raise ValueError('Production population is incomplete or duplicates component identities; all 132 lineage components are required.')
    if not set(ledger.classification).issubset(CLASSES):
        raise ValueError('Unknown production classification; no default node or exclusion.')
    owned = ledger.loc[ledger.sid.ne('') & ledger.represented_by.eq('')]
    if owned.sid.duplicated().any():
        raise ValueError('Duplicate production SID ownership; declare and verify aliases instead of counting them twice.')
    for row in ledger.itertuples():
        if row.classification in {'1','3'} and not row.represented_by and row.node not in nodes - {'UNMAPPED'}:
            raise ValueError(row.component_id+': mapped production needs an existing physical source node.')
        if row.classification == '5' and row.node != 'UNMAPPED':
            raise ValueError(row.component_id+': unidentified entry must remain UNMAPPED.')
        if row.classification=='2' and row.classification_verified=='True' and not row.represented_by:
            raise ValueError(row.component_id+': an overlapping calculation needs verified component ownership before exclusion.')
        if row.represented_by:
            owner = ledger.loc[ledger.component_id.eq(row.represented_by)]
            if (len(owner)!=1 or owner.iloc[0].represented_by or row.represented_by==row.component_id
                    or row.classification not in {'1','2'}):
                raise ValueError(row.component_id+': invalid, cyclic or chained component alias.')


def population_blockers(root, nodes, output=None):
    """Return specific unresolved classifications/coverage, never cached weights.

    A passing evidence ledger is a prerequisite, not operational observations.
    Any later weight calculation still requires fresh, complete 2024 SID inputs.
    """
    root=Path(root)
    if not (root/POPULATION).is_file() or not (root/LINEAGE).is_file():
        return ['Complete 2024 production ledger is unavailable; restore F2.2 population evidence before allocation.']
    ledger=pd.read_csv(root/POPULATION,keep_default_na=False,dtype=str)
    expected=pd.read_csv(root/LINEAGE,keep_default_na=False).component_column
    validate_ownership(ledger,expected,set(nodes))
    if output is not None:
        ledger.to_csv(Path(output)/'production_population.csv',index=False)
    pending=ledger.loc[ledger.classification_verified.ne('True') | ledger.coverage_verified.ne('True')]
    blockers=[]
    if len(pending):
        blockers.append('Complete 2024 production ledger failed: '+str(len(pending))+
            ' components have unresolved classification or historical coverage: '+
            ', '.join(row.component_id+' '+row.field for row in pending.itertuples())+
            '. See production_population.csv; no frozen weights, missing-to-zero or partial-population allocation.')
    # Identity certification is separate from per-component coverage.
    certification=root/'evidence/inputs/reconciled_supply_f22/assessment.json'
    import json
    if not certification.is_file() or json.loads(certification.read_text()).get('historical_gate_passed') is not True:
        blockers.append('Full 2024 national = LNG + outside-boundary + mapped + UNMAPPED identity is not certified; forecast allocation remains blocked.')
    return blockers


def reconcile_population(ledger, observations, national, snohvit, expected_components, nodes):
    """Reconcile independent SID observations, retaining discrepancy explicitly.

    No missing observations, signed net fields, aliases or unexplained remainder
    are clipped, filled or turned into exportable supply. Units are monthly bcm.
    """
    validate_ownership(ledger,expected_components,set(nodes))
    months=pd.period_range('2024-01','2024-12',freq='M')
    if (not observations.index.equals(months) or not national.index.equals(months)
            or not snohvit.index.equals(months)):
        raise ValueError('Frozen residual weights require the complete 2024 calendar year, never validation/holdout months.')
    if ledger.classification_verified.ne('True').any() or ledger.coverage_verified.ne('True').any():
        raise ValueError('Unverified production population; resolve classification and coverage before reconciliation.')
    owners=ledger.loc[ledger.represented_by.eq('') & ledger.classification.isin({'1','3','4','5'})]
    if set(observations.columns)!=set(owners.component_id):
        raise ValueError('Historical observations must exactly match unique component owners; no omitted or extra SID inputs.')
    numbers=pd.concat([observations,national.rename('national'),snohvit.rename('snohvit')],axis=1)
    if numbers.isna().any().any() or not numbers.map(lambda v: float('-inf')<v<float('inf')).all().all():
        raise ValueError('Historical observations are missing or nonfinite; no filling.')
    if observations.lt(0).any().any() or national.lt(0).any():
        raise ValueError('Signed/negative field accounting needs explicit review before nonnegative residual weights.')
    result=pd.DataFrame({'national_bcm':national,'snohvit_bcm':snohvit},index=months)
    for label,classes in [('mapped_bcm',{'1','3'}),('outside_boundary_bcm',{'4'}),('unmapped_bcm',{'5'})]:
        ids=owners.loc[owners.classification.isin(classes),'component_id']
        result[label]=observations.loc[:,ids].sum(axis=1)
    result['discrepancy_bcm']=national-snohvit-result[['mapped_bcm','outside_boundary_bcm','unmapped_bcm']].sum(axis=1)
    return result
