"""Bounded coarse-to-fine sampled surface-distance experiment (GLB-017).

This is *review-only* evidence from aligned triangle coordinates. Coarse error
ranks suspects; a fixed exploration budget also revisits large zero-error
faces, since an unnoticed opening may yield zero error at coarse resolution.
Neither phase proves equality, coverage, cavities, or a true Hausdorff bound.
"""
from __future__ import annotations

import math

from .glb_surface_distance import (
    SurfaceDistanceError, _validated_triangles, _build_bvh,
    _bvh_nearest_distance_squared, _radical_inverse,
)

COARSE_SAMPLES = 8
FINE_SAMPLES = 48
MAX_SUSPECT_FACES = 8
EXPLORATION_FACES = 2
SIGNAL_THRESHOLD = 1e-6


def _sample_at(face, index):
    a, b, c = face
    u, v = _radical_inverse(index, 2), _radical_inverse(index, 3)
    root = math.sqrt(u)
    weights = (1.0 - root, root * (1.0 - v), root * v)
    return tuple(sum(weights[j] * face[j][axis] for j in range(3))
                 for axis in range(3))


def _directed_multires(source, target):
    tree = _build_bvh(target)
    per_face = []
    precise_checks = 0
    for face, area in source:
        values = []
        for index in range(1, COARSE_SAMPLES + 1):
            d2, performed = _bvh_nearest_distance_squared(
                _sample_at(face, index), target, tree)
            precise_checks += performed
            distance = math.sqrt(d2)
            if not math.isfinite(distance):
                raise SurfaceDistanceError("Nonfinite surface sample distance")
            values.append(distance)
        per_face.append({"distances": values, "area": area})

    # Use *actual sampled discrepancy* to direct refinement. Large faces get
    # a small, independent exploration budget even if all initial scores are
    # zero; otherwise a small unseen cutout could never be discovered.
    suspected = sorted(
        (i for i, row in enumerate(per_face)
         if max(row["distances"]) > SIGNAL_THRESHOLD),
        key=lambda i: (-max(per_face[i]["distances"]), i),
    )[:MAX_SUSPECT_FACES]
    known = set(suspected)
    exploration = sorted(
        (i for i in range(len(source)) if i not in known),
        key=lambda i: (-per_face[i]["area"], i),
    )[:EXPLORATION_FACES]
    refined = set(suspected) | set(exploration)

    coarse_values = [tuple(row["distances"]) for row in per_face]
    extra = 0
    for i in sorted(refined):
        face = source[i][0]
        for index in range(COARSE_SAMPLES + 1, FINE_SAMPLES + 1):
            d2, performed = _bvh_nearest_distance_squared(
                _sample_at(face, index), target, tree)
            precise_checks += performed
            distance = math.sqrt(d2)
            if not math.isfinite(distance):
                raise SurfaceDistanceError("Nonfinite refined distance")
            per_face[i]["distances"].append(distance)
            extra += 1

    total_area = sum(row["area"] for row in per_face)
    if not math.isfinite(total_area) or total_area <= 0:
        raise SurfaceDistanceError("Invalid surface area")

    def aggregate(all_values):
        weighted = sum(
            per_face[i]["area"] * (sum(row) / len(row))
            for i, row in enumerate(all_values))
        value = weighted / total_area
        sampled_max = max(max(row) for row in all_values)
        if not math.isfinite(value) or not math.isfinite(sampled_max):
            raise SurfaceDistanceError("Nonfinite aggregated distance")
        return round(value, 7), round(sampled_max, 7)

    coarse_mean, coarse_max = aggregate(coarse_values)
    fine_mean, fine_max = aggregate([row["distances"] for row in per_face])
    return {
        "coarse_mean": coarse_mean,
        "coarse_sampled_max": coarse_max,
        "refined_mean": fine_mean,
        "refined_sampled_max": fine_max,
        "coarse_sample_count": len(source) * COARSE_SAMPLES,
        "additional_sample_count": extra,
        "total_sample_count": len(source) * COARSE_SAMPLES + extra,
        "refined_face_count": len(refined),
        "suspect_face_count": len(suspected),
        "exploration_face_count": len(exploration),
        "unrefined_face_count": len(source) - len(refined),
        "triangle_distance_evaluations": precise_checks,
        "new_nonzero_sample_after_refinement": (
            coarse_max <= SIGNAL_THRESHOLD and fine_max > SIGNAL_THRESHOLD
        ),
    }


def compare_multires_triangle_surfaces(reference: list, candidate: list) -> dict:
    """Two-way bounded coarse/fine experiment, no GLB loading or auto edits.

    A zero result is only "no sampled difference at these points". Selective
    refinement can still miss localized differences on unvisited faces.
    """
    ref = _validated_triangles(reference, "reference")
    cand = _validated_triangles(candidate, "candidate")
    forward = _directed_multires(ref, cand)
    backward = _directed_multires(cand, ref)
    return {
        "schema_version": 1,
        "kind": "cbdk_multires_sampled_surface_distance",
        "status": "review_only",
        "metric": "area_weighted_bidirectional_selectively_refined_point_to_triangle",
        "reference_to_candidate": forward,
        "candidate_to_reference": backward,
        "coarse_symmetric_mean": round(
            (forward["coarse_mean"] + backward["coarse_mean"]) / 2, 7),
        "refined_symmetric_mean": round(
            (forward["refined_mean"] + backward["refined_mean"]) / 2, 7),
        "coarse_symmetric_sampled_max": max(
            forward["coarse_sampled_max"], backward["coarse_sampled_max"]),
        "refined_symmetric_sampled_max": max(
            forward["refined_sampled_max"], backward["refined_sampled_max"]),
        "new_nonzero_sample_after_refinement": (
            forward["new_nonzero_sample_after_refinement"]
            or backward["new_nonzero_sample_after_refinement"]
        ),
        "coarse_samples_per_triangle": COARSE_SAMPLES,
        "fine_samples_per_selected_triangle": FINE_SAMPLES,
        "maximum_suspect_faces_per_direction": MAX_SUSPECT_FACES,
        "exploration_faces_per_direction": EXPLORATION_FACES,
        "reference_triangles": len(ref),
        "candidate_triangles": len(cand),
        "vertex_correspondence_required": False,
        "complete_surface_coverage": False,
        "exact_hausdorff_verified": False,
        "enclosed_cavities_verified": False,
        "auto_approve": False,
        "limitations": [
            "Unselected triangles are tested only at coarse sample resolution",
            "A narrow defect may be missed by both sample budgets",
            "Area-biased exploration is not uniform coverage or an error bound",
            "A zero sampled distance never proves identical surfaces or solids",
            "Scores are not guaranteed monotonic when sampling density varies",
            "Input triangles must be aligned in a common coordinate space",
        ],
        "safety": {
            "user_addon_executed": False,
            "private_glb_uploaded": False,
            "source_modified": False,
            "automatic_parameter_changes": False,
        },
    }
