"""CI-only fault injection after real synthetic GLB generation and comparison.

This never accepts user GLBs or addon source. The injected comparison timeout
is explicitly simulated; baseline generation/comparison use real Blender.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_surface_pipeline import GLBSurfacePipelineError
from cbdk.glb_synthetic_run_review import read_run_review, render_run_review
from scripts import run_glb022_synthetic_adaptive as runner


def main(argv=None):
    parser = argparse.ArgumentParser(description="CBDK synthetic-only controlled failure check")
    parser.add_argument("--blender", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    actual_compare = runner.run_glb_diff_visualize
    calls = 0

    def compare(*values, **options):
        nonlocal calls
        calls += 1
        if calls == 2:
            # Simulate a timeout only after baseline and candidate GLBs exist.
            try:
                raise subprocess.TimeoutExpired("CBDK-controlled-injection", 180)
            except subprocess.TimeoutExpired as exc:
                raise GLBSurfacePipelineError("controlled synthetic timeout") from exc
        return actual_compare(*values, **options)

    with patch.object(runner, "run_glb_diff_visualize", side_effect=compare):
        code = runner.main(["--blender", args.blender, "--output", args.output, "--budget", "1"])
    assert code == 1, "A controlled comparison failure must return a failure exit"
    output = Path(args.output)
    report = read_run_review(output / "synthetic_run_review.json")
    assert report["status"] == "failed"
    assert report["failure_code"] == "comparison_timeout"
    assert report["stage"] == "candidate_comparison"
    assert report["validated_attempts"] == 0
    assert report["active_trial_id"] == "adaptive_124"
    assert report["input_integrity"] == "verified"
    assert report["run_completed"] is False
    assert report["checkpoint"]["best_observed_trial_id"] == "narrow"
    assert not (output / "synthetic_adaptive_history.json").exists()
    assert "失敗・停止" in render_run_review(report)
    assert calls == 2
    print("CBDK_GLB022_CONTROLLED_FAILURE_REVIEW_PASS")
    print("Timeout simulated; synthetic baseline comparison and GLB generation were real")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
