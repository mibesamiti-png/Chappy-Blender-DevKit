"""R16 authored UI TOCTOU regressions; native bpy.ops is sole result authority.

Synthetic tests prove only that old Panel.draw hints must be recomputed. Native
Blender 4.4.3/4.5.15/5.2.1 jobs exercise actual FINISHED/CANCELLED operations.
No third-party addon, private scene, or arbitrary source is imported.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_readiness_r2 import (
    FEATURES, IDS, PreviewReadinessTests, mesh_context,
)


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
R16_MARKERS = (
    "native_r16_object_draw_then_edit_cancel",
    "native_r16_edit_draw_then_deselect_cancel",
    "native_r16_edit_draw_then_object_cancel",
    "native_r16_redraw_valid_actions_still_finish",
    "native_r16_foreign_scene_stale_cancel_safe",
    "native_r16_reenable_after_stale_draw",
)


class R16StaleAdvisoryTests(unittest.TestCase):
    setUp = PreviewReadinessTests.setUp
    draw = PreviewReadinessTests.draw

    def enabled(self, context):
        # The recorder also contains 2-field text/label entries.
        return {item[1]: item[2] for item in self.draw(context)
                if item[0] == "operator"}

    def test_object_hint_does_not_survive_edit_mode_switch(self):
        context = mesh_context()
        before = self.enabled(context)
        for feature in FEATURES[:3]:
            self.assertIs(before[IDS[feature]], True)
        context.mode = "EDIT_MESH"
        after = self.enabled(context)
        self.assertTrue(all(name not in after for name in (
            IDS["object_selection"], IDS["mesh_bounds"],
            IDS["modifier_summary"])))
        self.assertIs(after[IDS["edit_selection"]], True)
        # Static absence of a button does not prove live operator cancellation.

    def test_nudge_enabled_hint_expires_when_selection_cleared(self):
        context = mesh_context(mode="EDIT_MESH", selection=1)
        self.assertIs(self.enabled(context)[IDS["vertex_nudge"]], True)
        context.active_object.data.total_vert_sel = 0
        self.assertIs(self.enabled(context)[IDS["vertex_nudge"]], False)
        self.assertIs(self.enabled(context)[IDS["edit_selection"]], True)
        self.assertIn(("prop", "cbdk_modular_nudge_offset", True),
                      self.draw(context))

    def test_edit_hint_does_not_survive_object_mode_switch(self):
        context = mesh_context(mode="EDIT_MESH", selection=1)
        before = self.enabled(context)
        self.assertIs(before[IDS["edit_selection"]], True)
        self.assertIs(before[IDS["vertex_nudge"]], True)
        context.mode = "OBJECT"
        after = self.enabled(context)
        self.assertNotIn(IDS["edit_selection"], after)
        self.assertNotIn(IDS["vertex_nudge"], after)
        self.assertIs(after[IDS["object_selection"]], True)


class R16NativeOperatorContractTests(unittest.TestCase):
    def test_native_script_contains_six_executed_marker_assertions(self):
        source = NATIVE.read_text(encoding="utf-8")
        ast.parse(source)
        for marker in R16_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    source.count('checks.append("' + marker + '")'), 1)
        for previous in (
            "native_r13_failed_enable_evicts_live_module",
            "native_r14_three_generation_class_identity",
            "native_r15_foreign_scene_reenable_preserves_parity",
        ):
            self.assertIn('checks.append("' + previous + '")', source)
        for native_call in (
            "r16_expect_cancel(bpy.ops.cbdk.modular_selected_meshes)",
            "r16_expect_cancel(bpy.ops.cbdk.modular_mesh_bounds)",
            "r16_expect_cancel(bpy.ops.cbdk.modular_modifier_summary)",
            "r16_expect_cancel(bpy.ops.cbdk.modular_vertex_nudge)",
            "r16_expect_cancel(bpy.ops.cbdk.modular_edit_selection)",
        ):
            self.assertIn(native_call, source)
        self.assertIn("coordinates = r16_coords()", source)
        self.assertIn("result_before = bpy.context.scene.cbdk_modular_result",
                      source)
        self.assertIn("outcome == {\"CANCELLED\"}", source)
        self.assertIn("bmesh.from_edit_mesh(r16_mesh)", source)
        self.assertIn("foreign_r16", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertNotIn("input_sources_private/", source)
        # Marker assertions are not evidence of actual native execution.

    def test_fixed_feature_and_six_authored_recipe_contract(self):
        recipes = (
            "modular_objects", "modular_edit", "modular_combined",
            "modular_geometry", "modular_nudge", "modular_all",
        )
        self.assertEqual(len(FEATURES), 5)
        for recipe in recipes:
            with self.subTest(recipe=recipe):
                self.assertTrue((ROOT / "recipes" /
                                 (recipe + ".json")).is_file())


if __name__ == "__main__":
    unittest.main()
