"""R10 research-only quality-gated R8/R9 routing; no Blender scene changes.

R8 exactly once. R9 _one_pass applied only when R8 min triangle quality <.1.
This score is NOT a collision or validity oracle: use independent CGAL afterward.
"""
from time import monotonic
import numpy as np

from .geometry import Mesh
from .tapered_loft import tapered_radial_loft
from .flip_loft import _one_pass


def _fast_min_triangle_quality(mesh):
    """Vectorized equivalent of cbdk_geometry.geometry.quality's mean-ratio."""
    t = mesh.vertices[mesh.faces]
    v1 = t[:, 1] - t[:, 0]
    v2 = t[:, 2] - t[:, 0]
    double_area = np.linalg.norm(np.cross(v1, v2), axis=1)
    edge_square_sum = np.sum((np.roll(t, -1, axis=1) - t)**2, axis=(1, 2))
    values = 2.0 * np.sqrt(3.0) * double_area / edge_square_sum
    return float(np.min(values))


def conditional_flip_loft(a, b, cuts=3, seconds=10.0):
    """Return detached mesh, the chosen path, and diagnostic metadata.

    No production claims. Always validate with independent CGAL before adoption.
    """
    if (cuts != 3 or isinstance(seconds, bool) or
            not np.isfinite(seconds) or not 0 < seconds <= 60):
        raise ValueError("R10 fixes three cuts and requires finite 0<seconds<=60")
    started = monotonic()
    base = tapered_radial_loft(a, b, cuts=3, seconds=seconds)
    mesh = base["mesh"]
    before = _fast_min_triangle_quality(mesh)
    if before >= .1:
        return dict(mesh=mesh, method="r10_quality_router", path="fast",
                    trigger="min_triangle_quality_below_0.1", flips=0, passes=0,
                    initial_min_quality=before, final_min_quality=before,
                    unchanged_from_r8=True, approved=False)
    faces = np.array(mesh.faces, copy=True)
    flips = 0
    passes = 0
    for _ in range(3):
        count = _one_pass(mesh.vertices, faces)  # same frozen R9 heuristic
        if not count:
            break
        flips += count
        passes += 1
        if monotonic() - started > seconds:
            raise TimeoutError("R10 conditional repair exceeds time budget")
    result = Mesh(mesh.vertices, faces)
    # Hard invariant. A CGAL oracle separately checks global collisions.
    if (len(result.faces) != len(mesh.faces) or
            not np.array_equal(result.vertices, mesh.vertices)):
        raise RuntimeError("conditional R10 geometry invariant violated")
    after = _fast_min_triangle_quality(result)
    return dict(mesh=result, method="r10_quality_router", path="repair",
                trigger="min_triangle_quality_below_0.1", flips=flips, passes=passes,
                initial_min_quality=before, final_min_quality=after,
                unchanged_from_r8=bool(np.array_equal(result.faces, mesh.faces)),
                approved=False)
