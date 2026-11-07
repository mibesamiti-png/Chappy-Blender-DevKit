"""GLB-022: continuous sampled-max improvements, synthetic fixtures only."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from cbdk.glb_synthetic_progress import (
    BASELINE, CANDIDATES, build_synthetic_progress,
    render_synthetic_progress, write_synthetic_progress,
)


def review(variant):
    base_parts = [
        {"part_id": f"part_{i:03d}", "triangle_count": n,
         "low": n, "medium": 0, "high": 0}
        for i, n in enumerate((8, 48, 96), 1)
    ]
    candidate = copy.deepcopy(base_parts)
    if variant == "narrow":
        diameter_distance, socket_faces, ball_faces, diagonal = 0.4600, 24, 0, 6.0
    elif variant == "narrow_mid_shifted":
        diameter_distance, socket_faces, ball_faces, diagonal = 1.100, 24, 6, 7.0
    elif variant == "narrow_mid":
        # The yellow/red face count does not change; the max sampled distance does.
        diameter_distance, socket_faces, ball_faces, diagonal = 0.2300, 24, 0, 6.0
    elif variant == "identical":
        diameter_distance, socket_faces, ball_faces, diagonal = 0.0, 0, 0, 6.0
    else:
        raise ValueError("unknown synthetic test condition")
    candidate[2]["medium"] = socket_faces
    candidate[2]["low"] -= socket_faces
    candidate[0]["high"] = ball_faces
    candidate[0]["low"] -= ball_faces

    def edges(rows):
        return [
            {"part_id": item["part_id"], "triangle_count": item["triangle_count"],
             "boundary_edges": 0, "observed_boundary": False,
             "topology_proven": False}
            for item in rows
        ]

    return {
        "kind": "cbdk_glb_diff_visualization", "schema_version": 1,
        "status": "review_only", "auto_apply": False, "sampled_only": True,
        "complete_surface_equivalence_proven": False,
        "cross_file_part_identity_proven": False,
        "viewer_contains_derived_geometry": True, "viewer_local_only": True,
        "safety": {
            "executes_addon_code": False, "uploads_private_glb": False,
            "saves_raw_mesh_vertices_in_json": False, "changes_source_glbs": False,
        },
        "parts": {"reference": base_parts, "candidate": candidate},
        "reference": {k: sum(p[k] for p in base_parts)
                      for k in ("low", "medium", "high")},
        "candidate": {k: sum(p[k] for p in candidate)
                      for k in ("low", "medium", "high")},
        "boundary_edge_audit": {
            "method": "world_space_quantized_triangle_edge_incidence_v1",
            "fully_watertight_proven": False,
            "hole_locations_verified": False, "internal_voids_verified": False,
            "parts": {
                "reference": edges(base_parts), "candidate": edges(candidate),
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
                {"reference_part_id": f"part_{i:03d}", "status": "suggested",
                 "candidate_part_ids": [f"part_{i:03d}"],
                 "topology_review_required": False}
                for i in range(1, 4)
            ],
        },
        "reference_sampled_max": diameter_distance,
        "candidate_sampled_max": diameter_distance,
        "thresholds": {"combined_aabb_diagonal": diagonal},
    }


class SyntheticProgressTests(unittest.TestCase):
    def setUp(self):
        self.reports = {name: review(name) for name in
                        (BASELINE, *CANDIDATES)}

    def test_intermediate_progress_accepted_even_same_colored_face_count(self):
        h = build_synthetic_progress(self.reports)
        self.assertEqual([row["accepted"] for row in h["attempts"]],
                         [False, True, True])
        self.assertEqual([row["baseline_before"] for row in h["attempts"]],
                         ["narrow", "narrow", "narrow_mid"])
        self.assertEqual(h["attempts"][1]["socket_faces_before"], 24)
        self.assertEqual(h["attempts"][1]["socket_faces_candidate"], 24)
        self.assertLess(h["attempts"][1]["sampled_max_candidate"],
                        h["attempts"][1]["sampled_max_before"])
        self.assertEqual(h["attempts"][0]["decision"], "other_part_regression")
        self.assertEqual(h["accepted_trial_id"], "identical")
        self.assertEqual(h["stop_reason"], "observed_sampled_zero")
        self.assertEqual(h["final_sampled_max"], 0)
        self.assertFalse(any(h["safety"].values()))
        md = render_synthetic_progress(h)
        self.assertIn("段階的改善", md)
        self.assertIn("厳密な", md)

    def test_budget_one_stops_unfixed_and_budget_two_keeps_partial(self):
        for budget, expected in ((1, "narrow"), (2, "narrow_mid")):
            inp = {
                k: self.reports[k] for k in (BASELINE, *CANDIDATES[:budget])
            }
            h = build_synthetic_progress(inp, attempt_budget=budget)
            self.assertEqual(h["accepted_trial_id"], expected)
            self.assertEqual(h["stop_reason"], "attempt_budget_exhausted")
            self.assertEqual(len(h["attempts"]), budget)
            self.assertIn("attempt_budget_exhausted",
                          render_synthetic_progress(h))

    def test_missing_scale_and_bad_metric_fail_closed(self):
        for wrong in (float("nan"), float("inf"), -1.0, True, "0.2"):
            case = copy.deepcopy(self.reports)
            case["narrow"]["reference_sampled_max"] = wrong
            with self.subTest(wrong=str(wrong)), self.assertRaises(ValueError):
                build_synthetic_progress(case)
        case = copy.deepcopy(self.reports)
        case["narrow_mid"]["thresholds"]["combined_aabb_diagonal"] = 7.0
        with self.assertRaises(ValueError):
            build_synthetic_progress(case)

    def test_no_real_numeric_improvement_or_other_part_regression_rejected(self):
        case = copy.deepcopy(self.reports)
        case["narrow_mid"]["reference_sampled_max"] = 0.4600
        case["narrow_mid"]["candidate_sampled_max"] = 0.4600
        with self.assertRaises(ValueError):
            build_synthetic_progress(case)
        case = copy.deepcopy(self.reports)
        case["narrow_mid"]["parts"]["candidate"][0]["high"] = 1
        case["narrow_mid"]["parts"]["candidate"][0]["low"] -= 1
        case["narrow_mid"]["candidate"]["high"] = 1
        with self.assertRaises(ValueError):
            build_synthetic_progress(case)

    def test_unsafe_reports_budget_and_unknown_candidates_rejected(self):
        for budget in (0, 4, True, "3", 1.5):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                build_synthetic_progress(self.reports, attempt_budget=budget)
        with self.assertRaises(ValueError):
            build_synthetic_progress({**self.reports, "private_source.py": review("narrow")})
        case = copy.deepcopy(self.reports)
        case["narrow_mid"]["safety"]["executes_addon_code"] = True
        with self.assertRaises(Exception):
            build_synthetic_progress(case)

    def test_tampered_decision_and_history_rejected(self):
        original = build_synthetic_progress(self.reports)
        changes = []
        for edit in (
            lambda h: h["attempts"][0].__setitem__("accepted", True),
            lambda h: h["attempts"][1].__setitem__("decision", "bad"),
            lambda h: h["attempts"][0]["controls"].__setitem__(
                "synthetic_socket_diameter", 999),
            lambda h: h["attempts"][0].__setitem__("trial_id", "private.glb"),
            lambda h: h["safety"].__setitem__("runs_user_addons", True),
            lambda h: h.__setitem__("stop_reason", "guaranteed_equal"),
            lambda h: h["attempts"][2].__setitem__("sampled_max_candidate", float("nan")),
        ):
            h = copy.deepcopy(original)
            edit(h)
            changes.append(h)
        for i, h in enumerate(changes):
            with self.subTest(i=i), self.assertRaises(ValueError):
                render_synthetic_progress(h)

    def test_private_local_nonoverwrite_outputs(self):
        original = build_synthetic_progress(self.reports)
        with tempfile.TemporaryDirectory() as temp:
            paths = write_synthetic_progress(original, temp)
            self.assertEqual(json.loads(paths[0].read_text("utf-8")), original)
            self.assertIn("棄却（他部品悪化）", paths[1].read_text("utf-8"))
            for private in ("private_model.glb", "Mesh.001", "secret_addon.py"):
                self.assertNotIn(private, paths[0].read_text("utf-8"))
                self.assertNotIn(private, paths[1].read_text("utf-8"))
            with self.assertRaises(FileExistsError):
                write_synthetic_progress(original, temp)


if __name__ == "__main__":
    unittest.main()
