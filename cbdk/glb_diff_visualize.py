"""Opt-in local launcher for GLB-020 colored 3D surface difference exports."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

from .glb_surface_pipeline import _preflight, GLBSurfacePipelineError

MARKER = "CBDK_GLB_DIFF_VISUALIZE_PASS "
MAX_REPORT_BYTES = 128 * 1024
EXPECTED_FILES = ("reference_diff.glb", "candidate_diff.glb")


def run_glb_diff_visualize(blender, reference, candidate, output_dir, *, timeout=180):
    """Create two colored local GLBs and aggregate-only review.json.

    The output folder must be new. Never upload, modify source GLBs, execute
    addon Python or mark a sampled similarity as shape-equivalence proof.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 10 <= timeout <= 900:
        raise GLBSurfacePipelineError("timeout must be between 10 and 900 seconds")
    executable = Path(blender).resolve()
    if not executable.is_file():
        raise GLBSurfacePipelineError("Trusted Blender executable not found")
    ref = _preflight(reference)
    cand = _preflight(candidate)
    target = Path(output_dir).absolute()
    if target.exists() or target.is_symlink():
        raise GLBSurfacePipelineError("Visualization output folder must not exist")
    if target == ref.parent or target == cand.parent:
        raise GLBSurfacePipelineError("Output must be a separate new folder")
    runner = Path(__file__).resolve().parent.parent / "scripts" / "blender_glb_diff_visualize.py"
    if not runner.is_file():
        raise GLBSurfacePipelineError("Trusted CBDK visualization script is missing")
    target.mkdir(parents=True, exist_ok=False)
    cmd = [
        str(executable), "--background", "--factory-startup", "--disable-autoexec",
        "--python-exit-code", "7", "--python", str(runner), "--",
        str(ref), str(cand), str(target),
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GLBSurfacePipelineError("Blender GLB visualization launch failed") from exc
    markers = [line[len(MARKER):] for line in result.stdout.splitlines()
               if line.startswith(MARKER)]
    if result.returncode != 0 or len(markers) != 1:
        raise GLBSurfacePipelineError("Blender visualization failed; outputs unverified")
    try:
        ack = json.loads(markers[0])
        if ack != {"kind": "cbdk_glb_diff_visualization", "status": "review_only"}:
            raise ValueError("Invalid runner acknowledgement")
        report_path = target / "review.json"
        if not report_path.is_file() or report_path.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError("Missing or oversized review JSON")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if (report.get("schema_version") != 1
                or report.get("kind") != "cbdk_glb_diff_visualization"
                or report.get("status") != "review_only"
                or report.get("source") != "local_blender_import_color_overlay"
                or report.get("auto_apply") is not False
                or report.get("complete_surface_equivalence_proven") is not False
                or report.get("sampled_only") is not True
                or report.get("outputs") != list(EXPECTED_FILES)):
            raise ValueError("Invalid review metadata")
        if any(report.get("safety", {}).get(k) is not False for k in (
                "executes_addon_code", "uploads_private_glb",
                "saves_raw_mesh_vertices_in_json", "changes_source_glbs")):
            raise ValueError("Unsafe report flags")
        if report.get("triangle_limit_per_scene") != 512:
            raise ValueError("Unexpected triangle safety limit")
        for field in ("reference", "candidate"):
            counts = report.get(field)
            if not isinstance(counts, dict) or set(counts) != {"low", "medium", "high"}:
                raise ValueError("Invalid face-count report")
            if any(type(v) is not int or v < 0 for v in counts.values()):
                raise ValueError("Invalid face count")
            if not 1 <= sum(counts.values()) <= 512:
                raise ValueError("Invalid scene face count")
        if (report.get("part_count_limit_per_scene") != 64 or
                report.get("part_id_scheme") !=
                "anonymous_sequential_by_imported_object_name" or
                report.get("cross_file_part_identity_proven") is not False):
            raise ValueError("Invalid anonymous part scope")
        parts = report.get("parts")
        if not isinstance(parts, dict) or set(parts) != {"reference", "candidate"}:
            raise ValueError("Missing per-source part grouping")
        for field in ("reference", "candidate"):
            rows = parts[field]
            if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
                raise ValueError("Invalid number of visualized parts")
            totals = {"low": 0, "medium": 0, "high": 0}
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict) or set(row) != {
                        "part_id", "triangle_count", "low", "medium", "high"}:
                    raise ValueError("Invalid anonymous part record")
                if row["part_id"] != f"part_{index:03d}":
                    raise ValueError("Part index is missing or out of order")
                if any(type(row[key]) is not int or row[key] < 0
                       for key in ("triangle_count", "low", "medium", "high")):
                    raise ValueError("Invalid part surface counts")
                if not 1 <= row["triangle_count"] <= 512 or (
                    sum(row[key] for key in totals) != row["triangle_count"]
                ):
                    raise ValueError("Part face count does not match colors")
                for color in totals:
                    totals[color] += row[color]
            if totals != report[field]:
                raise ValueError("Per-part and total colors disagree")
        matches = report.get("part_match_candidates")
        if (not isinstance(matches, dict) or
                matches.get("status") != "review_only" or
                matches.get("method") !=
                "anonymous_spatial_centroid_extent_triangle_heuristic_v1" or
                matches.get("cross_file_part_identity_proven") is not False or
                matches.get("auto_apply") is not False or
                matches.get("shared_coordinate_frame_required") is not True or
                matches.get("topology_guard") !=
                "observed_boundary_nonmanifold_disagreement_demotes_suggestion"):
            raise ValueError("Invalid conservative spatial part matching")
        match_rows = matches.get("reference_parts")
        if not isinstance(match_rows, list) or len(match_rows) != len(parts["reference"]):
            raise ValueError("Missing reference part candidates")
        target_ids = {part["part_id"] for part in parts["candidate"]}
        suggested = set()
        for idx, row in enumerate(match_rows, start=1):
            if (not isinstance(row, dict) or
                    row.get("reference_part_id") != f"part_{idx:03d}" or
                    row.get("status") not in ("suggested", "ambiguous", "unmatched") or
                    not isinstance(row.get("candidate_part_ids"), list) or
                    len(row["candidate_part_ids"]) > 2 or
                    len(row["candidate_part_ids"]) != len(set(row["candidate_part_ids"])) or
                    any(sid not in target_ids for sid in row["candidate_part_ids"])):
                raise ValueError("Invalid anonymous candidate record")
            score = row.get("normalized_score")
            if isinstance(score, bool) or not isinstance(score, (float, int)) or not (
                    math.isfinite(score) and score >= 0):
                raise ValueError("Invalid part candidate score")
            if type(row.get("topology_review_required")) is not bool:
                raise ValueError("Missing conservative topology review flag")
            # v1 reports created before this optional diagnostic field remain
            # readable. New reports must not claim a topology-safe suggestion
            # while supplying contradictory or fabricated reason categories.
            reasons = row.get("topology_review_reasons")
            if reasons is not None:
                known = (
                    "boundary_edge_count_mismatch",
                    "nonmanifold_edge_count_mismatch",
                    "weld_collapsed_triangles_observed",
                    "boundary_spatial_layout_mismatch",
                    "boundary_layout_budget_exceeded",
                )
                if (not isinstance(reasons, list)
                        or reasons != [code for code in known if code in reasons]
                        or bool(reasons) != row["topology_review_required"]):
                    raise ValueError("Invalid topology review reason codes")
            if row["status"] == "suggested":
                if row["topology_review_required"]:
                    raise ValueError("Cannot suggest topology-incompatible pairing")
                if len(row["candidate_part_ids"]) != 1:
                    raise ValueError("Suggested match lacks unique candidate")
                sid = row["candidate_part_ids"][0]
                if sid in suggested:
                    raise ValueError("Multiple references suggest same candidate")
                suggested.add(sid)
            elif row["status"] == "unmatched" and row["candidate_part_ids"]:
                raise ValueError("Unmatched part cannot claim candidate IDs")
        unpaired = matches.get("unpaired_candidate_part_ids")
        if (not isinstance(unpaired, list) or
                unpaired != [p["part_id"] for p in parts["candidate"]
                             if p["part_id"] not in suggested]):
            raise ValueError("Unpaired candidate IDs do not match suggestions")
        edge_audit = report.get("boundary_edge_audit")
        if (not isinstance(edge_audit, dict) or
                edge_audit.get("method") !=
                "world_space_quantized_triangle_edge_incidence_v1" or
                edge_audit.get("relative_weld_epsilon") != 1e-7 or
                edge_audit.get("coordinate_welding_is_approximate") is not True or
                edge_audit.get("fully_watertight_proven") is not False or
                edge_audit.get("internal_voids_verified") is not False or
                edge_audit.get("hole_locations_verified") is not False):
            raise ValueError("Missing conservative boundary edge audit")
        edge_parts = edge_audit.get("parts")
        if (not isinstance(edge_parts, dict) or
                set(edge_parts) != {"reference", "candidate"}):
            raise ValueError("Missing per-source edge observations")
        for side in ("reference", "candidate"):
            records = edge_parts[side]
            stats = edge_audit.get(side)
            if (not isinstance(records, list) or
                    len(records) != len(parts[side]) or
                    not isinstance(stats, dict) or
                    set(stats) != {
                        "part_count", "triangle_count", "boundary_edges",
                        "nonmanifold_edge_incidence",
                        "parts_with_observed_boundaries",
                        "parts_with_nonmanifold_edges",
                        "weld_collapsed_triangles",
                    }):
                raise ValueError("Invalid boundary audit structure")
            if any(type(v) is not int or v < 0 for v in stats.values()):
                raise ValueError("Invalid boundary aggregate counts")
            if (stats["part_count"] != len(records) or
                    stats["triangle_count"] != sum(report[side].values())):
                raise ValueError("Mismatched edge part/triangle counts")
            for index, (row, part) in enumerate(zip(records, parts[side]), start=1):
                if (not isinstance(row, dict) or
                        row.get("part_id") != f"part_{index:03d}" or
                        row.get("triangle_count") != part["triangle_count"] or
                        row.get("topology_proven") is not False or
                        type(row.get("observed_boundary")) is not bool or
                        type(row.get("observed_nonmanifold_edge")) is not bool):
                    raise ValueError("Invalid anonymous edge row")
                for key in ("unique_edges", "boundary_edges", "shared_edges",
                            "nonmanifold_edge_incidence", "weld_collapsed_triangles"):
                    if type(row.get(key)) is not int or row[key] < 0:
                        raise ValueError("Invalid edge incidence")
                if (row["observed_boundary"] != (row["boundary_edges"] > 0)
                        or row["observed_nonmanifold_edge"] != (
                            row["nonmanifold_edge_incidence"] > 0)):
                    raise ValueError("Contradictory edge topology flags")
                if (row["unique_edges"] !=
                        row["boundary_edges"] + row["shared_edges"]
                        + row["nonmanifold_edge_incidence"] or
                        row["weld_collapsed_triangles"] > row["triangle_count"]):
                    raise ValueError("Contradictory edge totals")
            totals = {
                "boundary_edges": sum(x["boundary_edges"] for x in records),
                "nonmanifold_edge_incidence": sum(
                    x["nonmanifold_edge_incidence"] for x in records),
                "weld_collapsed_triangles": sum(
                    x["weld_collapsed_triangles"] for x in records),
                "parts_with_observed_boundaries": sum(
                    x["observed_boundary"] for x in records),
                "parts_with_nonmanifold_edges": sum(
                    x["observed_nonmanifold_edge"] for x in records),
            }
            if any(stats[key] != value for key, value in totals.items()):
                raise ValueError("Boundary audit summary mismatch")
        audit = report.get("sampling_sensitivity_audit")
        if (not isinstance(audit, dict) or
                audit.get("method") != "extra_halton_24_probe_sensitivity_v1" or
                audit.get("initial_samples_per_triangle") != 24 or
                audit.get("additional_samples_per_triangle") != 24 or
                audit.get("sensitivity_rule") !=
                "increase_gt_0.5pct_scene_diagonal_or_color_threshold_crossing" or
                audit.get("unobserved_regions_verified") is not False or
                audit.get("complete_surface_equivalence_proven") is not False):
            raise ValueError("Missing conservative second-pass sampling audit")
        per_part = audit.get("per_part_sensitive_faces")
        if not isinstance(per_part, dict) or set(per_part) != {"reference", "candidate"}:
            raise ValueError("Missing aggregate per-part sensitivity counts")
        for field in ("reference", "candidate"):
            summary = audit.get(field)
            if not isinstance(summary, dict) or set(summary) != {
                "sensitive_faces", "face_count", "max_observed_increase"}:
                raise ValueError("Invalid sensitivity summary")
            if (type(summary["sensitive_faces"]) is not int or
                    type(summary["face_count"]) is not int or
                    summary["face_count"] != sum(report[field].values()) or
                    not 0 <= summary["sensitive_faces"] <= summary["face_count"]):
                raise ValueError("Invalid sensitivity face counts")
            gain = summary["max_observed_increase"]
            if (type(gain) not in (int, float) or
                    not math.isfinite(gain) or gain < 0):
                raise ValueError("Invalid sensitivity gain")
            counts = per_part[field]
            if (not isinstance(counts, list) or len(counts) != len(parts[field])
                    or any(type(n) is not int or n < 0
                           for n in counts)
                    or any(n > part["triangle_count"]
                           for n, part in zip(counts, parts[field]))
                    or sum(counts) != summary["sensitive_faces"]):
                raise ValueError("Part sensitivity counts do not reconcile")
        threshold = report.get("thresholds")
        if not isinstance(threshold, dict) or any(
            isinstance(threshold.get(k), bool)
            or not isinstance(threshold.get(k), (float, int))
            or not math.isfinite(threshold[k]) or threshold[k] <= 0
            for k in ("combined_aabb_diagonal", "medium_from", "high_from")
        ):
            raise ValueError("Invalid error thresholds")
        if (report.get("viewer") != "compare_viewer.html"
                or report.get("viewer_contains_derived_geometry") is not True
                or report.get("viewer_local_only") is not True
                or report.get("viewer_shared_camera") is not True
                or report.get("viewer_browser_interaction_verified") is not False
                or report.get("unobserved_regions_verified") is not False):
            raise ValueError("Unsafe or missing offline viewer declaration")
        viewer_path = target / "compare_viewer.html"
        if (viewer_path.is_symlink() or not viewer_path.is_file()
                or not 1000 < viewer_path.stat().st_size <= 2 * 1024 * 1024):
            raise ValueError("Missing, linked or oversized local viewer")
        html = viewer_path.read_text(encoding="utf-8")
        if (html.count('id="cbdk-viewer-data"') != 1
                or "Content-Security-Policy" not in html
                or '"cbdk_local_diff_viewer"' not in html
                or "__CBDK_VIEWER_DATA__" in html
                or 'id="canvas-reference"' not in html
                or 'id="canvas-candidate"' not in html):
            raise ValueError("Invalid or incomplete local comparison viewer")
        for filename in EXPECTED_FILES:
            output = target / filename
            if (output.is_symlink() or not output.is_file()
                    or not 100 <= output.stat().st_size <= 24 * 1024 * 1024):
                raise ValueError("Missing or invalid colored GLB")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise GLBSurfacePipelineError("Invalid or unverified visualization outputs") from exc
    return report
