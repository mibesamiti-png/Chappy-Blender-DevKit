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
