"""R7 research-only XYZ radial loft for mildly nonplanar Z-separated loops.

Interpolate sampled 3D polygon boundary points without moving original edges.
Requires star-shaped XY projections, a common Z axis, and disjoint Z envelopes.
Not a generic arbitrary-oriented/non-manifold bridge or production API.
"""
from time import monotonic
import numpy as np
from .geometry import Mesh
from .radial_loft import _connect, _TAU


def _ordered3d(loop):
    center = loop[:, :2].mean(axis=0)
    vectors = loop[:, :2] - center
    theta = np.mod(np.arctan2(vectors[:, 1], vectors[:, 0]), _TAU)
    order = np.argsort(theta, kind="stable")
    angles = theta[order]
    gaps = np.diff(np.r_[angles, angles[0] + _TAU])
    if np.min(gaps) < 1e-6:
        raise ValueError("coincident or ambiguous radial angles")
    ranks = np.empty(len(loop), dtype=int)
    ranks[order] = np.arange(len(loop))
    steps = (np.roll(ranks, -1) - ranks) % len(loop)
    if not (np.all(steps == 1) or np.all(steps == len(loop)-1)):
        raise ValueError("nonmonotone polygon cannot be projected radially")
    return loop[order], angles, center


def _ray_sample3d(ordered, center, angles):
    xy = ordered[:, :2]
    vector = np.roll(xy, -1, axis=0) - xy
    origin = xy - center
    points = []
    for theta in angles:
        direction = np.array([np.cos(theta), np.sin(theta)])
        den = direction[0] * vector[:, 1] - direction[1] * vector[:, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            radius = (origin[:, 0]*vector[:, 1] - origin[:, 1]*vector[:, 0]) / den
            t = (origin[:, 0]*direction[1] - origin[:, 1]*direction[0]) / den
        hit = ((np.abs(den) > 1e-11) & (radius > 1e-10)
               & (t >= -1e-9) & (t <= 1.0 + 1e-9))
        indices = np.flatnonzero(hit)
        if len(indices) == 0:
            raise ValueError("radial ray did not intersect polygon boundary")
        candidate_radius = radius[indices]
        if np.max(candidate_radius) - np.min(candidate_radius) > 1e-7:
            raise ValueError("non-star-shaped or multiply intercepted XY projection")
        ix = int(indices[0])
        point = ordered[ix] + np.clip(t[ix], 0.0, 1.0) * (ordered[(ix+1) % len(ordered)]-ordered[ix])
        points.append(point)
    return np.asarray(points, dtype=float)


def warped_radial_loft(a, b, cuts=3, seconds=10.0):
    """Return detached research mesh for mildly nonplanar boundary correspondence."""
    if cuts != 3 or isinstance(seconds, bool) or not np.isfinite(seconds) or not 0 < seconds <= 60:
        raise ValueError("R7 fixes cuts=3, requires finite 0 < seconds <= 60")
    start = monotonic()
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    for ring in (a, b):
        if ring.ndim != 2 or ring.shape[1] != 3 or not 3 <= len(ring) <= 48:
            raise ValueError("ordered 3..48 XYZ boundary points required")
        if not np.isfinite(ring).all() or np.max(np.abs(ring)) > 1e8:
            raise ValueError("nonfinite/out-of-budget input")
        if len(np.unique(ring, axis=0)) != len(ring):
            raise ValueError("duplicate input point")
    if float(np.min(b[:, 2])-np.max(a[:, 2])) <= 1e-5:
        raise ValueError("R7 requires strict positive Z gap between whole boundary envelopes")
    pa, ta, ca = _ordered3d(a)
    pb, tb, cb = _ordered3d(b)
    k = max(len(a), len(b), 12)
    period = _TAU / k
    available = np.r_[ta % period, tb % period]
    offsets = (np.arange(8) + .5) * period / 8
    seam = max(offsets, key=lambda v: np.min(np.abs((available - v + period/2) % period - period/2)))
    sampled_angles = np.arange(k) * period + seam
    ra = _ray_sample3d(pa, ca, sampled_angles)
    rb = _ray_sample3d(pb, cb, sampled_angles)
    rings = [(pa, ta)]
    for h in range(1, cuts + 1):
        u = h / (cuts+1)
        rings.append(((1-u)*ra + u*rb, sampled_angles))
    rings.append((pb, tb))
    ring_offsets = np.cumsum([0] + [len(p) for p, _ in rings[:-1]])
    faces = []
    for i in range(len(rings)-1):
        faces.extend(_connect(rings[i][1], rings[i+1][1],
                              int(ring_offsets[i]), int(ring_offsets[i+1])))
    if monotonic()-start > seconds:
        raise TimeoutError("R7 generation exceeded budget")
    mesh = Mesh(np.concatenate([p for p, _ in rings]), np.array(faces, dtype=np.int64))
    return dict(mesh=mesh, approved=False, cuts=cuts,
                method="warped_radial_loft", added_vertices=cuts*k)
