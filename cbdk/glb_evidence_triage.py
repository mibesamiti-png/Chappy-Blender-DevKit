"""GLB R14: bounded, anonymous cross-evidence triage, never authorization.

Accept existing local aggregate reports only. Do not import GLBs, execute addon
sources, persist original reports, infer part correspondence or expose filenames,
object labels, source declarations, coordinates, or geometry from those reports.
Each evidence channel may belong to a DIFFERENT input/run; cross-report provenance
is deliberately *not* established here. The caller must check it separately.
"""
from __future__ import annotations

import math

from .glb_diagnose import RULES, diagnose_comparison
from .glb_experiment_triage import render_experiment_triage

KIND = "cbdk_glb_cross_evidence_triage_v1"
MAX_TRIANGLES = 512
MAX_PARTS = 64
MAX_DIFFERENCES = 2048


def _count(value, limit, label):
    if type(value) is not int or not 0 <= value <= limit:
        raise ValueError("Invalid " + label)
    return value


def _finite(value, label, *, maximum=None):
    if type(value) not in (int, float):
        raise ValueError("Invalid " + label)
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Invalid " + label) from exc
    if not math.isfinite(number) or number < 0 or (maximum is not None and number > maximum):
        raise ValueError("Invalid " + label)
    return number


def _comparison(report):
    if report is None:
        return ({"status": "not_measured"}, {"status": "not_measured"})
    if not isinstance(report, dict) or report.get("kind") != "cbdk_glb_scene_comparison":
        raise ValueError("Expected GLB comparison")
    # Existing diagnostic validation checks bounded differences and the known
    # severity / metric types. It does not authenticate the report producer.
    diagnose_comparison(report)
    differences, summary = report["differences"], report["summary"]
    if len(differences) > MAX_DIFFERENCES:
        raise ValueError("Too many comparison observations")
    errors = sum(row["severity"] == "error" for row in differences)
    warnings = sum(row["severity"] == "warning" for row in differences)
    infos = sum(row["severity"] == "info" for row in differences)
    if (report["passed"] is not (errors == 0)
            or any(_count(summary.get(k), MAX_DIFFERENCES, k) != value
                   for k, value in (("errors", errors), ("warnings", warnings),
                                    ("infos", infos)))):
        raise ValueError("Contradictory comparison counts")
    codes = sorted({row["code"] for row in differences if row["code"] in RULES})
    diff = {
        "status": "reported_differences" if differences else "no_difference_reported",
        "errors": errors, "warnings": warnings, "infos": infos,
        "recognized_difference_codes": codes,
        "unrecognized_difference_count": sum(row["code"] not in RULES
                                             for row in differences),
        "metadata_passed": report["passed"],
        "metadata_pass_is_geometry_proof": False,
    }
    ious = summary.get("scene_silhouette_iou", {})
    if not isinstance(ious, dict) or len(ious) > 16:
        raise ValueError("Invalid silhouette IoU observations")
    scores = [_finite(value, "silhouette IoU", maximum=1.0)
              for value in ious.values()]
    if "evidence" in report and isinstance(report["evidence"], dict):
        observed = report["evidence"].get("scene_silhouettes_compared")
        if type(observed) is not bool or observed != bool(scores):
            raise ValueError("Contradictory silhouette evidence")
    iou = ({"status": "measured", "view_count": len(scores),
            "worst_observed_iou": round(min(scores), 7),
            "silhouette_equivalence_proven": False}
           if scores else {"status": "not_measured"})
    return diff, iou


def _boundary_side(report):
    if not isinstance(report, dict) or report.get("coordinate_welding_is_approximate") is not True:
        raise ValueError("Expected bounded boundary audit")
    for flag in ("fully_watertight_proven", "internal_voids_verified",
                 "hole_locations_verified", "reference_identity_proven"):
        if report.get(flag) is not False:
            raise ValueError("Boundary audit cannot prove topology or identity")
    rows = report.get("parts")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_PARTS:
        raise ValueError("Invalid bounded boundary parts")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Missing boundary summary")
    totals = {"triangle_count": 0, "boundary_edges": 0,
              "nonmanifold_edge_incidence": 0, "weld_collapsed_triangles": 0,
              "parts_with_observed_boundaries": 0, "parts_with_nonmanifold_edges": 0}
    for index, row in enumerate(rows, start=1):
        if (not isinstance(row, dict)
                or row.get("part_id") != f"part_{index:03d}"
                or row.get("topology_proven") is not False):
            raise ValueError("Invalid anonymous boundary row")
        triangles = _count(row.get("triangle_count"), MAX_TRIANGLES, "part triangles")
        if triangles < 1:
            raise ValueError("Empty part")
        for key in ("unique_edges", "boundary_edges", "shared_edges",
                    "nonmanifold_edge_incidence", "weld_collapsed_triangles"):
            _count(row.get(key), 3 * triangles, "part " + key)
        if row["boundary_edges"] + row["shared_edges"] + row["nonmanifold_edge_incidence"] > row["unique_edges"]:
            raise ValueError("Impossible edge summary")
        if type(row.get("observed_boundary")) is not bool or row["observed_boundary"] != (row["boundary_edges"] > 0):
            raise ValueError("Incorrect boundary observation")
        if type(row.get("observed_nonmanifold_edge")) is not bool or row["observed_nonmanifold_edge"] != (row["nonmanifold_edge_incidence"] > 0):
            raise ValueError("Incorrect nonmanifold observation")
        totals["triangle_count"] += triangles
        for key in ("boundary_edges", "nonmanifold_edge_incidence", "weld_collapsed_triangles"):
            totals[key] += row[key]
        totals["parts_with_observed_boundaries"] += int(row["observed_boundary"])
        totals["parts_with_nonmanifold_edges"] += int(row["observed_nonmanifold_edge"])
    if totals["triangle_count"] > MAX_TRIANGLES:
        raise ValueError("Boundary triangle budget exceeded")
    expected = dict(totals, part_count=len(rows))
    if any(type(summary.get(key)) is not int or summary[key] != value
           for key, value in expected.items()):
        raise ValueError("Boundary summary and rows disagree")
    return totals


def _boundary(reference, candidate):
    if reference is None and candidate is None:
        return {"status": "not_measured"}
    if reference is None or candidate is None:
        raise ValueError("Both anonymous boundary audits are required")
    left, right = _boundary_side(reference), _boundary_side(candidate)
    differences = [key for key in ("triangle_count", "boundary_edges",
                                    "nonmanifold_edge_incidence",
                                    "weld_collapsed_triangles",
                                    "parts_with_observed_boundaries",
                                    "parts_with_nonmanifold_edges")
                   if left[key] != right[key]]
    return {
        "status": "observed_count_difference" if differences else "no_count_difference_observed",
        "different_aggregate_fields": differences,
        "reference_boundary_edges": left["boundary_edges"],
        "candidate_boundary_edges": right["boundary_edges"],
        "reference_weld_collapsed_triangles": left["weld_collapsed_triangles"],
        "candidate_weld_collapsed_triangles": right["weld_collapsed_triangles"],
        "same_counts_prove_same_holes": False,
        "part_correspondence_verified": False,
    }


def _surface(report):
    if report is None:
        return {"status": "not_measured"}
    if not isinstance(report, dict):
        raise ValueError("Expected bounded sampled surface review")
    kind = report.get("kind")
    if kind == "cbdk_sampled_triangle_surface_distance":
        if (report.get("status") != "review_only"
                or report.get("exact_surface_equivalence_verified") is not False
                or report.get("watertight_solid_equivalence_verified") is not False
                or report.get("enclosed_cavities_verified") is not False):
            raise ValueError("Untrusted sampled surface status")
        if not isinstance(report.get("safety"), dict) or any(
            report["safety"].get(k) is not False for k in (
                "executes_addon", "modifies_source", "auto_approves",
                "auto_applies_parameters", "uploads_private_geometry")
        ):
            raise ValueError("Unsafe sampled surface report")
        for k in ("reference_triangles", "candidate_triangles"):
            if not 1 <= _count(report.get(k), MAX_TRIANGLES, k):
                raise ValueError("No measured triangles")
        for k in ("reference_to_candidate", "candidate_to_reference"):
            if not isinstance(report.get(k), dict):
                raise ValueError("Missing directional samples")
        measured = _finite(report.get("symmetric_sampled_max"), "sampled max")
        directional = max(_finite(report[k].get("sampled_max"), "directional max")
                          for k in ("reference_to_candidate", "candidate_to_reference"))
        if abs(measured - directional) > 1e-6:
            raise ValueError("Sampled max contradicts directional observations")
    elif kind == "cbdk_glb_surface_review":
        if (type(report.get("schema_version")) is not int
                or report["schema_version"] != 1
                or report.get("complete_surface_equivalence_proven") is not False
                or report.get("auto_apply") is not False
                or report.get("source") != "local_blender_import_aggregate_only"):
            raise ValueError("Untrusted Blender surface report")
        if not isinstance(report.get("safety"), dict) or any(
            report["safety"].get(k) is not False for k in (
                "executes_addon_code", "uploads_private_glb",
                "saves_raw_mesh_vertices", "changes_source_glbs")
        ):
            raise ValueError("Unsafe Blender surface report")
        counts = [_count(report.get(k), 100000000, k)
                  for k in ("reference_triangles", "candidate_triangles")]
        if report.get("status") == "skipped":
            if (max(counts) <= MAX_TRIANGLES
                    or report.get("reason") != "triangle_limit"
                    or report.get("surface_observation") != "not_measured"
                    or "fixed_surface" in report or "adaptive_surface" in report):
                raise ValueError("Invalid skipped surface report")
            return {"status": "not_measured", "reason": "triangle_limit"}
        if (report.get("status") != "review_only"
                or not all(1 <= n <= MAX_TRIANGLES for n in counts)
                or not isinstance(report.get("fixed_surface"), dict)
                or not isinstance(report.get("adaptive_surface"), dict)):
            raise ValueError("Invalid measured surface report")
        fixed = _finite(report["fixed_surface"].get("symmetric_sampled_max"), "fixed sample")
        refined = _finite(report["adaptive_surface"].get("refined_symmetric_sampled_max"), "refined sample")
        measured = max(fixed, refined)
        detected = measured > 1e-6
        if (report.get("surface_observation") != (
                "sampled_difference_detected" if detected
                else "no_difference_observed_at_samples")):
            raise ValueError("Sampled observation contradicts measured distance")
    else:
        raise ValueError("Unsupported surface review")
    return {
        "status": "sampled_difference_detected" if measured > 1e-6
                  else "no_difference_observed_at_samples",
        "sampled_max": round(measured, 7),
        "true_hausdorff_or_hole_location_proven": False,
    }


def _static_property(report):
    if report is None:
        return {"status": "not_measured"}
    # Reuse the existing strict reconstruction: a user-supplied list of
    # declaration names and source labels is NOT accepted as evidence.
    render_experiment_triage(report)
    if report.get("kind") != "cbdk_glb_experiment_triage_v1" or report.get("status") != "review_only":
        raise ValueError("Invalid static candidate report")
    rows = report["candidate_reviews"]
    if len(rows) > 128:
        raise ValueError("Too many candidate observations")
    return {
        "status": "unverified_syntax_candidates" if rows else "no_syntax_candidates_observed",
        "candidate_family_count": len(rows),
        "ambiguous_family_count": sum(row["declaration_count"] > 1 for row in rows),
        "property_effect_verified": False,
        "selected_property": None,
    }


def build_glb_evidence_triage(*, comparison=None, boundary_reference=None,
                              boundary_candidate=None, sampled_surface=None,
                              static_property_triage=None):
    """Summarize independent in-memory measurements without pretending linkage.

    All source reports remain external; the result has only a fixed vocabulary,
    anonymous totals and bounded aggregate metrics. No file IO or code execution.
    """
    differences, iou = _comparison(comparison)
    boundary = _boundary(boundary_reference, boundary_candidate)
    surface = _surface(sampled_surface)
    static = _static_property(static_property_triage)
    channels = {
        "metadata_differences": differences, "silhouette_iou": iou,
        "boundary_counts": boundary, "sampled_surface_distance": surface,
        "static_property_candidates": static,
    }
    missing = [key for key, row in channels.items() if row["status"] == "not_measured"]
    return {
        "kind": KIND, "schema_version": 1, "status": "review_only",
        "channels": channels, "unobserved_channels": missing,
        "evidence_sources_verified_same_run": False,
        "review_topics": [
            key for key, row in channels.items() if row["status"] in (
                "reported_differences", "observed_count_difference",
                "sampled_difference_detected", "unverified_syntax_candidates")
        ],
        "safety": {
            "executes_source_code": False, "modifies_source_geometry": False,
            "auto_apply": False, "authorizes_parameter_values": False,
            "proves_part_identity": False, "proves_exact_geometry": False,
            "proves_causality": False, "authenticates_evidence": False,
            "licenses_or_release_approved": False,
        },
    }
