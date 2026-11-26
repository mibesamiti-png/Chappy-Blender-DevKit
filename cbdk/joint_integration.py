"""Bounded synthetic rotary candidate review. No execution, approval or R28 schema."""
from math import isfinite

POLICIES = ('LOCKED', 'PREFERRED', 'FREE')
MAX_CANDIDATES = 4


def number(value):
    if type(value) not in (int, float) or not isfinite(value) or not .01 <= value <= 100:
        raise ValueError('dimension_invalid')
    return float(value)


def proposals(original, target, policy):
    """Fixed bounded review probes, subsequently corrected by external CJM repair.

    A negative direction control, midpoint, then target, each from original.
    Preferences are disclosed, never silently treated as locks or override consent.
    """
    original, target = number(original), number(target)
    if policy not in POLICIES: raise ValueError('policy_invalid')
    if policy == 'LOCKED' or original == target: return []
    return [('negative_control', number(original+(original-target)/2)),
            ('midpoint', number((original+target)/2)), ('declared_target', target)]


def checked_measurement(row):
    if type(row) is not dict or set(row) != {'dimensions', 'protected_sha', 'gl', 'closed'}:
        raise ValueError('measurement_invalid')
    if len(row['dimensions']) != 2: raise ValueError('parts_missing')
    for xyz in row['dimensions']:
        if type(xyz) is not list or len(xyz) != 3: raise ValueError('dimensions_invalid')
        for x in xyz: number(x)
    h = row['protected_sha']
    if type(h) is not str or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
        raise ValueError('protected_digest_invalid')
    if type(row['closed']) is not bool: raise ValueError('closed_flag_invalid')
    if type(row['gl']) is not list or len(row['gl']) != 2: raise ValueError('gl_missing')
    for r in row['gl']:
        if type(r) is not dict or r.get('status') != 'measured' or r.get('pairs') != []:
            raise ValueError('geometry_unknown_or_intersecting')
    if not row['closed']: raise ValueError('geometry_not_closed')
    return row


def score(row, target):
    checked_measurement(row); target = number(target)
    # Z is axial length, not part of the declared radial objective.
    return max(abs(v-target) for xyz in row['dimensions'] for v in xyz[:2])


def review(baseline, candidate, target, best_score):
    """R28 principles: measurement, protected-part veto, strict progress; no adoption."""
    checked_measurement(baseline); checked_measurement(candidate)
    if type(best_score) not in (int, float) or not isfinite(best_score) or best_score < 0:
        raise ValueError('score_invalid')
    current = score(candidate, target)
    if candidate['protected_sha'] != baseline['protected_sha']:
        decision = 'protected_part_regression'
    elif any(abs(a[2]-b[2]) > 1e-5 for a,b in zip(baseline['dimensions'],candidate['dimensions'])):
        decision = 'axial_dimension_regression'
    elif best_score-current > 1e-5:
        decision = 'target_reached' if current <= 1e-5 else 'observed_improvement'
    elif current-best_score > 1e-5:
        decision = 'regression'
    else:
        decision = 'uncertain'
    return dict(decision=decision, score=current,
                accepted_for_review=decision in ('target_reached','observed_improvement'),
                auto_apply=False, approved=False, printable=False, continuous_collision_checked=False)


def verified_write(read, write, original, candidate, finish):
    """Readback transaction; a failed restoration blocks all subsequent attempts."""
    try:
        write(candidate)
        if read() != candidate: raise RuntimeError('rna_readback_mismatch')
        finish()
        if read() != candidate: raise RuntimeError('post_write_changed')
    except BaseException:
        try:
            write(original)
            if read() != original: raise RuntimeError('rollback_failed')
        except BaseException as error:
            raise RuntimeError('rollback_failed') from error
        raise
