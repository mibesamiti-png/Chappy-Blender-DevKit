"""GLB-020: self-contained *local* synchronized 3D shape review page.

Only CBDK-trusted numeric triangle coordinates and anonymous numeric part
indices enter the HTML. The HTML itself contains derived private geometry,
while review.json never contains vertex coordinates or source names.
No browser networking, dependencies, fetched scripts or user addon execution.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .glb_diff_colors import COLOR_RGBA, summarize_anonymous_parts
from .glb_surface_distance import _validated_triangles
from .glb_part_match import suggest_spatial_part_matches
from .glb_boundary_audit import boundary_audit

TEMPLATE = Path(__file__).with_name("glb_diff_viewer_template.html")
MARKER = "__CBDK_VIEWER_DATA__"
MAX_VIEWER_BYTES = 2 * 1024 * 1024


def _pack_faces(faces, labels, counts):
    # The exact same validation rules and 512-face cap as GLB-019.
    _validated_triangles(faces, "viewer_faces")
    parts = summarize_anonymous_parts(labels, counts)
    result = []
    colors = {key: i for i, key in enumerate(COLOR_RGBA)}
    index = 0
    for part_index, face_count in enumerate(counts, start=1):
        for _ in range(face_count):
            face = faces[index]
            category = labels[index]
            # No arbitrary text or source name ever flows into the page.
            result.append(
                [part_index, colors[category]] +
                [float(component) for vertex in face for component in vertex]
            )
            index += 1
    return {"faces": result, "parts": parts}


def render_local_diff_viewer(
    reference, candidate, reference_labels, candidate_labels,
    reference_counts, candidate_counts, *, sampling_flags=None,
):
    """Render an offline two-canvas 3D viewer; do not save/network it here.

    The returned string contains derived source geometry, so consumers must
    write it ONLY into a private/local user-requested directory.
    """
    if sampling_flags is None:
        sampling_flags = {
            "reference": [False] * len(reference),
            "candidate": [False] * len(candidate),
        }
    if (not isinstance(sampling_flags, dict)
            or set(sampling_flags) != {"reference", "candidate"}
            or any(not isinstance(sampling_flags[side], list)
                   or len(sampling_flags[side]) != len(faces)
                   or any(type(flag) is not bool for flag in sampling_flags[side])
                   for side, faces in (
                       ("reference", reference), ("candidate", candidate)))):
        raise ValueError("Invalid per-face supplemental sample flags")
    left = _pack_faces(reference, reference_labels, reference_counts)
    right = _pack_faces(candidate, candidate_labels, candidate_counts)
    points = [vertex for face in reference + candidate for vertex in face]
    lower = [min(vertex[k] for vertex in points) for k in range(3)]
    upper = [max(vertex[k] for vertex in points) for k in range(3)]
    diagonal = math.sqrt(sum((upper[k] - lower[k]) ** 2 for k in range(3)))
    if not math.isfinite(diagonal) or diagonal <= 0:
        raise ValueError("Viewer shared bounds are invalid")
    data = {
        "kind": "cbdk_local_diff_viewer",
        "version": 1,
        "center": [(upper[k] + lower[k]) * 0.5 for k in range(3)],
        "diagonal": diagonal,
        "reference": left,
        "candidate": right,
        "sampling_sensitivity_flags": {
            "reference": [int(v) for v in sampling_flags["reference"]],
            "candidate": [int(v) for v in sampling_flags["candidate"]],
        },
        "sampling_sensitivity_is_full_coverage": False,
        "unobserved_regions_verified": False,
        "cross_file_part_identity_proven": False,
        "boundary_observations": {
            "reference": boundary_audit(reference, reference_counts)["parts"],
            "candidate": boundary_audit(candidate, candidate_counts)["parts"],
        },
        "part_suggestions": suggest_spatial_part_matches(
            reference, candidate, reference_counts, candidate_counts,
        ),
        "auto_apply": False,
    }
    # The payload is entirely made from validated numbers, fixed keys and
    # allowlisted colors/anonymous part IDs: no HTML/script insertion surface.
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False)
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(MARKER) != 1:
        raise ValueError("Offline viewer template marker missing or ambiguous")
    rendered = template.replace(MARKER, payload)
    if len(rendered.encode("utf-8")) > MAX_VIEWER_BYTES:
        raise ValueError("Offline viewer exceeds conservative 2 MiB limit")
    return rendered
