"""Pure, bounded quantitative displacement analysis for trusted fixture meshes.

No Blender import. No GLB or private source ingestion: this utility is called
only on vertex positions of the repository-owned deterministic CI experiment.
"""
from __future__ import annotations

import math

MAX_VERTICES = 100_000


class ExperimentMetricError(ValueError):
    pass


def _vertices(points, label: str):
    if not isinstance(points, list) or not 1 <= len(points) <= MAX_VERTICES:
        raise ExperimentMetricError(f"{label} must contain 1..{MAX_VERTICES} vertices")
    valid = []
    for row in points:
        if (not isinstance(row, (list, tuple)) or len(row) != 3 or any(
                isinstance(v, bool) or not isinstance(v, (int, float))
                for v in row)):
            raise ExperimentMetricError(f"{label} contains an invalid XYZ point")
        try:
            xyz = tuple(float(v) for v in row)
        except (OverflowError, ValueError) as exc:
            raise ExperimentMetricError(f"{label} contains an unrepresentable point") from exc
        if not all(math.isfinite(v) for v in xyz):
            raise ExperimentMetricError(f"{label} contains a nonfinite point")
        valid.append(xyz)
    return valid


def vertex_displacement(reference: list, candidate: list) -> dict:
    """Index-aligned distances; only compare fixtures with identical topology.

    Vertex indices are not a general surface matching algorithm. Never use
    this result as geometric equivalence proof for arbitrary GLBs.
    """
    left = _vertices(reference, "reference")
    right = _vertices(candidate, "candidate")
    if len(left) != len(right):
        raise ExperimentMetricError("Index-aligned vertex counts must match")
    distances = [
        math.sqrt(sum((v - u) ** 2 for u, v in zip(a, b)))
        for a, b in zip(left, right)
    ]
    if not all(math.isfinite(d) for d in distances):
        raise ExperimentMetricError("Displacement exceeds finite numeric range")
    return {
        "vertex_count": len(distances),
        "mean_local_displacement": round(sum(distances) / len(distances), 7),
        "max_local_displacement": round(max(distances), 7),
        "changed_vertex_count": sum(d > 1e-6 for d in distances),
        "tolerance": 1e-6,
        "metric": "index_aligned_local_vertex_distance",
        "valid_for_arbitrary_glb": False,
    }

def radial_distribution_error(reference: list, candidate: list) -> dict:
    """Mean absolute sorted distance-from-local-origin difference.

    A conservative, order-independent *synthetic-fixture* diagnostic used for
    our centered sphere and bevel cube. It does NOT compare surfaces, direction,
    topology identity, cavities or vertex correspondence. Different shapes
    may share the exact same radial distribution.
    """
    left = _vertices(reference, "reference")
    right = _vertices(candidate, "candidate")
    if len(left) != len(right):
        raise ExperimentMetricError("Radial comparison vertex counts must match")

    def radii(points):
        values = [math.hypot(*xyz) for xyz in points]
        if not all(math.isfinite(r) for r in values):
            raise ExperimentMetricError("Radial distance is not finite")
        return sorted(values)

    a = radii(left)
    b = radii(right)
    score = sum(abs(u - v) for u, v in zip(a, b)) / len(a)
    if not math.isfinite(score):
        raise ExperimentMetricError("Radial distribution score is not finite")
    return {
        "mean_sorted_radius_error": round(score, 7),
        "vertex_count": len(a),
        "metric": "sorted_local_origin_radius_mean_absolute_difference",
        "invariant_to_vertex_order": True,
        "valid_for_arbitrary_glb": False,
        "geometry_equivalence_verified": False,
    }
