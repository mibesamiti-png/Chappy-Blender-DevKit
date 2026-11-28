"""Bounded, review-only AST hints from Blender properties to geometry code."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbdk.glb_property_map import map_repair_plan_properties
from cbdk.glb_geometry_flow import trace_geometry_paths


def review_plan(*names):
    return {
        "schema_version": 1, "kind": "cbdk_glb_repair_plan",
        "status": "review_only", "recommendation_count": 1,
        "recommendations": [{
            "target": "Ball", "suspected_category": "part_size_parameter",
            "requires_human_parameter_mapping": True,
            "possible_parameter_families": list(names),
        }],
        "unmapped_difference_codes": [],
        "safety": {
            "edits_code": False, "applies_parameters": False,
            "runs_untrusted_addons": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
    }


class GLBGeometryFlowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def source(self, text, name="private_addon.py"):
        p = self.root / name
        p.write_text(text, encoding="utf-8")
        return p

    def inspect(self, source):
        report = map_repair_plan_properties(review_plan("ball_diameter"), [source])
        matches = report["recommendations"][0]["exact_name_matches"]
        self.assertEqual(len(matches), 1)
        return matches[0]["possible_geometry_dataflow"], report

    def test_direct_property_expression_to_mesh_primitive(self):
        file = self.source(
            "import bpy\n"
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_uv_sphere_add(radius=self.ball_diameter / 2)\n")
        evidence, report = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 1)
        self.assertEqual(evidence["operation_counts"], {"mesh_primitive": 1})
        self.assertEqual(evidence["examples"][0]["recognized_api"],
                         "bpy.ops.mesh.primitive_uv_sphere_add")
        self.assertEqual(evidence["examples"][0]["syntactic_path"], "direct_self_attribute")
        self.assertEqual(evidence["examples"][0]["line"], 6)
        self.assertFalse(evidence["geometry_effect_verified"])
        self.assertFalse(evidence["receiver_binding_verified"])
        self.assertEqual(report["static_possible_geometry_paths_found"], 1)
        self.assertFalse(report["recommendations"][0]["validated_geometry_effect"])

    def test_local_alias_to_cylinder_primitive(self):
        file = self.source(
            "import bpy as B\n"
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        radius = self.ball_diameter / 2\n"
            "        B.ops.mesh.primitive_cylinder_add(radius=radius)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 1)
        self.assertEqual(evidence["examples"][0]["syntactic_path"],
                         "straight_line_local_alias")

    def test_variable_reassignment_clears_alias_before_call(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        radius = self.ball_diameter\n"
            "        radius = 3\n"
            "        bpy.ops.mesh.primitive_cube_add(size=radius)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_transitive_straight_line_local_alias(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        a = self.ball_diameter\n"
            "        b = a / 2\n"
            "        bpy.ops.mesh.primitive_ico_sphere_add(radius=b)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 1)

    def test_bmesh_geometry_operator_is_recognized(self):
        file = self.source(
            "import bmesh as BM\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self, mesh):\n"
            "        BM.ops.bevel(mesh, offset=self.ball_diameter)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["operation_counts"], {"bmesh_geometry_operation": 1})
        self.assertEqual(evidence["examples"][0]["recognized_api"], "bmesh.ops.bevel")

    def test_object_dimensions_assignment_is_review_hint_only(self):
        file = self.source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self, obj):\n"
            "        obj.dimensions = (self.ball_diameter, 1, 1)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["operation_counts"], {"object_transform_assignment": 1})
        self.assertEqual(evidence["examples"][0]["recognized_api"], "object.dimensions")
        self.assertFalse(evidence["geometry_effect_verified"])

    def test_unrelated_api_in_same_function_is_not_a_link(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        print(self.ball_diameter)\n"
            "        bpy.ops.mesh.primitive_cube_add(size=1)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_unrelated_object_property_does_not_become_declared_self(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self, other):\n"
            "        bpy.ops.mesh.primitive_cube_add(size=other.ball_diameter)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_other_class_self_does_not_link(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "class Another:\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_no_bpy_import_does_not_count_fake_ops(self):
        file = self.source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_branch_control_flow_not_followed(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self, conditional):\n"
            "        if conditional:\n"
            "            radius = self.ball_diameter\n"
            "        bpy.ops.mesh.primitive_cube_add(size=radius)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_earlier_alias_invalidated_by_unsupported_branch(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self, conditional):\n"
            "        radius = self.ball_diameter\n"
            "        if conditional:\n            radius = 1\n"
            "        bpy.ops.mesh.primitive_cube_add(size=radius)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_nested_function_is_not_inlined(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        def helper():\n"
            "            bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n"
            "        return helper()\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_dynamic_call_name_is_not_guessed(self):
        file = self.source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self, f):\n"
            "        f(self.ball_diameter)\n")
        evidence, _ = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_provenance_is_anonymized_and_no_source_executed(self):
        marker = self.root / "must_not_exist"
        private_value = "PRIVATE_CUTTER_KEY_NOT_FOR_GITHUB"
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            f"open({str(marker)!r}, 'w').write('BAD')\n"
            "class Settings:\n"
            f"    ball_diameter: FloatProperty(description={private_value!r})\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n")
        evidence, report = self.inspect(file)
        serialized = json.dumps(report)
        self.assertEqual(evidence["possible_path_count"], 1)
        self.assertFalse(marker.exists())
        self.assertNotIn(private_value, serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("private_addon.py", serialized)
        self.assertEqual(evidence["examples"][0]["source_label"], "source_1.py")
        self.assertFalse(report["safety"]["source_executed"])

    def test_examples_capped_total_not_lost(self):
        code = ("        bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n" * 16)
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self):\n" + code)
        evidence, report = self.inspect(file)
        self.assertEqual(evidence["possible_path_count"], 16)
        self.assertEqual(len(evidence["examples"]), 12)
        self.assertTrue(evidence["examples_truncated"])
        self.assertEqual(report["static_possible_geometry_paths_found"], 16)

    def test_property_is_not_invented_from_non_declared_name(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    another_field: FloatProperty()\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n")
        report = map_repair_plan_properties(review_plan("ball_diameter"), [file])
        self.assertEqual(report["static_possible_geometry_paths_found"], 0)
        self.assertFalse(report["recommendations"][0]["has_declared_name_match"])

    def test_cross_file_property_names_not_assumed_same_instance(self):
        a = self.source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n", "one.py")
        b = self.source(
            "import bpy\n"
            "class Settings:\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n", "two.py")
        report = map_repair_plan_properties(review_plan("ball_diameter"), [a, b])
        match = report["recommendations"][0]["exact_name_matches"][0]
        self.assertEqual(match["possible_geometry_dataflow"]["possible_path_count"], 0)

    def test_source_determinism(self):
        file = self.source(
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def build(self):\n"
            "        radius = self.ball_diameter / 2\n"
            "        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius)\n")
        first = map_repair_plan_properties(review_plan("ball_diameter"), [file])
        self.assertEqual(first, map_repair_plan_properties(review_plan("ball_diameter"), [file]))
        self.assertFalse(first["recommendations"][0]["exact_name_matches"][0]
                         ["possible_geometry_dataflow"]["geometry_effect_verified"])

    def test_direct_trace_requires_explicit_declaration_scope(self):
        file = self.source(
            "import bpy\nclass Settings:\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_cube_add(size=self.ball_diameter)\n")
        out = trace_geometry_paths([file], {})
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
