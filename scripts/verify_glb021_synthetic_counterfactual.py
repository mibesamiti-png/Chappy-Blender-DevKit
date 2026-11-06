"""GLB-021 controlled *synthetic-only* intervention; no user addon execution.

The synthetic ring is constructed with exactly two allowlisted opening
diameters. A negative control perturbs only an unrelated ball location, while
leaving the socket narrow. The static AST mapping is a review hint, not
evidence that a real Blender addon property controls the generated geometry.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _affected(report, part):
    row = report["parts"]["candidate"][part - 1]
    assert row["part_id"] == f"part_{part:03d}"
    return row["medium"] + row["high"]


def verify(root):
    root = Path(root)
    baseline = _read(root / "review_identical" / "review.json")
    defect = _read(root / "review_narrow" / "review.json")
    placebo = _read(root / "review_narrow_placebo" / "review.json")
    # Synthetic source shape produced with explicit fixed diameter=1.70.
    # A deliberately narrowed diameter=0.78 must cause observed socket error.
    assert _affected(baseline, 3) == 0
    assert _affected(defect, 3) > 0

    # Restoring the allowlisted known fixture control to 1.70 resolves the
    # observed defect in the synthetic model. This is *not* an inferred value
    # for an arbitrary user's addon.
    assert all(_affected(baseline, i) == 0 for i in (1, 2, 3))
    assert baseline["candidate"]["high"] == 0
    assert baseline["candidate"]["medium"] == 0

    # Changing a different control (ball location) must *not* cure the
    # socket defect; it introduces an additional ball discrepancy instead.
    assert _affected(placebo, 3) > 0, "Unrelated edit incorrectly passed as socket fix"
    assert _affected(placebo, 1) > 0, "Unrelated edit was not observed on the ball"
    assert _affected(defect, 1) == 0
    assert _affected(defect, 2) == 0
    assert _affected(placebo, 2) == 0
    # No silent topological repair, raw geometry or automatic parameter edit.
    for report in (baseline, defect, placebo):
        assert report["status"] == "review_only"
        assert report["auto_apply"] is False
        assert report["cross_file_part_identity_proven"] is False
        assert report["complete_surface_equivalence_proven"] is False
        assert report["safety"]["changes_source_glbs"] is False
        assert report["safety"]["executes_addon_code"] is False
        assert report["boundary_edge_audit"]["fully_watertight_proven"] is False
    # Record only an aggregate-only, synthetic-only experiment result.
    result = {
        "kind": "cbdk_glb021_synthetic_counterfactual_v1",
        "status": "synthetic_case_only",
        "fixture_generator_allowlisted": True,
        "input_addon_or_user_code_executed": False,
        "real_user_addon_cause_proven": False,
        "user_parameter_change_recommended": False,
        "cross_file_part_identity_proven": False,
        "intervention": {
            "synthetic_control": "socket_opening_diameter",
            "simulated_defect_diameter": 0.78,
            "synthetic_baseline_diameter": 1.70,
            "unrelated_control": "ball_location",
        },
        "observations": {
            "defective_socket_affected_faces": _affected(defect, 3),
            "restored_socket_affected_faces": _affected(baseline, 3),
            "placebo_socket_affected_faces": _affected(placebo, 3),
            "placebo_ball_affected_faces": _affected(placebo, 1),
        },
        "conclusion": (
            "Only the CBDK-owned synthetic generator has a tested causal "
            "link to the explicitly allowlisted socket dimension; the static "
            "AST match and arbitrary real add-ons remain unverified."
        ),
    }
    target = root / "synthetic_only_counterfactual_summary.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print("CBDK_GLB021_SYNTHETIC_COUNTERFACTUAL_PASS")
    print("Observed socket error: defect positive; restored zero; decoy still positive")
    print("No execution of user addons; no claim of actual addon cause")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Expected CBDK synthetic fixture directory")
    verify(sys.argv[1])
