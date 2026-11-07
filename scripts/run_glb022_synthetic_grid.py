"""GLB-022: real Blender re-generation for four computed CBDK-only grid values.

No arbitrary add-on, input GLB, or Python source accepted. The only executable
script is the tracked CBDK synthetic generator. Never modifies source GLBs.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cbdk.glb_diff_visualize import run_glb_diff_visualize
from cbdk.glb_synthetic_grid import (
    MAX_STEPS, build_grid_history, candidate_values, trial_id,
    write_grid_history,
)
from cbdk.glb_synthetic_progress import _decision, _metric, MIN_DELTA


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(blender, output, *, budget=MAX_STEPS):
    if type(budget) is not int or not 1 <= budget <= MAX_STEPS:
        raise ValueError("Only 1..4 CBDK synthetic grid attempts allowed")
    generator = REPO / "scripts" / "blender_make_glb_joint_mvp_fixtures.py"
    if generator.is_symlink() or not generator.is_file():
        raise ValueError("Trusted fixture generator is missing")
    executable = Path(blender).resolve()
    if not executable.is_file():
        raise ValueError("Trusted Blender binary must exist")
    root = Path(output).absolute()
    if (root.parent.resolve() != (REPO / "reports" / "ci").resolve()
            or root.is_symlink() or root.exists()):
        raise ValueError("Only a fresh repo-local reports/ci directory is allowed")
    root.mkdir(parents=True, exist_ok=False)
    sources = root / "synthetic_inputs"
    sources.mkdir()
    script_hash = _sha(generator)
    input_hashes = {}

    def generate(condition, *, diameter=None):
        if condition not in ("reference", "narrow", "grid_candidate"):
            raise ValueError("Unknown synthetic fixture generation")
        if (condition == "grid_candidate") != (diameter is not None):
            raise ValueError("Only grid conditions can carry a diameter")
        name = trial_id(diameter) if condition == "grid_candidate" else condition
        dest = sources / name
        args = [str(executable), "--background", "--factory-startup",
                "--disable-autoexec", "--python-exit-code", "7",
                "--python", str(generator), "--", str(dest),
                "--single", condition]
        if condition == "grid_candidate":
            args.extend(["--socket-diameter", f"{diameter:.2f}"])
        result = subprocess.run(args, capture_output=True, text=True,
                                encoding="utf-8", errors="replace",
                                timeout=180, check=False)
        if (result.returncode != 0
                or result.stdout.count("CBDK_JOINT_MVP_FIXTURES_PASS") != 1):
            raise RuntimeError("CBDK synthetic grid generation failed")
        glb = dest / (condition + ".glb")
        if glb.is_symlink() or not glb.is_file() or glb.stat().st_size < 100:
            raise RuntimeError("Expected original CBDK-generated GLB file")
        input_hashes[glb] = _sha(glb)
        return glb

    reference = generate("reference")
    narrow = generate("narrow")
    baseline = run_glb_diff_visualize(
        str(executable), reference, narrow,
        root / "review_narrow", timeout=180,
    )
    trials = {}
    current_id = "narrow"
    current_report = baseline
    for value in candidate_values()[:budget]:
        name = trial_id(value)
        generated = generate("grid_candidate", diameter=value)
        report = run_glb_diff_visualize(
            str(executable), reference, generated,
            root / ("review_" + name), timeout=180,
        )
        trials[name] = report
        before, after = _metric(current_report), _metric(report)
        if before["combined_aabb_diagonal"] != after["combined_aabb_diagonal"]:
            raise ValueError("Synthetic reference scene scale changed")
        accepted, _ = _decision(before, after)
        if after["other_parts_sampled_affected_faces"] != 0:
            raise ValueError("Generated socket changed an unrelated part")
        if accepted:
            current_id, current_report = name, report
        final = _metric(current_report)
        if (final["sampled_max_distance"] <= MIN_DELTA
                and final["socket_sampled_affected_faces"] == 0
                and final["other_parts_sampled_affected_faces"] == 0):
            break
    history = build_grid_history(baseline, trials, budget=budget)
    if (history["accepted_trial_id"] != current_id
            or _sha(generator) != script_hash
            or any(_sha(path) != digest
                   for path, digest in input_hashes.items())):
        raise ValueError("Synthetic source integrity or accepted state mismatch")
    write_grid_history(history, root)
    print("CBDK_GLB022_GENERATED_GRID_PASS")
    print("Generated numeric candidates, freshly compared GLBs, bounded and safely stopped")
    print("No user addon execution or real parameter recommendation")
    return history


def main(argv=None):
    parser = argparse.ArgumentParser(description="CBDK-owned synthetic grid-only CI")
    parser.add_argument("--blender", required=True)
    parser.add_argument("--output", default="reports/ci/glb022_generated_grid")
    parser.add_argument("--budget", type=int, default=MAX_STEPS)
    args = parser.parse_args(argv)
    run(args.blender, args.output, budget=args.budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
