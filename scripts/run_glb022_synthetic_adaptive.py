"""Feedback-driven synthetic Blender trials with durable review checkpoints.

Only the trusted CBDK fixture generator runs. Failures preserve a validated
measurement prefix, never an exception message, source path or geometry.
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
from cbdk.glb_surface_pipeline import GLBSurfacePipelineError
from cbdk.glb_synthetic_adaptive import (
    MAX_TRIALS, TARGET_SAMPLED_MAX, build_adaptive_checkpoint,
    build_adaptive_history, next_candidate, trial_id, write_adaptive_history,
)
from cbdk.glb_synthetic_progress import _metric
from cbdk.glb_synthetic_run_review import build_run_review, write_run_review
from cbdk.glb_synthetic_conditions import build_conditions, condition_source_digest


class SyntheticAdaptiveRunError(RuntimeError):
    """A fixed safe diagnostic code; never include external exception text."""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _caused_by_timeout(exc):
    for _ in range(8):
        if isinstance(exc, subprocess.TimeoutExpired):
            return True
        exc = exc.__cause__
        if exc is None:
            break
    return False


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
    initial_sha = sha(generator)
    initial_sources = condition_source_digest(REPO)
    glb_shas = {}
    checkpoint = None
    sequence = 0
    stage, active_trial = "reference_generation", None
    integrity = "not_checked"
    conditions = None

    def record(*, status="incomplete", failure_code=None):
        nonlocal sequence
        report = build_run_review(
            checkpoint, budget=budget, stage=stage, status=status,
            active_trial=active_trial, failure_code=failure_code, integrity=integrity,
            conditions=conditions,
        )
        if status == "incomplete":
            write_run_review(report, root, sequence=sequence)
            sequence += 1
        else:
            # Only the terminal pair may certify completion. A failed terminal
            # write leaves earlier checkpoints explicitly incomplete.
            write_run_review(report, root)

    def check_integrity():
        nonlocal integrity
        try:
            unchanged = (condition_source_digest(REPO) == initial_sources
                and not generator.is_symlink() and sha(generator) == initial_sha and all(
                not path.is_symlink() and sha(path) == digest
                for path, digest in glb_shas.items()))
        except (OSError, ValueError):
            unchanged = False
        integrity = "verified" if unchanged else "failed"
        if not unchanged:
            raise SyntheticAdaptiveRunError("input_integrity_changed")

    def generate(kind, centi=None):
        if kind not in ("reference", "narrow", "adaptive_candidate"):
            raise ValueError("Unknown generator type")
        if (kind == "adaptive_candidate") != (centi is not None):
            raise ValueError("Only adaptive generation may have a dimension")
        check_integrity()
        name = trial_id(centi) if kind == "adaptive_candidate" else kind
        folder = root / "synthetic_inputs" / name
        command = [
            str(exe), "--background", "--factory-startup", "--disable-autoexec",
            "--python-exit-code", "7", "--python", str(generator), "--",
            str(folder), "--single", kind,
        ]
        if centi is not None:
            command.extend(("--socket-diameter", f"{centi / 100:.2f}"))
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace",
                                    timeout=180, check=False)
        except subprocess.TimeoutExpired:
            raise SyntheticAdaptiveRunError("generation_timeout") from None
        except OSError:
            raise SyntheticAdaptiveRunError("generation_failed") from None
        if result.returncode or result.stdout.count("CBDK_JOINT_MVP_FIXTURES_PASS") != 1:
            raise SyntheticAdaptiveRunError("generation_failed")
        candidate = folder / (kind + ".glb")
        if candidate.is_symlink() or not candidate.is_file() or candidate.stat().st_size <= 100:
            raise SyntheticAdaptiveRunError("generation_failed")
        glb_shas[candidate] = sha(candidate)
        check_integrity()
        return candidate

    def compare(reference, candidate, name):
        try:
            report = run_glb_diff_visualize(
                str(exe), reference, candidate, root / name, timeout=180)
        except (GLBSurfacePipelineError, subprocess.TimeoutExpired) as exc:
            code = "comparison_timeout" if _caused_by_timeout(exc) else "comparison_failed"
            raise SyntheticAdaptiveRunError(code) from None
        check_integrity()
        try:
            metric = _metric(report)
        except (ValueError, TypeError, KeyError):
            raise SyntheticAdaptiveRunError("invalid_measurement") from None
        return report, metric

    try:
        record()
        reference = generate("reference")
        stage = "baseline_generation"
        record()
        narrow = generate("narrow")
        stage = "baseline_comparison"
        record()
        baseline, baseline_metric = compare(reference, narrow, "review_narrow")
        try:
            checkpoint = build_adaptive_checkpoint(baseline, {}, budget=budget)
            conditions = build_conditions(
                source_sha256=initial_sources, reference_sha256=glb_shas[reference],
                baseline_sha256=glb_shas[narrow], blender_version=baseline.get("blender_version"),
                scale=baseline_metric["combined_aabb_diagonal"],
                initial_max=baseline_metric["sampled_max_distance"],
                initial_faces=baseline_metric["socket_sampled_affected_faces"],
            )
        except ValueError:
            checkpoint = None
            raise SyntheticAdaptiveRunError("invalid_measurement") from None
        stage = "measurement_validated"
        record()
        lo, hi = 78, 170
        trials = {}
        for _ in range(budget):
            candidate_centi = next_candidate(lo, hi)
            if candidate_centi is None:
                raise SyntheticAdaptiveRunError("invalid_measurement")
            active_trial = trial_id(candidate_centi)
            stage = "candidate_generation"
            record()
            glb = generate("adaptive_candidate", candidate_centi)
            stage = "candidate_comparison"
            record()
            report, metric = compare(reference, glb, "review_" + active_trial)
            if report.get("blender_version") != conditions["blender_version"]:
                raise SyntheticAdaptiveRunError("invalid_measurement")
            if metric["combined_aabb_diagonal"] != baseline_metric["combined_aabb_diagonal"]:
                raise SyntheticAdaptiveRunError("coordinate_scale_changed")
            if metric["other_parts_sampled_affected_faces"] != 0:
                raise SyntheticAdaptiveRunError("cross_part_regression")
            proposed = {**trials, active_trial: report}
            try:
                next_checkpoint = build_adaptive_checkpoint(baseline, proposed, budget=budget)
            except ValueError:
                raise SyntheticAdaptiveRunError("invalid_measurement") from None
            trials, checkpoint = proposed, next_checkpoint
            if metric["sampled_max_distance"] <= TARGET_SAMPLED_MAX:
                hi = candidate_centi
            else:
                lo = candidate_centi
            active_trial = None
            # The next external operation is journaled before it starts.
        stage = "input_integrity"
        record()
        check_integrity()
        stage = "history_output"
        record()
        history = build_adaptive_history(baseline, trials, budget=budget)
        write_adaptive_history(history, root)
        check_integrity()
        stage = "completed"
        record(status="completed")
    except (Exception, KeyboardInterrupt) as exc:
        code = (str(exc) if isinstance(exc, SyntheticAdaptiveRunError) else
                "interrupted" if isinstance(exc, KeyboardInterrupt) else
                "io_failure" if isinstance(exc, OSError) else "unexpected_error")
        try:
            check_integrity()
        except SyntheticAdaptiveRunError:
            code = "input_integrity_changed"
        # A failure while writing the success receipt must not imply completion.
        if stage == "completed":
            stage = "history_output"
        try:
            record(status="failed", failure_code=code)
        except (OSError, ValueError):
            # Existing immutable checkpoints remain; no terminal success is asserted.
            raise SyntheticAdaptiveRunError("review_output_failed") from None
        raise SyntheticAdaptiveRunError(code) from None
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
    try:
        run(a.blender, a.output, budget=a.budget)
    except (ValueError, OSError, SyntheticAdaptiveRunError) as exc:
        print("Synthetic adaptive run did not complete; inspect local run review.", file=sys.stderr)
        return 130 if isinstance(exc, SyntheticAdaptiveRunError) and str(exc) == "interrupted" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
