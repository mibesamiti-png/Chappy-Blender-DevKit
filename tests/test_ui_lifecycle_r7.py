"""Team C R7: controlled rollback when Scene ownership changes mid-register.

The native Blender fixture in tests/blender_ui_lifecycle_r5.py is run by
the A-owned CI matrix. These mocks are separate and never count as Blender
runtime evidence. Only trusted CBDK-authored preview code is exercised.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_rolling_r3 import PreviewRollingLifecycleTests
from test_ui_reload_r6 import _reload_guard


MARKERS = (
    "native_r7_mid_register_missing_foreign_rollback",
    "native_r7_partial_live_reload_rejected",
    "native_r7_foreign_reload_collision_preserved",
    "native_r7_enable_disable_after_recovery_2",
)
NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"


class R7PartialRegistrationRollbackTests(unittest.TestCase):
    def setUp(self):
        # Reuse R3's known-trusted mocked bpy context without inheriting and
        # accidentally re-running its individual tests.
        PreviewRollingLifecycleTests.setUp(self)

    assert_fully_unregistered = PreviewRollingLifecycleTests.assert_fully_unregistered

    def test_missing_and_foreign_replaced_declarations_during_second_class_failure(self):
        names = self.namespace["_PROPERTY_NAMES"]
        for missing, replaced in ((names[0], names[1]),
                                  (names[1], names[0])):
            with self.subTest(missing=missing, replaced=replaced):
                foreign = object()
                normal = self.utils.register_class
                calls = [0]

                def inject_failure(cls):
                    calls[0] += 1
                    if calls[0] == 2:
                        self.assertEqual(len(self.namespace["_REGISTERED"]), 1)
                        # R6's live reload refusal still applies while
                        # register() is only halfway through its class loop.
                        with self.assertRaisesRegex(
                                RuntimeError, "unregistered before module reload"):
                            exec(_reload_guard(), self.namespace)
                        delattr(self.scene, missing)
                        setattr(self.scene, replaced, foreign)
                        raise RuntimeError("controlled R7 partial registration")
                    return normal(cls)

                self.utils.register_class = inject_failure
                try:
                    with self.assertRaisesRegex(
                            RuntimeError, "controlled R7 partial registration"):
                        self.register()
                finally:
                    self.utils.register_class = normal

                self.assertEqual(calls[0], 2)
                self.assert_fully_unregistered()
                self.assertFalse(hasattr(self.scene, missing))
                self.assertIs(getattr(self.scene, replaced), foreign)
                with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
                    self.register()
                self.assertIs(getattr(self.scene, replaced), foreign)
                self.assert_fully_unregistered()
                delattr(self.scene, replaced)
                self.register()
                self.unregister()
                self.assert_fully_unregistered()

    def test_partial_cleanup_failure_does_not_convert_foreign_name_to_owned(self):
        self.register()
        foreign = object()
        # During a deliberately failed first detach, foreign value replaces
        # one of the original Scene declarations while the other disappears.
        self.utils.fail_unregister = self.a
        delattr(self.scene, "cbdk_modular_result")
        self.scene.cbdk_modular_nudge_offset = foreign
        with self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
            self.unregister()
        self.assertEqual(self.namespace["_REGISTERED"], [self.a])
        self.assertIs(self.scene.cbdk_modular_nudge_offset, foreign)
        with self.assertRaisesRegex(RuntimeError, "unregistered before module reload"):
            exec(_reload_guard(), self.namespace)
        self.unregister()
        self.assert_fully_unregistered()
        self.assertIs(self.scene.cbdk_modular_nudge_offset, foreign)
        with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
            self.register()
        delattr(self.scene, "cbdk_modular_nudge_offset")
        self.register()
        self.unregister()
        self.assert_fully_unregistered()


class R7NativeRegressionContractTests(unittest.TestCase):
    def test_native_fixture_marks_each_bounded_r7_case_once(self):
        source = NATIVE.read_text(encoding="utf-8")
        ast.parse(source)
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    source.count('checks.append("' + marker + '")'), 1)
        self.assertIn("addon_utils.enable(", source)
        self.assertIn("addon_utils.disable(PACKAGE", source)
        self.assertIn("fail_after_foreign_mutation", source)
        self.assertIn("importlib.reload(module)", source)
        self.assertIn("foreign_descriptor", source)
        self.assertIn("range(2)", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertNotIn("input_sources_private/", source)
        # Static presence is not proof of the Blender-version runtime verdict.

    def test_native_script_does_not_import_or_execute_untrusted_addons(self):
        tree = ast.parse(NATIVE.read_text(encoding="utf-8"))
        imported = {
            alias.name.partition(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(imported <= {
            "addon_utils", "bmesh", "bpy", "importlib", "json", "sys", "tempfile"
        })
        self.assertTrue(all(
            not isinstance(node, ast.ImportFrom)
            or node.module in ("pathlib", "types", "zipfile", "__future__")
            for node in ast.walk(tree)))
        self.assertFalse(any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"eval", "exec"}
            for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
