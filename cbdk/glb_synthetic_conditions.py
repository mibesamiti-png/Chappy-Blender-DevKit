"""Anonymous, bounded conditions for comparing CBDK synthetic experiments.

Digests detect stale inputs/code; they do not authenticate an evidence producer.
Only fixed repository-authored source paths are read, never user Python.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

SOURCES = (
    "scripts/blender_make_glb_joint_mvp_fixtures.py",
    "scripts/run_glb022_synthetic_adaptive.py",
    "scripts/blender_glb_diff_visualize.py",
    "cbdk/glb_diff_visualize.py", "cbdk/glb_diff_colors.py",
    "cbdk/glb_surface_distance.py", "cbdk/glb_sampling_audit.py",
    "cbdk/glb_boundary_audit.py", "cbdk/glb_part_match.py",
    "cbdk/glb_synthetic_adaptive.py", "cbdk/glb_synthetic_progress.py",
    "cbdk/glb_synthetic_trial_history.py", "cbdk/glb_visual_property_review.py",
    "cbdk/glb_inspector.py", "cbdk/glb_surface_pipeline.py",
    "cbdk/glb_synthetic_conditions.py", "cbdk/glb_synthetic_run_review.py",
)
FIXED = {
    "protocol": "cbdk_owned_adaptive_socket_v1",
    "metric": "global_bidirectional_sampled_max_not_exact_hausdorff",
    "units": "synthetic_fixture_input_units",
    "range_centi": [78, 170], "max_trials": 4,
    "target_sampled_max": 0.12, "samples_per_triangle": 24,
    "triangle_limit": 512,
}


def condition_source_digest(root):
    """Hash a fixed trusted source manifest without importing or executing it."""
    root = Path(root).resolve()
    digest = hashlib.sha256()
    for name in SOURCES:
        source = root / name
        if (source.is_symlink() or not source.is_file()
                or not source.resolve().is_relative_to(root)
                or source.stat().st_size > 1024 * 1024):
            raise ValueError("Missing or unsafe trusted condition source")
        body = source.read_bytes()
        digest.update(name.encode("ascii") + b"\0")
        digest.update(hashlib.sha256(body).digest())
    return digest.hexdigest()


def build_conditions(*, source_sha256, reference_sha256, baseline_sha256,
                     blender_version, scale, initial_max, initial_faces,
                     baseline_review_sha256=None):
    for digest in (source_sha256, reference_sha256, baseline_sha256):
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("Invalid synthetic condition digest")
    if (not isinstance(blender_version, str)
            or re.fullmatch(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?: LTS)?", blender_version) is None):
        raise ValueError("Invalid declared Blender version")
    for value, lower, upper in ((scale, 0, 1e6), (initial_max, .12, 1e5)):
        if type(value) not in (int, float) or not math.isfinite(value) or not lower < value <= upper:
            raise ValueError("Invalid synthetic baseline observation")
    if type(initial_faces) is not int or not 1 <= initial_faces <= 96:
        raise ValueError("Invalid baseline face count")
    output = {
        **FIXED, "range_centi": list(FIXED["range_centi"]),
        "source_sha256": source_sha256, "reference_sha256": reference_sha256,
        "baseline_sha256": baseline_sha256, "blender_version": blender_version,
        "combined_aabb_diagonal": scale, "initial_sampled_max": initial_max,
        "initial_socket_affected_faces": initial_faces,
    }
    if baseline_review_sha256 is not None:
        if (not isinstance(baseline_review_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", baseline_review_sha256) is None):
            raise ValueError("Invalid aggregate review binding")
        output["baseline_review_sha256"] = baseline_review_sha256
    return output


def aggregate_review_digest(report):
    """Bind an already validated aggregate, independently of file formatting."""
    try:
        body = json.dumps(report, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
        if not isinstance(report, dict) or len(body) > 128 * 1024:
            raise ValueError("Invalid or oversized aggregate review")
    except (TypeError, RecursionError, OverflowError) as exc:
        raise ValueError("Invalid aggregate review") from exc
    return hashlib.sha256(body).hexdigest()


def validate_conditions(value):
    if not isinstance(value, dict):
        raise ValueError("Missing synthetic conditions")
    try:
        expected = build_conditions(
            source_sha256=value["source_sha256"], reference_sha256=value["reference_sha256"],
            baseline_sha256=value["baseline_sha256"], blender_version=value["blender_version"],
            scale=value["combined_aabb_diagonal"], initial_max=value["initial_sampled_max"],
            initial_faces=value["initial_socket_affected_faces"],
            baseline_review_sha256=value.get("baseline_review_sha256"),
        )
        if json.dumps(value, sort_keys=True, allow_nan=False) != json.dumps(
            expected, sort_keys=True, allow_nan=False
        ):
            raise ValueError("Unknown or forged synthetic conditions")
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("Malformed synthetic conditions") from exc
    return expected
