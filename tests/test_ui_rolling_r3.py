"""Team C R3 rolling regression: repeated mode switching and RNA ownership.

Execute only trusted CBDK template AST against synthetic Blender-like contexts.
This is not a real GUI, native Blender OOM, or registration crash test.
"""
from __future__ import annotations

import unittest
from math import isfinite
from types import SimpleNamespace

from test_ui_readiness_r2 import (
    FEATURES, EDIT_FEATURES, IDS, RecordingLayout, mesh_context,
    _FakeUtils, _SceneMeta, _trusted_functions,
)


class PreviewRollingModeTests(unittest.TestCase):
    def setUp(self):
        self.namespace = {
            "isfinite": isfinite,
            "_EDIT_MODE_FEATURES": EDIT_FEATURES,
            "_FEATURE_MODULES": {"vertex_nudge": SimpleNamespace(
                ui_unavailable_reason=lambda ctx:
                    ("Select at least one vertex before translating"
                     if ctx.active_object.data.total_vert_sel == 0 else None))},
            "_UI_SECTIONS": (("Mixed preview", tuple(
                (feature, feature) for feature in FEATURES)),),
            "_UI_OPTIONS": {
                "section_styles": ({"visible_in": "always", "boxed": True,
                                    "layout": "column"},),
                "control_visibility": (("object", "object", "object",
                                        "edit_mesh", "edit_mesh"),),
            },
            "_OPERATORS_BY_FEATURE": {
                feature: SimpleNamespace(bl_idname=IDS[feature])
                for feature in FEATURES},
        }
        exec(_trusted_functions("_preview_unavailable_reason", draw=True),
             self.namespace)

    def draw(self, context):
        layout = RecordingLayout()
        self.namespace["draw"](SimpleNamespace(layout=layout), context)
        return layout.events

    def test_repeated_object_edit_sculpt_cycles_do_not_leak_buttons(self):
        ctx = mesh_context()
        for _ in range(6):
            for mode, expected in (
                ("OBJECT", {IDS[f] for f in FEATURES[:3]}),
                ("EDIT_MESH", {IDS[f] for f in FEATURES[3:]}),
                ("SCULPT", set()),
            ):
                ctx.mode = mode
                events = self.draw(ctx)
                self.assertEqual(
                    {e[1] for e in events if e[0] == "operator"}, expected)
                self.assertEqual(
                    bool([e for e in events if e[0] == "prop"]),
                    mode == "EDIT_MESH")

    def test_switching_mesh_and_selection_never_enables_wrong_action(self):
        ctx = mesh_context(mode="EDIT_MESH", selection=0)
        for _ in range(5):
            events = self.draw(ctx)
            self.assertIn(("prop", "cbdk_modular_nudge_offset", True), events)
            self.assertIn(("operator", IDS["vertex_nudge"], False), events)
            ctx.active_object.data.total_vert_sel = 1
            self.assertIn(("operator", IDS["vertex_nudge"], True),
                          self.draw(ctx))
            ctx.mode = "OBJECT"
            self.assertNotIn(("operator", IDS["vertex_nudge"], True),
                             self.draw(ctx))
            ctx.active_object.data = None
            self.assertTrue(all(not event[2] for event in self.draw(ctx)
                                if event[0] == "operator"))
            ctx.active_object.data = SimpleNamespace(
                vertices=[0, 1, 2], total_vert_sel=0)
            ctx.mode = "EDIT_MESH"

    def test_missing_mode_fails_closed_instead_of_crashing_draw(self):
        ctx = mesh_context()
        for value in (None, 0, False, []):
            with self.subTest(value=value):
                ctx.mode = value
                events = self.draw(ctx)
                self.assertFalse(any(e[0] == "operator" for e in events))
                self.assertIn(("label", "No preview controls for this mode"),
                              events)


class PreviewRollingLifecycleTests(unittest.TestCase):
    def setUp(self):
        class Scene(metaclass=_SceneMeta):
            pass
        _SceneMeta.failed_deletions = set()
        self.scene = Scene
        self.a = type("CBDK_R3_One", (), {})
        self.b = type("CBDK_R3_Two", (), {})
        self.utils = _FakeUtils()
        self.namespace = {
            "bpy": SimpleNamespace(
                types=SimpleNamespace(Scene=self.scene),
                utils=self.utils,
                props=SimpleNamespace(
                    StringProperty=lambda **kw: kw,
                    FloatVectorProperty=lambda **kw: kw)),
            "_CLASSES": (self.a, self.b),
            "_REGISTERED": [],
            "_OWNED_PROPERTIES": [],
            "_OWNED_PROPERTY_TOKENS": {},
            "_PROPERTY_NAMES": ("cbdk_modular_result",
                                "cbdk_modular_nudge_offset"),
            "_UI_OPTIONS": {"nudge_offset": {
                "size": 3, "min": -10.0, "max": 10.0,
                "default": (0.0, 0.0, 0.1)}},
        }
        exec(_trusted_functions("register", "unregister"), self.namespace)
        self.register = self.namespace["register"]
        self.unregister = self.namespace["unregister"]

    def assert_fully_unregistered(self):
        self.assertFalse(self.utils.active)
        self.assertFalse(self.namespace["_REGISTERED"])
        self.assertFalse(self.namespace["_OWNED_PROPERTIES"])
        self.assertFalse(self.namespace["_OWNED_PROPERTY_TOKENS"])

    def test_six_register_unregister_cycles_reject_duplicate_registration(self):
        for _ in range(6):
            self.register()
            self.assertEqual(len(self.utils.active), 2)
            with self.assertRaisesRegex(RuntimeError, "already registered"):
                self.register()
            self.assertEqual(len(self.utils.active), 2)
            self.unregister()
            self.unregister()
            self.assert_fully_unregistered()
            self.assertFalse(hasattr(self.scene, "cbdk_modular_result"))

    def test_foreign_property_replacement_is_not_deleted_by_unregister(self):
        self.register()
        originally_owned = self.scene.__dict__["cbdk_modular_result"]
        foreign_value = object()
        self.scene.cbdk_modular_result = foreign_value
        self.assertIsNot(self.scene.__dict__["cbdk_modular_result"],
                         originally_owned)
        self.unregister()
        self.assert_fully_unregistered()
        self.assertIs(self.scene.cbdk_modular_result, foreign_value)
        self.assertFalse(hasattr(self.scene, "cbdk_modular_nudge_offset"))
        with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
            self.register()
        self.assertIs(self.scene.cbdk_modular_result, foreign_value)
        del self.scene.cbdk_modular_result
        self.register()
        self.unregister()
        self.assert_fully_unregistered()

    def test_foreign_replacement_after_controlled_failure_survives_retry(self):
        self.register()
        _SceneMeta.failed_deletions.add("cbdk_modular_result")
        with self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
            self.unregister()
        self.assertIn("cbdk_modular_result",
                      self.namespace["_OWNED_PROPERTY_TOKENS"])
        foreign = object()
        self.scene.cbdk_modular_result = foreign
        self.unregister()
        self.assert_fully_unregistered()
        self.assertIs(self.scene.cbdk_modular_result, foreign)
        with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
            self.register()
        del self.scene.cbdk_modular_result

    def test_repeated_foreign_collision_cannot_alter_existing_property(self):
        foreign = object()
        self.scene.cbdk_modular_nudge_offset = foreign
        for _ in range(4):
            with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
                self.register()
            self.assertIs(self.scene.cbdk_modular_nudge_offset, foreign)
            self.assert_fully_unregistered()
        del self.scene.cbdk_modular_nudge_offset
        self.register()
        self.unregister()
        self.assert_fully_unregistered()

    def test_transient_class_unregister_failure_still_allows_next_cycle(self):
        for _ in range(3):
            self.register()
            self.utils.fail_unregister = self.a
            with self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
                self.unregister()
            self.assertEqual(self.namespace["_REGISTERED"], [self.a])
            self.assertFalse(self.namespace["_OWNED_PROPERTY_TOKENS"])
            with self.assertRaisesRegex(RuntimeError, "already registered"):
                self.register()
            self.unregister()
            self.assert_fully_unregistered()


if __name__ == "__main__":
    unittest.main()
