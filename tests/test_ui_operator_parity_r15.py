"""Team C R15: authored UI readiness versus real operator result contract.

Python checks inspect only CBDK's trusted panel logic and static native probe.
Only the Blender matrix executes real bpy.ops; mocked readiness is advisory.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_readiness_r2 import (
    FEATURES, IDS, PreviewReadinessTests, mesh_context,
)


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
MARKERS = (
    "native_r15_object_ui_execute_status_parity",
    "native_r15_empty_missing_mesh_cancel_parity",
    "native_r15_edit_zero_selection_cancel_parity",
    "native_r15_edit_selected_operator_result_parity",
    "native_r15_mode_switch_rechecks_operator_parity",
    "native_r15_foreign_scene_reenable_preserves_parity",
)


class R15AdvisoryModeMatrix(unittest.TestCase):
    def setUp(self):
        PreviewReadinessTests.setUp(self)

    # Reuse the trusted recorder, without inheriting and re-running every
    # older PreviewReadinessTests unittest through discovery.
    draw = PreviewReadinessTests.draw

    def visible_flags(self, context):
        return {name: enabled for kind, name, enabled in self.draw(context)
                if kind == "operator"}

    def test_object_mesh_empty_and_missing_context_advice(self):
        context = mesh_context()
        expected = {
            IDS["object_selection"]: True,
            IDS["mesh_bounds"]: True,
            IDS["modifier_summary"]: True,
        }
        self.assertEqual(self.visible_flags(context), expected)
        context.active_object.data.vertices.clear()
        expected[IDS["mesh_bounds"]] = False
        self.assertEqual(self.visible_flags(context), expected)
        context.active_object = None
        expected = {name: False for name in expected}
        self.assertEqual(self.visible_flags(context), expected)

    def test_zero_and_nonzero_edit_selection_keep_xyz_input_independent(self):
        context = mesh_context(mode="EDIT_MESH", selection=0)
        self.assertEqual(self.visible_flags(context), {
            IDS["edit_selection"]: True,
            IDS["vertex_nudge"]: False,
        })
        self.assertIn(("prop", "cbdk_modular_nudge_offset", True),
                      self.draw(context))
        context.active_object.data.total_vert_sel = 1
        self.assertEqual(self.visible_flags(context), {
            IDS["edit_selection"]: True,
            IDS["vertex_nudge"]: True,
        })
        self.assertIn(("prop", "cbdk_modular_nudge_offset", True),
                      self.draw(context))
        context.active_object.data.total_vert_sel = 0
        self.assertFalse(self.visible_flags(context)[IDS["vertex_nudge"]])

    def test_mode_switch_never_caches_previous_advice(self):
        context = mesh_context()
        for mode, selection, expected in (
            ("OBJECT", 1, {IDS[f]: True for f in FEATURES[:3]}),
            ("EDIT_MESH", 0, {
                IDS["edit_selection"]: True,
                IDS["vertex_nudge"]: False,
            }),
            ("EDIT_MESH", 1, {
                IDS["edit_selection"]: True,
                IDS["vertex_nudge"]: True,
            }),
            ("OBJECT", 1, {IDS[f]: True for f in FEATURES[:3]}),
            ("SCULPT", 1, {}),
        ):
            with self.subTest(mode=mode, selection=selection):
                context.mode = mode
                context.active_object.data.total_vert_sel = selection
                self.assertEqual(self.visible_flags(context), expected)

    def test_advisory_enabled_cannot_assert_native_operator_finished(self):
        context = mesh_context(mode="EDIT_MESH", selection=1)
        self.assertTrue(self.visible_flags(context)[IDS["vertex_nudge"]])
        # A context or selection can change between draw and execution.
        context.active_object.data.total_vert_sel = 0
        self.assertFalse(self.visible_flags(context)[IDS["vertex_nudge"]])
        # The actual Blender result must come from native R15 markers,
        # never this synthetic test's predicted boolean.


class R15NativeOperatorContract(unittest.TestCase):
    def test_all_r15_live_bpy_operator_markers_and_older_checks_retained(self):
        source = NATIVE.read_text(encoding="utf-8")
        ast.parse(source)
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(source.count(
                    'checks.append("' + marker + '")'), 1)
        for older in (
            "native_r13_failed_enable_evicts_live_module",
            "native_r14_three_generation_class_identity",
            "native_r14_reenable_after_all_generations",
        ):
            self.assertIn('checks.append("' + older + '")', source)
        self.assertIn("outcome = operator_call()", source)
        self.assertIn('{"FINISHED"} if ready else {"CANCELLED"}', source)
        self.assertIn("r15_assert_ui_matches_execute(", source)
        self.assertIn("bmesh.from_edit_mesh(r15_mesh)", source)
        self.assertIn("original_geometry", source)
        self.assertIn("foreign_r15", source)
        self.assertIn("addon_utils.disable(PACKAGE", source)
        self.assertIn("addon_utils.enable(", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertNotIn("input_sources_private/", source)

    def test_fixed_features_and_six_authored_recipe_files_remain(self):
        recipes = (
            "modular_objects", "modular_edit", "modular_combined",
            "modular_geometry", "modular_nudge", "modular_all",
        )
        for name in recipes:
            with self.subTest(recipe=name):
                self.assertTrue((ROOT / "recipes" / (name + ".json")).is_file())
        self.assertEqual(len(FEATURES), 5)
        # The existing R6 build/ZIP tests prove generated recipe content.
        # This source contract does not replace them or native Blender CI.


if __name__ == "__main__":
    unittest.main()
