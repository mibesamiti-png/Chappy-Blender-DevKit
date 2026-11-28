"""R20 expanded-profile core checks; native GLB integration is separate."""
import copy
import io
import json
from contextlib import redirect_stdout, redirect_stderr
import unittest
from unittest.mock import patch

from cbdk.glb_surface_distance import (
    SurfaceDistanceError, _SurfaceWorkBudget, compare_triangle_surfaces,
    _directed, _validated_triangles,
)
from cbdk.glb_multires_surface import (
    _expanded_review, compare_expanded_triangle_surfaces,
    compare_multires_triangle_surfaces,
)
from cbdk import glb_multires_surface
from cbdk.glb_surface_pipeline import _validate_expanded_report


def grid(n, z=0.0):
    return [((float(i), 0.0, z), (float(i + 1), 0.0, z),
             (float(i), 1.0, z)) for i in range(n)]


class ExpandedSurfaceTests(unittest.TestCase):
    def test_legacy_parity_and_two_builds(self):
        ref, cand = grid(5), grid(5, 0.125)
        old_fixed = compare_triangle_surfaces(ref, cand)
        old_adaptive = compare_multires_triangle_surfaces(ref, cand)
        with patch.object(glb_multires_surface, "_build_bvh",
                          wraps=glb_multires_surface._build_bvh) as build:
            new = compare_expanded_triangle_surfaces(ref, cand)
        self.assertEqual(build.call_count, 2)
        self.assertEqual(new["status"], "review_only")
        self.assertEqual(new["fixed_surface"]["symmetric_mean"], 0.125)
        self.assertEqual(new["adaptive_surface"]["refined_symmetric_mean"], 0.125)
        for key in ("reference_to_candidate", "candidate_to_reference"):
            self.assertEqual(new["fixed_surface"][key], old_fixed[key])
            self.assertEqual(new["adaptive_surface"][key], old_adaptive[key])
        exhaustive = _directed(_validated_triangles(ref, "ref"),
                               _validated_triangles(cand, "cand"), accelerated=False)
        for key in ("mean", "sampled_max", "sample_count"):
            self.assertEqual(new["fixed_surface"]["reference_to_candidate"][key],
                             exhaustive[key])
        reports = (new["fixed_surface"], new["adaptive_surface"])
        directions = ("reference_to_candidate", "candidate_to_reference")
        self.assertEqual(new["work_budget"]["used"]["triangle_evaluations"],
                         sum(x[k]["triangle_distance_evaluations"]
                             for x in reports for k in directions))

    def test_expanded_parent_rejects_forged_counters_and_schema(self):
        evidence = compare_expanded_triangle_surfaces(grid(5), grid(5, 0.25))
        _validate_expanded_report(evidence)
        for key, replacement in (
            ("samples", -1), ("node_visits", True),
            ("triangle_evaluations", evidence["work_budget"]["used"]["triangle_evaluations"] + 1),
        ):
            forged = copy.deepcopy(evidence)
            forged["work_budget"]["used"][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                _validate_expanded_report(forged)
        for key, value in (("schema_version", 1), ("symmetric_mean", float("inf")),
                           ("exact_surface_equivalence_verified", True)):
            forged = copy.deepcopy(evidence)
            forged["fixed_surface"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                _validate_expanded_report(forged)

    def test_strict_limits(self):
        with self.assertRaises(SurfaceDistanceError):
            compare_triangle_surfaces(grid(513), grid(1))
        with self.assertRaises(SurfaceDistanceError):
            compare_expanded_triangle_surfaces(grid(2049), grid(1))

    def test_expanded_more_than_legacy(self):
        ref, cand = grid(513), grid(513, 0.25)
        new = compare_expanded_triangle_surfaces(ref, cand)
        self.assertEqual(new["status"], "review_only")
        self.assertEqual(new["fixed_surface"]["symmetric_sampled_max"], 0.25)
        self.assertEqual(new["adaptive_surface"]["refined_symmetric_sampled_max"], 0.25)

    def test_every_budget_can_stop_without_distances(self):
        for key in ("samples", "node_visits", "triangle_evaluations"):
            with self.subTest(key=key):
                budget = _SurfaceWorkBudget()
                budget.LIMITS = dict(budget.LIMITS, **{key: 1})
                new = _expanded_review(grid(3), grid(3), budget)
                self.assertEqual(new["status"], "skipped")
                self.assertEqual(new["exhausted_counter"], key)
                self.assertEqual(new["surface_observation"], "not_measured")
                self.assertNotIn("fixed_surface", new)
                self.assertNotIn("adaptive_surface", new)
                self.assertEqual(new["work_budget"]["used"][key], 1)


class ExpandedSurfaceCLITests(unittest.TestCase):
    def test_explicit_profile_and_legacy_default_forwarding(self):
        from cbdk.__main__ import main
        args = ["glb-surface-review", "ref.glb", "cand.glb", "--blender", "blender",
                "--output", "out.json", "--timeout", "42"]
        evidence = {"kind": "cbdk_glb_surface_review", "status": "review_only",
                    "reference_triangles": 2048, "candidate_triangles": 2048,
                    "surface_observation": "sampled_difference_detected"}
        with patch("cbdk.__main__.run_glb_surface_review", return_value=evidence) as run:
            with redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(main(args + ["--profile", "expanded_2048"]), 0)
            run.assert_called_once_with("blender", "ref.glb", "cand.glb", "out.json",
                                        timeout=42, profile="expanded_2048")
            self.assertEqual(json.loads(stdout.getvalue())["profile"], "expanded_2048")
            run.reset_mock()
            evidence.update(status="skipped", reason="triangle_limit",
                            surface_observation="not_measured")
            with redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(main(args), 2)
            run.assert_called_once_with("blender", "ref.glb", "cand.glb", "out.json", timeout=42)
            self.assertNotIn("profile", json.loads(stdout.getvalue()))
            run.reset_mock()
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(args + ["--profile", "unbounded"])
            self.assertEqual(exc.exception.code, 2)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
