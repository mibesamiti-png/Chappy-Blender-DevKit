"""R9 Scene RNA deletion-failure recovery tests, Team C owned.

Mocked bpy registration tests are NOT native Blender evidence. The C-owned
native lifecycle probe must still run on Blender 4.4.3, 4.5.15 and 5.2.1.
"""
from __future__ import annotations

import ast
import unittest

from cbdk.addon_builder import ROOT
from test_ui_rolling_r3 import PreviewRollingLifecycleTests
from test_ui_reload_r6 import _reload_guard


NATIVE = ROOT / "tests" / "blender_ui_lifecycle_r5.py"
R9_MARKERS = (
    "native_r9_scene_delete_failure_retains_ledger",
    "native_r9_pending_cleanup_reload_rejected",
    "native_r9_foreign_replace_retry_preserved",
    "native_r9_owned_delete_retry_recovered",
)


class R9SceneDeletionRetryTests(unittest.TestCase):
    def setUp(self):
        # Borrow only fixture setup and its full-detach assertion; do not
        # accidentally inherit previous test cases.
        PreviewRollingLifecycleTests.setUp(self)

    assert_fully_unregistered = PreviewRollingLifecycleTests.assert_fully_unregistered

    def test_foreign_replacement_after_failed_scene_delete_preserved_for_both_names(self):
        for failing_name in self.namespace["_PROPERTY_NAMES"]:
            with self.subTest(name=failing_name):
                self.register()
                token = self.namespace["_OWNED_PROPERTY_TOKENS"][failing_name]
                other_name = next(x for x in self.namespace["_PROPERTY_NAMES"]
                                  if x != failing_name)
                assert "delattr" not in self.namespace
                attempts = [0]

                def fail_first(owner, name):
                    if (owner is self.scene and name == failing_name
                            and attempts[0] == 0):
                        attempts[0] += 1
                        raise RuntimeError("R9 injected property deletion failure")
                    return delattr(owner, name)

                # exec() of the trusted template's register/unregister copies
                # the functions into this namespace. Shadow *only* this one
                # global name, never the Python builtin or Blender metaclass.
                self.namespace["delattr"] = fail_first
                try:
                    with self.assertRaisesRegex(
                            RuntimeError, "cleanup incomplete"):
                        self.unregister()
                finally:
                    self.namespace.pop("delattr", None)

                self.assertEqual(attempts, [1])
                self.assertFalse(self.utils.active)
                self.assertEqual(self.namespace["_REGISTERED"], [])
                self.assertEqual(self.namespace["_OWNED_PROPERTIES"],
                                 [failing_name])
                self.assertEqual(set(self.namespace["_OWNED_PROPERTY_TOKENS"]),
                                 {failing_name})
                self.assertIs(
                    self.namespace["_OWNED_PROPERTY_TOKENS"][failing_name],
                    token)
                self.assertIs(self.scene.__dict__[failing_name], token)
                self.assertFalse(hasattr(self.scene, other_name))
                with self.assertRaisesRegex(
                        RuntimeError, "unregistered before module reload"):
                    exec(_reload_guard(), self.namespace)
                with self.assertRaisesRegex(RuntimeError, "already registered"):
                    self.register()

                foreign = object()
                setattr(self.scene, failing_name, foreign)
                self.unregister()
                self.assert_fully_unregistered()
                self.assertIs(getattr(self.scene, failing_name), foreign)
                with self.assertRaisesRegex(
                        RuntimeError, "Scene properties conflict"):
                    self.register()
                self.assertIs(getattr(self.scene, failing_name), foreign)
                delattr(self.scene, failing_name)
                self.register()
                self.unregister()
                self.assert_fully_unregistered()

    def test_repeated_deletion_error_retains_owned_token_until_success(self):
        self.register()
        name = self.namespace["_PROPERTY_NAMES"][1]
        token = self.namespace["_OWNED_PROPERTY_TOKENS"][name]
        attempts = [0]

        def fail_twice(owner, key):
            if owner is self.scene and key == name and attempts[0] < 2:
                attempts[0] += 1
                raise RuntimeError("R9 twice-injected deletion failure")
            return delattr(owner, key)

        self.namespace["delattr"] = fail_twice
        try:
            for attempt in range(2):
                with self.subTest(attempt=attempt):
                    with self.assertRaisesRegex(
                            RuntimeError, "cleanup incomplete"):
                        self.unregister()
                    self.assertFalse(self.utils.active)
                    self.assertFalse(self.namespace["_REGISTERED"])
                    self.assertEqual(self.namespace["_OWNED_PROPERTIES"], [name])
                    self.assertIs(
                        self.namespace["_OWNED_PROPERTY_TOKENS"][name], token)
                    with self.assertRaisesRegex(
                            RuntimeError, "unregistered before module reload"):
                        exec(_reload_guard(), self.namespace)
        finally:
            self.namespace.pop("delattr", None)

        self.assertEqual(attempts, [2])
        self.unregister()
        self.assert_fully_unregistered()
        self.assertFalse(hasattr(self.scene, name))
        self.register()
        self.unregister()
        self.assert_fully_unregistered()


class R9NativeProbeContractTests(unittest.TestCase):
    def test_native_probe_contains_each_r9_runtime_check_exactly_once(self):
        source = NATIVE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for marker in R9_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(source.count('checks.append("' + marker + '")'), 1)
        self.assertIn('module.__dict__["delattr"] = fail_one_scene_delete',
                      source)
        self.assertIn('module.__dict__.pop("delattr", None)', source)
        self.assertIn('module._OWNED_PROPERTY_TOKENS[failing_name] is owned_token',
                      source)
        self.assertIn('module._OWNED_PROPERTIES == [failing_name]', source)
        self.assertIn("importlib.reload(module)", source)
        self.assertIn("CBDK_R5_UI_LIFECYCLE_PASS ", source)
        self.assertNotIn("input_sources_private/", source)
        imported = {
            name.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for name in node.names
        }
        self.assertTrue(imported <= {
            "addon_utils", "bmesh", "bpy", "importlib", "json", "sys",
            "tempfile",
        })
        # A string in the script is not evidence it ran in real Blender.


if __name__ == "__main__":
    unittest.main()
