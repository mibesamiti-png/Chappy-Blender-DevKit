from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_regression import run_glb_regression


class GLBRegressionTests(unittest.TestCase):
    def test_orchestrates_two_previews_then_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref = root / "ref.glb"; cand = root / "cand.glb"
            ref.write_bytes(b"x"); cand.write_bytes(b"y")
            comparison = {
                "kind": "cbdk_glb_scene_comparison",
                "passed": True,
                "summary": {"errors": 0},
                "differences": [],
            }
            with patch("cbdk.glb_regression.write_glb_inspection") as inspect, \
                 patch("cbdk.glb_regression.render_glb_preview") as render, \
                 patch("cbdk.glb_regression.write_scene_comparison", return_value=comparison) as compare:
                result = run_glb_regression(
                    root / "blender", ref, cand, root / "out",
                    resolution=320, timeout=90, profile="shape",
                )
            self.assertEqual(inspect.call_count, 2)
            self.assertEqual(render.call_count, 2)
            self.assertEqual(compare.call_count, 1)
            self.assertTrue(result["passed"])
            self.assertEqual(result["profile"], "shape")
            self.assertEqual(result["parameter_review_candidates"], 0)
            self.assertTrue((root / "out" / "repair_plan.json").is_file())


    def test_optional_surface_review_is_called_and_remains_review_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref, cand = root / "ref.glb", root / "cand.glb"
            ref.write_bytes(b"x")
            cand.write_bytes(b"y")
            comparison = {
                "kind": "cbdk_glb_scene_comparison",
                "passed": True,
                "summary": {"errors": 0},
                "differences": [],
            }
            surface = {
                "kind": "cbdk_glb_surface_review",
                "status": "review_only",
                "surface_observation": "sampled_difference_detected",
            }
            with patch("cbdk.glb_regression.write_glb_inspection"), \
                 patch("cbdk.glb_regression.render_glb_preview"), \
                 patch("cbdk.glb_regression.write_scene_comparison",
                       return_value=comparison), \
                 patch("cbdk.glb_regression.run_glb_surface_review",
                       return_value=surface) as review:
                result = run_glb_regression(
                    root / "blender", ref, cand, root / "out",
                    surface_review=True, timeout=150,
                )
            review.assert_called_once_with(
                root / "blender", ref, cand,
                root / "out" / "surface_review.json", timeout=150)
            self.assertTrue(result["passed"])
            self.assertTrue(result["passed_is_metadata_only"])
            self.assertTrue(result["surface_does_not_auto_approve"])
            self.assertEqual(result["surface_status"], "review_only")
            self.assertEqual(result["surface_observation"],
                             "sampled_difference_detected")

    def test_optional_surface_stage_can_report_skipped_without_false_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            comparison = {
                "kind": "cbdk_glb_scene_comparison",
                "passed": False,
                "summary": {"errors": 1},
                "differences": [],
            }
            with patch("cbdk.glb_regression.write_glb_inspection"), \
                 patch("cbdk.glb_regression.render_glb_preview"), \
                 patch("cbdk.glb_regression.write_scene_comparison",
                       return_value=comparison), \
                 patch("cbdk.glb_regression.run_glb_surface_review",
                       return_value={
                           "kind": "cbdk_glb_surface_review",
                           "status": "skipped",
                           "surface_observation": "not_measured",
                       }):
                result = run_glb_regression(
                    root / "blender", root / "a.glb", root / "b.glb",
                    root / "out", surface_review=True)
            self.assertFalse(result["passed"])
            self.assertEqual(result["surface_status"], "skipped")
            self.assertEqual(result["surface_observation"], "not_measured")

    def test_invalid_surface_review_switch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_glb_regression(
                    Path(tmp) / "blender", Path(tmp) / "a.glb",
                    Path(tmp) / "b.glb", Path(tmp) / "out",
                    surface_review="yes")


if __name__ == "__main__":
    unittest.main()
