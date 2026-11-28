"""Bidirectional focus: missing candidate evidence is never a clean reference."""
import copy
import unittest

from cbdk.glb_debug_focus import build_debug_focus, validate_debug_focus
from test_glb_synthetic_adaptive import review


class DebugFocusTests(unittest.TestCase):
    def setUp(self):
        self.visual = review(distance=.46, socket_faces=24)

    def set_counts(self, side, index, *, medium=0, high=0):
        row = self.visual["parts"][side][index]
        row.update(medium=medium, high=high, low=row["triangle_count"] - medium - high)
        self.visual[side] = {k: sum(r[k] for r in self.visual["parts"][side])
                             for k in ("low", "medium", "high")}

    def test_baseline_targets_socket_and_preserves_healthy_observations(self):
        focus = build_debug_focus(self.visual)
        self.assertEqual(validate_debug_focus(focus), focus)
        self.assertEqual([(r["side"], r["part_id"]) for r in focus["focus"]], [("candidate", "part_003")])
        self.assertEqual(len(focus["no_observed_change_parts"]), 5)
        self.assertFalse(any(focus["safety"].values()))

    def test_reference_only_difference_survives(self):
        self.set_counts("candidate", 2)
        self.set_counts("reference", 2, high=12)
        focus = build_debug_focus(self.visual)["focus"]
        self.assertEqual([(r["side"], r["part_id"]) for r in focus], [("reference", "part_003")])

    def test_small_severe_part_precedes_large_low_fraction_part(self):
        self.set_counts("candidate", 0, high=4)
        self.set_counts("candidate", 2, high=12)
        focus = build_debug_focus(self.visual)["focus"]
        self.assertEqual([r["part_id"] for r in focus], ["part_001", "part_003"])
        self.assertEqual(focus[0]["observed_affected_fraction"], .5)

    def test_equal_open_boundaries_are_not_a_proven_difference(self):
        self.set_counts("candidate", 2)
        for side in ("reference", "candidate"):
            self.visual["boundary_edge_audit"]["parts"][side][2].update(boundary_edges=3, observed_boundary=True)
        self.assertEqual(build_debug_focus(self.visual)["focus"], [])

    def test_ambiguous_boundary_is_an_unpaired_observation(self):
        self.set_counts("candidate", 2)
        self.visual["boundary_edge_audit"]["parts"]["candidate"][2].update(boundary_edges=3, observed_boundary=True)
        match = self.visual["part_match_candidates"]["reference_parts"][2]
        match.update(status="ambiguous", topology_review_required=True)
        row = build_debug_focus(self.visual)["focus"][0]
        self.assertIsNone(row["tentative_peer"])
        self.assertEqual(row["reasons"], ["unpaired_boundary_observation"])

    def test_reordered_pair_does_not_assume_equal_part_ids(self):
        matches = self.visual["part_match_candidates"]["reference_parts"]
        matches[0]["candidate_part_ids"] = ["part_003"]
        matches[2]["candidate_part_ids"] = ["part_001"]
        row = build_debug_focus(self.visual)["focus"][0]
        self.assertEqual(row["part_id"], "part_003")
        self.assertEqual(row["tentative_peer"], "part_001")

    def test_saved_focus_rejects_forged_priority_types_or_geometry(self):
        good = build_debug_focus(self.visual)
        for change in (
            lambda r: r["focus"][0].update(observed_affected_fraction=1),
            lambda r: r["safety"].update(part_identity_proven=True),
            lambda r: r["observations"]["candidate"][2].update(high=True),
            lambda r: r["observations"]["candidate"][2].update(tentative_peer="part_001"),
            lambda r: r.update(raw_vertices=[]),
        ):
            bad = copy.deepcopy(good); change(bad)
            with self.assertRaises(ValueError):
                validate_debug_focus(bad)

    def test_original_observations_are_unchanged(self):
        before = copy.deepcopy(self.visual)
        build_debug_focus(self.visual)
        self.assertEqual(self.visual, before)

    def test_boolean_schema_is_not_a_version_number(self):
        self.visual["schema_version"] = True
        with self.assertRaises(ValueError):
            build_debug_focus(self.visual)
