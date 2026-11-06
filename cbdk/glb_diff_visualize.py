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
        threshold = report.get("thresholds")
        if not isinstance(threshold, dict) or any(
            isinstance(threshold.get(k), bool)
            or not isinstance(threshold.get(k), (float, int))
            or not math.isfinite(threshold[k]) or threshold[k] <= 0
            for k in ("combined_aabb_diagonal", "medium_from", "high_from")
        ):
            raise ValueError("Invalid error thresholds")
        for filename in EXPECTED_FILES:
            output = target / filename
            if (output.is_symlink() or not output.is_file()
                    or not 100 <= output.stat().st_size <= 24 * 1024 * 1024):
                raise ValueError("Missing or invalid colored GLB")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise GLBSurfacePipelineError("Invalid or unverified visualization outputs") from exc
    return report
