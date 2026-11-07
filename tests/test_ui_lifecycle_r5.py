"""Team C R5: lifecycle edge cases and native-script contract.

Python tests are synthetic. tests/blender_ui_lifecycle_r5.py is separately
executed in the existing A-owned Blender matrix, with real version-specific evidence.
"""
from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, build_addon
from test_ui_rolling_r3 import PreviewRollingLifecycleTests, _SceneMeta


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
R5_CHECKS = (
    "native_object_edit_cancel_mode_cycles_3",
    "native_zero_selection_xyz_editable_and_non_mutating",
    "native_register_unregister_cycles_4",
    "native_preexisting_foreign_collision_preserved",
    "native_foreign_replacement_preserved",
    "native_cleanup_and_reregister_after_collision",
)


class R5SyntheticLifecycleTests(unittest.TestCase):
    """Reuse R3's fixture without accidentally re-running R3 test methods."""

    def setUp(self):
        PreviewRollingLifecycleTests.setUp(self)

    assert_fully_unregistered = PreviewRollingLifecycleTests.assert_fully_unregistered

    def test_absent_descriptor_token_cannot_delete_inherited_foreign_property(self):
        class ForeignParent:
            pass

        class Scene(ForeignParent, metaclass=_SceneMeta):
            pass

        self.scene = Scene
        self.namespace["bpy"].types.Scene = Scene
        self.register()
        foreign = object()
        # Simulate a lost CBDK declaration and an inherited foreign property.
        del Scene.cbdk_modular_result
        ForeignParent.cbdk_modular_result = foreign
        self.namespace["_OWNED_PROPERTY_TOKENS"]["cbdk_modular_result"] = None
        try:
            # If the ownership check used 'None is None', delattr(Scene, ...)
            # would raise AttributeError, retaining stale ownership forever.
            self.unregister()
            self.assert_fully_unregistered()
            self.assertIs(Scene.cbdk_modular_result, foreign)
            with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
                self.register()
            self.assertIs(Scene.cbdk_modular_result, foreign)
        finally:
            del ForeignParent.cbdk_modular_result

        self.register()
        self.unregister()
        self.assert_fully_unregistered()

    def test_synthetic_replacement_of_both_owned_fields_preserves_both(self):
        self.register()
        foreign_result = object()
        foreign_offset = object()
        self.scene.cbdk_modular_result = foreign_result
        self.scene.cbdk_modular_nudge_offset = foreign_offset
        self.unregister()
        self.assert_fully_unregistered()
        self.assertIs(self.scene.cbdk_modular_result, foreign_result)
        self.assertIs(self.scene.cbdk_modular_nudge_offset, foreign_offset)
        with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
            self.register()
        del self.scene.cbdk_modular_nudge_offset
        del self.scene.cbdk_modular_result
        self.register()
        self.unregister()
        self.assert_fully_unregistered()


class R5NativeProbePackagingTests(unittest.TestCase):
    def test_probe_is_standalone_trusted_blender_script_with_fixed_checks(self):
        source = NATIVE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(imports <= {
            "importlib", "json", "sys", "tempfile", "addon_utils", "bmesh", "bpy"})
        assert "input_sources_private" not in source
        self.assertNotIn("eval(", source)
        self.assertNotIn("exec(", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertIn("bpy.ops.wm.read_factory_settings(use_empty=True)", source)
        self.assertIn("addon_utils.enable(PACKAGE", source)
        self.assertIn("addon_utils.disable(PACKAGE", source)
        for check in R5_CHECKS:
            self.assertIn('checks.append("' + check + '")', source)
        # Static assertion intentionally does NOT count as a native pass.
        self.assertIn("real_blender_headless", source)
        self.assertIn("real_windows_gui_tested", source)

    def test_native_probe_accepts_only_fixed_all_feature_preview_zip(self):
        recipe = ROOT / "recipes" / "modular_all.json"
        with tempfile.TemporaryDirectory(prefix="cbdk-r5-package-") as d:
            output = Path(d) / "preview.zip"
            result = build_addon(
                recipe, output, root=ROOT, preview_unapproved=True)
            self.assertIs(result["preview_only"], True)
            self.assertIs(result["approved"], False)
            with ZipFile(output) as archive:
                info = json.loads(archive.read(
                    "cbdk_modular_preview/CBDK_BUILD_INFO.json"))
                self.assertEqual(set(info["features"]), {
                    "object_selection", "mesh_bounds", "modifier_summary",
                    "edit_selection", "vertex_nudge"})
                self.assertIs(info["preview_only"], True)
                self.assertIs(info["redistribution_cleared"], False)


if __name__ == "__main__":
    unittest.main()
