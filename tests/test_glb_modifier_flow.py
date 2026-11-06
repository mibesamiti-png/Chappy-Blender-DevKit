"""Modifier assignment hints in GLB-010: AST-only, never runtime proof."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cbdk.glb_geometry_flow import trace_geometry_paths


class ModifierGeometryFlowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def trace(self, body, *, imports="from bpy.props import FloatProperty\n",
              name="wall_thickness"):
        source = self.directory / "private_addon.py"
        source.write_text(
            imports +
            "class Settings:\n"
            f"    {name}: FloatProperty()\n"
            "    def build(self, modifier):\n" +
            body, encoding="utf-8")
        return trace_geometry_paths([source], {("source_1.py", "Settings"): {name}})[name]

    def test_solidify_thickness_direct(self):
        evidence = self.trace("        modifier.thickness = self.wall_thickness\n")
        self.assertEqual(evidence["possible_path_count"], 1)
        self.assertEqual(evidence["operation_counts"],
                         {"possible_modifier_setting_assignment": 1})
        self.assertEqual(evidence["examples"][0]["recognized_api"], "modifier.thickness")
        self.assertEqual(evidence["examples"][0]["syntactic_path"], "direct_self_attribute")
        self.assertFalse(evidence["geometry_effect_verified"])

    def test_bevel_width_through_local_alias(self):
        evidence = self.trace(
            "        offset = self.wall_thickness / 2\n"
            "        modifier.width = offset\n")
        self.assertEqual(evidence["examples"][0]["recognized_api"], "modifier.width")
        self.assertEqual(evidence["examples"][0]["syntactic_path"],
                         "straight_line_local_alias")

    def test_boolean_cutter_object_is_only_a_hint(self):
        evidence = self.trace("        modifier.object = self.wall_thickness\n")
        self.assertEqual(evidence["examples"][0]["recognized_api"], "modifier.object")
        self.assertFalse(evidence["receiver_binding_verified"])

    def test_boolean_operation_assignment(self):
        evidence = self.trace("        modifier.operation = self.wall_thickness\n")
        self.assertEqual(evidence["examples"][0]["recognized_api"], "modifier.operation")

    def test_modifier_segments_and_levels(self):
        evidence = self.trace(
            "        modifier.segments = self.wall_thickness\n"
            "        modifier.levels = self.wall_thickness\n")
        self.assertEqual(evidence["possible_path_count"], 2)

    def test_modifier_compound_assignment(self):
        evidence = self.trace("        modifier.thickness += self.wall_thickness\n")
        self.assertEqual(evidence["possible_path_count"], 1)
        self.assertEqual(evidence["examples"][0]["recognized_api"], "modifier.thickness")

    def test_unknown_attribute_does_not_claim_modifier(self):
        evidence = self.trace("        modifier.custom_unknown = self.wall_thickness\n")
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_cooccurrence_is_not_a_dataflow(self):
        evidence = self.trace(
            "        print(self.wall_thickness)\n"
            "        modifier.thickness = 1.0\n")
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_unrelated_receiver_property_not_declared_self(self):
        evidence = self.trace("        modifier.thickness = other.wall_thickness\n")
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_reassignment_invalidates_stale_alias(self):
        evidence = self.trace(
            "        thickness = self.wall_thickness\n"
            "        thickness = 0.5\n"
            "        modifier.thickness = thickness\n")
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_augmented_local_alias_still_traces(self):
        evidence = self.trace(
            "        t = self.wall_thickness\n"
            "        t += 1.0\n"
            "        modifier.thickness = t\n")
        self.assertEqual(evidence["possible_path_count"], 1)

    def test_branches_not_followed(self):
        evidence = self.trace(
            "        if True:\n"
            "            modifier.thickness = self.wall_thickness\n")
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_functions_are_not_followed(self):
        evidence = self.trace(
            "        def helper():\n"
            "            modifier.thickness = self.wall_thickness\n"
            "        helper()\n")
        self.assertEqual(evidence["possible_path_count"], 0)

    def test_no_private_value_or_path_is_emitted(self):
        marker = self.directory / "SHOULD_NOT_EXIST"
        source = self.directory / "private_addon.py"
        source.write_text(
            "from bpy.props import FloatProperty\n"
            f"open({str(marker)!r}, 'w').write('PRIVATE_SECRET')\n"
            "class Settings:\n"
            "    wall_thickness: FloatProperty()\n"
            "    def build(self, mod):\n"
            "        mod.thickness = self.wall_thickness\n",
            encoding="utf-8")
        evidence = trace_geometry_paths(
            [source], {("source_1.py", "Settings"): {"wall_thickness"}})
        text = str(evidence)
        self.assertFalse(marker.exists())
        self.assertNotIn("PRIVATE_SECRET", text)
        self.assertNotIn(str(self.directory), text)
        self.assertNotIn("private_addon.py", text)

    def test_not_a_geometry_proof_even_with_match(self):
        evidence = self.trace("        dummy.thickness = self.wall_thickness\n")
        self.assertEqual(evidence["possible_path_count"], 1)
        self.assertFalse(evidence["geometry_effect_verified"])
        self.assertEqual(evidence["examples"][0]["geometry_operation_category"],
                         "possible_modifier_setting_assignment")


if __name__ == "__main__":
    unittest.main()
