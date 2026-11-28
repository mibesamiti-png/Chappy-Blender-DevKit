"""R12 pure-Python ledger checks, distinct from actual addon_utils probes."""
import ast
import unittest

import test_ui_rolling_r3 as rolling
from test_ui_reload_r6 import _reload_guard
from cbdk.addon_builder import ROOT


class R12LedgerTests(unittest.TestCase):
    setUp = rolling.PreviewRollingLifecycleTests.setUp
    assert_fully_unregistered = rolling.PreviewRollingLifecycleTests.assert_fully_unregistered

    def test_explicit_retry_recovers_each_failure_kind_and_preserves_foreign(self):
        for kind in ('class', 'scene', 'both'):
            for name in self.namespace['_PROPERTY_NAMES']:
                self.register()
                cls = self.namespace['_REGISTERED'][-1]
                original = self.utils.unregister_class
                attempts = [0, 0]
                def fail_class(value):
                    if kind != 'scene' and value is cls and not attempts[0]:
                        attempts[0] += 1
                        raise RuntimeError('synthetic class failure')
                    return original(value)
                def fail_scene(owner, prop):
                    if kind != 'class' and prop == name and not attempts[1]:
                        attempts[1] += 1
                        raise RuntimeError('synthetic Scene failure')
                    return delattr(owner, prop)
                self.utils.unregister_class = fail_class
                self.namespace['delattr'] = fail_scene
                foreign = object()
                try:
                    with self.assertRaises(RuntimeError):
                        self.unregister()
                    self.assertEqual(bool(self.namespace['_REGISTERED']), kind != 'scene')
                    self.assertEqual(bool(self.namespace['_OWNED_PROPERTIES']), kind != 'class')
                    setattr(self.scene, name, foreign)
                    with self.assertRaises(RuntimeError):
                        self.register()
                    with self.assertRaises(RuntimeError):
                        exec(_reload_guard(), self.namespace)
                    self.unregister()
                    self.assert_fully_unregistered()
                    self.assertIs(getattr(self.scene, name), foreign)
                finally:
                    self.utils.unregister_class = original
                    self.namespace.pop('delattr', None)
                    self.unregister()
                    if getattr(self.scene, name, None) is foreign:
                        delattr(self.scene, name)

    def test_native_matrix_and_r11_execution_contract_retained(self):
        source = (ROOT/'tests/blender_ui_lifecycle_r5.py').read_text()
        ast.parse(source)
        for marker in ('three_failure_kinds_foreign_matrix',
                       'second_disable_keeps_pending_ledgers',
                       'reenable_eviction_original_reference_cleanup',
                       'explicit_recovery_no_owned_leaks'):
            self.assertEqual(source.count('checks.append("native_r12_'+marker+'")'), 1)
        self.assertIn('assert PACKAGE not in sys.modules', source)
        self.assertIn('assert module.__addon_enabled__ is False', source)
        self.assertIn('native_r11_disable_failure_explicit_recovery', source)
