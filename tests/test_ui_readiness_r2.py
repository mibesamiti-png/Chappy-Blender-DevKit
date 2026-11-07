"""Synthetic R2 panel-readiness and retry tests; execute CBDK-authored AST only.

No Blender import, private addon import, BMesh scan or user-provided code.
The actual built-in operators remain the authority for execute-time safety.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from cbdk.addon_builder import ROOT


TEMPLATE = ROOT / "templates/modular_preview/__init__.py"
FEATURES = (
    "object_selection", "mesh_bounds", "modifier_summary",
    "edit_selection", "vertex_nudge",
)
IDS = {feature: "cbdk.modular_" + feature for feature in FEATURES}
EDIT_FEATURES = frozenset(("edit_selection", "vertex_nudge"))


def _trusted_functions(*names, draw=False):
    tree = ast.parse(TEMPLATE.read_text(encoding="utf-8"))
    selected = [node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    if draw:
        panel = next(node for node in tree.body
                     if isinstance(node, ast.ClassDef)
                     and node.name == "VIEW3D_PT_cbdk_modular_preview")
        selected.extend(node for node in panel.body
                        if isinstance(node, ast.FunctionDef) and node.name == "draw")
    if len(selected) != len(names) + bool(draw):
        raise AssertionError("Trusted template methods changed")
    return compile(ast.fix_missing_locations(
        ast.Module(body=selected, type_ignores=[])), "<trusted-CBDK-r2>", "exec")


class RecordingLayout:
    """Record each field/action's *effective* enabled value, including parents."""

    def __init__(self, events=None, parent_enabled=True):
        self.events = [] if events is None else events
        self._enabled = parent_enabled

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = self._enabled and bool(value)
        self.events.append(("enabled", self._enabled))

    def row(self, align=False):
        return RecordingLayout(self.events, self._enabled)

    def column(self, align=False):
        return RecordingLayout(self.events, self._enabled)

    def box(self):
        return RecordingLayout(self.events, self._enabled)

    def label(self, *, text):
        self.events.append(("label", text))

    def prop(self, scene, name, *, text):
        self.events.append(("prop", name, self._enabled))

    def operator(self, identifier, *, text):
        self.events.append(("operator", identifier, self._enabled))
        return SimpleNamespace(offset=None)


def mesh_context(*, mode="OBJECT", vertices=3, data=True, mesh=True,
                 bound_box=True, selection=1, unique=1):
    obj = SimpleNamespace(
        type="MESH" if mesh else "LIGHT",
        data=(SimpleNamespace(vertices=list(range(vertices)),
                              total_vert_sel=selection)
              if data else None),
        bound_box=[(0.0, 0.0, 0.0)] * 8 if bound_box else None,
    )
    scene = SimpleNamespace(cbdk_modular_nudge_offset=(0.0, 0.0, 0.1),
                            cbdk_modular_result="No inspection yet")
    return SimpleNamespace(
        mode=mode, active_object=obj, scene=scene,
        objects_in_mode_unique_data=tuple(
            SimpleNamespace(type="MESH") for _ in range(unique)
        ),
    )


class PreviewReadinessTests(unittest.TestCase):
    def setUp(self):
        self.namespace = {
            "_EDIT_MODE_FEATURES": EDIT_FEATURES,
            "_FEATURE_MODULES": {"vertex_nudge": SimpleNamespace(
                ui_unavailable_reason=lambda ctx:
                    "Select at least one vertex before translating"
                    if ctx.active_object.data.total_vert_sel < 1 else None)},
            "_UI_SECTIONS": (("Mixed authored preview", tuple(
                (feature, feature) for feature in FEATURES)),),
            "_UI_OPTIONS": {
                "section_styles": ({"visible_in": "always", "boxed": False,
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
        self.reason = self.namespace["_preview_unavailable_reason"]

    def draw(self, context):
        layout = RecordingLayout()
        self.namespace["draw"](SimpleNamespace(layout=layout), context)
        return layout.events

    def test_object_mode_normal_mesh_all_three_readonly_buttons_enabled(self):
        ctx = mesh_context()
        for feature in FEATURES[:3]:
            self.assertIsNone(self.reason(feature, ctx))
        buttons = [e for e in self.draw(ctx) if e[0] == "operator"]
        self.assertEqual([(x[1], x[2]) for x in buttons],
                         [(IDS[f], True) for f in FEATURES[:3]])

    def test_empty_mesh_only_bounds_disabled_while_other_readers_work(self):
        ctx = mesh_context(vertices=0)
        self.assertIn("contain vertices", self.reason("mesh_bounds", ctx))
        events = self.draw(ctx)
        self.assertIn(("operator", IDS["mesh_bounds"], False), events)
        self.assertIn(("operator", IDS["object_selection"], True), events)
        self.assertIn(("operator", IDS["modifier_summary"], True), events)
        self.assertTrue(any(e[0] == "label" and "contain vertices" in e[1]
                            for e in events))

    def test_invalid_bounding_box_is_disabled_without_geometry_evaluation(self):
        ctx = mesh_context(bound_box=False)
        self.assertIn("bounding box", self.reason("mesh_bounds", ctx))
        self.assertIn(("operator", IDS["mesh_bounds"], False), self.draw(ctx))

    def test_no_data_and_non_mesh_are_rejected_for_all_features(self):
        for ctx in (mesh_context(data=False), mesh_context(mesh=False)):
            for mode, features in (("OBJECT", FEATURES[:3]),
                                   ("EDIT_MESH", FEATURES[3:])):
                ctx.mode = mode
                for feature in features:
                    self.assertIn("active mesh", self.reason(feature, ctx))
                events = self.draw(ctx)
                self.assertTrue(all(not event[2] for event in events
                                    if event[0] == "operator"))

    def test_missing_active_object_does_not_raise(self):
        ctx = mesh_context()
        ctx.active_object = None
        self.assertIn("active mesh", self.reason("mesh_bounds", ctx))
        self.assertIn(("operator", IDS["mesh_bounds"], False), self.draw(ctx))

    def test_multiple_unique_edit_meshes_disable_selection_and_nudge(self):
        ctx = mesh_context(mode="EDIT_MESH", unique=2)
        # Nudge's existing module-owned check refuses multi-object Edit Mode.
        self.namespace["_FEATURE_MODULES"]["vertex_nudge"] = SimpleNamespace(
            ui_unavailable_reason=lambda _: "Exactly one unique mesh must be in Edit Mode")
        for feature in ("edit_selection", "vertex_nudge"):
            self.assertIn("Exactly one unique mesh", self.reason(feature, ctx))
        events = self.draw(ctx)
        self.assertIn(("operator", IDS["edit_selection"], False), events)
        self.assertIn(("operator", IDS["vertex_nudge"], False), events)
        # Editing XYZ is still possible when mesh + mode are valid.
        self.assertIn(("prop", "cbdk_modular_nudge_offset", True), events)

    def test_unknown_multiedit_state_is_not_assumed_safe(self):
        ctx = mesh_context(mode="EDIT_MESH")
        ctx.objects_in_mode_unique_data = None
        self.assertIn("Cannot verify", self.reason("edit_selection", ctx))
        self.assertIn(("operator", IDS["edit_selection"], False), self.draw(ctx))

    def test_zero_selection_keeps_xyz_editable_while_action_disabled(self):
        ctx = mesh_context(mode="EDIT_MESH", selection=0)
        events = self.draw(ctx)
        self.assertIn(("operator", IDS["edit_selection"], True), events)
        self.assertIn(("prop", "cbdk_modular_nudge_offset", True), events)
        self.assertIn(("operator", IDS["vertex_nudge"], False), events)
        self.assertTrue(any(e[0] == "label" and "Select at least one" in e[1]
                            for e in events))

    def test_existing_mixed_mode_controls_are_visibility_filtered(self):
        for mode, visible in (("OBJECT", set(FEATURES[:3])),
                              ("EDIT_MESH", set(FEATURES[3:])),
                              ("SCULPT", set())):
            ctx = mesh_context(mode=mode)
            observed = {e[1] for e in self.draw(ctx) if e[0] == "operator"}
            self.assertEqual(observed, {IDS[feature] for feature in visible})

    def test_advisory_is_not_blender_edit_authorization(self):
        # This test never executes a Blender operator. Its result is a hint
        # based on current cached context, not a geometry/Undo guarantee.
        ctx = mesh_context(mode="EDIT_MESH", selection=1)
        self.assertIsNone(self.reason("vertex_nudge", ctx))
        ctx.active_object.data.total_vert_sel = 0
        self.assertIn("Select", self.reason("vertex_nudge", ctx))


class _SceneMeta(type):
    failed_deletions = set()

    def __delattr__(cls, name):
        if name in cls.failed_deletions:
            cls.failed_deletions.remove(name)
            raise RuntimeError("controlled Scene property deletion failure")
        return super().__delattr__(name)


class _FakeUtils:
    def __init__(self):
        self.active = set()
        self.fail_register = None
        self.fail_unregister = None

    def register_class(self, cls):
        if cls is self.fail_register:
            raise RuntimeError("controlled class registration failure")
        self.active.add(cls)

    def unregister_class(self, cls):
        if cls is self.fail_unregister:
            self.fail_unregister = None
            raise RuntimeError("controlled class unregister failure")
        self.active.remove(cls)


class RetryAndCollisionTests(unittest.TestCase):
    def setUp(self):
        class Scene(metaclass=_SceneMeta):
            pass

        _SceneMeta.failed_deletions = set()
        self.scene = Scene
        self.first = type("CBDK_Test_One", (), {})
        self.second = type("CBDK_Test_Two", (), {})
        self.utils = _FakeUtils()
        props = SimpleNamespace(StringProperty=lambda **kw: kw,
                                FloatVectorProperty=lambda **kw: kw)
        self.namespace = {
            "bpy": SimpleNamespace(types=SimpleNamespace(Scene=self.scene),
                                   utils=self.utils, props=props),
            "_CLASSES": (self.first, self.second),
            "_REGISTERED": [],
            "_OWNED_PROPERTIES": [],
            "_OWNED_PROPERTY_TOKENS": {},
            "_PROPERTY_NAMES": ("cbdk_modular_result", "cbdk_modular_nudge_offset"),
            "_UI_OPTIONS": {"nudge_offset": {"size": 3, "min": -10., "max": 10.,
                                             "default": (0., 0., 0.1)}},
        }
        exec(_trusted_functions("register", "unregister"), self.namespace)
        self.register = self.namespace["register"]
        self.unregister = self.namespace["unregister"]

    def test_scene_property_deletion_failure_retained_for_retry(self):
        self.register()
        _SceneMeta.failed_deletions.add("cbdk_modular_result")
        with self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
            self.unregister()
        self.assertEqual(self.namespace["_OWNED_PROPERTIES"], ["cbdk_modular_result"])
        self.assertFalse(self.namespace["_REGISTERED"])
        self.assertFalse(self.utils.active)
        self.assertTrue(hasattr(self.scene, "cbdk_modular_result"))
        self.assertFalse(hasattr(self.scene, "cbdk_modular_nudge_offset"))
        with self.assertRaisesRegex(RuntimeError, "already registered"):
            self.register()
        self.unregister()
        self.assertFalse(self.namespace["_OWNED_PROPERTIES"])
        self.register()
        self.unregister()

    def test_concurrent_class_and_property_cleanup_failures_are_retryable(self):
        self.register()
        self.utils.fail_unregister = self.first
        _SceneMeta.failed_deletions.add("cbdk_modular_nudge_offset")
        with self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
            self.unregister()
        self.assertEqual(self.namespace["_REGISTERED"], [self.first])
        self.assertEqual(self.namespace["_OWNED_PROPERTIES"],
                         ["cbdk_modular_nudge_offset"])
        self.assertNotIn(self.second, self.utils.active)
        self.unregister()
        self.assertFalse(self.utils.active)
        self.assertFalse(self.namespace["_REGISTERED"])
        self.assertFalse(self.namespace["_OWNED_PROPERTIES"])

    def test_foreign_scene_property_collision_never_deletes_foreign_value(self):
        foreign = object()
        self.scene.cbdk_modular_result = foreign
        with self.assertRaisesRegex(RuntimeError, "Scene properties conflict"):
            self.register()
        self.assertIs(self.scene.cbdk_modular_result, foreign)
        self.assertFalse(hasattr(self.scene, "cbdk_modular_nudge_offset"))
        self.assertFalse(self.utils.active)
        del self.scene.cbdk_modular_result

    def test_primary_register_error_survives_secondary_cleanup_failure(self):
        self.utils.fail_register = self.second
        _SceneMeta.failed_deletions.add("cbdk_modular_nudge_offset")
        with self.assertRaisesRegex(RuntimeError, "controlled class registration") as caught:
            self.register()
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)
        self.assertIn("cleanup incomplete", str(caught.exception.__cause__))
        self.assertIsNotNone(caught.exception.__cause__.__cause__)
        self.assertIn("controlled Scene property deletion",
                      str(caught.exception.__cause__.__cause__))
        self.assertEqual(self.namespace["_OWNED_PROPERTIES"],
                         ["cbdk_modular_nudge_offset"])
        self.assertFalse(self.utils.active)
        self.unregister()
        self.utils.fail_register = None
        self.register()
        self.unregister()


if __name__ == "__main__":
    unittest.main()
