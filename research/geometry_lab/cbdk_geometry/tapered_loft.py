"""R8: one experimental tapered-density XYZ radial loft (not an add-on).

No Blender or scene imports. Original boundary vertices and edges stay fixed.
Unlike R7 uniform-k internal rings, internal ring h has a vertex count
interpolating the two input loop sizes. Limited to XY-star-shaped/Z-separated
nonplanar rings. All results are research-only and approved=False.
"""
from time import monotonic

import numpy as np
from .geometry import Mesh
from .radial_loft import _TAU, _connect
from .warped_loft import _ordered3d, _ray_sample3d


def tapered_radial_loft(a, b, cuts=3, seconds=10.0):
    """Build one detached triangulated strip, with 3 variable-density rings."""
    if cuts != 3 or isinstance(seconds, bool) or not np.isfinite(seconds) or not 0 < seconds <= 60:
        raise ValueError("R8 fixes cuts=3 and requires 0 < seconds <= 60")
    begin = monotonic()
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    for ring in (a, b):
        if ring.ndim != 2 or ring.shape[1] != 3 or not 3 <= len(ring) <= 48:
            raise ValueError("R8 requires ordered loops of 3..48 XYZ points")
        if (not np.isfinite(ring).all() or np.max(np.abs(ring)) > 1e8
                or len(np.unique(ring, axis=0)) != len(ring)):
            raise ValueError("nonfinite/duplicate/overbudget input")
    if float(np.min(b[:, 2]) - np.max(a[:, 2])) <= 1e-5:
        raise ValueError("R8 requires disjoint ring Z envelopes")

    pa, ta, ca = _ordered3d(a)
    pb, tb, cb = _ordered3d(b)

    base_k = max(len(a), len(b), 12)
    period = _TAU / base_k
    angles_known = np.r_[ta % period, tb % period]
    choices = (np.arange(8) + 0.5) * period / 8
    seam = max(choices,
               key=lambda v: np.min(np.abs((angles_known-v+period/2) % period-period/2)))

    rings = [(pa, ta)]
    internal_counts = []
    for h in range(1, cuts + 1):
        u = h / (cuts+1)
        density = max(12, int(round((1-u)*len(a) + u*len(b))))
        internal_counts.append(density)
        theta = np.arange(density) * (_TAU/density) + seam
        start = _ray_sample3d(pa, ca, theta)
        end = _ray_sample3d(pb, cb, theta)
        rings.append(((1-u)*start + u*end, theta))
    rings.append((pb, tb))

    offsets = np.cumsum([0] + [len(points) for points, _ in rings[:-1]])
    faces = []
    for i in range(len(rings)-1):
        faces.extend(_connect(rings[i][1], rings[i+1][1],
                              int(offsets[i]), int(offsets[i+1])))
    if monotonic() - begin > seconds:
        raise TimeoutError("R8 generation time budget exceeded")
    mesh = Mesh(np.concatenate([ring[0] for ring in rings]),
                np.asarray(faces, dtype=np.int64))
    return dict(mesh=mesh, approved=False, method="tapered_radial_loft_3cuts",
                cuts=cuts, internal_counts=internal_counts,
                added_vertices=sum(internal_counts))
