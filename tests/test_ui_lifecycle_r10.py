"""Team C R10: two simultaneous cleanup failures and bounded recovery.

Pure-Python synthetic bpy mocks do not replace required real Blender 3-version
CI evidence. No real third-party addon, user source or private GLB is loaded.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_rolling_r3 import PreviewRollingLifecycleTests
from test_ui_reload_r6 import _reload_guard
from test_ui_lifecycle_r9 import R9_MARKERS


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
R10_MARKERS = (
    "native_r10_dual_failure_retains_both_ledgers",
    "native_r10_class_retry_preserves_foreign",
    "native_r10_scene_retry_preserves_foreign",
    "native_r10_partial_retry_blocks_reload",
    "native_r10_enable_disable_after_dual_recovery_2",
)


class R10DualFailureOwnershipTests(unittest.TestCase):
    def setUp(self):
        PreviewRollingLifecycleTests.setUp(self)

    assert_fully_unregistered = PreviewRollingLifecycleTests.assert_fully_unregistered

    def test_both_scene_properties_and_both_second_failure_orders(self):
        for missing in self.namespace["_PROPERTY_NAMES"]:
            for second_failure in ("class", "scene"):
                with self.subTest(missing=missing, second_failure=second_failure):
                    self.register()
                    other = next(name for name in self.namespace["_PROPERTY_NAMES"]
                                 if name != missing)
                    owned = self.namespace["_OWNED_PROPERTY_TOKENS"][missing]
                    last_class = self.namespace["_REGISTERED"][-1]
                    base_unregister = self.utils.unregister_class
                    assert "delattr" not in self.namespace
                    class_attempts, scene_attempts = [0], [0]
                    class_budget = 2 if second_failure == "class" else 1
                    scene_budget = 2 if second_failure == "scene" else 1
                    foreign = object()

                    def fail_class_twice_or_once(cls):
                        if (cls is last_class
                                and class_attempts[0] < class_budget):
                            class_attempts[0] += 1
                            raise RuntimeError("R10 injected class failure")
                        return base_unregister(cls)

                    def fail_scene_twice_or_once(owner, name):
                        if (owner is self.scene and name == missing
                                and scene_attempts[0] < scene_budget):
                            scene_attempts[0] += 1
                            raise RuntimeError("R10 injected Scene deletion failure")
                        return delattr(owner, name)

                    self.utils.unregister_class = fail_class_twice_or_once
                    self.namespace["delattr"] = fail_scene_twice_or_once
                    try:
                        with self.assertRaisesRegex(
                                RuntimeError, "cleanup incomplete"):
                            self.unregister()
                        self.assertEqual(class_attempts, [1])
                        self.assertEqual(scene_attempts, [1])
                        self.assertEqual(self.utils.active, {last_class})
                        self.assertEqual(self.namespace["_REGISTERED"],
                                         [last_class])
                        self.assertEqual(self.namespace["_OWNED_PROPERTIES"],
                                         [missing])
                        self.assertIs(
                            self.namespace["_OWNED_PROPERTY_TOKENS"][missing],
                            owned)
                        self.assertIs(self.scene.__dict__[missing], owned)
                        self.assertFalse(hasattr(self.scene, other))
                        with self.assertRaisesRegex(
                                RuntimeError, "unregistered before module reload"):
                            exec(_reload_guard(), self.namespace)
                        with self.assertRaisesRegex(
                                RuntimeError, "already registered"):
                            self.register()

                        if second_failure == "class":
                            setattr(self.scene, missing, foreign)
                        with self.assertRaisesRegex(
                                RuntimeError, "cleanup incomplete"):
                            self.unregister()

                        if second_failure == "class":
                            self.assertEqual(class_attempts, [2])
                            self.assertEqual(scene_attempts, [1])
                            self.assertEqual(self.namespace["_REGISTERED"],
                                             [last_class])
                            self.assertEqual(self.utils.active, {last_class})
                            self.assertFalse(
                                self.namespace["_OWNED_PROPERTIES"])
                            self.assertFalse(
                                self.namespace["_OWNED_PROPERTY_TOKENS"])
                        else:
                            self.assertEqual(class_attempts, [1])
                            self.assertEqual(scene_attempts, [2])
                            self.assertFalse(self.utils.active)
                            self.assertFalse(self.namespace["_REGISTERED"])
                            self.assertEqual(self.namespace["_OWNED_PROPERTIES"],
                                             [missing])
                            self.assertIs(
                                self.namespace["_OWNED_PROPERTY_TOKENS"][missing],
                                owned)
                            setattr(self.scene, missing, foreign)
                        self.assertIs(getattr(self.scene, missing), foreign)
                        with self.assertRaisesRegex(
                                RuntimeError, "unregistered before module reload"):
                            exec(_reload_guard(), self.namespace)
                        with self.assertRaisesRegex(
                                RuntimeError, "already registered"):
                            self.register()

                        self.unregister()
                        self.assert_fully_unregistered()
                        self.assertIs(getattr(self.scene, missing), foreign)
                        with self.assertRaisesRegex(
                                RuntimeError, "Scene properties conflict"):
                            self.register()
                        self.assertIs(getattr(self.scene, missing), foreign)
                    finally:
                        self.utils.unregister_class = base_unregister
                        self.namespace.pop("delattr", None)
                        if getattr(self.scene, missing, None) is foreign:
                            delattr(self.scene, missing)
                    self.assert_fully_unregistered()
                    self.register()
                    self.unregister()
                    self.assert_fully_unregistered()

    def test_three_separate_retries_do_not_erase_pending_ownership(self):
        self.register()
        owned_name = self.namespace["_PROPERTY_NAMES"][1]
        owned_token = self.namespace["_OWNED_PROPERTY_TOKENS"][owned_name]
        kept_class = self.namespace["_REGISTERED"][-1]
        native_unregister = self.utils.unregister_class
        class_attempts, scene_attempts = [0], [0]

        def fail_class_first_three(cls):
            if cls is kept_class and class_attempts[0] < 3:
                class_attempts[0] += 1
                raise RuntimeError("R10 bounded class cleanup failure")
            return native_unregister(cls)

        def fail_scene_first_three(cls, name):
            if (cls is self.scene and name == owned_name
                    and scene_attempts[0] < 3):
                scene_attempts[0] += 1
                raise RuntimeError("R10 bounded property cleanup failure")
            return delattr(cls, name)

        self.utils.unregister_class = fail_class_first_three
        self.namespace["delattr"] = fail_scene_first_three
        try:
            for attempt in range(3):
                with self.subTest(attempt=attempt):
                    with self.assertRaisesRegex(
                            RuntimeError, "cleanup incomplete"):
                        self.unregister()
                    self.assertEqual(self.utils.active, {kept_class})
                    self.assertEqual(self.namespace["_REGISTERED"],
                                     [kept_class])
                    self.assertEqual(self.namespace["_OWNED_PROPERTIES"],
                                     [owned_name])
                    self.assertIs(
                        self.namespace["_OWNED_PROPERTY_TOKENS"][owned_name],
                        owned_token)
                    with self.assertRaisesRegex(
                            RuntimeError, "unregistered before module reload"):
                        exec(_reload_guard(), self.namespace)
        finally:
            self.utils.unregister_class = native_unregister
            self.namespace.pop("delattr", None)
        self.assertEqual(class_attempts, [3])
        self.assertEqual(scene_attempts, [3])
        self.unregister()
        self.assert_fully_unregistered()


class R10NativeProbeContractTests(unittest.TestCase):
    def test_r10_native_markers_and_real_blender_path_intact(self):
        source = NATIVE.read_text(encoding="utf-8")
        ast.parse(source)
        for marker in R9_MARKERS + R10_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    source.count('checks.append("' + marker + '")'), 1)
        self.assertIn('module.__dict__["delattr"] = r10_scene_failure', source)
        self.assertIn("bpy.utils.unregister_class = r10_class_failure", source)
        self.assertIn("module._OWNED_PROPERTIES == [failing_name]", source)
        self.assertIn("scene_budget = 2 if second_failure", source)
        self.assertIn("class_budget = 2 if second_failure", source)
        self.assertIn("addon_utils.enable(", source)
        self.assertIn("importlib.reload(module)", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertNotIn("input_sources_private/", source)
        imported = {
            alias.name.partition(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(imported <= {
            "addon_utils", "bmesh", "bpy", "importlib", "json", "sys",
            "tempfile",
        })
        # Static script validation is NOT an actual Blender pass.


if __name__ == "__main__":
    unittest.main()
