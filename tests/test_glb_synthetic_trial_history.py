"""GLB-021 review-only history of allowlisted synthetic socket experiments."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from cbdk.glb_synthetic_trial_history import (
    build_synthetic_trial_history, render_synthetic_trial_history,
    write_synthetic_trial_history,
)


def make_review(kind):
    medium = 15 if kind in ("narrow", "narrow_placebo") else 0
    moved = 5 if kind == "narrow_placebo" else 0
    r = [
        dict(part_id=f"part_{i:03d}", triangle_count=n,
             low=n, medium=0, high=0)
        for i, n in enumerate((8, 48, 96), 1)
    ]
    c = copy.deepcopy(r)
    c[2]["medium"] = medium
    c[2]["low"] -= medium
    c[0]["high"] = moved
    c[0]["low"] -= moved

    def edge(part):
        return dict(part_id=part["part_id"], triangle_count=part["triangle_count"],
                    boundary_edges=0, observed_boundary=False,
                    topology_proven=False)

    return dict(
        kind="cbdk_glb_diff_visualization", schema_version=1,
        status="review_only", auto_apply=False, sampled_only=True,
        complete_surface_equivalence_proven=False,
        cross_file_part_identity_proven=False,
        viewer_contains_derived_geometry=True, viewer_local_only=True,
        safety=dict(executes_addon_code=False, uploads_private_glb=False,
                    saves_raw_mesh_vertices_in_json=False,
                    changes_source_glbs=False),
        parts=dict(reference=r, candidate=c),
        reference={k: sum(p[k] for p in r) for k in ("low", "medium", "high")},
        candidate={k: sum(p[k] for p in c) for k in ("low", "medium", "high")},
        boundary_edge_audit=dict(
            method="world_space_quantized_triangle_edge_incidence_v1",
            fully_watertight_proven=False,
            hole_locations_verified=False, internal_voids_verified=False,
            parts=dict(reference=[edge(p) for p in r],
                       candidate=[edge(p) for p in c])),
        sampling_sensitivity_audit=dict(
            method="extra_halton_24_probe_sensitivity_v1",
            unobserved_regions_verified=False,
            complete_surface_equivalence_proven=False),
        part_match_candidates=dict(
            status="review_only", auto_apply=False,
            cross_file_part_identity_proven=False,
            reference_parts=[
                dict(reference_part_id=f"part_{i:03d}", status="suggested",
                     candidate_part_ids=[f"part_{i:03d}"],
                     topology_review_required=False) for i in range(1, 4)]),
    )


class TrialHistoryTests(unittest.TestCase):
    def setUp(self):
        self.reports = {k: make_review(k)
                        for k in ("narrow", "narrow_placebo", "identical")}

    def test_ordered_trial_history_shows_repair_without_decoy_false_success(self):
        r = build_synthetic_trial_history(self.reports)
        self.assertEqual(r["kind"], "cbdk_glb021_synthetic_trial_history_v1")
        self.assertEqual(r["experiment_order"],
                         ["narrow", "narrow_placebo", "identical"])
        self.assertEqual([t["sampled_affected_faces_total"]
                          for t in r["trials"]], [15, 20, 0])
        self.assertEqual(r["comparison"]["socket_affected_faces_before"], 15)
        self.assertEqual(r["comparison"]["socket_affected_faces_after_restoration"], 0)
        self.assertEqual(r["comparison"]["socket_affected_faces_after_unrelated_change"], 15)
        self.assertTrue(r["comparison"]["unrelated_change_did_not_fix_socket"])
        self.assertFalse(r["safety"]["real_addon_causality_proven"])
        self.assertFalse(r["safety"]["parameter_value_recommended_to_user"])
        sheet = render_synthetic_trial_history(r)
        self.assertIn("ソケットの黄＋赤", sheet)
        self.assertIn("narrow_placebo", sheet)
        self.assertIn("15 | 5 |", sheet)
        self.assertIn("実際のアドオンの修正提案ではありません", sheet)

    def test_negative_controls_and_invalid_repair_rejected(self):
        mutations = []
        bad = copy.deepcopy(self.reports)
        bad["narrow_placebo"]["parts"]["candidate"][2]["medium"] = 0
        bad["narrow_placebo"]["parts"]["candidate"][2]["low"] = 96
        bad["narrow_placebo"]["candidate"]["medium"] = 0
        mutations.append(bad)
        bad = copy.deepcopy(self.reports)
        bad["identical"]["parts"]["candidate"][2]["medium"] = 1
        bad["identical"]["parts"]["candidate"][2]["low"] = 95
        bad["identical"]["candidate"]["medium"] = 1
        mutations.append(bad)
        bad = copy.deepcopy(self.reports)
        bad["narrow"]["parts"]["candidate"][1]["high"] = 1
        bad["narrow"]["parts"]["candidate"][1]["low"] -= 1
        bad["narrow"]["candidate"]["high"] = 1
        mutations.append(bad)
        bad = copy.deepcopy(self.reports)
        bad["narrow"]["parts"]["candidate"][2]["triangle_count"] = 97
        mutations.append(bad)
        bad = copy.deepcopy(self.reports)
        bad["identical"]["safety"]["executes_addon_code"] = True
        mutations.append(bad)
        bad = copy.deepcopy(self.reports)
        bad["narrow"]["parts"]["candidate"][2]["high"] = True
        mutations.append(bad)
        for idx, data in enumerate(mutations):
            with self.subTest(idx=idx), self.assertRaises((ValueError, TypeError)):
                build_synthetic_trial_history(data)

    def test_only_exact_allowlisted_trials_accepted(self):
        for reports in ({}, {"narrow": self.reports["narrow"]},
                        {**self.reports, "other": self.reports["narrow"]}):
            with self.assertRaises(ValueError):
                build_synthetic_trial_history(reports)

    def test_local_files_are_fresh_and_contain_no_private_input_metadata(self):
        history = build_synthetic_trial_history(self.reports)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = write_synthetic_trial_history(history, root)
            self.assertTrue(all(p.is_file() for p in paths))
            self.assertEqual(json.loads(paths[0].read_text("utf-8")), history)
            self.assertEqual(paths[1].read_text("utf-8"),
                             render_synthetic_trial_history(history))
            for source in ("private_joe_addon", "Mesh.001", "/home/users/",
                           "candidate_diff.glb", "source_1.py"):
                self.assertNotIn(source, paths[0].read_text("utf-8"))
                self.assertNotIn(source, paths[1].read_text("utf-8"))
            with self.assertRaises(FileExistsError):
                write_synthetic_trial_history(history, root)

    def test_unsafe_or_injected_history_cannot_be_rendered_or_written(self):
        history = build_synthetic_trial_history(self.reports)
        cases = []
        x = copy.deepcopy(history)
        x["safety"]["real_addon_causality_proven"] = True
        cases.append(x)
        x = copy.deepcopy(history)
        x["trials"][1]["trial_id"] = "arbitrary_private_source_name"
        cases.append(x)
        x = copy.deepcopy(history)
        x["trials"][0]["allowlisted_fixture_controls"]["socket_opening_diameter"] = 9.99
        cases.append(x)
        for idx, invalid in enumerate(cases):
            with self.subTest(idx=idx):
                with self.assertRaises(ValueError):
                    render_synthetic_trial_history(invalid)
                with tempfile.TemporaryDirectory() as temp:
                    with self.assertRaises(ValueError):
                        write_synthetic_trial_history(invalid, temp)


if __name__ == "__main__":
    unittest.main()
