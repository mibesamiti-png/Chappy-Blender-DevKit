"""Bounded, review-only bidirectional sampled point-to-triangle surface distances.

Unlike vertex-index or radial signatures, this checks actual 3D positions
against the other mesh's triangular surfaces. Differences in vertex order or
triangulation are allowed. The result is an APPROXIMATION: sparse features,
internal voids, non-manifold edges, topology, and exact solid equivalence are
not established. No GLB reading or addon execution occurs in this module.
"""
from __future__ import annotations

import math

MAX_TRIANGLES = 128
SAMPLES_PER_TRIANGLE = 24
MAX_COORDINATE = 1_000_000.0
MIN_DOUBLE_AREA = 1e-10


class SurfaceDistanceError(ValueError):
    pass


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm2(v):
    return _dot(v, v)


def _validated_triangles(value, label):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_TRIANGLES:
        raise SurfaceDistanceError(f"{label} needs 1..{MAX_TRIANGLES} triangles")
    items = []
    for i, face in enumerate(value):
        if not isinstance(face, (list, tuple)) or len(face) != 3:
            raise SurfaceDistanceError(f"{label}[{i}] must be a triangle")
        points = []
        for vertex in face:
            if not isinstance(vertex, (list, tuple)) or len(vertex) != 3:
                raise SurfaceDistanceError(f"{label}[{i}] has invalid XYZ")
            coords = []
            for x in vertex:
                if isinstance(x, bool) or not isinstance(x, (int, float)):
                    raise SurfaceDistanceError(f"{label}[{i}] has nonnumeric coordinates")
                try:
                    v = float(x)
                except (OverflowError, ValueError) as exc:
                    raise SurfaceDistanceError(f"{label}[{i}] has unrepresentable XYZ") from exc
                if not math.isfinite(v) or abs(v) > MAX_COORDINATE:
                    raise SurfaceDistanceError(f"{label}[{i}] coordinates out of range")
                coords.append(v)
            points.append(tuple(coords))
        # Canonical triangle ordering makes winding and face-list ordering
        # irrelevant for deterministic sample placement.
        a, b, c = sorted(points)
        area2 = math.sqrt(_norm2(_cross(_sub(b, a), _sub(c, a))))
        if not math.isfinite(area2) or area2 <= MIN_DOUBLE_AREA:
            raise SurfaceDistanceError(f"{label}[{i}] is degenerate")
        items.append(((a, b, c), area2 * 0.5))
    items.sort(key=lambda item: item[0])
    return items


def _closest_distance_squared(p, face):
    """Exact closest point on one triangle (Ericson Voronoi-region method)."""
    a, b, c = face
    ab, ac, ap = _sub(b, a), _sub(c, a), _sub(p, a)
    d1, d2 = _dot(ab, ap), _dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return _norm2(ap)
    bp = _sub(p, b)
    d3, d4 = _dot(ab, bp), _dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return _norm2(bp)
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        q = (a[0] + v * ab[0], a[1] + v * ab[1], a[2] + v * ab[2])
        return _norm2(_sub(p, q))
    cp = _sub(p, c)
    d5, d6 = _dot(ab, cp), _dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return _norm2(cp)
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        q = (a[0] + w * ac[0], a[1] + w * ac[1], a[2] + w * ac[2])
        return _norm2(_sub(p, q))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        edge = _sub(c, b)
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        q = (b[0] + w * edge[0], b[1] + w * edge[1], b[2] + w * edge[2])
        return _norm2(_sub(p, q))
    denom = va + vb + vc
    if denom <= 0:
        raise SurfaceDistanceError("Closest-point computation is degenerate")
    v, w = vb / denom, vc / denom
    q = tuple(a[i] + ab[i] * v + ac[i] * w for i in range(3))
    return _norm2(_sub(p, q))


def _radical_inverse(index, base):
    factor, value = 1.0 / base, 0.0
    while index:
        value += (index % base) * factor
        index //= base
        factor /= base
    return value


def _sample(face):
    a, b, c = face
    for i in range(1, SAMPLES_PER_TRIANGLE + 1):
        # Base-2/base-3 Halton points avoid the strongly correlated 2D sample
        # sequence that previously missed the synthetic square's center hole.
        # Samples are deterministic and are never included in JSON reports.
        u, v = _radical_inverse(i, 2), _radical_inverse(i, 3)
        root = math.sqrt(u)
        alpha, beta, gamma = 1.0 - root, root * (1.0 - v), root * v
        yield tuple(alpha * a[j] + beta * b[j] + gamma * c[j] for j in range(3))


def _directed(source, target):
    total_area = sum(area for _, area in source)
    weighted_sum, worst = 0.0, 0.0
    for face, area in source:
        face_sum = 0.0
        for point in _sample(face):
            shortest = min(_closest_distance_squared(point, other)
                           for other, _ in target)
            distance = math.sqrt(max(shortest, 0.0))
            if not math.isfinite(distance):
                raise SurfaceDistanceError("Nonfinite surface distance")
            face_sum += distance
            worst = max(worst, distance)
        weighted_sum += area * face_sum / SAMPLES_PER_TRIANGLE
    mean = weighted_sum / total_area
    if not math.isfinite(mean):
        raise SurfaceDistanceError("Nonfinite mean surface distance")
    return {
        "mean": round(mean, 7),
        "sampled_max": round(worst, 7),
        "sample_count": len(source) * SAMPLES_PER_TRIANGLE,
    }


def compare_triangle_surfaces(reference: list, candidate: list) -> dict:
    """Return approximate directed/symmetric world-space surface distances.

    Operates only on bounded triangle coordinate arrays. A max distance here is
    a maximum OVER SAMPLES, NOT a true Hausdorff bound. Open hole/cutout
    detection is demonstrated with synthetic planar meshes; enclosed cavities
    and arbitrary GLB exactness are not verified.
    """
    ref = _validated_triangles(reference, "reference")
    cand = _validated_triangles(candidate, "candidate")
    forward = _directed(ref, cand)
    backward = _directed(cand, ref)
    symmetric_mean = (forward["mean"] + backward["mean"]) * 0.5
    symmetric_max = max(forward["sampled_max"], backward["sampled_max"])
    return {
        "schema_version": 1,
        "kind": "cbdk_sampled_triangle_surface_distance",
        "status": "review_only",
        "metric": "area_weighted_bidirectional_sampled_point_to_triangle_distance",
        "reference_to_candidate": forward,
        "candidate_to_reference": backward,
        "symmetric_mean": round(symmetric_mean, 7),
        "symmetric_sampled_max": round(symmetric_max, 7),
        "reference_triangles": len(ref),
        "candidate_triangles": len(cand),
        "samples_per_triangle": SAMPLES_PER_TRIANGLE,
        "units": "input_coordinate_units",
        "vertex_correspondence_required": False,
        "triangulation_correspondence_required": False,
        "exact_surface_equivalence_verified": False,
        "watertight_solid_equivalence_verified": False,
        "enclosed_cavities_verified": False,
        "limitations": [
            "Discrete surface samples can miss small holes and thin features",
            "Sampled maximum is not an exact Hausdorff distance",
            "Degenerate faces, excessive sizes and nonfinite vertices are rejected",
            "Geometry must be in an explicitly aligned common coordinate space",
            "No topology, watertightness or internal-volume equivalence proof",
        ],
        "safety": {
            "executes_addon": False,
            "modifies_source": False,
            "auto_approves": False,
            "auto_applies_parameters": False,
            "uploads_private_geometry": False,
        },
    }
