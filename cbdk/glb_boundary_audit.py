"""GLB-020 boundary-edge *observations* from bounded triangle soups.

This is intentionally a coordinate-welded topology heuristic: same-position
vertices are approximated using a tiny relative quantization tolerance.
It can highlight missing caps or possible opening discrepancies, but does NOT
prove an opening, watertightness, a solid's interior, or semantic part identity.
No per-vertex coordinates, edge indices or source names leave this module.
"""
from __future__ import annotations

import math

from .glb_diff_colors import MAX_PARTS
from .glb_surface_distance import _validated_triangles

METHOD = "world_space_quantized_triangle_edge_incidence_v1"
RELATIVE_WELD_EPSILON = 1e-7
MIN_WELD_EPSILON = 1e-9


def boundary_audit(faces, part_counts):
    """Count edges appearing once/twice/3+ times, independently per input part.

    The input's original triangle/part order is retained for anonymous IDs.
    Coordinates are used transiently for counting only, never in output.
    A missing boundary does NOT establish a manifold, valid inside/outside,
    or the absence of tiny holes/sub-grid geometry.
    """
    _validated_triangles(faces, "boundary_audit_faces")
    if (not isinstance(part_counts, list)
            or not 1 <= len(part_counts) <= MAX_PARTS
            or any(type(x) is not int or x < 1 for x in part_counts)
            or sum(part_counts) != len(faces)):
        raise ValueError("Invalid anonymous part face counts")
    vertices = [v for triangle in faces for v in triangle]
    extent = [max(float(v[k]) for v in vertices) -
              min(float(v[k]) for v in vertices) for k in range(3)]
    diagonal = math.sqrt(sum(d * d for d in extent))
    if not math.isfinite(diagonal) or diagonal <= 0:
        raise ValueError("Invalid bounding diagonal")
    tolerance = max(diagonal * RELATIVE_WELD_EPSILON, MIN_WELD_EPSILON)

    def key(vertex):
        return tuple(round(float(vertex[k]) / tolerance) for k in range(3))

    rows = []
    pos = 0
    for part_idx, count in enumerate(part_counts, start=1):
        edge_counts = {}
        degenerate_after_welding = 0
        for face in faces[pos:pos + count]:
            a, b, c = (key(v) for v in face)
            if len({a, b, c}) != 3:
                degenerate_after_welding += 1
                continue
            for left, right in ((a, b), (b, c), (c, a)):
                edge = (left, right) if left < right else (right, left)
                edge_counts[edge] = edge_counts.get(edge, 0) + 1
        pos += count
        open_edges = sum(n == 1 for n in edge_counts.values())
        shared_edges = sum(n == 2 for n in edge_counts.values())
        excess_edges = sum(n > 2 for n in edge_counts.values())
        rows.append({
            "part_id": f"part_{part_idx:03d}",
            "triangle_count": count,
            "unique_edges": len(edge_counts),
            "boundary_edges": open_edges,
            "shared_edges": shared_edges,
            "nonmanifold_edge_incidence": excess_edges,
            "weld_collapsed_triangles": degenerate_after_welding,
            "observed_boundary": open_edges > 0,
            "observed_nonmanifold_edge": excess_edges > 0,
            "topology_proven": False,
        })
    return {
        "method": METHOD,
        "relative_weld_epsilon": RELATIVE_WELD_EPSILON,
        "coordinate_welding_is_approximate": True,
        "fully_watertight_proven": False,
        "internal_voids_verified": False,
        "hole_locations_verified": False,
        "reference_identity_proven": False,
        "parts": rows,
        "summary": {
            "part_count": len(rows),
            "triangle_count": len(faces),
            "boundary_edges": sum(r["boundary_edges"] for r in rows),
            "nonmanifold_edge_incidence": sum(r["nonmanifold_edge_incidence"] for r in rows),
            "parts_with_observed_boundaries": sum(r["observed_boundary"] for r in rows),
            "parts_with_nonmanifold_edges": sum(r["observed_nonmanifold_edge"] for r in rows),
            "weld_collapsed_triangles": sum(r["weld_collapsed_triangles"] for r in rows),
        },
    }
