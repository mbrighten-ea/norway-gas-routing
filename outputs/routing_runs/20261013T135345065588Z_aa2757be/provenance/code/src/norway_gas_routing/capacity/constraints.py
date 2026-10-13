"""Separate serial point bounds, reserved for reviewed compatible inputs.

Not called for the currently blocked public ENTSOG candidates.
"""
import math

from .contract import IDENTITIES


def add_reviewed_point_bounds(built, rows):
    seen = set()
    validated = []
    for row in rows:
        key = row['asset_key']
        if key in seen or key not in IDENTITIES:
            raise ValueError('Distinct known point bounds required')
        seen.add(key)
        expected = IDENTITIES[key]
        if tuple(row[k] for k in ('operator', 'point', 'direction', 'arc')) != expected:
            raise ValueError('Reviewed point/arc identity mismatch')
        if (row.get('status') != 'VERIFIED_COMPATIBLE' or row.get('optimiser_eligible') is not True
                or row.get('capacity_category') != 'point_technical'
                or row.get('coverage_status') != 'complete' or not row.get('activation_reference')
                or row.get('conversion_approved') is not True or row.get('maintenance_deductions', 0) != 0):
            raise ValueError('Point bound requires reviewed physical/conversion eligibility; no extra derate')
        value = row['candidate_bcm']
        if value is None or not math.isfinite(value) or value < 0:
            raise ValueError('Unknown capacity cannot become a point limit')
        arc = expected[3]
        if arc not in built['flows']:
            raise ValueError('Point arc missing from existing network')
        name = 'public_point_' + key.replace(':', '_')
        if built['problem'].get_constraint_by_name(name) is not None:
            raise ValueError('Point constraint already present')
        validated.append((arc,value,name))
    for arc,value,name in validated:
        built['problem'] += built['flows'][arc] <= value, name
    return seen
