"""R5 research-only radial loft: two planar, star-shaped, Z-separated loops.

No Blender state is accessed. Original boundary vertices and polygon edges are
preserved; intermediate rings are permitted, but neither hole branching nor
non-planar boundaries are supported. Not an approved CBDK operator.
"""
from time import monotonic
import numpy as np
from .geometry import Mesh

_TAU = 2.0 * np.pi


def _ordered(loop):
    xy = loop[:, :2]
    center = xy.mean(axis=0)
    angles = np.mod(np.arctan2(xy[:, 1] - center[1], xy[:, 0] - center[0]), _TAU)
    order = np.argsort(angles, kind="stable")
    sorted_angles = angles[order]
    if np.min(np.diff(np.r_[sorted_angles, sorted_angles[0] + _TAU])) < 1e-6:
        raise ValueError("ambiguous radial order")
    ranks = np.empty(len(loop), dtype=int)
    ranks[order] = np.arange(len(loop))
    steps = (np.roll(ranks, -1) - ranks) % len(loop)
    if not (np.all(steps == 1) or np.all(steps == len(loop)-1)):
        raise ValueError("edge order is not angularly monotone")
    if np.ptp(loop[:, 2]) > 1e-5:
        raise ValueError("non-planar boundary is outside R5 contract")
    return loop[order], sorted_angles, center


def _ray_sample(loop, center, angles):
    xy = loop[:, :2]
    edge = np.roll(xy, -1, axis=0) - xy
    start = xy - center
    result = []
    for theta in angles:
        direction = np.array([np.cos(theta), np.sin(theta)])
        den = direction[0]*edge[:, 1] - direction[1]*edge[:, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            distance = (start[:, 0]*edge[:, 1] - start[:, 1]*edge[:, 0]) / den
            part = (start[:, 0]*direction[1] - start[:, 1]*direction[0]) / den
        mask = (np.abs(den) > 1e-11) & (distance > 1e-10) & (part >= -1e-9) & (part <= 1+1e-9)
        hits = np.sort(distance[mask])
        if len(hits) == 0 or hits[-1]-hits[0] > 1e-7:
            raise ValueError("non-star-shaped polygon or invalid ray intersection")
        result.append(np.r_[center + hits[0]*direction, loop[0, 2]])
    return np.array(result)


def _connect(theta_a, theta_b, offset_a, offset_b):
    n, m = len(theta_a), len(theta_b)
    faces = []
    i = j = 0
    while i < n or j < m:
        if i == n:
            advance_a = False
        elif j == m:
            advance_a = True
        else:
            next_a = theta_a[(i+1) % n] + (_TAU if i+1 >= n else 0.0)
            next_b = theta_b[(j+1) % m] + (_TAU if j+1 >= m else 0.0)
            advance_a = next_a <= next_b
        if advance_a:
            faces.append((offset_a + i % n, offset_a + (i+1) % n, offset_b + j % m))
            i += 1
        else:
            faces.append((offset_a + i % n, offset_b + (j+1) % m, offset_b + j % m))
            j += 1
    return faces


def radial_loft(a, b, cuts=3, seconds=10.0):
    """Propose a detached triangulated annular strip.

    cuts=3 is the R5 preregistered research candidate, not a tuned default for
    arbitrary production meshes. Synthetic-only radial/z-axis scope.
    """
    if cuts != 3 or isinstance(seconds, bool) or not np.isfinite(seconds) or not 0 < seconds <= 60:
        raise ValueError("R5 freezes cuts=3 and requires seconds in (0, 60]")
    start = monotonic()
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    for loop in (a, b):
        if loop.ndim != 2 or loop.shape[1] != 3 or not 3 <= len(loop) <= 48:
            raise ValueError("each loop must be 3..48 ordered XYZ points")
        if not np.isfinite(loop).all() or np.max(np.abs(loop)) > 1e8 or len(np.unique(loop, axis=0)) != len(loop):
            raise ValueError("nonfinite, duplicate, or out-of-budget coordinates")
    if np.max(a[:, 2]) >= np.min(b[:, 2]):
        raise ValueError("R5 requires disjoint Z planes in increasing order")
    pa, ta, ca = _ordered(a)
    pb, tb, cb = _ordered(b)
    k = max(len(a), len(b), 12)
    period = _TAU / k
    available = np.r_[ta % period, tb % period]
    offsets = (np.arange(8) + 0.5) * period / 8
    seam = max(offsets, key=lambda v: np.min(np.abs((available-v+period/2) % period - period/2)))
    angles = np.arange(k) * period + seam
    qa = _ray_sample(pa, ca, angles)
    qb = _ray_sample(pb, cb, angles)
    rings = [(pa, ta)]
    for h in range(1, cuts+1):
        u = h / (cuts+1)
        rings.append(((1-u)*qa+u*qb, angles))
    rings.append((pb, tb))
    offsets = np.cumsum([0] + [len(r[0]) for r in rings[:-1]])
    faces = []
    for i in range(len(rings)-1):
        faces.extend(_connect(rings[i][1], rings[i+1][1], int(offsets[i]), int(offsets[i+1])))
    if monotonic()-start > seconds:
        raise TimeoutError("R5 generation time budget exceeded")
    mesh = Mesh(np.concatenate([r[0] for r in rings]), np.asarray(faces, dtype=np.int64))
    return dict(mesh=mesh, approved=False, method="radial_loft_3cuts", cuts=cuts, added_vertices=cuts*k)
