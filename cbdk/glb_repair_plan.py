"""Review-only parameter investigation plans from CBDK GLB comparison diagnoses.

This is a *candidate parameter family* planner, not an addon introspector.
Object names provide weak role hints, never evidence of a specific property.
No Blender source is loaded or changed, and no edits are executed.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from .glb_diagnose import diagnose_comparison_file

MAX_HYPOTHESES = 2048

# Fixed, reviewable vocabulary. These are possible parameter *families*, not
# verified identifiers in any particular addon.
FAMILIES = {
    "global_scale_or_units": (
        ("scene_units", "export_scale", "root_object_scale"),
        ("Check the reference/candidate unit convention", "Compare scene bounds before editing geometry")),
    "root_origin_or_parent_transform": (
        ("root_object_location", "parent_transform", "origin_offset"),
        ("Compare the assembly world-space centers", "Check object parenting and export transforms")),
    "part_size_parameter": (
        ("object_scale", "outer_dimensions", "radius_or_length"),
        ("Compare reference/candidate world-space part bounds", "Distinguish size edits from transform scaling")),
    "part_placement_or_joint_center": (
        ("part_location", "joint_anchor", "parent_transform"),
        ("Compare world-space part centers", "Check attachment axes and parent-local offsets")),
    "assembly_shape_mismatch": (
        ("part_arrangement", "rotation", "visible_profile"),
        ("Inspect lowest-IoU views first", "Check overall orientation and overlapping components")),
    "part_profile_boolean_or_cutout": (
        ("profile_shape", "boolean_cutter", "opening_or_cut_depth"),
        ("Inspect affected views and cross-sections", "Check whether cutouts or openings are present")),
    "missing_generation_branch_or_mode": (
        ("generation_mode", "split_mode", "part_visibility"),
        ("Confirm the part is actually generated", "Check collection linking and split-mode branches")),
    "unexpected_generation_or_cleanup": (
        ("duplicate_count", "temporary_cutter_cleanup", "preview_visibility"),
        ("Inspect unexpected objects", "Check cutters and helpers were removed on export")),
    "topology_or_modifier_difference": (
        ("segment_count", "subdivision_level", "modifier_application"),
        ("Compare topology counts separately from the silhouette", "Check export triangulation settings")),
    "role_or_naming_mapping": (
        ("object_role_name", "left_right_mapping", "generated_name_suffix"),
        ("Review name/role mapping, not geometry alone", "Check whether geometry-based matching selected the correct part")),
    "part_count_mismatch": (
        ("split_mode", "part_count", "join_or_merge_mode"),
        ("Compare expected part count", "Check object generation and join/merge steps")),
}
ROLE_HINTS = {
    "socket": {
        "part_size_parameter": ("socket_outer_diameter", "wall_thickness", "clearance"),
        "part_profile_boolean_or_cutout": ("socket_opening_diameter", "clearance", "socket_split_gap"),
        "part_placement_or_joint_center": ("socket_center", "joint_anchor", "hinge_axis_offset"),
    },
    "ball": {
        "part_size_parameter": ("ball_diameter", "shaft_diameter", "object_scale"),
        "part_profile_boolean_or_cutout": ("ball_profile", "shaft_transition", "cutout_radius"),
        "part_placement_or_joint_center": ("ball_center", "shaft_alignment", "joint_anchor"),
    },
    "hinge": {
        "part_size_parameter": ("hinge_axis_diameter", "hinge_pin_length", "outer_dimensions"),
        "part_profile_boolean_or_cutout": ("hinge_clearance", "hinge_cutout", "pin_hole_diameter"),
        "part_placement_or_joint_center": ("hinge_axis_location", "pivot_offset", "parent_transform"),
    },
}


class RepairPlanError(ValueError):
    pass


def _review_text(value, label):
    if (not isinstance(value, str) or not value or len(value) > 192
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        raise RepairPlanError(label + " must be a short, safe text label")
    return value


def _number(value, label, *, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RepairPlanError(label + " must be numeric")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise RepairPlanError(label + " cannot be converted") from exc
    if not math.isfinite(result) or result < 0 or (maximum is not None and result > maximum):
        raise RepairPlanError(label + " is out of bounds")
    return result


def _role(name):
    tokens = re.split(r"[^a-z0-9]+", name.lower())
    for role in ("socket", "ball", "hinge"):
        if role in tokens:
            return role
    return None


def _axis_hint(evidence, category):
    """Only report observed values; never extrapolate a parameter setting."""
    if category not in {"part_size_parameter", "part_placement_or_joint_center",
                        "global_scale_or_units", "root_origin_or_parent_transform"}:
        return None
    for row in evidence:
        left = row.get("reference")
        right = row.get("candidate")
        if (not isinstance(left, list) or not isinstance(right, list)
                or len(left) != 3 or len(right) != 3):
            continue
        if any(isinstance(x, bool) or not isinstance(x, (int, float))
               for x in left + right):
            continue
        try:
            a = [float(x) for x in left]
            b = [float(x) for x in right]
        except (ValueError, OverflowError):
            continue
        if not all(math.isfinite(x) for x in a + b):
            continue
        differences = [abs(v - u) for u, v in zip(a, b)]
        index = max(range(3), key=lambda i: differences[i])
        if differences[index] == 0:
            continue
        return {
            "axis": ("X", "Y", "Z")[index],
            "reference_observed": a[index],
            "candidate_observed": b[index],
            "candidate_direction": "larger_or_positive" if b[index] > a[index]
                                   else "smaller_or_negative",
            "unit": "unknown_from_comparison",
            "parameter_value_recommendation": None,
        }
    return None


def build_repair_plan(diagnosis: dict) -> dict:
    """Return bounded, deterministic inspection suggestions from diagnosis evidence."""
    if not isinstance(diagnosis, dict) or diagnosis.get("kind") != "cbdk_glb_diagnosis":
        raise RepairPlanError("Expected CBDK GLB diagnosis report")
    if type(diagnosis.get("comparison_passed")) is not bool:
        raise RepairPlanError("comparison_passed must be boolean")
    hypotheses = diagnosis.get("hypotheses")
    if not isinstance(hypotheses, list) or len(hypotheses) > MAX_HYPOTHESES:
        raise RepairPlanError("Expected bounded diagnosis hypotheses")
    if type(diagnosis.get("hypothesis_count")) is not int or diagnosis["hypothesis_count"] != len(hypotheses):
        raise RepairPlanError("Diagnosis hypothesis count does not match")
    unsupported = diagnosis.get("unsupported_difference_codes")
    if not isinstance(unsupported, list) or len(unsupported) > MAX_HYPOTHESES:
        raise RepairPlanError("Invalid unsupported difference codes")
    for code in unsupported:
        _review_text(code, "unsupported code")

    recommendations = []
    for index, item in enumerate(hypotheses):
        if not isinstance(item, dict):
            raise RepairPlanError(f"hypotheses[{index}] must be a JSON object")
        target = _review_text(item.get("target"), "hypothesis target")
        category = _review_text(item.get("category"), "hypothesis category")
        priority = _number(item.get("priority"), "priority", maximum=100)
        confidence = _number(item.get("confidence"), "confidence", maximum=1)
        metrics = item.get("evidence_items")
        if not isinstance(metrics, list) or not metrics or len(metrics) > MAX_HYPOTHESES:
            raise RepairPlanError("Expected bounded evidence_items")
        if any(not isinstance(row, dict) for row in metrics):
            raise RepairPlanError("Each evidence item must be an object")
        summary = item.get("evidence_summary")
        if not isinstance(summary, dict) or summary.get("evidence_count") != len(metrics):
            raise RepairPlanError("Inconsistent evidence_summary")
        views = summary.get("affected_views")
        if (not isinstance(views, list) or any(
                not isinstance(v, str) or len(v) > 32 for v in views)):
            raise RepairPlanError("Invalid affected_views")
        worst_iou = summary.get("worst_iou")
        if worst_iou is not None:
            _number(worst_iou, "worst_iou", maximum=1)
        for label in ("max_relative_error", "max_volume_fraction"):
            if summary.get(label) is not None:
                _number(summary[label], label,
                        maximum=1 if label == "max_volume_fraction" else None)

        rule = FAMILIES.get(category)
        role = _role(target) if target != "scene" else None
        if rule is None:
            params = ()
            checklist = ("Review this unrecognized category manually",)
        else:
            params, checklist = rule
        # A role is a weak hint extracted from the name, never a confirmed type.
        if role in ROLE_HINTS:
            role_params = ROLE_HINTS[role].get(category, ())
            params = tuple(dict.fromkeys((*role_params, *params)))
        recommendation = {
            "target": target,
            "suspected_category": category,
            "priority": int(priority),
            "diagnostic_confidence": confidence,
            "role_guess_from_object_name": role,
            "role_guess_is_unverified": role is not None,
            "possible_parameter_families": list(params),
            "inspect_checks": list(checklist),
            "affected_views": sorted(set(views)),
            "worst_iou": worst_iou,
            "observed_axis_difference": _axis_hint(metrics, category),
            "requires_human_parameter_mapping": True,
            "edits_code": False,
        }
        recommendations.append(recommendation)

    recommendations.sort(key=lambda x: (-x["priority"], -x["diagnostic_confidence"],
                                        x["target"], x["suspected_category"]))
    return {
        "schema_version": 1,
        "kind": "cbdk_glb_repair_plan",
        "status": "review_only",
        "source": "cbdk_glb_diagnosis",
        "comparison_passed": diagnosis["comparison_passed"],
        "requires_review": bool(recommendations or unsupported),
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "unmapped_difference_codes": sorted(set(unsupported)),
        "next_actions": [
            "inspect_reported_parameter_families_in_actual_addon_source",
            "human_select_a_single_change_on_a_separate_copy",
            "regenerate_candidate_glb_and_compare_again",
            "run_python_windows_blender_ci_before_approval",
        ] if recommendations or unsupported else [],
        "limitations": [
            "Object name role guesses are unverified, not a verified parameter mapping",
            "No exact addon property or numeric correction is inferred from GLB bounds alone",
            "32x32 silhouettes cannot verify small holes or internal cavities",
        ],
        "safety": {
            "edits_code": False, "applies_parameters": False,
            "runs_untrusted_addons": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
    }


def write_repair_plan(plan: dict, destination: str | Path) -> Path:
    if (not isinstance(plan, dict) or plan.get("kind") != "cbdk_glb_repair_plan"
            or plan.get("status") != "review_only"
            or not isinstance(plan.get("safety"), dict)
            or any(plan["safety"].get(flag) is not False for flag in
                   ("edits_code", "applies_parameters", "runs_untrusted_addons",
                    "auto_approves", "auto_merges", "private_geometry_required"))):
        raise RepairPlanError("Expected safe, review-only repair plan")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return target


def plan_from_comparison(comparison: str | Path, destination: str | Path) -> dict:
    from .glb_diagnose import diagnose_comparison_file
    diagnosis = diagnose_comparison_file(comparison)
    result = build_repair_plan(diagnosis)
    write_repair_plan(result, destination)
    return result
