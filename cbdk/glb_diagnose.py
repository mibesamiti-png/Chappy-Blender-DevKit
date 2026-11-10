"""Review-only GLB shape diagnostics from trusted comparison report data.

No user GLB is loaded, no code is executed, and hypotheses are never automatic
code edits or approvals. The comparator's tolerances are evidence boundaries:
a passed comparison does not establish exact solid geometry equivalence.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_DIFFERENCES = 2048
MAX_METRIC_BYTES = 4096
SEVERITIES = {"error", "warning", "info"}
RULES = {
    "scene_dimensions": ("global_scale_or_units", 90, 0.90, ["scene scale", "unit conversion", "root transform", "export scale"]),
    "scene_center": ("root_origin_or_parent_transform", 80, 0.85, ["root object location", "origin placement", "parent transform", "cursor/reference center"]),
    "object_dimensions": ("part_size_parameter", 95, 0.92, ["radius/diameter/length parameters", "clearance/wall thickness", "object scale", "modifier dimensions"]),
    "object_center": ("part_placement_or_joint_center", 94, 0.92, ["joint center", "hinge axis location", "3D cursor placement", "parent/local transform"]),
    "scene_silhouette": ("assembly_shape_mismatch", 85, 0.78, ["overall assembly layout", "missing cuts", "wrong orientation", "unexpected overlaps"]),
    "object_silhouette": ("part_profile_boolean_or_cutout", 98, 0.95, ["boolean cutters", "opening/profile", "split shape", "rib/tab/dowel geometry", "rotation/orientation"]),
    "missing_reference_object": ("missing_generation_branch_or_mode", 100, 0.98, ["feature toggle", "split/integrated mode", "object creation branch", "collection linking"]),
    "extra_candidate_object": ("unexpected_generation_or_cleanup", 88, 0.90, ["temporary cutters", "duplicate generation", "cleanup step", "preview-only helpers"]),
    "object_topology": ("topology_or_modifier_difference", 55, 0.55, ["segments/resolution", "modifier application", "triangulation", "mesh generation algorithm"]),
    "object_name_fallback": ("role_or_naming_mapping", 35, 0.60, ["object role names", "left/right naming", "generated suffixes", "mapping metadata"]),
    "object_count": ("part_count_mismatch", 92, 0.90, ["split mode", "duplicate generation", "merge/join step", "hidden generated objects"]),
}


class DiagnosticError(ValueError):
    pass


def _load(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file() or source.is_symlink():
        raise DiagnosticError(f"Comparison report missing or symlinked: {source}")
    if source.stat().st_size > MAX_REPORT_BYTES:
        raise DiagnosticError("Comparison report exceeds safe size limit")

    def unique_keys(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise DiagnosticError("Duplicate comparison key: " + key)
            data[key] = value
        return data

    try:
        data = json.loads(source.read_text(encoding="utf-8"),
                          object_pairs_hook=unique_keys,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              DiagnosticError("Non-finite JSON constant: " + value)))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DiagnosticError("Invalid comparison report JSON") from exc
    if not isinstance(data, dict) or data.get("kind") != "cbdk_glb_scene_comparison":
        raise DiagnosticError("Expected cbdk_glb_scene_comparison report")
    return data


def _count(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise DiagnosticError(label + " must be a non-negative integer")
    return value


def _numeric(metrics: dict, key: str, *, fraction: bool = False) -> float | None:
    if key not in metrics:
        return None
    value = metrics[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiagnosticError(key + " must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise DiagnosticError(key + " cannot be represented as a number") from exc
    if not math.isfinite(number) or number < 0 or (fraction and number > 1):
        raise DiagnosticError(key + " must be finite and within expected range")
    return number


def _target(metrics: dict[str, Any]) -> str:
    for field in ("reference_object", "object"):
        name = metrics.get(field)
        if isinstance(name, str) and name:
            return name
    # All scene camera directions form one assembly-level hypothesis.
    return "scene"


def _evidence_summary(items: list[dict], severities: list[str]) -> dict:
    views = sorted({row["view"] for row in items
                    if isinstance(row.get("view"), str) and row["view"]})
    ious = [row["iou"] for row in items if "iou" in row]
    errors = [row["relative_error"] for row in items if "relative_error" in row]
    fractions = [row["volume_fraction"] for row in items if "volume_fraction" in row]
    return {
        "evidence_count": len(items),
        "affected_views": views,
        "worst_iou": min(ious) if ious else None,
        "max_relative_error": max(errors) if errors else None,
        "max_volume_fraction": max(fractions) if fractions else None,
        "error_count": severities.count("error"),
        "warning_count": severities.count("warning"),
        "info_count": severities.count("info"),
    }


def diagnose_comparison(report: dict) -> dict:
    if not isinstance(report, dict) or report.get("kind") != "cbdk_glb_scene_comparison":
        raise DiagnosticError("Expected cbdk_glb_scene_comparison report")
    if "schema_version" in report and (type(report["schema_version"]) is not int
                                        or report["schema_version"] != 1):
        raise DiagnosticError("Unsupported comparison schema")
    if type(report.get("passed")) is not bool:
        raise DiagnosticError("comparison.passed must be boolean")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise DiagnosticError("comparison.summary must be an object")
    errors = _count(summary.get("errors"), "comparison.summary.errors")
    diffs = report.get("differences")
    if not isinstance(diffs, list) or len(diffs) > MAX_DIFFERENCES:
        raise DiagnosticError("comparison.differences must be a bounded array")
    grouped: dict[tuple[str, str], dict] = {}
    unsupported: list[str] = []
    observed = {severity: 0 for severity in SEVERITIES}

    for index, row in enumerate(diffs):
        if not isinstance(row, dict):
            raise DiagnosticError(f"difference[{index}] must be an object")
        code, severity, metrics = row.get("code"), row.get("severity"), row.get("metrics", {})
        if not isinstance(code, str) or not 1 <= len(code) <= 128:
            raise DiagnosticError(f"difference[{index}].code is invalid")
        if not isinstance(severity, str) or severity not in SEVERITIES:
            raise DiagnosticError(f"difference[{index}].severity is invalid")
        if not isinstance(metrics, dict):
            raise DiagnosticError(f"difference[{index}].metrics is invalid")
        try:
            metric_size = len(json.dumps(metrics, ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError, OverflowError) as exc:
            raise DiagnosticError(f"difference[{index}].metrics must be finite JSON") from exc
        if metric_size > MAX_METRIC_BYTES:
            raise DiagnosticError(f"difference[{index}].metrics exceeds safe limit")
        for field in ("iou", "minimum", "volume_fraction"):
            _numeric(metrics, field, fraction=True)
        for field in ("relative_error", "tolerance"):
            _numeric(metrics, field)
        observed[severity] += 1
        rule = RULES.get(code)
        if rule is None:
            unsupported.append(code)
            continue
        category, base, confidence, inspect = rule
        boost = {"error": 20, "warning": 8, "info": 0}[severity]
        key = (_target(metrics), category)
        entry = grouped.get(key)
        if entry is None:
            entry = {
                "target": key[0], "category": category,
                "priority": min(100, base + boost), "confidence": confidence,
                "inspect": list(inspect), "source_codes": [code],
                "evidence_items": [], "severities": [],
            }
            grouped[key] = entry
        else:
            entry["priority"] = max(entry["priority"], min(100, base + boost))
            entry["confidence"] = max(entry["confidence"], confidence)
            if code not in entry["source_codes"]:
                entry["source_codes"].append(code)
        entry["evidence_items"].append(metrics)
        entry["severities"].append(severity)

    if observed["error"] != errors:
        raise DiagnosticError("comparison.summary.errors conflicts with difference severities")
    for severity, field in (("warning", "warnings"), ("info", "infos")):
        if field in summary and _count(summary[field], "comparison.summary." + field) != observed[severity]:
            raise DiagnosticError("comparison.summary." + field + " conflicts with differences")
    if report["passed"] != (errors == 0):
        raise DiagnosticError("comparison.passed conflicts with error count")

    for entry in grouped.values():
        entry["evidence_summary"] = _evidence_summary(entry["evidence_items"],
                                                       entry["severities"])
    ranked = sorted(grouped.values(),
                    key=lambda row: (-row["priority"], -row["confidence"],
                                     -row["evidence_summary"]["evidence_count"],
                                     row["target"], row["category"]))
    unresolved = sorted(set(unsupported))
    if errors:
        next_step = "inspect_highest_priority_hypothesis_then_regenerate_candidate"
    elif ranked:
        next_step = "review_warnings_and_informational_differences"
    elif unresolved:
        next_step = "review_unsupported_difference_codes"
    else:
        next_step = "no_comparison_differences_reported"

    return {
        "schema_version": 1, "kind": "cbdk_glb_diagnosis",
        "comparison_passed": report["passed"],
        "needs_review": bool(diffs),
        "hypothesis_count": len(ranked),
        "unsupported_difference_codes": unresolved,
        "hypotheses": ranked,
        "recommended_next_step": next_step,
        "evidence_summary": {
            "total_differences": len(diffs), "errors": observed["error"],
            "warnings": observed["warning"], "infos": observed["info"],
            "unsupported_codes": len(unresolved),
        },
        "limitations": [
            "A passed comparison only means differences were within configured tolerances",
            "32x32 silhouette signatures can miss small cavities, internal surfaces and fine details",
            "Categories are review hypotheses, not proven root causes",
        ],
        "safety": {
            "edits_code": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
    }


def diagnose_comparison_file(path: str | Path) -> dict:
    return diagnose_comparison(_load(path))


def write_diagnosis_report(report: dict, output: str | Path) -> dict:
    if not isinstance(report, dict) or report.get("kind") != "cbdk_glb_diagnosis":
        raise DiagnosticError("Expected cbdk_glb_diagnosis report")
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
                      + "\n", encoding="utf-8")
    return report


def write_diagnosis(path: str | Path, output: str | Path) -> dict:
    return write_diagnosis_report(diagnose_comparison_file(path), output)
