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


if __name__ == "__main__":
    unittest.main()
