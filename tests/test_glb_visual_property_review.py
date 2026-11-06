"""GLB-021: strict, review-only linkage from aggregate GLB-020 to AST evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from cbdk.glb_property_map import PropertyMappingError
from cbdk.glb_visual_property_review import (
    build_visual_property_review, parse_role_labels, review_visual_file,
)


def part(index, size, *, medium=0, high=0):
    return {
        "part_id": f"part_{index:03d}",
        "triangle_count": size,
        "low": size - medium - high,
        "medium": medium,
        "high": high,
    }


def audit_part(row, boundary_edges=0):
    return {
        "part_id": row["part_id"],
        "triangle_count": row["triangle_count"],
        "boundary_edges": boundary_edges,
        "observed_boundary": boundary_edges > 0,
        "topology_proven": False,
    }


def sample_review(*, scenario="narrow"):
    left = [part(1, 8), part(2, 48), part(3, 96)]
    right = [part(1, 8), part(2, 48), part(3, 96)]
    open_count = 0
    if scenario == "narrow":
        right[2] = part(3, 96, medium=24, high=48)
    elif scenario == "shifted":
        right[0] = part(1, 8, high=8)
    elif scenario == "uncapped":
        right[2] = part(3, 94)
        open_count = 4
    elif scenario != "identical":
        raise ValueError("Unknown synthetic case")
    labels = {
        side: {key: sum(x[key] for x in rows) for key in ("low", "medium", "high")}
        for side, rows in (("reference", left), ("candidate", right))
    }
    return {
        "kind": "cbdk_glb_diff_visualization",
        "schema_version": 1,
        "status": "review_only",
        "sampled_only": True,
        "auto_apply": False,
        "complete_surface_equivalence_proven": False,
        "cross_file_part_identity_proven": False,
        "viewer_contains_derived_geometry": True,
        "viewer_local_only": True,
        "safety": {
            "executes_addon_code": False,
            "uploads_private_glb": False,
            "saves_raw_mesh_vertices_in_json": False,
            "changes_source_glbs": False,
        },
        "parts": {"reference": left, "candidate": right},
        **labels,
        "boundary_edge_audit": {
            "fully_watertight_proven": False,
            "hole_locations_verified": False,
            "internal_voids_verified": False,
            "parts": {
                "reference": [audit_part(p) for p in left],
                "candidate": [
                    audit_part(p, open_count if p["part_id"] == "part_003" else 0)
                    for p in right
                ],
            },
        },
        "part_match_candidates": {
            "status": "review_only",
            "cross_file_part_identity_proven": False,
            "auto_apply": False,
            "reference_parts": [
                {
                    "reference_part_id": p["part_id"],
                    "status": "ambiguous" if (open_count and i == 2) else "suggested",
                    "candidate_part_ids": [p["part_id"]],
                    "topology_review_required": bool(open_count and i == 2),
                }
                for i, p in enumerate(left)
            ],
        },
    }


class VisualPropertyReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "PRIVATE_joint_addon.py"
        self.source.write_text(
            "from bpy.props import FloatProperty\n"
            "class JointProps:\n"
            "    socket_opening_diameter: FloatProperty(default=123456789.123)\n"
            "    clearance: FloatProperty(default=0.2)\n"
            "    profile_shape: FloatProperty(default=0.01)\n"
            "    ball_diameter: FloatProperty(default=1.0)\n"
            "    part_location: FloatProperty(default=0.0)\n",
            encoding="utf-8",
        )

    def test_manually_labeled_socket_narrowing_yields_ast_hints_not_cause(self):
        result = build_visual_property_review(
            sample_review(), [self.source], roles={"part_003": "socket"},
        )
        self.assertEqual(result["link_kind"],
                         "glb020_visual_diff_to_ast_property_candidates_v1")
        self.assertEqual(result["recommendation_count"], 1)
        r = result["recommendations"][0]
        self.assertEqual(r["target"], "part_003")
        self.assertEqual(r["suspected_category"], "surface_or_boundary_change_unclassified")
        names = [x["candidate_family"] for x in r["exact_name_matches"]]
        self.assertIn("socket_opening_diameter", names)
        self.assertIn("clearance", names)
        self.assertTrue(all(m["requires_human_review"] for m in r["exact_name_matches"]))
        evidence = r["visual_observation"]
        self.assertEqual(evidence["observed_medium_faces"], 24)
        self.assertEqual(evidence["observed_high_faces"], 48)
        self.assertEqual(evidence["tentative_reference_part_id"], "part_003")
        self.assertEqual(evidence["manual_role_label"], "socket")
        self.assertIsNone(evidence["recommended_parameter_value"])
        self.assertFalse(evidence["geometry_effect_verified"])
        self.assertFalse(result["cause_and_effect_proven"])
        self.assertFalse(result["cross_file_part_identity_proven"])
        self.assertFalse(result["safety"]["source_executed"])
        encoded = json.dumps(result)
        self.assertNotIn("PRIVATE_joint_addon", encoded)
        self.assertNotIn("123456789.123", encoded)
        self.assertNotIn(str(self.root), encoded)

    def test_default_has_generic_hints_without_hallucinating_socket_role(self):
        result = build_visual_property_review(sample_review(), [self.source])
        row = result["recommendations"][0]
        self.assertIsNone(row["visual_observation"]["manual_role_label"])
        self.assertIsNone(row["visual_observation"]["recommended_parameter_value"])
        self.assertNotIn(
            "socket_opening_diameter",
            [x["candidate_family"] for x in row["exact_name_matches"]],
        )
        self.assertIn("profile_shape",
                      [x["candidate_family"] for x in row["exact_name_matches"]])

    def test_no_false_positive_on_identical_shapes(self):
        result = build_visual_property_review(sample_review(scenario="identical"),
                                              [self.source])
        self.assertEqual(result["recommendation_count"], 0)
        self.assertEqual(result["recommendations"], [])
        self.assertFalse(result["parameter_values_inferred"])

    def test_unmatched_boundary_still_requires_review_not_cause(self):
        result = build_visual_property_review(
            sample_review(scenario="uncapped"), [self.source],
            roles={"part_003": "socket"},
        )
        row = result["recommendations"][0]
        self.assertEqual(row["visual_observation"]["observed_boundary_edges"], 4)
        self.assertIsNone(row["visual_observation"]["tentative_reference_part_id"])
        self.assertFalse(row["candidate_cause_verified"])

    def test_shifted_ball_is_not_misclassified_as_diameter_change(self):
        result = build_visual_property_review(
            sample_review(scenario="shifted"), [self.source],
            roles={"part_001": "ball"},
        )
        row = result["recommendations"][0]
        self.assertEqual(row["target"], "part_001")
        self.assertEqual(row["suspected_category"],
                         "surface_or_boundary_change_unclassified")
        self.assertIn("ball_diameter",
                      [x["candidate_family"] for x in row["exact_name_matches"]])
        self.assertFalse(row["candidate_cause_verified"])

    def test_no_execution_even_if_source_has_top_level_side_effect(self):
        marker = self.root / "SHOULD_NOT_EXIST"
        self.source.write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed')\n"
            "from bpy.props import FloatProperty\n"
            "class Props:\n"
            "    socket_opening_diameter: FloatProperty(default=3)\n",
            encoding="utf-8",
        )
        build_visual_property_review(sample_review(), [self.source],
                                     roles={"part_003": "socket"})
        self.assertFalse(marker.exists())

    def test_bad_input_flags_counts_roles_and_claims_are_refused(self):
        base = sample_review()
        mutations = []
        for field, value in (
            ("kind", "other"), ("auto_apply", True),
            ("cross_file_part_identity_proven", True),
            ("sampled_only", False), ("viewer_local_only", False),
        ):
            v = copy.deepcopy(base)
            v[field] = value
            mutations.append(v)
        v = copy.deepcopy(base)
        v["parts"]["candidate"][2]["triangle_count"] = 95
        mutations.append(v)
        v = copy.deepcopy(base)
        v["parts"]["candidate"][2]["high"] = True
        mutations.append(v)
        v = copy.deepcopy(base)
        v["safety"]["executes_addon_code"] = True
        mutations.append(v)
        v = copy.deepcopy(base)
        v["part_match_candidates"]["reference_parts"][2]["topology_review_required"] = True
        mutations.append(v)
        v = copy.deepcopy(base)
        v["boundary_edge_audit"]["parts"]["candidate"][2]["observed_boundary"] = True
        mutations.append(v)
        for idx, changed in enumerate(mutations):
            with self.subTest(case=idx), self.assertRaises(PropertyMappingError):
                build_visual_property_review(changed, [self.source])
        for labels in (
            ["part_003=socket", "part_003=ball"],
            ["part_003=unknown"], ["bad=socket"],
            ["part_999=socket"], ["part_001=socket=ball"],
        ):
            with self.subTest(labels=labels), self.assertRaises(PropertyMappingError):
                parse_role_labels(labels)
        with self.assertRaises(PropertyMappingError):
            build_visual_property_review(base, [self.source],
                                         roles={"part_004": "ball"})

    def test_private_fresh_output_and_nonoverwrite(self):
        inp = self.root / "observation.json"
        inp.write_text(json.dumps(sample_review()), encoding="utf-8")
        output = "reports/latest/mapping_v1.json"
        old_source = self.source.read_bytes()
        old_input = inp.read_bytes()
        result = review_visual_file(
            inp, [self.source], output,
            role_labels=["part_003=socket"], root=self.root,
        )
        saved = self.root / output
        self.assertEqual(json.loads(saved.read_text("utf-8")), result)
        self.assertEqual(self.source.read_bytes(), old_source)
        self.assertEqual(inp.read_bytes(), old_input)
        with self.assertRaises(FileExistsError):
            review_visual_file(inp, [self.source], output,
                               role_labels=["part_003=socket"], root=self.root)
        with self.assertRaises(PropertyMappingError):
            review_visual_file(inp, [self.source], "../published.json",
                               root=self.root)

    def test_duplicate_key_json_rejected(self):
        file = self.root / "bad.json"
        content = json.dumps(sample_review())
        file.write_text(content[:-1] + ',"status":"review_only"}', "utf-8")
        with self.assertRaisesRegex(PropertyMappingError, "Duplicate"):
            review_visual_file(file, [self.source], root=self.root)


if __name__ == "__main__":
    unittest.main()
