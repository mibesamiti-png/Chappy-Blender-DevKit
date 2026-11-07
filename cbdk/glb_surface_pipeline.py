"""Safe local opt-in bridge from GLB files to bounded surface diagnostics.

Only the fixed CBDK Blender script is executed. The two GLB files are static
preflight-inspected locally. No addon Python, source code, screenshots or raw
triangle coordinates enter the generated JSON or any network workflow.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

from .glb_inspector import GLBInspectionError, inspect_glb
from .glb_part_hints import count_based_part_hints

MAX_INPUT_BYTES = 24 * 1024 * 1024
MAX_VERTEX_REFERENCES = 100_000
MAX_REPORT_BYTES = 1024 * 1024
MARKER = "CBDK_GLB_SURFACE_REVIEW_PASS "


class GLBSurfacePipelineError(ValueError):
    pass


def _reject_duplicate_keys(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate JSON key")
        output[key] = value
    return output


def _reject_nonfinite_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def _strict_json(text):
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys,
                      parse_constant=_reject_nonfinite_constant)


def _preflight(source: str | Path) -> Path:
    path = Path(source).resolve()
    if not path.is_file() or path.suffix.lower() != ".glb":
        raise GLBSurfacePipelineError("A local .glb file is required")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise GLBSurfacePipelineError("GLB exceeds the conservative 24 MiB import limit")
    try:
        inspection = inspect_glb(path)
    except (GLBInspectionError, OSError, RecursionError) as exc:
        raise GLBSurfacePipelineError("GLB failed static preflight") from exc
    if inspection["external_uris"]:
        raise GLBSurfacePipelineError("External GLB URI resources are not allowed")
    if inspection["counts"]["meshes"] < 1:
        raise GLBSurfacePipelineError("GLB contains no mesh")
    if inspection["counts"]["approximate_vertex_references"] > MAX_VERTEX_REFERENCES:
        raise GLBSurfacePipelineError("GLB references too many vertices for safe import")
    return path


def run_glb_surface_review(
    blender: str | Path,
    reference: str | Path,
    candidate: str | Path,
    output: str | Path,
    *,
    timeout: int = 180,
) -> dict:
    """Load two local GLBs in factory-startup Blender and save aggregate-only JSON.

    Returns status='review_only' for measured differences (including zero), or
    status='skipped' for triangle-count limits. Never interprets zero as proof.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 10 <= timeout <= 900:
        raise GLBSurfacePipelineError("timeout must be between 10 and 900 seconds")
    executable = Path(blender).resolve()
    if not executable.is_file():
        raise GLBSurfacePipelineError("The Blender executable does not exist")
    ref = _preflight(reference)
    cand = _preflight(candidate)
    target = Path(output).resolve()
    if target.suffix.lower() != ".json" or target in (ref, cand):
        raise GLBSurfacePipelineError("Output must be a separate .json file")
    script = Path(__file__).resolve().parent.parent / "scripts" / "blender_glb_surface_review.py"
    if not script.is_file():
        raise GLBSurfacePipelineError("Trusted CBDK Blender surface runner was not found")

    target.parent.mkdir(parents=True, exist_ok=True)
    # Avoid accidentally trusting stale evidence after a failed/partial run.
    if target.exists():
        target.unlink()
    cmd = [
        str(executable), "--background", "--factory-startup", "--disable-autoexec",
        "--python-exit-code", "7", "--python", str(script),
        "--", str(ref), str(cand), str(target),
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GLBSurfacePipelineError("Trusted Blender surface review timed out") from exc
    except OSError as exc:
        raise GLBSurfacePipelineError("Could not start Blender for GLB review") from exc

    payloads = [line.split(MARKER, 1)[1] for line in result.stdout.splitlines()
                if line.startswith(MARKER)]
    if result.returncode != 0 or len(payloads) != 1:
        raise GLBSurfacePipelineError("Blender surface review failed; no report was accepted")
    try:
        payload = _strict_json(payloads[0])
        if not isinstance(payload, dict) or set(payload) != {"kind", "status"}:
            raise ValueError("invalid runner acknowledgment")
        if payload["kind"] != "cbdk_glb_surface_review":
            raise ValueError("unexpected kind")
        if payload["status"] not in ("review_only", "skipped"):
            raise ValueError("unexpected status")
        if not target.is_file() or target.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError("report is missing or too large")
        report = _strict_json(target.read_text(encoding="utf-8"))
        if not isinstance(report, dict) or report.get("kind") != payload["kind"]:
            raise ValueError("invalid report kind")
        if (report.get("status") != payload["status"]
                or type(report.get("schema_version")) is not int
                or report["schema_version"] != 1):
            raise ValueError("invalid report status or version")
        if report.get("source") != "local_blender_import_aggregate_only":
            raise ValueError("unexpected report source")
        if report.get("complete_surface_equivalence_proven") is not False:
            raise ValueError("invalid equality safety flag")
        if report.get("auto_apply") is not False:
            raise ValueError("automatic action must be disabled")
        if not isinstance(report.get("safety"), dict) or any(
            report["safety"].get(key) is not False
            for key in ("executes_addon_code", "uploads_private_glb",
                        "saves_raw_mesh_vertices", "changes_source_glbs")
        ):
            raise ValueError("invalid safety flags")
        if payload["status"] == "review_only" and (
            not isinstance(report.get("fixed_surface"), dict)
            or not isinstance(report.get("adaptive_surface"), dict)
        ):
            raise ValueError("missing surface evidence")
        if payload["status"] == "skipped" and report.get("reason") != "triangle_limit":
            raise ValueError("unknown skip reason")
        # A Blender process is an external evidence producer, not an authority.
        # Reject malformed aggregate metrics instead of passing through NaN,
        # non-finite scores or clearly inconsistent status fields.
        for name in ("reference_triangles", "candidate_triangles"):
            count = report.get(name)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("invalid triangle count")
        inventory = report.get("part_inventory")
        if inventory is not None:
            if not isinstance(inventory, dict) or set(inventory) != {
                "reference_object_count", "candidate_object_count",
                "reference_triangle_counts", "candidate_triangle_counts",
                "max_listed_per_side", "correspondence_verified",
                "identifies_changed_part", "notes",
            }:
                raise ValueError("invalid part inventory schema")
            if (type(inventory["max_listed_per_side"]) is not int
                    or inventory["max_listed_per_side"] != 32
                    or inventory["correspondence_verified"] is not False
                    or inventory["identifies_changed_part"] is not False
                    or inventory["notes"] !=
                    "Anonymous size-ranked inventory, not matched objects"):
                raise ValueError("invalid part inventory disclaimers")
            for side in ("reference", "candidate"):
                total = inventory[side + "_object_count"]
                counts = inventory[side + "_triangle_counts"]
                if (isinstance(total, bool) or not isinstance(total, int)
                        or total < 1 or not isinstance(counts, list)
                        or len(counts) != min(total, 32)
                        or any(isinstance(v, bool) or not isinstance(v, int)
                               or v < 0 or (payload["status"] == "review_only" and v > 512)
                               for v in counts)
                        or counts != sorted(counts, reverse=True)):
                    raise ValueError("invalid anonymous part counts")
                # A truncated, size-ranked inventory still bounds the total:
                # each unlisted object has at most the last listed face count.
                # Apply these constraints to skipped reports as well.
                listed = sum(counts)
                maximum = listed + (total - len(counts)) * counts[-1]
                if not listed <= report[side + "_triangles"] <= maximum:
                    raise ValueError("part inventory contradicts total triangles")
        hints = report.get("part_count_hints")
        if hints is not None:
            if inventory is None or not isinstance(hints, dict):
                raise ValueError("part hints require a valid inventory")
            expected_hints = count_based_part_hints(
                inventory["reference_triangle_counts"],
                inventory["candidate_triangle_counts"],
                reference_total=inventory["reference_object_count"],
                candidate_total=inventory["candidate_object_count"],
            )
            # Python equality aliases False/0 and True/1 (including in lists).
            # Canonical JSON preserves these scalar types while ignoring key order.
            if json.dumps(hints, sort_keys=True, allow_nan=False) != json.dumps(
                expected_hints, sort_keys=True, allow_nan=False
            ):
                raise ValueError("part hints contradict anonymous inventory")
        observation = report.get("surface_observation")
        if payload["status"] == "review_only":
            if observation not in (
                "sampled_difference_detected", "no_difference_observed_at_samples"
            ):
                raise ValueError("invalid surface observation")
            for group, metric in (
                ("fixed_surface", "symmetric_sampled_max"),
                ("adaptive_surface", "refined_symmetric_sampled_max"),
            ):
                value = report[group].get(metric)
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or value < 0):
                    raise ValueError("invalid surface metric")
            measured_difference = max(
                report["fixed_surface"]["symmetric_sampled_max"],
                report["adaptive_surface"]["refined_symmetric_sampled_max"],
            ) > 1e-6
            if measured_difference != (observation == "sampled_difference_detected"):
                raise ValueError("surface observation contradicts metrics")
            if any(not 1 <= report[name] <= 512 for name in (
                "reference_triangles", "candidate_triangles"
            )):
                raise ValueError("measured triangle count is outside the safe range")
        else:
            if observation != "not_measured" or (
                "fixed_surface" in report or "adaptive_surface" in report
            ):
                raise ValueError("skipped evidence must not contain measurements")
            if max(report["reference_triangles"], report["candidate_triangles"]) <= 512:
                raise ValueError("triangle-limit skip requires an over-limit scene")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise GLBSurfacePipelineError("Untrusted or corrupt Blender surface report") from exc
    return report
