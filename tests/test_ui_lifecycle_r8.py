"""R8 regression: class detach retry, foreign Scene ownership and edit cancel.

Synthetic Python unit tests are intentionally distinct from the Blender 3-version
native lifecycle probe. No user addons, assets or scene files are imported.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_rolling_r3 import PreviewRollingLifecycleTests
from test_ui_reload_r6 import _reload_guard


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
R8_MARKERS = (
    "native_r8_partial_unregister_foreign_retry",
    "native_r8_partial_unregister_reload_fail_closed",
    "native_r8_validation_cancel_input_unchanged",
    "native_r8_guarded_exception_cancel_input_unchanged",
    "native_r8_edit_mode_cleanup_after_cancellation",
)


class R8UnregisterFailureTests(unittest.TestCase):
    def setUp(self):
        PreviewRollingLifecycleTests.setUp(self)

    assert_fully_unregistered = PreviewRollingLifecycleTests.assert_fully_unregistered

    def test_both_foreign_descriptor_replacements_are_kept_through_class_retry(self):
        for replaced in self.namespace["_PROPERTY_NAMES"]:
            with self.subTest(replaced=replaced):
                self.register()
                failing = self.namespace["_REGISTERED"][-1]
                foreign = object()
                normal_unregister = self.utils.unregister_class
                failures = [0]

                def unregister_with_foreign_replacement(cls):
                    if cls is failing and failures[0] == 0:
                        failures[0] += 1
                        setattr(self.scene, replaced, foreign)
                        raise RuntimeError("R8 controlled class detach failure")
                    return normal_unregister(cls)

                self.utils.unregister_class = unregister_with_foreign_replacement
                try:
                    with self.assertRaisesRegex(
                            RuntimeError, "cleanup incomplete"):
                        self.unregister()
                finally:
                    self.utils.unregister_class = normal_unregister

                self.assertEqual(failures, [1])
                self.assertEqual(self.namespace["_REGISTERED"], [failing])
                self.assertEqual(self.utils.active, {failing})
                self.assertEqual(self.namespace["_OWNED_PROPERTIES"], [])
                self.assertEqual(self.namespace["_OWNED_PROPERTY_TOKENS"], {})
                self.assertIs(getattr(self.scene, replaced), foreign)
                with self.assertRaisesRegex(
                        RuntimeError, "unregistered before module reload"):
                    exec(_reload_guard(), self.namespace)
                with self.assertRaisesRegex(RuntimeError, "already registered"):
                    self.register()
                self.assertIs(getattr(self.scene, replaced), foreign)

                self.unregister()
                self.assert_fully_unregistered()
                self.assertIs(getattr(self.scene, replaced), foreign)
                with self.assertRaisesRegex(
                        RuntimeError, "Scene properties conflict"):
                    self.register()
                self.assertIs(getattr(self.scene, replaced), foreign)
                delattr(self.scene, replaced)
                self.register()
                self.unregister()
                self.assert_fully_unregistered()

    def test_failed_detach_twice_remains_live_and_is_retriable(self):
        self.register()
        failing = self.namespace["_REGISTERED"][-1]
        original = self.utils.unregister_class
        failures = [0]

        def unregister_twice(cls):
            if cls is failing and failures[0] < 2:
                failures[0] += 1
                raise RuntimeError("R8 controlled repeat detach failure")
            return original(cls)

        self.utils.unregister_class = unregister_twice
        try:
            for attempt in range(2):
                with self.subTest(attempt=attempt):
                    with self.assertRaisesRegex(
                            RuntimeError, "cleanup incomplete"):
                        self.unregister()
                    self.assertEqual(self.namespace["_REGISTERED"], [failing])
                    self.assertEqual(self.utils.active, {failing})
                    with self.assertRaisesRegex(
                            RuntimeError, "unregistered before module reload"):
                        exec(_reload_guard(), self.namespace)
        finally:
            self.utils.unregister_class = original
        self.assertEqual(failures, [2])
        self.unregister()
        self.assert_fully_unregistered()
        self.register()
        self.unregister()
        self.assert_fully_unregistered()


class R8NativeContractTests(unittest.TestCase):
    def test_real_blender_probe_has_fixed_new_checks(self):
        source = NATIVE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for marker in R8_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    source.count('checks.append("' + marker + '")'), 1)
        imports = {
            name.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for name in node.names
        }
        self.assertIn("bmesh", imports)
        self.assertIn("edit_input_snapshot()", source)
        self.assertIn("bmesh.from_edit_mesh(mesh)", source)
        self.assertIn("importlib.reload(module)", source)
        self.assertIn("fail_once_during_unregister", source)
        self.assertIn("nudge.translate_selected_vertices = raise_nudge_validation",
                      source)
        self.assertIn("counter.count_edit_selection = raise_count_validation",
                      source)
        self.assertIn("addon_utils.disable(PACKAGE", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertNotIn("input_sources_private/", source)
        # Script presence is not evidence of a successful native Blender run.


if __name__ == "__main__":
    unittest.main()
