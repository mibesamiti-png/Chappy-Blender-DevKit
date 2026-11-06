"""GLB-021: connect aggregate-only GLB-020 observations to static AST hints.

No Blender import, addon import, addon execution, mesh editing, parameter
application, guessing of property values, or automatic part identity claim.

Human-authored role labels are OPTIONAL and UNVERIFIED, not model recognition.
Source property identifiers/AST lines in the resulting report may be private;
write exclusively to ignored local reports/latest using the existing writer.
"""
from __future__ import annotations

from pathlib import Path

from .glb_property_map import (
    PropertyMappingError, _read_json, map_repair_plan_properties,
    write_local_mapping,
)

MAX_PARTS = 64
ALLOWED_ROLES = frozenset({"socket", "ball", "shaft", "hinge"})
GENERIC_FAMILIES = (
    "profile_shape", "boolean_cutter", "opening_or_cut_depth",
    "object_scale", "part_location", "segment_count",
)
ROLE_FAMILIES = {
    "socket": (
        "socket_opening_diameter", "clearance", "wall_thickness",
        "socket_split_gap", "profile_shape", "boolean_cutter",
    ),
    "ball": (
        "ball_diameter", "ball_center", "joint_anchor", "object_scale",
        "part_location", "profile_shape",
    ),
    "shaft": (
        "shaft_diameter", "shaft_length", "shaft_alignment",
        "part_location", "object_scale", "profile_shape",
    ),
    "hinge": (
        "hinge_clearance", "hinge_axis_diameter", "hinge_axis_location",
        "pivot_offset", "profile_shape", "boolean_cutter",
    ),
}


def parse_role_labels(raw: list[str] | None) -> dict[str, str]:
    """Explicit operator labels only; never auto-infer roles from GLB names."""
    if raw is None:
        return {}
    if not isinstance(raw, list) or len(raw) > MAX_PARTS:
        raise PropertyMappingError("Expected up to 64 manual --role labels")
    result = {}
    for item in raw:
        if not isinstance(item, str) or item.count("=") != 1:
            raise PropertyMappingError("Use --role part_001=socket")
        part, role = item.split("=", 1)
        if (len(part) != 8 or not part.startswith("part_")
                or not part[5:].isdigit() or part[5:] == "000"
                or int(part[5:]) > MAX_PARTS or role not in ALLOWED_ROLES
                or part in result):
            raise PropertyMappingError("Invalid, repeated or unsupported manual part role")
        result[part] = role
    return result


def _check_rows(report, side):
    totals = report.get(side)
    layout = report.get("parts")
    if not isinstance(layout, dict):
        raise PropertyMappingError("Missing anonymous GLB-020 part collections")
    parts = layout.get(side)
    if (not isinstance(totals, dict)
            or set(totals) != {"low", "medium", "high"}
            or not isinstance(parts, list) or not 1 <= len(parts) <= MAX_PARTS):
        raise PropertyMappingError("Invalid anonymous GLB-020 part layout")
    count = {"low": 0, "medium": 0, "high": 0}
    for index, row in enumerate(parts, 1):
        if (not isinstance(row, dict)
                or set(row) != {"part_id", "triangle_count", "low", "medium", "high"}
                or row["part_id"] != f"part_{index:03d}"
                or type(row["triangle_count"]) is not int
                or not 1 <= row["triangle_count"] <= 512):
            raise PropertyMappingError("Invalid anonymous part record")
        for key in count:
            val = row[key]
            if type(val) is not int or val < 0:
                raise PropertyMappingError("Invalid per-part triangle classification")
            count[key] += val
        if sum(row[key] for key in count) != row["triangle_count"]:
            raise PropertyMappingError("Per-part face classifications do not reconcile")
    if (count != totals or sum(count.values()) > 512
            or any(type(totals[x]) is not int for x in count)):
        raise PropertyMappingError("Invalid GLB-020 aggregate face totals")
    return parts


def _read_observations(report: dict):
    if (not isinstance(report, dict)
            or report.get("kind") != "cbdk_glb_diff_visualization"
            or report.get("schema_version") != 1
            or report.get("status") != "review_only"
            or report.get("auto_apply") is not False
            or report.get("sampled_only") is not True
            or report.get("complete_surface_equivalence_proven") is not False
            or report.get("cross_file_part_identity_proven") is not False):
        raise PropertyMappingError("Expected unapproved GLB-020 aggregate review")
    safety = report.get("safety")
    if (not isinstance(safety, dict)
            or any(safety.get(key) is not False for key in (
                "executes_addon_code", "uploads_private_glb",
                "saves_raw_mesh_vertices_in_json", "changes_source_glbs"))):
        raise PropertyMappingError("Unsafe GLB-020 review safety flags")
    if (report.get("viewer_contains_derived_geometry") is not True
            or report.get("viewer_local_only") is not True):
        raise PropertyMappingError("GLB-020 private geometry locality is unverified")
    reference = _check_rows(report, "reference")
    candidate = _check_rows(report, "candidate")
    audit = report.get("boundary_edge_audit")
    if (not isinstance(audit, dict)
            or audit.get("method") != "world_space_quantized_triangle_edge_incidence_v1"
            or audit.get("fully_watertight_proven") is not False
            or audit.get("hole_locations_verified") is not False
            or audit.get("internal_voids_verified") is not False
            or not isinstance(audit.get("parts"), dict)):
        raise PropertyMappingError("Missing conservative boundary observations")
    edges = audit["parts"]
    for side, parts in (("reference", reference), ("candidate", candidate)):
        rows = edges.get(side)
        if not isinstance(rows, list) or len(rows) != len(parts):
            raise PropertyMappingError("Boundary audit part count mismatch")
        for idx, row in enumerate(rows):
            if (not isinstance(row, dict)
                    or row.get("part_id") != parts[idx]["part_id"]
                    or row.get("triangle_count") != parts[idx]["triangle_count"]
                    or type(row.get("boundary_edges")) is not int
                    or not 0 <= row["boundary_edges"] <= 3 * parts[idx]["triangle_count"]
                    or type(row.get("observed_boundary")) is not bool
                    or row["observed_boundary"] != (row["boundary_edges"] > 0)
                    or row.get("topology_proven") is not False):
                raise PropertyMappingError("Invalid edge evidence")
    sensitivity = report.get("sampling_sensitivity_audit")
    if (not isinstance(sensitivity, dict)
            or sensitivity.get("method") !=
            "extra_halton_24_probe_sensitivity_v1"
            or sensitivity.get("unobserved_regions_verified") is not False
            or sensitivity.get("complete_surface_equivalence_proven") is not False):
        raise PropertyMappingError("Unverified supplemental sampling audit")
    matches = report.get("part_match_candidates")
    if (not isinstance(matches, dict)
            or matches.get("status") != "review_only"
            or matches.get("cross_file_part_identity_proven") is not False
            or matches.get("auto_apply") is not False
            or not isinstance(matches.get("reference_parts"), list)
            or len(matches["reference_parts"]) != len(reference)):
        raise PropertyMappingError("Invalid tentative part correspondence")
    candidate_ids = {item["part_id"] for item in candidate}
    associations = {}
    for idx, row in enumerate(matches["reference_parts"]):
        if (not isinstance(row, dict)
                or row.get("reference_part_id") != reference[idx]["part_id"]
                or row.get("status") not in {"suggested", "ambiguous", "unmatched"}
                or not isinstance(row.get("candidate_part_ids"), list)
                or len(row["candidate_part_ids"]) > 2
                or len(set(row["candidate_part_ids"])) != len(row["candidate_part_ids"])
                or any(type(x) is not str or x not in candidate_ids
                       for x in row["candidate_part_ids"])):
            raise PropertyMappingError("Invalid anonymous part match status")
        if row["status"] == "suggested":
            if (len(row["candidate_part_ids"]) != 1
                    or row.get("topology_review_required") is not False):
                raise PropertyMappingError("Unsafe/conflicting part suggestion")
            target = row["candidate_part_ids"][0]
            if target in associations:
                raise PropertyMappingError("Non-unique candidate association")
            associations[target] = reference[idx]["part_id"]
    return candidate, edges["candidate"], associations


def build_visual_property_review(
    review: dict, sources: list[str | Path], *, roles: dict[str, str] | None = None,
) -> dict:
    """Map observed candidate-side changed mesh parts to AST name suggestions."""
    candidate, edges, associations = _read_observations(review)
    roles = {} if roles is None else roles
    valid_ids = {row["part_id"] for row in candidate}
    if (not isinstance(roles, dict)
            or any(part not in valid_ids or role not in ALLOWED_ROLES
                   for part, role in roles.items())):
        raise PropertyMappingError("Manual role labels must refer to candidate parts")

    evidence, plan_rows = [], []
    for index, (row, edge) in enumerate(zip(candidate, edges)):
        observed_color = row["medium"] + row["high"]
        observed_open = edge["boundary_edges"] > 0
        if not observed_color and not observed_open:
            continue
        part_id = row["part_id"]
        role = roles.get(part_id)
        candidate_families = ROLE_FAMILIES[role] if role else GENERIC_FAMILIES
        # No conclusions about *which* setting caused the effect; a human
        # part-role label only changes the names considered for static lookup.
        plan_rows.append({
            "target": part_id,
            "suspected_category": "surface_or_boundary_change_unclassified",
            "possible_parameter_families": list(candidate_families),
            "requires_human_parameter_mapping": True,
        })
        evidence.append({
            "candidate_part_id": part_id,
            "observed_medium_faces": row["medium"],
            "observed_high_faces": row["high"],
            "observed_boundary_edges": edge["boundary_edges"],
            "tentative_reference_part_id": associations.get(part_id),
            "reference_candidate_identity_proven": False,
            "manual_role_label": role,
            "role_recognition_verified": False,
            "diagnosis": "observed_change_not_proven_cause",
            "geometry_effect_verified": False,
            "recommended_parameter_value": None,
            "requires_human_review": True,
        })
    plan = {
        "schema_version": 1,
        "kind": "cbdk_glb_repair_plan",
        "status": "review_only",
        "recommendation_count": len(plan_rows),
        "recommendations": plan_rows,
        "unmapped_difference_codes": [],
        "safety": {
            "edits_code": False,
            "applies_parameters": False,
            "runs_untrusted_addons": False,
            "auto_approves": False,
            "auto_merges": False,
            "private_geometry_required": False,
        },
    }
    mapped = map_repair_plan_properties(plan, sources)
    if mapped.get("kind") != "cbdk_glb_property_mapping":
        raise PropertyMappingError("Unexpected AST mapper output")
    for row, observation in zip(mapped["recommendations"], evidence):
        row["visual_observation"] = observation
        row["candidate_cause_verified"] = False
        row["manual_role_only"] = True
    mapped.update({
        "link_kind": "glb020_visual_diff_to_ast_property_candidates_v1",
        "observation_source": "aggregate_only_glb020_review_json",
        "input_glb_or_addon_executed": False,
        "parameter_values_inferred": False,
        "cause_and_effect_proven": False,
        "cross_file_part_identity_proven": False,
        "role_labels_human_declared_only": True,
        "next_action": "human_review_candidate_properties_and_validate_on_synthetic_fixture",
    })
    return mapped


def review_visual_file(review_path: str | Path, sources: list[str | Path],
                       output: str | Path = "reports/latest/glb_visual_property_review.json",
                       *, role_labels: list[str] | None = None,
                       root: Path | None = None) -> dict:
    roles = parse_role_labels(role_labels)
    # Existing reader rejects symlinks, oversized inputs, duplicate JSON keys,
    # nonfinite JSON constants, and does not execute input source.
    report = build_visual_property_review(_read_json(review_path), sources, roles=roles)
    kwargs = {} if root is None else {"root": root}
    write_local_mapping(report, output, **kwargs)
    return report
