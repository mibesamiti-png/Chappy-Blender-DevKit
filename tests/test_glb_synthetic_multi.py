"""GLB-022 phase-2 multi-candidate cross-part rejection and stop gates."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from cbdk.glb_synthetic_multi import (
    CANDIDATES, build_multi_iteration_history,
    render_multi_iteration_markdown, write_multi_iteration_history,
)


def report(case):
    sizes = (8, 48, 96)
    ref = [
        {"part_id": f"part_{i:03d}", "triangle_count": n,
         "low": n, "medium": 0, "high": 0}
        for i, n in enumerate(sizes, 1)
    ]
    cand = copy.deepcopy(ref)
    if case in ("narrow", "narrow_placebo"):
        cand[2]["medium"], cand[2]["low"] = 20, 76
    if case in ("narrow_placebo", "shifted"):
        cand[0]["high"], cand[0]["low"] = 5, 3
    def edges(rows):
        return [
            {"part_id": r["part_id"], "triangle_count": r["triangle_count"],
             "boundary_edges": 0, "observed_boundary": False,
             "topology_proven": False}
            for r in rows
        ]
    return {
        "kind": "cbdk_glb_diff_visualization", "schema_version": 1,
        "status": "review_only", "auto_apply": False, "sampled_only": True,
        "complete_surface_equivalence_proven": False,
        "cross_file_part_identity_proven": False,
        "viewer_contains_derived_geometry": True, "viewer_local_only": True,
        "safety": {
            "executes_addon_code": False, "uploads_private_glb": False,
            "saves_raw_mesh_vertices_in_json": False,
            "changes_source_glbs": False,
        },
        "parts": {"reference": ref, "candidate": cand},
        "reference": {k: sum(p[k] for p in ref)
                      for k in ("low", "medium", "high")},
        "candidate": {k: sum(p[k] for p in cand)
                      for k in ("low", "medium", "high")},
        "boundary_edge_audit": {
            "method": "world_space_quantized_triangle_edge_incidence_v1",
            "fully_watertight_proven": False,
            "hole_locations_verified": False, "internal_voids_verified": False,
            "parts": {
                "reference": edges(ref), "candidate": edges(cand),
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


class MultiCandidateTests(unittest.TestCase):
    def setUp(self):
        self.reports = {
            trial: report(trial)
            for trial in ("narrow", *CANDIDATES)
        }

    def test_actual_three_candidate_acceptance_and_rejection(self):
        result = build_multi_iteration_history(self.reports)
        self.assertEqual(result["attempts_executed"], 3)
        self.assertEqual([x["accepted"] for x in result["attempts"]],
                         [False, False, True])
        self.assertEqual(
            [x["decision"] for x in result["attempts"]],
            [
                "socket_not_improved",
                "unrelated_part_regression",
                "strict_sampled_socket_improvement_no_observed_regression",
            ],
        )
        self.assertEqual(
            [x["accepted_baseline_before"] for x in result["attempts"]],
            ["narrow", "narrow", "narrow"],
        )
        self.assertEqual(result["accepted_candidate_id"], "identical")
        self.assertEqual(result["stop_reason"],
                         "sampled_zero_without_other_part_regression")
        self.assertEqual(result["final_observations"], {
            "socket_sampled_affected_faces": 0,
            "other_parts_sampled_affected_faces": 0,
        })
        self.assertFalse(any(result["safety"].values()))
        sheet = render_multi_iteration_markdown(result)
        self.assertIn("棄却（ソケット改善なし）", sheet)
        self.assertIn("棄却（他部品が悪化）", sheet)
        self.assertIn("採用（合成モデル限定）", sheet)
        self.assertIn("実アドオンに設定値を適用しない", sheet)

    def test_budget_exhaustion_preserves_original_baseline(self):
        for budget in (1, 2):
            inputs = {
                k: self.reports[k]
                for k in ("narrow", *CANDIDATES[:budget])
            }
            result = build_multi_iteration_history(inputs,
                                                   attempt_budget=budget)
            self.assertEqual(result["attempts_executed"], budget)
            self.assertEqual(result["stop_reason"], "attempt_budget_exhausted")
            self.assertEqual(result["accepted_candidate_id"], "narrow")
            self.assertTrue(all(not row["accepted"] for row in result["attempts"]))
            self.assertIn("attempt_budget_exhausted",
                          render_multi_iteration_markdown(result))

    def test_malformed_budget_or_unknown_trial_rejected(self):
        for budget in (0, 4, True, 2.5, "3"):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                build_multi_iteration_history(self.reports,
                                              attempt_budget=budget)
        for inputs in (
            {}, {"narrow": self.reports["narrow"]},
            {**self.reports, "other": self.reports["identical"]},
        ):
            with self.assertRaises(ValueError):
                build_multi_iteration_history(inputs)

    def test_cross_part_regression_not_mistaken_for_improvement(self):
        data = copy.deepcopy(self.reports)
        data["shifted"]["parts"]["candidate"][0]["high"] = 0
        data["shifted"]["parts"]["candidate"][0]["low"] = 8
        data["shifted"]["candidate"]["high"] = 0
        with self.assertRaises(ValueError):
            build_multi_iteration_history(data)

    def test_spurious_restore_or_unsafe_glb020_report_rejected(self):
        for kind in ("narrow_placebo", "shifted", "identical"):
            broken = copy.deepcopy(self.reports)
            broken[kind]["safety"]["executes_addon_code"] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                build_multi_iteration_history(broken)
        broken = copy.deepcopy(self.reports)
        broken["identical"]["parts"]["candidate"][2]["medium"] = 4
        broken["identical"]["parts"]["candidate"][2]["low"] = 92
        broken["identical"]["candidate"]["medium"] = 4
        with self.assertRaises(ValueError):
            build_multi_iteration_history(broken)

    def test_forged_history_cannot_be_printed_or_written(self):
        data = build_multi_iteration_history(self.reports)
        cases = []
        for mutate in (
            lambda x: x["attempts"][0].__setitem__("accepted", True),
            lambda x: x["attempts"][1].__setitem__(
                "decision", "strict_sampled_socket_improvement_no_observed_regression"),
            lambda x: x["attempts"][2]["synthetic_controls"].__setitem__(
                "socket_opening_diameter", 10),
            lambda x: x["attempts"][0].__setitem__(
                "candidate_id", "private_addon.py"),
            lambda x: x["safety"].__setitem__("runs_user_addons", True),
            lambda x: x.__setitem__("stop_reason", "unverified_success"),
        ):
            item = copy.deepcopy(data)
            mutate(item)
            cases.append(item)
        for idx, item in enumerate(cases):
            with self.subTest(idx=idx), self.assertRaises(ValueError):
                render_multi_iteration_markdown(item)
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):
                    write_multi_iteration_history(item, folder)

    def test_local_files_new_and_source_free(self):
        data = build_multi_iteration_history(self.reports)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = write_multi_iteration_history(data, root)
            self.assertEqual(json.loads(files[0].read_text("utf-8")), data)
            self.assertIn("他部品が悪化", files[1].read_text("utf-8"))
            for private_text in ("private.blend", "Mesh.001", "private_addon.py"):
                self.assertNotIn(private_text, files[0].read_text("utf-8"))
                self.assertNotIn(private_text, files[1].read_text("utf-8"))
            with self.assertRaises(FileExistsError):
                write_multi_iteration_history(data, root)


if __name__ == "__main__":
    unittest.main()
