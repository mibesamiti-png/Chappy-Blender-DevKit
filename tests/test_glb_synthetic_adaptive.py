"""Feedback-driven search branching and local-only history safety."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from cbdk.glb_synthetic_adaptive import (
    build_adaptive_history, next_candidate, trial_id,
    render_adaptive_history, write_adaptive_history,
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
        "blender_version": "4.5.15",
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


class AdaptiveSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.baseline=review(distance=0.46,socket_faces=24)
        # This is the expected replay of *measured* feedback:
        # 1.24 is above target -> try 1.47; it passes -> refine to 1.35;
        # it fails -> refine to 1.41.
        self.trials={
            "adaptive_124":review(distance=0.23,socket_faces=24),
            "adaptive_147":review(distance=0.115,socket_faces=12),
            "adaptive_135":review(distance=0.175,socket_faces=18),
            "adaptive_141":review(distance=0.145,socket_faces=15),
        }

    def test_adaptive_bracket_uses_observed_feedback(self):
        self.assertEqual(next_candidate(78,170),124)
        self.assertEqual(next_candidate(124,170),147)
        self.assertEqual(next_candidate(124,147),135)
        self.assertEqual(next_candidate(135,147),141)
        h=build_adaptive_history(self.baseline,self.trials)
        self.assertEqual([x["trial_id"] for x in h["steps"]],list(self.trials))
        self.assertEqual([x["target_met"] for x in h["steps"]],
                         [False,True,False,False])
        self.assertEqual(h["final_bracket"],[1.41,1.47])
        self.assertEqual(h["measured_feasible_trial_id"],"adaptive_147")
        self.assertEqual(h["best_observed_trial_id"],"adaptive_147")
        self.assertEqual(h["sampled_target_status"],"target_feasible_in_sampled_test")
        self.assertEqual(h["stop_reason"],"attempt_budget_exhausted")
        self.assertFalse(h["safety"]["real_addon_causality_proven"])
        md=render_adaptive_history(h)
        self.assertIn("より小さい値へ",md)
        self.assertIn("より大きい値へ",md)
        self.assertIn("実物の公差ではありません",md)

    def test_different_measured_result_changes_next_trial(self):
        altered={
            "adaptive_124":review(distance=0.05,socket_faces=10),
            "adaptive_101":review(distance=0.345,socket_faces=24),
            "adaptive_112":review(distance=0.29,socket_faces=22),
            "adaptive_118":review(distance=0.26,socket_faces=20),
        }
        h=build_adaptive_history(self.baseline,altered)
        self.assertEqual([x["trial_id"] for x in h["steps"]],list(altered))
        self.assertEqual(h["final_bracket"],[1.18,1.24])
        self.assertEqual(h["measured_feasible_trial_id"],"adaptive_124")
        self.assertNotEqual(list(altered),list(self.trials))
        self.assertIn("1.01",render_adaptive_history(h))

    def test_budget_limited_remains_honest(self):
        for budget in (1,2,3):
            part=dict(list(self.trials.items())[:budget])
            h=build_adaptive_history(self.baseline,part,budget=budget)
            self.assertEqual(h["attempts_executed"],budget)
            self.assertEqual(h["stop_reason"],"attempt_budget_exhausted")
            if budget==1:
                self.assertIsNone(h["measured_feasible_trial_id"])
                self.assertEqual(h["sampled_target_status"],
                                 "no_measured_feasible_candidate")
            else:
                self.assertEqual(h["measured_feasible_trial_id"],"adaptive_147")

    def test_unknown_values_out_of_order_and_safety_fail_closed(self):
        for value in (78,171,0,True,1.24,"124",float("nan")):
            with self.subTest(value=value),self.assertRaises(ValueError):
                trial_id(value)
        for inputs in ({"unknown":self.trials["adaptive_124"]},
                       {"adaptive_147":self.trials["adaptive_147"]},
                       dict(reversed(list(self.trials.items())))):
            with self.assertRaises(ValueError):
                build_adaptive_history(self.baseline,inputs,budget=len(inputs))
        for budget in (0,5,True,2.5,"4"):
            with self.assertRaises(ValueError):
                build_adaptive_history(self.baseline,self.trials,budget=budget)
        modified=copy.deepcopy(self.trials)
        modified["adaptive_135"]["safety"]["executes_addon_code"]=True
        with self.assertRaises(Exception):
            build_adaptive_history(self.baseline,modified)
        modified=copy.deepcopy(self.trials)
        modified["adaptive_135"]["parts"]["candidate"][0]["high"]=1
        modified["adaptive_135"]["parts"]["candidate"][0]["low"]-=1
        modified["adaptive_135"]["candidate"]["high"]=1
        with self.assertRaises(ValueError):
            build_adaptive_history(self.baseline,modified)

    def test_history_forgery_and_new_only_local_output(self):
        h=build_adaptive_history(self.baseline,self.trials)
        variants=[]
        for change in (
            lambda a:a["steps"][1].__setitem__("trial_id","secret.py"),
            lambda a:a["steps"][0].__setitem__("target_met",True),
            lambda a:a["steps"][0].__setitem__("accepted_as_measured_progress",False),
            lambda a:a["steps"][0].__setitem__("progress_reason","forged"),
            lambda a:a["steps"][1].__setitem__("sampled_max",0.23),
            lambda a:a["steps"][1].__setitem__("bracket_after",[1.24,1.70]),
            lambda a:a["safety"].__setitem__("real_addon_causality_proven",True),
            lambda a:a.__setitem__("sampled_target_status","verified_for_user"),
        ):
            modified=copy.deepcopy(h)
            change(modified)
            variants.append(modified)
        for i,bad in enumerate(variants):
            with self.subTest(i=i),self.assertRaises(ValueError):
                render_adaptive_history(bad)
        with tempfile.TemporaryDirectory() as temp:
            j,m=write_adaptive_history(h,temp)
            self.assertEqual(json.loads(j.read_text("utf-8")),h)
            self.assertEqual(m.read_text("utf-8"),render_adaptive_history(h))
            for text in ("secret.py","private.glb","Mesh.001"):
                self.assertNotIn(text,j.read_text("utf-8"))
                self.assertNotIn(text,m.read_text("utf-8"))
            with self.assertRaises(FileExistsError):
                write_adaptive_history(h,temp)

if __name__ == "__main__":
    unittest.main()
