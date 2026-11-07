"""Conservative geometry-feature hints for bounded GLB surface refinement.

Only operates on already validated canonical triangles. It is not a topology
validator or a proof that a boundary corresponds to a hole. All hints are
syntactic/geometric priorities, never claims of true user-model features.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict

from .glb_surface_distance import _cross, _dot, _norm2, _sub

SHARP_COS_THRESHOLD = math.cos(math.radians(40))
INTERIOR_BOUNDARY_MARGIN = .08
SMALL_FACE_RATIO = .45


def _edges(face):
    a, b, c = face
    return (tuple(sorted((a, b))), tuple(sorted((a, c))),
            tuple(sorted((b, c))))


def _unit_normal(face):
    a, b, c = face
    v = _cross(_sub(b, a), _sub(c, a))
    magnitude = math.sqrt(_norm2(v))
    return tuple(x / magnitude for x in v)


def geometry_feature_hints(triangles):
    """Per-face review hints on canonical (face, area) records.

    The bbox-internal boundary heuristic is meant to highlight potential
    planar openings. A boundary edge alone is NOT evidence of a hole: it can
    be an outer border, a seam, or an incomplete/nonmanifold mesh.
    """
    all_points = [p for face, _ in triangles for p in face]
    extents = [(min(p[a] for p in all_points), max(p[a] for p in all_points))
               for a in range(3)]
    active = [a for a, (lo, hi) in enumerate(extents) if hi - lo > 1e-8]
    median_area = statistics.median(area for _, area in triangles)

    edge_owners = defaultdict(list)
    vertex_owners = defaultdict(set)
    normals = []
    for i, (face, _) in enumerate(triangles):
        normals.append(_unit_normal(face))
        for e in _edges(face):
            edge_owners[e].append(i)
        for p in face:
            vertex_owners[p].add(i)

    result = []
    for i, (face, area) in enumerate(triangles):
        boundary = interior_boundary = sharp = nonmanifold = 0
        for edge in _edges(face):
            owners = edge_owners[edge]
            if len(owners) == 1:
                boundary += 1
                if len(active) >= 2:
                    mid = tuple((edge[0][ax] + edge[1][ax]) * .5
                                for ax in range(3))
                    if all(
                        extents[ax][0] + INTERIOR_BOUNDARY_MARGIN *
                        (extents[ax][1] - extents[ax][0]) <
                        mid[ax] <
                        extents[ax][1] - INTERIOR_BOUNDARY_MARGIN *
                        (extents[ax][1] - extents[ax][0])
                        for ax in active
                    ):
                        interior_boundary += 1
            elif len(owners) == 2:
                other = owners[0] if owners[1] == i else owners[1]
                dot = abs(_dot(normals[i], normals[other]))
                if dot < SHARP_COS_THRESHOLD:
                    sharp += 1
            else:
                nonmanifold += 1

        neighbors = set()
        for p in face:
            neighbors.update(vertex_owners[p])
        neighbors.discard(i)
        small = len(triangles) >= 3 and area <= median_area * SMALL_FACE_RATIO
        dense = len(neighbors) >= 5
        flags = {
            "bbox_interior_boundary_hint": interior_boundary > 0,
            "sharp_shared_edge_hint": sharp > 0,
            "small_triangle_hint": bool(small),
            "high_vertex_neighbor_count_hint": bool(dense),
            "open_boundary_hint": boundary > 0,
            "nonmanifold_edge_hint": nonmanifold > 0,
        }
        # Strongly prioritize a possible interior opening or crease. A small
        # face/dense local neighborhood is a weaker detail proxy, and an
        # outside border alone is weakest.
        priority = (
            8 * int(flags["bbox_interior_boundary_hint"]) +
            6 * int(flags["sharp_shared_edge_hint"]) +
            5 * int(flags["nonmanifold_edge_hint"]) +
            3 * int(flags["small_triangle_hint"]) +
            2 * int(flags["high_vertex_neighbor_count_hint"]) +
            1 * int(flags["open_boundary_hint"])
        )
        result.append({
            "priority": priority,
            "flags": flags,
            "area": area,
        })
    return result


def choose_exploration_faces(triangles, excluded, coarse_errors, *,
                             max_faces=2, feature_aware=True):
    """Pick one distinctive face and retain one area/coverage fallback.

    Inputs are canonical validated triangles and aligned sample error arrays.
    Returning only canonical indices/reason categories does not prove a
    selected face contains a defect. No raw triangle coordinates are emitted.
    """
    available = [i for i in range(len(triangles)) if i not in excluded]
    if not available or max_faces < 1:
        return [], [], []
    hints = geometry_feature_hints(triangles) if feature_aware else [
        {"priority": 0, "flags": {}, "area": area}
        for _, area in triangles
    ]
    selected = []
    reasons = []
    if feature_aware and max_faces >= 2:
        eligible = [i for i in available if hints[i]["priority"] > 1]
        if eligible:
            i = min(eligible, key=lambda j: (
                -hints[j]["priority"],
                -(max(coarse_errors[j]) - min(coarse_errors[j])),
                -hints[j]["area"],
                j,
            ))
            selected.append(i)
            reasons.append("geometry_feature_hint")
            available.remove(i)
    for i in sorted(available, key=lambda j: (-hints[j]["area"], j)):
        if len(selected) >= max_faces:
            break
        selected.append(i)
        reasons.append("area_coverage_fallback")
    return selected, reasons, hints
