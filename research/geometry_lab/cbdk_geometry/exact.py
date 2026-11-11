"""Exact rational intersection of represented binary64 triangle coordinates.

Research implementation, not a formal proof. No tolerance or vertex inset.
Uses edge/plane clipping, independently testable against CGAL's kernel.
"""
from fractions import Fraction
from itertools import combinations
import math
from time import monotonic


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def lerp(a, b, t):
    return tuple(x+t*(y-x) for x, y in zip(a, b))


def rational_triangle(values):
    if len(values) != 3 or any(len(p) != 3 for p in values):
        raise ValueError('triangle must be 3x3')
    points = []
    for p in values:
        floats = tuple(float(x) for x in p)
        if not all(math.isfinite(x) and abs(x) <= 1e100 for x in floats):
            raise ValueError('coordinates must be finite and bounded by 1e100')
        points.append(tuple(Fraction(x) for x in floats))
    if not any(cross(sub(points[1], points[0]), sub(points[2], points[0]))):
        raise ValueError('exactly degenerate triangle')
    return tuple(points)


def _segment_clip(p, q, triangle, normal):
    """Intersect a segment with a triangle using exact linear inequalities."""
    dp, dq = dot(normal, sub(p, triangle[0])), dot(normal, sub(q, triangle[0]))
    if dp and dq and (dp > 0) == (dq > 0):
        return []
    if dp != dq:
        t = dp/(dp-dq)
        if not 0 <= t <= 1:
            return []
        p = q = lerp(p, q, t)
    elif dp:  # parallel, off the plane
        return []
    lower, upper = Fraction(0), Fraction(1)
    for i in range(3):
        a, b = triangle[i], triangle[(i+1) % 3]
        edge = sub(b, a)
        u = dot(cross(edge, sub(p, a)), normal)
        v = dot(cross(edge, sub(q, a)), normal)
        if u < 0 and v < 0:
            return []
        if u < 0:
            lower = max(lower, u/(u-v))
        elif v < 0:
            upper = min(upper, u/(u-v))
    if lower > upper:
        return []
    return [lerp(p, q, lower), lerp(p, q, upper)]


def _intersection(a, b):
    na, nb = cross(sub(a[1], a[0]), sub(a[2], a[0])), cross(sub(b[1], b[0]), sub(b[2], b[0]))
    points = set()
    for first, second, normal in ((a, b, nb), (b, a, na)):
        for i in range(3):
            points.update(_segment_clip(first[i], first[(i+1) % 3], second, normal))
    return points


def _on_shared(p, shared):
    if len(shared) == 1:
        return p == shared[0]
    if len(shared) == 2:
        a, b = shared
        return not any(cross(sub(p, a), sub(b, a))) and dot(sub(p, a), sub(p, b)) <= 0
    return False


def classify_pair(a, b, ids_a=None, ids_b=None, prefilter=True):
    """Return disjoint/shared_boundary/intersection/duplicate.

    IDs express actual mesh connectivity, not coordinate welding. All contact
    outside the common simplex counts as intersection, including touching.
    """
    if (ids_a is None) != (ids_b is None):
        raise ValueError('provide both ID triples or neither')
    if ids_a is not None:
        if len(ids_a) != 3 or len(ids_b) != 3 or len(set(ids_a)) != 3 or len(set(ids_b)) != 3:
            raise ValueError('unique triangle ID triples required')
        for i, x in enumerate(ids_a):
            for j, y in enumerate(ids_b):
                if x == y and tuple(a[i]) != tuple(b[j]):
                    raise ValueError('shared ID coordinate mismatch')
    # Compare input coordinates directly: extrema only, no rounded arithmetic.
    # Validate before early rejection so invalid geometry is never "disjoint".
    a, b = rational_triangle(a), rational_triangle(b)
    if prefilter and any(max(p[k] for p in a) < min(p[k] for p in b) or
                        max(p[k] for p in b) < min(p[k] for p in a) for k in range(3)):
        return 'disjoint'
    points = _intersection(a, b)
    if not points:
        return 'disjoint'
    common = [] if ids_a is None else [a[i] for i,x in enumerate(ids_a) if x in ids_b]
    if len(common) == 3:
        return 'duplicate'
    if common and all(_on_shared(p, common) for p in points):
        return 'shared_boundary'
    return 'intersection'


def detect_exact(mesh, pair_budget=200000, seconds=30):
    """Bound ALL broad-phase scans; incomplete reports never claim a clean mesh.

    Returned pairs contain face indices only. A binary64-exact arithmetic model
    is not a formal software certificate or proof of the intended CAD surface.
    """
    if type(pair_budget) is not int or not 1 <= pair_budget <= 2000000:
        raise ValueError('pair_budget must be integer in 1..2000000')
    if isinstance(seconds, bool) or not math.isfinite(seconds) or not 0 < seconds <= 300:
        raise ValueError('seconds must be in (0,300]')
    if len(mesh.faces) > 2048:
        return dict(status='budget_exceeded', reason='face_limit', pairs=None,
                    scanned=0, narrow_tests=0, certified=False)
    deadline, scanned, narrow = monotonic()+seconds, 0, 0
    triangles = mesh.vertices[mesh.faces]
    lo, hi = triangles.min(1), triangles.max(1)
    hits = []
    for i, j in combinations(range(len(triangles)), 2):
        if scanned >= pair_budget or monotonic() >= deadline:
            return dict(status='budget_exceeded', reason='pair_or_time_limit', pairs=None,
                        scanned=scanned, narrow_tests=narrow, certified=False)
        scanned += 1
        if any(hi[i,k] < lo[j,k] or hi[j,k] < lo[i,k] for k in range(3)):
            continue
        narrow += 1
        result = classify_pair(triangles[i], triangles[j], mesh.faces[i], mesh.faces[j])
        if result in ('intersection', 'duplicate'):
            hits.append((i, j))
    return dict(status='measured', reason=None, pairs=hits, scanned=scanned,
                narrow_tests=narrow, certified=False, arithmetic='exact_binary64_rational')
