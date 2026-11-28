"""R14: bounded multi-generation stale-module ownership regressions.

Python mocks model the ownership protocol only. Actual Blender evidence must
come from the 4.4.3, 4.5.15, and 5.2.1 native job logs.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_rolling_r3 import PreviewRollingLifecycleTests
from test_ui_readiness_r2 import _SceneMeta, _trusted_functions
from test_ui_reload_r6 import _reload_guard


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
MARKERS = (
    "native_r14_three_generation_class_identity",
    "native_r14_fresh_empty_ledger_is_unknown",
    "native_r14_foreign_collision_refused",
    "native_r14_all_old_references_explicitly_recovered",
    "native_r14_pending_scene_second_generation",
    "native_r14_foreign_scene_identity_recovered",
    "native_r14_reenable_after_all_generations",
)


class R14GenerationalOwnershipTests(unittest.TestCase):
    setUp = PreviewRollingLifecycleTests.setUp

    @staticmethod
    def fresh_namespace(original):
        # This emulates a *newly imported* trusted module's independently
        # initialized globals.  It is not a Python importlib native test.
        new = dict(original)
        new.update(_REGISTERED=[], _OWNED_PROPERTIES=[],
                   _OWNED_PROPERTY_TOKENS={})
        exec(_trusted_functions("register", "unregister"), new)
        return new

    def test_three_old_class_ledgers_are_not_visible_to_new_import(self):
        base = self.namespace
        classes = tuple(type("CBDK_R14_%d" % i, (), {}) for i in range(5))
        base["_CLASSES"] = classes
        current = base
        stale = []
        for fail_idx, keep_idx in ((4, 3), (3, 2), (2, 1)):
            with self.subTest(generation=len(stale)):
                expected_fail = classes[fail_idx]
                retained = classes[keep_idx]
                old_register = self.utils.register_class
                old_unregister = self.utils.unregister_class
                failed_registration = [0]
                failed_rollback = [0]

                def fail_selected_register(cls):
                    if cls is expected_fail and not failed_registration[0]:
                        failed_registration[0] += 1
                        raise RuntimeError("R14 controlled failed enable")
                    return old_register(cls)

                def fail_selected_rollback(cls):
                    if cls is retained and not failed_rollback[0]:
                        failed_rollback[0] += 1
                        raise RuntimeError("R14 controlled failed rollback")
                    return old_unregister(cls)

                self.utils.register_class = fail_selected_register
                self.utils.unregister_class = fail_selected_rollback
                try:
                    with self.assertRaisesRegex(
                            RuntimeError, "R14 controlled failed enable"):
                        current["register"]()
                finally:
                    self.utils.register_class = old_register
                    self.utils.unregister_class = old_unregister

                self.assertEqual(failed_registration, [1])
                self.assertEqual(failed_rollback, [1])
                self.assertEqual(current["_REGISTERED"], [retained])
                self.assertFalse(current["_OWNED_PROPERTIES"])
                self.assertFalse(current["_OWNED_PROPERTY_TOKENS"])
                self.assertFalse(hasattr(self.scene, "cbdk_modular_result"))
                stale.append((current, retained))
                self.assertEqual(
                    self.utils.active, {cls for _, cls in stale})
                with self.assertRaisesRegex(
                        RuntimeError, "unregistered before module reload"):
                    exec(_reload_guard(), current)

                fresh = self.fresh_namespace(current)
                self.assertIsNot(fresh, current)
                self.assertFalse(fresh["_REGISTERED"])
                self.assertFalse(fresh["_OWNED_PROPERTIES"])
                self.assertFalse(fresh["_OWNED_PROPERTY_TOKENS"])
                exec(_reload_guard(), fresh)
                # Fresh ledger says nothing about native resources owned by
                # previous generations. Thus global state is UNKNOWN.
                self.assertTrue(self.utils.active)
                current = fresh

        self.assertEqual(len(stale), 3)
        current["unregister"]()
        self.assertEqual(self.utils.active, {classes[1], classes[2], classes[3]})

        foreign = object()
        self.scene.cbdk_modular_result = foreign
        try:
            with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
                current["register"]()
            self.assertIs(self.scene.cbdk_modular_result, foreign)
            self.assertEqual(self.utils.active,
                             {classes[1], classes[2], classes[3]})
            for index, (old, retained) in enumerate(stale):
                old["unregister"]()
                self.assertFalse(old["_REGISTERED"])
                self.assertFalse(old["_OWNED_PROPERTIES"])
                self.assertFalse(old["_OWNED_PROPERTY_TOKENS"])
                self.assertNotIn(retained, self.utils.active)
                self.assertEqual(
                    self.utils.active,
                    {cls for _, cls in stale[index + 1:]})
                self.assertIs(self.scene.cbdk_modular_result, foreign)
        finally:
            if getattr(self.scene, "cbdk_modular_result", None) is foreign:
                del self.scene.cbdk_modular_result

        self.assertFalse(self.utils.active)
        current["register"]()
        self.assertEqual(len(self.utils.active), len(classes))
        current["unregister"]()
        self.assertFalse(self.utils.active)
        self.assertFalse(current["_REGISTERED"])

    def test_evicted_scene_token_rejects_fresh_import_until_old_retry(self):
        old = self.namespace
        self.utils.fail_register = self.b
        _SceneMeta.failed_deletions.add("cbdk_modular_result")
        try:
            with self.assertRaises(RuntimeError):
                old["register"]()
            self.assertFalse(old["_REGISTERED"])
            self.assertEqual(old["_OWNED_PROPERTIES"],
                             ["cbdk_modular_result"])
            owned_token = old["_OWNED_PROPERTY_TOKENS"][
                "cbdk_modular_result"]
            self.assertIs(self.scene.__dict__["cbdk_modular_result"],
                          owned_token)
            fresh = self.fresh_namespace(old)
            self.assertFalse(fresh["_OWNED_PROPERTIES"])
            self.assertIsNot(old["_OWNED_PROPERTY_TOKENS"],
                             fresh["_OWNED_PROPERTY_TOKENS"])
            with self.assertRaisesRegex(
                    RuntimeError, "Scene properties conflict"):
                fresh["register"]()
            fresh["unregister"]()
            self.assertIs(
                old["_OWNED_PROPERTY_TOKENS"]["cbdk_modular_result"],
                owned_token)
        finally:
            self.utils.fail_register = None
            _SceneMeta.failed_deletions.discard("cbdk_modular_result")

        foreign = object()
        self.scene.cbdk_modular_result = foreign
        old["unregister"]()
        self.assertFalse(old["_REGISTERED"])
        self.assertFalse(old["_OWNED_PROPERTIES"])
        self.assertFalse(old["_OWNED_PROPERTY_TOKENS"])
        self.assertIs(self.scene.cbdk_modular_result, foreign)
        with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
            fresh["register"]()
        self.assertIs(self.scene.cbdk_modular_result, foreign)
        del self.scene.cbdk_modular_result
        fresh["register"]()
        fresh["unregister"]()
        self.assertFalse(self.utils.active)


class R14NativeContractTests(unittest.TestCase):
    def test_r14_marker_contract_preserves_r13_and_features(self):
        source = NATIVE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(source.count(
                    'checks.append("' + marker + '")'), 1)
        self.assertIn("native_r13_failed_enable_evicts_live_module", source)
        self.assertIn("native_r12_three_failure_kinds_foreign_matrix", source)
        self.assertIn("addon_utils.enable(", source)
        self.assertIn("module = importlib.import_module(PACKAGE)", source)
        self.assertIn("owner.unregister()", source)
        self.assertIn("native_r14_foreign_scene_identity_recovered", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertNotIn("input_sources_private/", source)
        imports = {
            alias.name.partition(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(imports <= {
            "addon_utils", "bmesh", "bpy", "importlib", "json", "sys",
            "tempfile",
        })
        # Static marker validation is not actual Blender evidence.


if __name__ == "__main__":
    unittest.main()
