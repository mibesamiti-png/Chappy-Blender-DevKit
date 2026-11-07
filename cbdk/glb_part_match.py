"""Conservative GLB-020 spatial *candidates*, never confirmed part identity.

Only finite, bounded geometry in memory is compared. No object names, source
paths, raw coordinates, addon execution or automatic modifications are emitted.
"""
from __future__ import annotations

import math

from .glb_diff_colors import MAX_PARTS
from .glb_boundary_audit import boundary_audit, local_boundary_segments
from .glb_surface_distance import _validated_triangles

METHOD = "anonymous_spatial_centroid_extent_triangle_heuristic_v1"
MAX_SCORE = 0.20
MIN_MARGIN = 0.045
# Bound the quadratic contour comparison without weakening the 512-face input cap.
MAX_LAYOUT_BOUNDARY_EDGES = 256
BOUNDARY_LAYOUT_RELATIVE_TOLERANCE = 0.002


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


def _exact_undirected_contour_signature(segments):
    """Canonical, collision-free key for bounded, part-local open segments.

    This is an *exact* equality shortcut, not a tolerance hash, proof of
    hole topology, or public/reportable geometry signature. Call only after
    the existing per-part boundary-edge budget is enforced. Canonicalize
    both endpoint orientation and edge ordering, preserving multiplicity.
    """
    return tuple(sorted(
        (start, end) if start <= end else (end, start)
        for start, end in segments
    ))


def _outside_expanded_boundary_segment_box(point, start, end, margin):
    """Conservatively reject points too far from a segment on any axis.

    If a point is within Euclidean radius tol of any point on a
    segment, each axis lies within the segment's [min,max] +/- tol.
    We deliberately use a 2x tol envelope to avoid borderline floating
    rounding false exclusions. Returning False always remains safe: the
    unmodified R2 point-to-segment predicate decides the actual match.
    """
    return any(
        point[axis] < min(start[axis], end[axis]) - margin
        or point[axis] > max(start[axis], end[axis]) + margin
        for axis in range(3)
    )


def _boundary_layout_issue(ref_lines, cand_lines, ref_part, cand_part):
    """Compare corresponding open-contour segments in part-local coordinates.

    Only a conservative mismatch/unmeasured reason is returned, never coordinates
    or a claim that a physical hole was located. Nearest-*segment* queries
    tolerate equivalent contour triangulation and reversed edge directions.
    """
    if (len(ref_lines) > MAX_LAYOUT_BOUNDARY_EDGES
            or len(cand_lines) > MAX_LAYOUT_BOUNDARY_EDGES):
        return "boundary_layout_budget_exceeded"
    if not ref_lines or not cand_lines:
        return None
    scale = max(
        math.sqrt(sum(dim * dim for dim in ref_part["size"])),
        math.sqrt(sum(dim * dim for dim in cand_part["size"])),
    )
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid part-local boundary scale")

    def centered(lines, part):
        origin = part["center"]
        return [
            (tuple((x - origin[k]) / scale for k, x in enumerate(raw[1:4])),
             tuple((x - origin[k]) / scale for k, x in enumerate(raw[4:7])))
            for raw in lines
        ]

    left = centered(ref_lines, ref_part)
    right = centered(cand_lines, cand_part)

    # A canonical *exact* undirected contour match proves that every R2
    # point sample lies on an identical opposing segment. It is therefore
    # equivalent to the normal R2 distance guard returning no issue. Any
    # float32 drift, changed edge subdivision, moved opening or other
    # difference falls through to the original bidirectional distance scan.
    # The R3 boundary-graph connectivity guard is evaluated by the caller
    # independently and MUST NOT be bypassed by this optimization.
    # The original R2 distance scanner ignores zero-squared-length
    # opposite segments. Exact equality of such degenerate inputs would
    # otherwise bypass that fail-closed scanner and incorrectly return None.
    # Keep the fast path only when *every* segment is usable by the scanner.
    # The 256-edge budget still runs above, so this linear guard is bounded.
    if (all(sum((end[k] - start[k]) ** 2 for k in range(3)) > 0
            for start, end in left + right)
            and _exact_undirected_contour_signature(left)
            == _exact_undirected_contour_signature(right)):
        return None

    limit2 = BOUNDARY_LAYOUT_RELATIVE_TOLERANCE ** 2

    # R10: the R8 conservative AABB may cost more than it saves when
    # candidate boxes overlap almost every sample point. Observe only the
    # first 64 *bounded* box checks, then disable the optional filter if
    # fewer than 1/8 of them can exclude a segment. This decision affects
    # performance only: the original R2 distance predicate still runs for
    # every nonexcluded segment, including ALL segments after disabling.
    # No geometry, probe counts or signatures are written into reports.
    sampled_boxes = 0
    rejected_boxes = 0
    use_bbox = True

    def within_any(point, segments):
        nonlocal sampled_boxes, rejected_boxes, use_bbox
        for start, end in segments:
            if use_bbox:
                # R8: outside a 2*t expanded AABB guarantees that the
                # original R2 Euclidean distance predicate cannot pass.
                outside = _outside_expanded_boundary_segment_box(
                    point, start, end, 2 * BOUNDARY_LAYOUT_RELATIVE_TOLERANCE)
                if sampled_boxes < 64:
                    sampled_boxes += 1
                    rejected_boxes += int(outside)
                    if sampled_boxes == 64 and rejected_boxes < 8:
                        use_bbox = False
                if outside:
                    continue
            direction = tuple(end[k] - start[k] for k in range(3))
            norm2 = sum(v * v for v in direction)
            if norm2 <= 0:
                continue
            factor = max(0., min(1., sum(
                (point[k] - start[k]) * direction[k] for k in range(3)
            ) / norm2))
            if sum((point[k] - start[k] - factor * direction[k]) ** 2
                   for k in range(3)) <= limit2:
                return True
        return False

    # Both directions: one contour may have a missing or additional section.
    # Endpoint + midpoint samples reduce missed gaps; this is not full coverage.
    for source, target in ((left, right), (right, left)):
        for start, end in source:
            for fraction in (0., 0.5, 1.):
                point = tuple(start[k] + fraction * (end[k] - start[k])
                              for k in range(3))
                if not within_any(point, target):
                    return "boundary_spatial_layout_mismatch"
    return None


def _observed_boundary_component_count(lines):
    """Count components of a bounded coordinate-welded *boundary graph*.

    Vertices are the anonymous, quantized endpoints already emitted by
    local_boundary_segments. Point-contact and near-contact are different in
    this observation, even if the R2 distance probe sees the same contour.
    This is NOT a watertightness, true hole, or object-identity certificate.
    """
    adjacency = {}
    for segment in lines:
        start, end = tuple(segment[1:4]), tuple(segment[4:7])
        adjacency.setdefault(start, set()).add(end)
        adjacency.setdefault(end, set()).add(start)
    unseen = set(adjacency)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            for neighbour in adjacency[stack.pop()]:
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
    return components


def suggest_spatial_part_matches(reference, candidate, ref_counts, cand_counts):
    """Suggest spatially plausible pairings; ties and weak matches are not bound.

    A suggestion is NOT identity proof, and does not propagate addon settings.
    The comparison assumes a shared coordinate frame and no substantial
    transform changes. Shapes with coincident bounds are intentionally marked
    ambiguous rather than automatically paired.
    """
    ref = _features(reference, ref_counts)
    cand = _features(candidate, cand_counts)
    # Coordinate-bearing segments exist only transiently in memory. Never put
    # them into public JSON, debug logs, or a cross-file identity assertion.
    ref_lines = [[] for _ in ref]
    cand_lines = [[] for _ in cand]
    for line in local_boundary_segments(reference, ref_counts):
        ref_lines[line[0] - 1].append(line)
    for line in local_boundary_segments(candidate, cand_counts):
        cand_lines[line[0] - 1].append(line)
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
        if (ref[i]["boundary_edges"] > 0
                and ref[i]["boundary_edges"] == cand[best_j]["boundary_edges"]):
            layout_issue = _boundary_layout_issue(
                ref_lines[i], cand_lines[best_j], ref[i], cand[best_j],
            )
            if layout_issue is not None:
                topology_reasons.append(layout_issue)
            elif (_observed_boundary_component_count(ref_lines[i])
                    != _observed_boundary_component_count(cand_lines[best_j])):
                # This catches sub-layout-tolerance disconnections/point
                # contacts that a geometric nearest-segment probe can miss.
                # Do not imply an actual physical opening was identified.
                topology_reasons.append("boundary_component_count_mismatch")
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
