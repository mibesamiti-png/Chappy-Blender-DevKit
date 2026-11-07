"""Conservative GLB-020 spatial *candidates*, never confirmed part identity.

Only finite, bounded geometry in memory is compared. No object names, source
paths, raw coordinates, addon execution or automatic modifications are emitted.
"""
from __future__ import annotations

import math

from .glb_diff_colors import MAX_PARTS
from .glb_boundary_audit import boundary_audit
from .glb_surface_distance import _validated_triangles

METHOD = "anonymous_spatial_centroid_extent_triangle_heuristic_v1"
MAX_SCORE = 0.20
MIN_MARGIN = 0.045


def _features(faces, counts):
    _validated_triangles(faces, "spatial_candidate_faces")
    if (not isinstance(counts, list) or not 1 <= len(counts) <= MAX_PARTS
            or any(type(n) is not int or n < 1 for n in counts)
            or sum(counts) != len(faces)):
        raise ValueError("Invalid original per-part face layout")
    result = []
    edge_parts = boundary_audit(faces, counts)["parts"]
    start = 0
    for n in counts:
        pts = [p for f in faces[start:start + n] for p in f]
        lower = tuple(min(p[k] for p in pts) for k in range(3))
        upper = tuple(max(p[k] for p in pts) for k in range(3))
        result.append({
            "center": tuple((lower[k] + upper[k]) / 2.0 for k in range(3)),
            "size": tuple(upper[k] - lower[k] for k in range(3)),
            "triangles": n,
            "boundary_edges": edge_parts[len(result)]["boundary_edges"],
            "nonmanifold_edge_incidence": edge_parts[len(result)]["nonmanifold_edge_incidence"],
            "weld_collapsed_triangles": edge_parts[len(result)]["weld_collapsed_triangles"],
        })
        start += n
    return result


def _distance(a, b):
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))


def suggest_spatial_part_matches(reference, candidate, ref_counts, cand_counts):
    """Suggest spatially plausible pairings; ties and weak matches are not bound.

    A suggestion is NOT identity proof, and does not propagate addon settings.
    The comparison assumes a shared coordinate frame and no substantial
    transform changes. Shapes with coincident bounds are intentionally marked
    ambiguous rather than automatically paired.
    """
    ref = _features(reference, ref_counts)
    cand = _features(candidate, cand_counts)
    pts = [p for f in reference + candidate for p in f]
    low = [min(p[k] for p in pts) for k in range(3)]
    high = [max(p[k] for p in pts) for k in range(3)]
    diag = _distance(low, high)
    if not math.isfinite(diag) or diag <= 0:
        raise ValueError("Invalid shared scene scale")

    def cost(a, b):
        # Position is more important than coarse triangle count. All features
        # are world-space and normalized, but cannot establish correspondence.
        center = _distance(a["center"], b["center"]) / diag
        extent = _distance(a["size"], b["size"]) / diag
        count = abs(math.log(a["triangles"] / b["triangles"]))
        return 0.58 * center + 0.32 * extent + 0.10 * min(count, 2.0)

    matrix = [[cost(a, b) for b in cand] for a in ref]

    def ranked(row):
        return sorted(enumerate(row), key=lambda item: (item[1], item[0]))

    reverse_rank = [
        ranked([matrix[i][j] for i in range(len(ref))])
        for j in range(len(cand))
    ]
    rows, used = [], set()
    for i in range(len(ref)):
        scores = ranked(matrix[i])
        best_j, best = scores[0]
        second = scores[1][1] if len(scores) > 1 else math.inf
        ref_margin = second - best
        reverse = reverse_rank[best_j]
        reverse_margin = reverse[1][1] - reverse[0][1] if len(reverse) > 1 else math.inf
        mutual = reverse[0][0] == i
        strong = (
            best <= MAX_SCORE and mutual
            and ref_margin >= MIN_MARGIN
            and reverse_margin >= MIN_MARGIN
        )
        # Boolean open/nonmanifold flags alone miss differences between two
        # *already-open* or two *already-nonmanifold* synthetic meshes.
        # These are coordinate-welded observations, not hole/identity proof.
        topology_reasons = []
        if ref[i]["boundary_edges"] != cand[best_j]["boundary_edges"]:
            topology_reasons.append("boundary_edge_count_mismatch")
        if (ref[i]["nonmanifold_edge_incidence"]
                != cand[best_j]["nonmanifold_edge_incidence"]):
            topology_reasons.append("nonmanifold_edge_count_mismatch")
        if (ref[i]["weld_collapsed_triangles"] > 0
                or cand[best_j]["weld_collapsed_triangles"] > 0):
            topology_reasons.append("weld_collapsed_triangles_observed")
        topo_review = bool(topology_reasons)
        if strong and not topo_review:
            used.add(best_j)
            status = "suggested"
            suggestions = [f"part_{best_j + 1:03d}"]
        elif best > MAX_SCORE:
            status = "unmatched"
            suggestions = []
        else:
            status = "ambiguous"
            # Present at most two nearby candidates for manual review.
            suggestions = [
                f"part_{j + 1:03d}"
                for j, value in scores[:2]
                if value <= MAX_SCORE
            ]
        rows.append({
            "reference_part_id": f"part_{i + 1:03d}",
            "status": status,
            "candidate_part_ids": suggestions,
            "normalized_score": round(best, 6),
            "topology_review_required": topo_review,
            "topology_review_reasons": topology_reasons,
        })
    return {
        "method": METHOD,
        "status": "review_only",
        "shared_coordinate_frame_required": True,
        "cross_file_part_identity_proven": False,
        "auto_apply": False,
        "topology_guard": "observed_boundary_nonmanifold_disagreement_demotes_suggestion",
        "thresholds": {"max_normalized_score": MAX_SCORE, "min_margin": MIN_MARGIN},
        "reference_parts": rows,
        "unpaired_candidate_part_ids": [
            f"part_{j + 1:03d}" for j in range(len(cand)) if j not in used
        ],
    }
