"""GLB-020 supplemental surface probes: reveal sampling sensitivity, not proof of coverage.

The existing 24 points/triangle remain the primary GLB-020 color metric.
We compute a second, disjoint 24-point Halton set on each same triangle and
flag places where additional sampling *raises the observed error materially*
or crosses a color threshold. All faces remain unverified for exact equivalence.

No raw coordinates/names or individual flagged face indices go into review.json.
Only the user-private HTML will carry per-face numeric 0/1 flags.
"""
from __future__ import annotations

import math

from .glb_surface_distance import (
    SAMPLES_PER_TRIANGLE, _validated_triangles, _build_bvh,
    _bvh_nearest_distance_squared, _sample, _radical_inverse,
)

METHOD = "extra_halton_24_probe_sensitivity_v1"
ADDITIONAL_SAMPLES = 24
MIN_INCREASE_DIAGONAL_RATIO = 0.005


def _additional_points(face):
    a, b, c = face
    for index in range(SAMPLES_PER_TRIANGLE + 1,
                       SAMPLES_PER_TRIANGLE + ADDITIONAL_SAMPLES + 1):
        u, v = _radical_inverse(index, 2), _radical_inverse(index, 3)
        root = math.sqrt(u)
        alpha, beta, gamma = 1.0 - root, root * (1.0 - v), root * v
        yield tuple(alpha * a[k] + beta * b[k] + gamma * c[k]
                    for k in range(3))


def probe_sampling_sensitivity(reference, candidate, low_threshold, high_threshold):
    """Return per-side boolean flags for local visualization, plus aggregate counts.

    A zero-flag result DOES NOT mean every point was tested; the region between
    samples, interior voids, small holes, and topology remain unverified.
    """
    _validated_triangles(reference, "reference")
    _validated_triangles(candidate, "candidate")
    if (any(type(x) not in (float, int) or not math.isfinite(x) or x <= 0
            for x in (low_threshold, high_threshold)) or
            low_threshold >= high_threshold):
        raise ValueError("Invalid finite positive GLB-020 thresholds")

    points = [p for face in reference + candidate for p in face]
    lo = [min(p[k] for p in points) for k in range(3)]
    hi = [max(p[k] for p in points) for k in range(3)]
    diagonal = math.sqrt(sum((a - b)**2 for a, b in zip(hi, lo)))
    if not math.isfinite(diagonal) or diagonal <= 0:
        raise ValueError("Invalid shared GLB bounds")
    significant_gain = diagonal * MIN_INCREASE_DIAGONAL_RATIO

    def directed(faces, target):
        target_bvh_faces = _validated_triangles(target, "target")
        bvh = _build_bvh(target_bvh_faces)
        flags = []
        gains = []
        for original in faces:
            face, _ = _validated_triangles([original], "face")[0]
            def max_error(samples):
                worst = 0.0
                for point in samples:
                    d2, _ = _bvh_nearest_distance_squared(
                        point, target_bvh_faces, bvh)
                    distance = math.sqrt(max(0.0, d2))
                    if not math.isfinite(distance):
                        raise ValueError("Invalid sampled surface distance")
                    worst = max(worst, distance)
                return worst
            first = max_error(_sample(face))
            second = max_error(_additional_points(face))
            growth = max(0.0, second - first)
            flag = (
                growth >= significant_gain or
                (first < low_threshold <= second) or
                (first < high_threshold <= second)
            )
            flags.append(bool(flag))
            gains.append(growth)
        return flags, {
            "sensitive_faces": sum(flags),
            "face_count": len(faces),
            "max_observed_increase": round(max(gains), 7),
        }

    ref, ref_summary = directed(reference, candidate)
    cand, cand_summary = directed(candidate, reference)
    return {
        "method": METHOD,
        "initial_samples_per_triangle": SAMPLES_PER_TRIANGLE,
        "additional_samples_per_triangle": ADDITIONAL_SAMPLES,
        "sensitivity_rule": "increase_gt_0.5pct_scene_diagonal_or_color_threshold_crossing",
        "unobserved_regions_verified": False,
        "complete_surface_equivalence_proven": False,
        "reference_flags": ref,
        "candidate_flags": cand,
        "reference_summary": ref_summary,
        "candidate_summary": cand_summary,
    }


def counts_by_part(flags, face_counts):
    if (not isinstance(flags, list) or
            not isinstance(face_counts, list) or
            any(type(x) is not bool for x in flags) or
            any(type(x) is not int or x < 1 for x in face_counts) or
            sum(face_counts) != len(flags) or
            not 1 <= len(face_counts) <= 64 or len(flags) > 512):
        raise ValueError("Invalid part/sample sensitivity alignment")
    result = []
    offset = 0
    for n in face_counts:
        result.append(sum(flags[offset:offset+n]))
        offset += n
    return result
