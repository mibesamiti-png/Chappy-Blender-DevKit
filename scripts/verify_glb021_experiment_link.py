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
from cbdk.glb_experiment_triage import build_experiment_triage, render_experiment_triage, write_experiment_triage
from cbdk.glb_debug_focus import build_debug_focus


def verify(root, failed_root):
    root, failed_root = Path(root), Path(failed_root)
    fixture = Path("tests/fixtures/glb021_synthetic_settings.py")
    ambiguous_fixture = Path("tests/fixtures/glb021_ambiguous_settings.py")
    cases = (
        ("complete", root / "review_narrow/review.json", root / "synthetic_run_review.json", "completed"),
        ("incomplete", root / "review_narrow/review.json", root / "checkpoint_003.json", "incomplete"),
        ("failed", failed_root / "review_narrow/review.json", failed_root / "synthetic_run_review.json", "failed"),
    )
    originals = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                 for _, visual, run, _ in cases for path in (fixture, visual, run)}
    originals[ambiguous_fixture] = hashlib.sha256(ambiguous_fixture.read_bytes()).hexdigest()
    for label, visual, run, expected_status in cases:
        output = Path("reports/latest") / ("ci_bound_triage_" + label + ".json")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--visual-review", str(visual), "--run-review", str(run),
                         "--source", str(fixture), "--role", "part_003=socket", "--output", str(output)])
        assert code == 0
        assert "socket_opening_diameter" not in stdout.getvalue()
        result = json.loads(output.read_text(encoding="utf-8"))
        assert result["linked_candidate_count"] == 1
        assert result["experiment_review"]["status"] == expected_status
        assert all(value is False for value in result["safety"].values())
        assert all(row["property_effect_verified"] is False for row in result["candidate_links"])
        text = render_visual_experiment_review(result)
        assert "実プロパティの因果は未証明" in text
        assert "source_1.py" in text and "socket_opening_diameter" in text
        assert "tests/fixtures" not in text
        assert output.with_suffix(".md").read_text(encoding="utf-8") == text
        aggregate = json.loads(visual.read_text(encoding="utf-8"))
        triage = build_experiment_triage(aggregate, result)
        assert triage["experiment_status"] == expected_status
        assert {row["part_id"] for row in triage["focus_review"]["focus"]} == {"part_003"}
        assert {row["side"] for row in triage["focus_review"]["focus"]} == {"reference", "candidate"}
        assert not any(triage["safety"].values())
        assert all(row["selected_declaration"] is None for row in triage["candidate_reviews"])
        write_experiment_triage(triage, Path("reports/latest") / ("ci_triage_" + label + ".json"))
        assert "実プロパティ因果は未証明" in render_experiment_triage(triage)
        # Reuse actual measured baseline/trial reviews. No fixture code runs.
        ambiguous_output = Path("reports/latest") / ("ci_ambiguous_" + label + ".json")
        with redirect_stdout(io.StringIO()):
            assert main(["--visual-review", str(visual), "--run-review", str(run),
                         "--source", str(ambiguous_fixture), "--role", "part_003=socket",
                         "--output", str(ambiguous_output)]) == 0
        ambiguous = build_experiment_triage(aggregate, json.loads(ambiguous_output.read_text(encoding="utf-8")))
        assert len(ambiguous["candidate_reviews"]) == 1
        assert ambiguous["candidate_reviews"][0]["declaration_count"] == 2
        assert ambiguous["candidate_reviews"][0]["status"] == "multiple_static_declarations"
        assert ambiguous["candidate_reviews"][0]["selected_declaration"] is None
    # A freshly measured candidate must change focus consistently with its
    # actual classified geometry. Global distance stays explicitly non-local.
    baseline_focus = build_debug_focus(json.loads((root / "review_narrow/review.json").read_text(encoding="utf-8")))
    trial_focus = build_debug_focus(json.loads((root / "review_adaptive_124/review.json").read_text(encoding="utf-8")))
    assert {row["part_id"] for row in baseline_focus["focus"]} == {"part_003"}
    assert {row["part_id"] for row in trial_focus["focus"]} == {"part_003"}
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
    print("CBDK_GLB008_009_TRIAGE_PASS: bidirectional socket focus and multiple declarations remain unverified")


def entry(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--failed-run", required=True)
    args = parser.parse_args(argv)
    verify(args.run, args.failed_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(entry())
