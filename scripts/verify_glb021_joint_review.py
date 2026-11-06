"""GLB-021 synthetic end-to-end AST property review against real Blender GLBs.

This script consumes only aggregate GLB-020 review.json and explicitly
selected CBDK-authored synthetic addon source. Never import/execute that addon,
publish source text, or automatically apply an inferred property value.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.__main__ import main


def verify(root):
    root = Path(root)
    fixture = Path("tests/fixtures/glb021_synthetic_settings.py")
    original = fixture.read_bytes()
    roles = {
        "identical": [],
        "narrow": ["part_003=socket"],
        "shifted": ["part_001=ball"],
        "uncapped": ["part_003=socket"],
    }
    for scenario, annotations in roles.items():
        observation = root / f"review_{scenario}" / "review.json"
        observation_bytes = observation.read_bytes()
        output = f"reports/latest/ci_glb021_{scenario}.json"
        command = [
            "glb-visual-property-review", str(observation),
            "--source", str(fixture), "--output", output, "--markdown",
        ]
        for label in annotations:
            command.extend(["--role", label])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(command)
        assert status == 0, scenario
        # CLI stdout must not expose AST property identifiers/private file paths.
        printed = stdout.getvalue()
        assert "socket_opening_diameter" not in printed
        assert "glb021_synthetic_settings.py" not in printed
        result = json.loads(Path(output).read_text(encoding="utf-8"))
        sheet_file = Path(output).with_suffix(".md")
        assert sheet_file.is_file(), scenario
        sheet = sheet_file.read_text(encoding="utf-8")
        assert "GLB-021 設定候補レビュー" in sheet, scenario
        assert "原因の証明ではありません" in sheet, scenario
        assert "人による確認項目" in sheet or scenario == "identical"
        assert "glb021_synthetic_settings.py" not in sheet
        assert "default=" not in sheet
        assert "CBDK_SYNTH" not in sheet
        assert result["kind"] == "cbdk_glb_property_mapping"
        assert result["link_kind"] == "glb020_visual_diff_to_ast_property_candidates_v1"
        assert result["status"] == "review_only"
        assert result["cause_and_effect_proven"] is False
        assert result["cross_file_part_identity_proven"] is False
        assert result["parameter_values_inferred"] is False
        assert result["input_glb_or_addon_executed"] is False
        assert result["safety"]["source_executed"] is False
        assert result["safety"]["source_modified"] is False
        assert result["safety"]["applies_parameters"] is False
        assert fixture.read_bytes() == original
        assert observation.read_bytes() == observation_bytes
        if scenario == "identical":
            assert result["recommendation_count"] == 0
            assert "レビューが必要な生成側の部品: 0件" in sheet
            continue
        assert result["recommendation_count"] == 1, scenario
        item = result["recommendations"][0]
        part = "part_001" if scenario == "shifted" else "part_003"
        assert item["target"] == part, scenario
        assert item["candidate_cause_verified"] is False
        assert item["visual_observation"]["candidate_part_id"] == part
        assert item["visual_observation"]["requires_human_review"] is True
        assert item["visual_observation"]["recommended_parameter_value"] is None
        assert item["exact_name_matches"], scenario
        identifiers = [x["candidate_family"] for x in item["exact_name_matches"]]
        expected = "ball_diameter" if scenario == "shifted" else "socket_opening_diameter"
        assert expected in identifiers, (scenario, identifiers)
        assert expected in sheet, scenario
        assert "原因未確定" in sheet, scenario
        for hint in item["exact_name_matches"]:
            assert hint["match"] == "exact_declaration_name_only"
            assert hint["requires_human_review"] is True
            assert all(d["registered_in_blender"] == "not_checked"
                       and d["controls_geometry"] == "not_checked"
                       for d in hint["declarations"])
        if scenario == "uncapped":
            assert item["visual_observation"]["observed_boundary_edges"] == 4
            assert item["visual_observation"]["tentative_reference_part_id"] is None
        if scenario == "narrow":
            assert item["visual_observation"]["observed_medium_faces"] \
                + item["visual_observation"]["observed_high_faces"] > 0
    print("CBDK_GLB021_SYNTHETIC_AST_LINK_PASS")
    print("identical: zero proposals; narrow/shifted/uncapped: review-only AST hints")
    print("no source execution, no parameter application, local-only report")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Pass temporary GLB-020 synthetic joint CI directory")
    verify(sys.argv[1])
