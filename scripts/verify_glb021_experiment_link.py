"""Synthetic-only CI: bind actual GLB aggregate/AST review to experiment history.

Only the repository-owned AST fixture is parsed; it is never imported. Linked
private sheets stay in ignored reports/latest, outside uploaded CI artifacts.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_visual_experiment_review import main, render_visual_experiment_review


def verify(root, failed_root):
    root, failed_root = Path(root), Path(failed_root)
    fixture = Path("tests/fixtures/glb021_synthetic_settings.py")
    cases = (
        ("complete", root / "review_narrow/review.json", root / "synthetic_run_review.json", "completed"),
        ("incomplete", root / "review_narrow/review.json", root / "checkpoint_003.json", "incomplete"),
        ("failed", failed_root / "review_narrow/review.json", failed_root / "synthetic_run_review.json", "failed"),
    )
    originals = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                 for _, visual, run, _ in cases for path in (fixture, visual, run)}
    for label, visual, run, expected_status in cases:
        output = Path("reports/latest") / ("ci_bound_" + label + ".json")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--visual-review", str(visual), "--run-review", str(run),
                         "--source", str(fixture), "--role", "part_003=socket", "--output", str(output)])
        assert code == 0
        assert "socket_opening_diameter" not in stdout.getvalue()
        result = json.loads(output.read_text())
        assert result["linked_candidate_count"] == 1
        assert result["experiment_review"]["status"] == expected_status
        assert all(value is False for value in result["safety"].values())
        assert all(row["property_effect_verified"] is False for row in result["candidate_links"])
        text = render_visual_experiment_review(result)
        assert "実プロパティの因果は未証明" in text
        assert "source_1.py" in text and "socket_opening_diameter" in text
        assert "tests/fixtures" not in text
        assert output.with_suffix(".md").read_text() == text
    # A later trial's aggregate is not the experiment's faulty initial baseline.
    with redirect_stderr(io.StringIO()):
        try:
            main(["--visual-review", str(root / "review_adaptive_124/review.json"),
                  "--run-review", str(root / "synthetic_run_review.json"),
                  "--source", str(fixture), "--role", "part_003=socket",
                  "--output", "reports/latest/ci_bound_mismatch.json"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("Different aggregate baseline was accepted")
    assert not Path("reports/latest/ci_bound_mismatch.json").exists()
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest
               for path, digest in originals.items())
    print("CBDK_GLB021_BOUND_EXPERIMENT_REVIEW_PASS")
    print("Completed/incomplete/controlled-failure evidence linked; mismatched baseline refused")
    print("AST fixture never executed; real addon causality remains unverified")


def entry(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--failed-run", required=True)
    args = parser.parse_args(argv)
    verify(args.run, args.failed_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(entry())
