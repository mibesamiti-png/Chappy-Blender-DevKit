"""R11 ownership identity probes; mocks are separate from native CI proof."""
import ast
import unittest
from types import SimpleNamespace

from cbdk.addon_builder import ROOT
import test_ui_rolling_r3 as rolling
from test_ui_reload_r6 import _reload_guard


class R11OwnershipTests(unittest.TestCase):
    setUp = rolling.PreviewRollingLifecycleTests.setUp
    assert_fully_unregistered = rolling.PreviewRollingLifecycleTests.assert_fully_unregistered

    def test_missing_foreign_and_owned_looking_tokens_with_pending_class(self):
        for name in self.namespace['_PROPERTY_NAMES']:
            for kind in ('missing', 'foreign', 'owned_looking'):
                self.register()
                token = self.namespace['_OWNED_PROPERTY_TOKENS'][name]
                cls = self.namespace['_REGISTERED'][-1]
                original = self.utils.unregister_class
                def fail_class(value):
                    if value is cls:
                        raise RuntimeError('synthetic class failure')
                    return original(value)
                def fail_scene(owner, prop):
                    if prop == name:
                        raise RuntimeError('synthetic Scene failure')
                    return delattr(owner, prop)
                self.utils.unregister_class = fail_class
                self.namespace['delattr'] = fail_scene
                try:
                    with self.assertRaisesRegex(RuntimeError, 'cleanup incomplete'):
                        self.unregister()
                    self.assertIs(self.namespace['_OWNED_PROPERTY_TOKENS'][name], token)
                    delattr(self.scene, name)
                    foreign = None
                    if kind != 'missing':
                        foreign = (dict(token) if kind == 'owned_looking'
                                   else SimpleNamespace(name=name))
                        if kind == 'owned_looking':
                            self.assertEqual(foreign, token)
                        self.assertIsNot(foreign, token)
                        setattr(self.scene, name, foreign)
                    with self.assertRaisesRegex(RuntimeError, 'cleanup incomplete'):
                        self.unregister()
                    self.assertEqual(self.namespace['_REGISTERED'], [cls])
                    self.assertFalse(self.namespace['_OWNED_PROPERTIES'])
                    self.assertFalse(self.namespace['_OWNED_PROPERTY_TOKENS'])
                    self.assertIs(self.scene.__dict__.get(name), foreign)
                    with self.assertRaises(RuntimeError):
                        exec(_reload_guard(), self.namespace)
                    with self.assertRaises(RuntimeError):
                        self.register()
                finally:
                    self.utils.unregister_class = original
                    self.namespace.pop('delattr', None)
                    self.unregister()
                self.assert_fully_unregistered()
                self.assertIs(self.scene.__dict__.get(name), foreign)
                if foreign is not None:
                    delattr(self.scene, name)

    def test_native_r11_markers_are_in_existing_native_execution_path(self):
        source = (ROOT/'tests/blender_ui_lifecycle_r5.py').read_text()
        ast.parse(source)
        for marker in ('missing_scene_pending_class',
                       'foreign_and_owned_looking_identity',
                       'partial_retry_blocks_reload_register',
                       'disable_failure_explicit_recovery'):
            self.assertEqual(source.count('checks.append("native_r11_'+marker+'")'), 1)
        self.assertIn('handle_error=lambda exc:', source)
        self.assertIn('assert disable_errors == ["RuntimeError"]', source)
        # This static check alone is not proof that Blender ran the markers.
