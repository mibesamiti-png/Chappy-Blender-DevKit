"""Team C R13: module eviction can hide an older live Blender ledger.

These tests model Python module identities and authorized CBDK preview code.
They do NOT substitute for three actual Blender-version addon_utils logs.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_rolling_r3 import PreviewRollingLifecycleTests
from test_ui_readiness_r2 import _trusted_functions
from test_ui_reload_r6 import _reload_guard


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
R13_MARKERS = (
    "native_r13_failed_enable_evicts_live_module",
    "native_r13_fresh_import_hides_original_pending_ledger",
    "native_r13_old_reference_recovers_live_classes",
    "native_r13_foreign_scene_survives_recovery",
    "native_r13_reenable_after_eviction_2",
)


class R13OldModuleLedgerTests(unittest.TestCase):
    def setUp(self):
        PreviewRollingLifecycleTests.setUp(self)

    assert_fully_unregistered = (
        PreviewRollingLifecycleTests.assert_fully_unregistered
    )

    def test_failed_registration_rollback_evicts_old_reference_but_new_namespace_hides_ledger(self):
        for scene_cleanup_pending in (False, True):
            with self.subTest(scene_cleanup_pending=scene_cleanup_pending):
                old = self.namespace
                registry = {"cbdk_modular_preview": old}
                original_register = self.utils.register_class
                original_unregister = self.utils.unregister_class
                calls, rollback_errors, scene_errors = [0], [0], [0]

                def fail_second_register(cls):
                    calls[0] += 1
                    if calls[0] == 2:
                        raise RuntimeError("R13 synthetic enable failure")
                    return original_register(cls)

                def fail_rollback_class(cls):
                    if (old["_REGISTERED"]
                            and cls is old["_REGISTERED"][0]
                            and rollback_errors[0] == 0):
                        rollback_errors[0] += 1
                        raise RuntimeError("R13 synthetic rollback failure")
                    return original_unregister(cls)

                def fail_scene_rollback(owner, name):
                    if (scene_cleanup_pending and owner is self.scene
                            and name == "cbdk_modular_result"
                            and scene_errors[0] == 0):
                        scene_errors[0] += 1
                        raise RuntimeError("R13 synthetic RNA delete failure")
                    return delattr(owner, name)

                self.utils.register_class = fail_second_register
                self.utils.unregister_class = fail_rollback_class
                if scene_cleanup_pending:
                    old["delattr"] = fail_scene_rollback
                try:
                    with self.assertRaisesRegex(
                            RuntimeError, "R13 synthetic enable failure"):
                        self.register()
                    # Model Blender's addon_utils.enable() failure eviction.
                    registry.pop("cbdk_modular_preview")
                finally:
                    self.utils.register_class = original_register
                    self.utils.unregister_class = original_unregister
                    old.pop("delattr", None)

                self.assertEqual(calls, [2])
                self.assertEqual(rollback_errors, [1])
                self.assertEqual(scene_errors, [int(scene_cleanup_pending)])
                self.assertNotIn("cbdk_modular_preview", registry)
                kept_class = old["_REGISTERED"][0]
                self.assertEqual(old["_REGISTERED"], [kept_class])
                self.assertIn(kept_class, self.utils.active)
                self.assertEqual(old["_OWNED_PROPERTIES"],
                                 (["cbdk_modular_result"]
                                  if scene_cleanup_pending else []))
                token = old["_OWNED_PROPERTY_TOKENS"].get(
                    "cbdk_modular_result")
                if scene_cleanup_pending:
                    self.assertIs(
                        self.scene.__dict__["cbdk_modular_result"], token)

                # A same-name fresh import has a DISTINCT module-global
                # namespace, although Blender still holds the old class.
                fresh = dict(old)
                fresh.update(
                    _REGISTERED=[], _OWNED_PROPERTIES=[],
                    _OWNED_PROPERTY_TOKENS={})
                exec(_trusted_functions("register", "unregister"), fresh)
                registry["cbdk_modular_preview"] = fresh
                self.assertIsNot(old, fresh)
                self.assertIsNot(old["_REGISTERED"], fresh["_REGISTERED"])
                self.assertFalse(fresh["_REGISTERED"])
                self.assertFalse(fresh["_OWNED_PROPERTIES"])
                self.assertFalse(fresh["_OWNED_PROPERTY_TOKENS"])
                self.assertEqual(old["_REGISTERED"], [kept_class])
                self.assertIn(kept_class, self.utils.active)
                with self.assertRaisesRegex(
                        RuntimeError, "unregistered before module reload"):
                    exec(_reload_guard(), old)
                # The guard only sees the NEW namespace, not the old ledger.
                exec(_reload_guard(), fresh)

                foreign = object()
                self.scene.cbdk_modular_result = foreign
                try:
                    with self.assertRaisesRegex(
                            RuntimeError, "Scene properties conflict"):
                        fresh["register"]()
                    fresh["unregister"]()
                    self.assertIn(kept_class, self.utils.active)
                    self.assertEqual(old["_REGISTERED"], [kept_class])
                    self.assertIs(self.scene.cbdk_modular_result, foreign)

                    # Must call OLD unregister(), not the fresh module's.
                    self.unregister()
                    self.assert_fully_unregistered()
                    self.assertFalse(self.utils.active)
                    self.assertIs(self.scene.cbdk_modular_result, foreign)
                    self.assertFalse(fresh["_REGISTERED"])
                finally:
                    if getattr(self.scene, "cbdk_modular_result", None) is foreign:
                        del self.scene.cbdk_modular_result

                fresh["register"]()
                self.assertEqual(len(self.utils.active), len(fresh["_CLASSES"]))
                fresh["unregister"]()
                self.assertFalse(self.utils.active)
                self.assertFalse(fresh["_REGISTERED"])
                self.assertFalse(fresh["_OWNED_PROPERTY_TOKENS"])

    def test_old_owned_token_survives_new_namespace_reset_without_foreign_claim(self):
        self.register()
        old = self.namespace
        original_ledger = old["_REGISTERED"]
        original_token = old["_OWNED_PROPERTY_TOKENS"][
            "cbdk_modular_nudge_offset"]
        fresh = dict(old)
        fresh.update(
            _REGISTERED=[], _OWNED_PROPERTIES=[],
            _OWNED_PROPERTY_TOKENS={})
        exec(_trusted_functions("register", "unregister"), fresh)
        self.assertIsNot(original_ledger, fresh["_REGISTERED"])
        self.assertIs(old["_OWNED_PROPERTY_TOKENS"][
            "cbdk_modular_nudge_offset"], original_token)
        self.assertTrue(self.utils.active)
        fresh["unregister"]()
        self.assertTrue(self.utils.active)
        self.assertIs(self.scene.__dict__["cbdk_modular_nudge_offset"],
                      original_token)
        self.unregister()
        self.assert_fully_unregistered()
        fresh["register"]()
        fresh["unregister"]()
        self.assertFalse(self.utils.active)


class R13NativeContractTests(unittest.TestCase):
    def test_native_script_retains_r5_r12_and_executes_fixed_r13_markers(self):
        source = NATIVE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for marker in R13_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(
                    source.count('checks.append("' + marker + '")'), 1)
        self.assertIn('result = addon_utils.enable(', source)
        self.assertIn('assert PACKAGE not in sys.modules', source)
        self.assertIn('fresh_module = importlib.import_module(PACKAGE)',
                      source)
        self.assertIn('fresh_module is not original_module', source)
        self.assertIn('original_module.unregister()', source)
        self.assertIn('bpy.types.Scene.__dict__.get(PROPERTIES[0])', source)
        self.assertIn('native_r12_reenable_eviction_original_reference_cleanup',
                      source)
        self.assertIn('CBDK_R5_UI_LIFECYCLE_PASS ', source)
        self.assertNotIn('input_sources_private/', source)
        self.assertFalse(any(isinstance(n, ast.ImportFrom)
                             and n.module not in
                             ("__future__", "pathlib", "types", "zipfile")
                             for n in ast.walk(tree)))
        # Marker presence in source does not mean the native job ran.


if __name__ == "__main__":
    unittest.main()
