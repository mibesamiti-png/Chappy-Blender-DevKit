"""GLB-022: arithmetic candidate generation and conservative grid selection."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from cbdk.glb_synthetic_grid import (
    build_grid_history, candidate_values, render_grid_history,
    trial_id, write_grid_history,
)


def review(*, distance, socket_faces, ball_faces=0, scale=6.0):
    sizes = (8, 48, 96)
    ref = [
        {"part_id": f"part_{i:03d}", "triangle_count": n,
         "low": n, "medium": 0, "high": 0}
        for i, n in enumerate(sizes, 1)
    ]
    cand = copy.deepcopy(ref)
    cand[2]["medium"] = socket_faces
    cand[2]["low"] -= socket_faces
    cand[0]["high"] = ball_faces
    cand[0]["low"] -= ball_faces

    def edges(parts):
        return [{
            "part_id": row["part_id"],
            "triangle_count": row["triangle_count"], "boundary_edges": 0,
            "observed_boundary": False, "topology_proven": False,
        } for row in parts]

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
        "reference": {k: sum(row[k] for row in ref)
                      for k in ("low", "medium", "high")},
        "candidate": {k: sum(row[k] for row in cand)
                      for k in ("low", "medium", "high")},
        "boundary_edge_audit": {
            "method": "world_space_quantized_triangle_edge_incidence_v1",
            "fully_watertight_proven": False,
            "hole_locations_verified": False, "internal_voids_verified": False,
            "parts": {"reference": edges(ref), "candidate": edges(cand)},
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
                {"reference_part_id": f"part_{i:03d}", "status": "suggested",
                 "candidate_part_ids": [f"part_{i:03d}"],
                 "topology_review_required": False}
                for i in range(1, 4)
            ],
        },
        "reference_sampled_max": distance,
        "candidate_sampled_max": distance,
        "thresholds": {"combined_aabb_diagonal": scale},
    }


class GeneratedGridTests(unittest.TestCase):
    def setUp(self):
        self.base = review(distance=0.46, socket_faces=24)
        self.trials = {
            trial_id(1.01): review(distance=0.345, socket_faces=24),
            trial_id(1.24): review(distance=0.23, socket_faces=24),
            trial_id(1.47): review(distance=0.115, socket_faces=12),
            trial_id(1.70): review(distance=0, socket_faces=0),
        }

    def test_numeric_candidates_are_computed_in_bounded_grid(self):
        self.assertEqual(candidate_values(), (1.01, 1.24, 1.47, 1.7))
        self.assertEqual([trial_id(x) for x in candidate_values()],
                         ["grid_101", "grid_124", "grid_147", "grid_170"])
        for invalid in (0.78, 0.99, 1.02, 2.5, "1.24", True, float("nan")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                trial_id(invalid)

    def test_four_improving_candidates_and_stop_at_sampled_zero(self):
        h = build_grid_history(self.base, self.trials)
        self.assertEqual(h["attempt_budget"], 4)
        self.assertEqual([x["generated_socket_diameter"] for x in h["attempts"]],
                         list(candidate_values()))
        self.assertEqual([x["accepted"] for x in h["attempts"]],
                         [True, True, True, True])
        self.assertEqual(h["accepted_trial_id"], "grid_170")
        self.assertEqual(h["stop_reason"], "observed_sampled_zero")
        self.assertEqual(h["final_sampled_max"], 0)
        self.assertFalse(h["safety"]["real_addon_causality_proven"])
        sheet = render_grid_history(h)
        self.assertIn("自動生成", sheet)
        self.assertIn("1.24", sheet)
        self.assertIn("実ユーザーアドオンの設定変更", sheet)

    def test_stalled_candidate_rejected_without_baseline_replacement(self):
        modified = copy.deepcopy(self.trials)
        modified["grid_124"]["reference_sampled_max"] = 0.345
        modified["grid_124"]["candidate_sampled_max"] = 0.345
        h = build_grid_history(self.base, modified)
        self.assertEqual([x["accepted"] for x in h["attempts"]],
                         [True, False, True, True])
        self.assertEqual(h["attempts"][1]["baseline_after"], "grid_101")
        self.assertEqual(h["attempts"][2]["baseline_before"], "grid_101")
        self.assertIn("棄却", render_grid_history(h))

    def test_trial_budget_one_two_three_remains_unfinished(self):
        for budget in (1, 2, 3):
            data = dict(list(self.trials.items())[:budget])
            h = build_grid_history(self.base, data, budget=budget)
            self.assertEqual(len(h["attempts"]), budget)
            self.assertEqual(h["stop_reason"],
                             "attempt_budget_exhausted_unfinished")
            self.assertGreater(h["final_sampled_max"], 0)
            self.assertIn("未完了", render_grid_history(h))

    def test_unsafe_input_or_changed_scene_scale_rejected(self):
        for wrong in (True, 0, 5, 1.2, "4"):
            with self.subTest(budget=wrong), self.assertRaises(ValueError):
                build_grid_history(self.base, self.trials, budget=wrong)
        bad = copy.deepcopy(self.trials)
        bad["grid_101"]["safety"]["executes_addon_code"] = True
        with self.assertRaises(Exception):
            build_grid_history(self.base, bad)
        bad = copy.deepcopy(self.trials)
        bad["grid_124"]["thresholds"]["combined_aabb_diagonal"] = 10
        with self.assertRaises(ValueError):
            build_grid_history(self.base, bad)
        bad = copy.deepcopy(self.trials)
        bad["grid_147"]["parts"]["candidate"][0]["high"] = 1
        bad["grid_147"]["parts"]["candidate"][0]["low"] = 7
        bad["grid_147"]["candidate"]["high"] = 1
        with self.assertRaises(ValueError):
            build_grid_history(self.base, bad)
        with self.assertRaises(ValueError):
            build_grid_history(self.base, {"private_model": self.base})
        bad = copy.deepcopy(self.trials)
        bad["grid_170"]["reference_sampled_max"] = 0.01
        with self.assertRaises(ValueError):
            build_grid_history(self.base, bad)

    def test_tampered_report_flags_names_decisions_not_publishable(self):
        report = build_grid_history(self.base, self.trials)
        mutated = []
        for edit in (
            lambda x: x["safety"].__setitem__("real_addon_causality_proven", True),
            lambda x: x["attempts"][0].__setitem__("accepted", False),
            lambda x: x["attempts"][1].__setitem__("trial_id", "private_addon.py"),
            lambda x: x["attempts"][2].__setitem__("generated_socket_diameter", 9.99),
            lambda x: x.__setitem__("stop_reason", "success_guaranteed"),
            lambda x: x["attempts"][1].__setitem__("max_sampled_candidate", float("nan")),
        ):
            x = copy.deepcopy(report)
            edit(x)
            mutated.append(x)
        for index, bad in enumerate(mutated):
            with self.subTest(index=index), self.assertRaises(ValueError):
                render_grid_history(bad)

    def test_local_json_markdown_new_files_only(self):
        report = build_grid_history(self.base, self.trials)
        with tempfile.TemporaryDirectory() as temporary:
            paths = write_grid_history(report, temporary)
            self.assertEqual(json.loads(paths[0].read_text("utf-8")), report)
            self.assertIn("1.47", paths[1].read_text("utf-8"))
            for private in ("private.glb", "Mesh.001", "personal_addon.py"):
                self.assertNotIn(private, paths[0].read_text("utf-8"))
                self.assertNotIn(private, paths[1].read_text("utf-8"))
            with self.assertRaises(FileExistsError):
                write_grid_history(report, temporary)


if __name__ == "__main__":
    unittest.main()
