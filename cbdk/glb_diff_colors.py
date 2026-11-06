"""GLB-020: bounded, review-only per-triangle 3D difference colors.

No Blender dependency, file access, addon execution or persistence.
Each source face receives a classification from deterministic 24-point samples
against a BVH of the opposite mesh. Sampling is not full surface equivalence.
"""
from __future__ import annotations

import math

from .glb_surface_distance import (
    SAMPLES_PER_TRIANGLE, _build_bvh, _bvh_nearest_distance_squared,
    _sample, _validated_triangles,
)

COLOR_RGBA = {
    "low": (0.55, 0.58, 0.63, 1.0),       # grey: no sampled change above threshold
    "medium": (1.00, 0.72, 0.08, 1.0),    # amber: review
    "high": (0.92, 0.09, 0.08, 1.0),      # red: investigate
}
LABELS = tuple(COLOR_RGBA)


def _diagonal(ref_faces, cand_faces):
    points = [p for face in ref_faces + cand_faces for p in face]
    mins = [min(p[axis] for p in points) for axis in range(3)]
    maxs = [max(p[axis] for p in points) for axis in range(3)]
    length = math.sqrt(sum((hi - lo) ** 2 for lo, hi in zip(mins, maxs)))
    if not math.isfinite(length) or length <= 0:
        raise ValueError("Invalid shared world-space bounds")
    return length


def classify_faces(reference, candidate):
    """Compute directional per-face sampled-error classes in original face order.

    Outputs are intentionally limited to classifications and aggregate counts;
    no source coordinates, geometry or names are written to reports.
    """
    # Validation enforces the same hard 512-triangle and finite-coordinate
    # limits as the existing GLB-019 surface comparison.
    ref = _validated_triangles(reference, "reference")
    cand = _validated_triangles(candidate, "candidate")
    scale = _diagonal(reference, candidate)
    low_threshold = max(scale * 0.01, 1e-7)
    high_threshold = max(scale * 0.05, low_threshold * 2)

    def classify(source_faces, target):
        tree = _build_bvh(target)
        labels = []
        worst = 0.0
        for original in source_faces:
            canonical, _ = _validated_triangles([original], "face")[0]
            err = 0.0
            for point in _sample(canonical):
                d2, _ = _bvh_nearest_distance_squared(point, target, tree)
                d = math.sqrt(max(0.0, d2))
                if not math.isfinite(d):
                    raise ValueError("Nonfinite triangle distance")
                err = max(err, d)
            labels.append("high" if err >= high_threshold
                          else "medium" if err >= low_threshold else "low")
            worst = max(worst, err)
        counts = {key: labels.count(key) for key in LABELS}
        return labels, counts, round(worst, 7)

    ref_labels, ref_counts, ref_worst = classify(reference, cand)
    cand_labels, cand_counts, cand_worst = classify(candidate, ref)
    return {
        "reference_labels": ref_labels,
        "candidate_labels": cand_labels,
        "reference_counts": ref_counts,
        "candidate_counts": cand_counts,
        "reference_sampled_max": ref_worst,
        "candidate_sampled_max": cand_worst,
        "legend": {
            "low": "sampled error below 1% of combined AABB diagonal",
            "medium": "sampled error from 1% to below 5%",
            "high": "sampled error at least 5%",
        },
        "thresholds": {
            "units": "input_coordinate_units",
            "combined_aabb_diagonal": round(scale, 7),
            "medium_from": round(low_threshold, 7),
            "high_from": round(high_threshold, 7),
            "samples_per_triangle": SAMPLES_PER_TRIANGLE,
        },
        "sampled_only": True,
        "complete_surface_equivalence_proven": False,
    }
