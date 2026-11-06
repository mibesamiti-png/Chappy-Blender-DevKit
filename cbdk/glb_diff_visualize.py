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
