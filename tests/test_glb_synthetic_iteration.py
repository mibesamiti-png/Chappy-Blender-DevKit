"""GLB-022 stage-1 fixed synthetic iteration decision and safety tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from cbdk.glb_synthetic_iteration import (
    build_synthetic_iteration_history,
    render_iteration_markdown,
    write_iteration_history,
)


def report(kind):
    medium = 20 if kind in ("narrow", "narrow_placebo") else 0
    moved = 5 if kind == "narrow_placebo" else 0
    a = [
        {"part_id": f"part_{i:03d}", "triangle_count": n,
         "low": n, "medium": 0, "high": 0}
        for i, n in enumerate((8, 48, 96), 1)
    ]
    b = copy.deepcopy(a)
    b[2]["medium"], b[2]["low"] = medium, 96 - medium
    b[0]["high"], b[0]["low"] = moved, 8 - moved
    return {
        "kind": "cbdk_glb_diff_visualization",
        "schema_version": 1,
        "status": "review_only", "auto_apply": False, "sampled_only": True,
        "complete_surface_equivalence_proven": False,
        "cross_file_part_identity_proven": False,
        "viewer_contains_derived_geometry": True, "viewer_local_only": True,
        "safety": {
            "executes_addon_code": False, "uploads_private_glb": False,
            "saves_raw_mesh_vertices_in_json": False,
            "changes_source_glbs": False,
        },
        "parts": {"reference": a, "candidate": b},
        "reference": {k: sum(x[k] for x in a) for k in ("low", "medium", "high")},
        "candidate": {k: sum(x[k] for x in b) for k in ("low", "medium", "high")},
        "boundary_edge_audit": {
            "method": "world_space_quantized_triangle_edge_incidence_v1",
            "fully_watertight_proven": False,
            "hole_locations_verified": False,
            "internal_voids_verified": False,
            "parts": {
                "reference": [
                    {"part_id": x["part_id"], "triangle_count": x["triangle_count"],
                     "boundary_edges": 0, "observed_boundary": False,
                     "topology_proven": False} for x in a
                ],
                "candidate": [
                    {"part_id": x["part_id"], "triangle_count": x["triangle_count"],
                     "boundary_edges": 0, "observed_boundary": False,
                     "topology_proven": False} for x in b
                ],
            },
        },
        "sampling_sensitivity_audit": {
            "method": "extra_halton_24_probe_sensitivity_v1",
            "unobserved_regions_verified": False,
            "complete_surface_equivalence_proven": False,
        },
        "part_match_candidates": {
            "status": "review_only", "auto_apply": False,
            "cross_file_part_identity_proven": False,
            "reference_parts": [
                {"reference_part_id": f"part_{i:03d}",
                 "status": "suggested",
                 "candidate_part_ids": [f"part_{i:03d}"],
                 "topology_review_required": False}
                for i in range(1, 4)
            ],
        },
    }


class IterationTests(unittest.TestCase):
    def setUp(self):
        self.reports = {x: report(x)
                        for x in ("narrow", "narrow_placebo", "identical")}

    def test_reject_unrelated_change_then_accept_restoration_and_stop(self):
        h = build_synthetic_iteration_history(self.reports)
        self.assertEqual(h["attempts_executed"], 2)
        self.assertEqual(h["stop_reason"],
                         "observed_zero_and_no_other_part_regression")
        self.assertEqual(h["accepted_candidate_id"], "identical")
        self.assertEqual([a["accepted"] for a in h["attempts"]], [False, True])
        self.assertEqual(h["attempts"][0]["baseline_id_after"], "narrow")
        self.assertEqual(h["attempts"][1]["baseline_id_before"], "narrow")
        self.assertEqual(h["attempts"][0]["candidate_sampled"]
                         ["other_parts_sampled_affected_faces"], 5)
        self.assertEqual(h["final_observations"]
                         ["socket_sampled_affected_faces"], 0)
        self.assertTrue(all(v is False for v in h["safety"].values()))
        sheet = render_iteration_markdown(h)
        self.assertIn("不採用", sheet)
        self.assertIn("採用（合成実験のみ）", sheet)
        self.assertIn("停止理由", sheet)
        self.assertNotIn("実アドオンの最適化です", sheet)

    def test_bad_safety_and_bogus_improvement_rejected(self):
        cases = []
        one = copy.deepcopy(self.reports)
        one["narrow"]["safety"]["executes_addon_code"] = True
        cases.append(one)
        one = copy.deepcopy(self.reports)
        one["narrow_placebo"]["parts"]["candidate"][2]["medium"] = 0
        one["narrow_placebo"]["parts"]["candidate"][2]["low"] = 96
        one["narrow_placebo"]["candidate"]["medium"] = 0
        cases.append(one)
        one = copy.deepcopy(self.reports)
        one["identical"]["parts"]["candidate"][2]["medium"] = 8
        one["identical"]["parts"]["candidate"][2]["low"] = 88
        one["identical"]["candidate"]["medium"] = 8
        cases.append(one)
        one = copy.deepcopy(self.reports)
        one["identical"]["parts"]["candidate"][0]["medium"] = 1
        one["identical"]["parts"]["candidate"][0]["low"] = 7
        one["identical"]["candidate"]["medium"] = 1
        cases.append(one)
        one = copy.deepcopy(self.reports)
        one["narrow"]["parts"]["candidate"][2]["high"] = True
        cases.append(one)
        for i, case in enumerate(cases):
            with self.subTest(i=i):
                with self.assertRaises((ValueError, TypeError)):
                    build_synthetic_iteration_history(case)

    def test_unsafe_trial_counts_and_fake_history_rejected(self):
        base = build_synthetic_iteration_history(self.reports)
        variants = []
        x = copy.deepcopy(base)
        x["safety"]["proves_real_addon_causality"] = True
        variants.append(x)
        x = copy.deepcopy(base)
        x["attempts"][0]["candidate_id"] = "private_user_source.py"
        variants.append(x)
        x = copy.deepcopy(base)
        x["attempts"][0]["accepted"] = True
        variants.append(x)
        x = copy.deepcopy(base)
        x["attempts"][0]["candidate_sampled"]["socket_sampled_affected_faces"] = 0
        variants.append(x)
        x = copy.deepcopy(base)
        x["attempts"][1]["control"]["socket_opening_diameter"] = 4.5
        variants.append(x)
        x = copy.deepcopy(base)
        x["attempts"][1]["candidate_sampled"]["socket_sampled_affected_faces"] = True
        variants.append(x)
        for i, invalid in enumerate(variants):
            with self.subTest(i=i), self.assertRaises(ValueError):
                render_iteration_markdown(invalid)

    def test_local_history_is_new_not_overwritten(self):
        h = build_synthetic_iteration_history(self.reports)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, b = write_iteration_history(h, root)
            self.assertEqual(json.loads(a.read_text("utf-8")), h)
            self.assertIn("不採用", b.read_text("utf-8"))
            with self.assertRaises(FileExistsError):
                write_iteration_history(h, root)
            self.assertNotIn("private_user_source.py", a.read_text("utf-8"))

    def test_no_arbitrary_trial_keys_or_extra_iterations(self):
        with self.assertRaises(ValueError):
            build_synthetic_iteration_history({"narrow": self.reports["narrow"]})
        with self.assertRaises(ValueError):
            build_synthetic_iteration_history({
                **self.reports, "private_user_addon": self.reports["identical"]
            })


if __name__ == "__main__":
    unittest.main()
