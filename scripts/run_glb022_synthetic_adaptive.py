"""Real feedback-driven synthetic Blender test, not a user addon optimizer.

At each step the *last measured* aggregate GLB score changes the next 2-decimal
candidate. Only CBDK's trusted fixture generator is executed.
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
from cbdk.glb_synthetic_adaptive import (
    MAX_TRIALS, TARGET_SAMPLED_MAX, build_adaptive_history,
    next_candidate, trial_id, write_adaptive_history,
)
from cbdk.glb_synthetic_progress import _metric, MIN_DELTA


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(blender, output, *, budget=MAX_TRIALS):
    if type(budget) is not int or not 1 <= budget <= MAX_TRIALS:
        raise ValueError("Synthetic adaptive budget must be 1..4")
    generator = REPO / "scripts" / "blender_make_glb_joint_mvp_fixtures.py"
    if generator.is_symlink() or not generator.is_file():
        raise ValueError("CBDK synthetic generator missing or symlinked")
    exe = Path(blender).resolve()
    if not exe.is_file():
        raise ValueError("Explicit trusted Blender binary required")
    root = Path(output).absolute()
    if (root.parent.resolve() != (REPO / "reports" / "ci").resolve()
            or root.exists() or root.is_symlink()):
        raise ValueError("Only new repo-local reports/ci output folder allowed")
    root.mkdir(parents=True, exist_ok=False)
    source_dir = root / "synthetic_inputs"
    source_dir.mkdir()
    initial_sha = sha(generator)
    glb_shas = {}

    def generate(kind, centi=None):
        if kind not in ("reference", "narrow", "adaptive_candidate"):
            raise ValueError("Unknown generator type")
        if (kind == "adaptive_candidate") != (centi is not None):
            raise ValueError("Only adaptive generation may have a dimension")
        name = trial_id(centi) if kind == "adaptive_candidate" else kind
        folder = source_dir / name
        command = [
            str(exe), "--background", "--factory-startup", "--disable-autoexec",
            "--python-exit-code", "7", "--python", str(generator), "--",
            str(folder), "--single", kind,
        ]
        if centi is not None:
            command.extend(("--socket-diameter", f"{centi / 100:.2f}"))
        result = subprocess.run(command, capture_output=True, text=True,
                                encoding="utf-8", errors="replace",
                                timeout=180, check=False)
        if result.returncode or result.stdout.count("CBDK_JOINT_MVP_FIXTURES_PASS") != 1:
            raise RuntimeError("Trusted adaptive fixture generation failed")
        candidate = folder / (kind + ".glb")
        if candidate.is_symlink() or not candidate.is_file() or candidate.stat().st_size <= 100:
            raise RuntimeError("Expected newly generated CBDK GLB")
        glb_shas[candidate] = sha(candidate)
        return candidate

    reference = generate("reference")
    narrow = generate("narrow")
    baseline = run_glb_diff_visualize(
        str(exe), reference, narrow, root / "review_narrow", timeout=180,
    )
    baseline_metric = _metric(baseline)
    if (baseline_metric["sampled_max_distance"] <= TARGET_SAMPLED_MAX
            or baseline_metric["socket_sampled_affected_faces"] < 1):
        raise ValueError("Synthetic baseline does not exceed fixed trial target")
    lo, hi = 78, 170
    trials = {}
    for index in range(budget):
        candidate_centi = next_candidate(lo, hi)
        if candidate_centi is None:
            raise ValueError("Adaptive lattice converged before requested trial budget")
        name = trial_id(candidate_centi)
        glb = generate("adaptive_candidate", candidate_centi)
        report = run_glb_diff_visualize(
            str(exe), reference, glb, root / ("review_" + name), timeout=180,
        )
        metric = _metric(report)
        if (metric["combined_aabb_diagonal"] != baseline_metric["combined_aabb_diagonal"]
                or metric["other_parts_sampled_affected_faces"] != 0):
            raise ValueError("Synthetic feedback is unsafe or cross-part regressed")
        trials[name] = report
        if metric["sampled_max_distance"] <= TARGET_SAMPLED_MAX:
            hi = candidate_centi
        else:
            lo = candidate_centi
    history = build_adaptive_history(baseline, trials, budget=budget)
    if (sha(generator) != initial_sha
            or any(sha(path) != digest for path, digest in glb_shas.items())):
        raise ValueError("Synthetic source/code digest changed during adaptive trial")
    write_adaptive_history(history, root)
    print("CBDK_GLB022_ADAPTIVE_SYNTHETIC_PASS")
    print("Actual measured results selected subsequent bounded Blender candidates")
    print("No user addons, no real joint parameter recommendation")
    return history


def main(argv=None):
    p = argparse.ArgumentParser(description="CBDK-owned synthetic feedback CI")
    p.add_argument("--blender", required=True)
    p.add_argument("--output", default="reports/ci/glb022_adaptive")
    p.add_argument("--budget", type=int, default=MAX_TRIALS)
    a = p.parse_args(argv)
    run(a.blender, a.output, budget=a.budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
