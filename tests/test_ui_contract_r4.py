"""R4 UI contract: authored plan -> generated ZIP -> panel -> operator preflight.

Only trusted CBDK-owned source/recipe files are read. The fixture compiles
bounded AST methods, not arbitrary addon source or user-supplied Python.
Synthetic contexts do NOT replace actual headless Blender or GUI tests.
"""
from __future__ import annotations

import ast
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, build_addon
from cbdk.ui_layout import plan_ui_layout
from parts.blender.context import (
    BlenderContextError, require_active_mesh, selected_mesh_objects,
)
from parts.blender.edit_mesh import count_edit_selection
from parts.blender.measure import mesh_world_bounds
from parts.blender.modifiers import modifier_snapshot
from parts.blender.edit_transform import (
    translation_unavailable_reason, translate_selected_vertices,
)
from test_ui_readiness_r2 import RecordingLayout, mesh_context


RECIPE_NAMES = (
    "modular_objects", "modular_edit", "modular_combined",
    "modular_geometry", "modular_nudge", "modular_all",
)
AUTHORED_OPS = {
    "object_selection": "cbdk.modular_selected_meshes",
    "edit_selection": "cbdk.modular_edit_selection",
    "mesh_bounds": "cbdk.modular_mesh_bounds",
    "modifier_summary": "cbdk.modular_modifier_summary",
    "vertex_nudge": "cbdk.modular_vertex_nudge",
}
EDIT_FEATURES = frozenset(("edit_selection", "vertex_nudge"))


def _generated_panel_namespace(source):
    """Compile only two fixed functions and the CBDK-authored draw method."""
    tree = ast.parse(source)
    assignments = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in (
                "_FEATURE_IDS", "_UI_SECTIONS", "_UI_OPTIONS"):
                assignments[target.id] = ast.literal_eval(node.value)
    assert set(assignments) == {"_FEATURE_IDS", "_UI_SECTIONS", "_UI_OPTIONS"}
    callback = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef)
                    and node.name == "_preview_unavailable_reason")
    panel = next(node for node in tree.body
                 if isinstance(node, ast.ClassDef)
                 and node.name == "VIEW3D_PT_cbdk_modular_preview")
    draw = next(node for node in panel.body
                if isinstance(node, ast.FunctionDef) and node.name == "draw")
    namespace = {
        **assignments,
        "isfinite": math.isfinite,
        "_EDIT_MODE_FEATURES": EDIT_FEATURES,
        "_FEATURE_MODULES": {"vertex_nudge": SimpleNamespace(
            ui_unavailable_reason=lambda ctx:
                translation_unavailable_reason(
                    ctx, tuple(ctx.scene.cbdk_modular_nudge_offset)
                ))},
        "_OPERATORS_BY_FEATURE": {
            fid: SimpleNamespace(bl_idname=AUTHORED_OPS[fid])
            for fid in assignments["_FEATURE_IDS"]},
    }
    code = compile(ast.fix_missing_locations(
        ast.Module(body=[callback, draw], type_ignores=[])),
        "<CBDK-generated-R4-trusted-AST>", "exec")
    exec(code, namespace)
    return namespace


def _draw(namespace, context):
    layout = RecordingLayout()
    namespace["draw"](SimpleNamespace(layout=layout), context)
    actual = {}
    for event in layout.events:
        if event[0] == "operator":
            actual[event[1]] = event[2]
    return actual, layout.events


def _visible_features(namespace, context_mode):
    mode = context_mode.lower()
    visible = []
    for (_, entries), style, modes in zip(
            namespace["_UI_SECTIONS"],
            namespace["_UI_OPTIONS"]["section_styles"],
            namespace["_UI_OPTIONS"]["control_visibility"]):
        if style["visible_in"] not in ("always", mode):
            continue
        visible.extend(fid for (fid, _), scope in zip(entries, modes)
                       if scope in ("always", mode))
    return tuple(visible)


def _assert_rejected_with_no_result_change(testcase, feature, context):
    """Run an actual authored feature execute method, with native guards.

    The selected invalid contexts fail before importing Blender's BMesh or
    mathutils runtime, so these Python tests stay headless.
    """
    feature_path = ROOT / "templates/modular_preview/features" / (feature + ".py")
    tree = ast.parse(feature_path.read_text(encoding="utf-8"))
    operator_classes = [node for node in tree.body
                        if isinstance(node, ast.ClassDef)
                        and any(isinstance(c, ast.Assign)
                                and any(isinstance(t, ast.Name) and t.id == "bl_idname"
                                        for t in c.targets) for c in node.body)]
    testcase.assertEqual(len(operator_classes), 1)
    methods = [node for node in operator_classes[0].body
               if isinstance(node, ast.FunctionDef) and node.name == "execute"]
    testcase.assertEqual(len(methods), 1)
    namespace = {
        "BlenderContextError": BlenderContextError,
        "require_active_mesh": require_active_mesh,
        "selected_mesh_objects": selected_mesh_objects,
        "count_edit_selection": count_edit_selection,
        "mesh_world_bounds": mesh_world_bounds,
        "modifier_snapshot": modifier_snapshot,
        "translate_selected_vertices": translate_selected_vertices,
    }
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=methods, type_ignores=[])),
        "<CBDK-authored-operator-execute>", "exec"), namespace)
    reports = []
    op = SimpleNamespace(
        offset=(0.0, 0.0, 0.1),
        report=lambda kind, msg: reports.append((kind, msg)),
    )
    before = context.scene.cbdk_modular_result
    before_mode = context.mode
    before_data = getattr(context.active_object, "data", None)
    outcome = namespace["execute"](op, context)
    testcase.assertEqual(outcome, {"CANCELLED"})
    testcase.assertEqual(context.scene.cbdk_modular_result, before)
    testcase.assertEqual(context.mode, before_mode)
    testcase.assertIs(getattr(context.active_object, "data", None), before_data)
    testcase.assertTrue(any("WARNING" in kind for kind, _ in reports))


class BuiltPreviewPlanContractTests(unittest.TestCase):
    def test_all_six_generated_recipes_have_exact_plan_and_safe_metadata(self):
        with tempfile.TemporaryDirectory(prefix="cbdk-ui-r4-") as temp:
            for name in RECIPE_NAMES:
                with self.subTest(recipe=name):
                    path = ROOT / "recipes" / (name + ".json")
                    data = json.loads(path.read_text(encoding="utf-8"))
                    expected_plan, expected_options = plan_ui_layout(
                        data["features"], root=ROOT, include_options=True)
                    archive_path = Path(temp) / (name + ".zip")
                    result = build_addon(
                        path, archive_path, root=ROOT, preview_unapproved=True)
                    self.assertEqual(result["package_id"], "cbdk_modular_preview")
                    self.assertFalse(result["approved"])
                    with ZipFile(archive_path) as archive:
                        prefix = "cbdk_modular_preview/"
                        generated = archive.read(prefix + "__init__.py").decode("utf-8")
                        metadata = json.loads(archive.read(prefix + "CBDK_BUILD_INFO.json"))
                    self.assertIs(metadata["preview_only"], True)
                    self.assertIs(metadata["approved"], False)
                    self.assertIs(metadata["redistribution_cleared"], False)
                    self.assertEqual(set(metadata["features"]), set(data["features"]))
                    self.assertEqual(metadata["ui_options"],
                                     json.loads(json.dumps(expected_options)))
                    namespace = _generated_panel_namespace(generated)
                    self.assertEqual(namespace["_UI_SECTIONS"], expected_plan)
                    self.assertEqual(namespace["_UI_OPTIONS"], expected_options)
                    self.assertEqual(set(namespace["_FEATURE_IDS"]),
                                     set(data["features"]))

                    for mode in ("OBJECT", "EDIT_MESH", "SCULPT"):
                        context = mesh_context(mode=mode)
                        observed, _ = _draw(namespace, context)
                        expected = _visible_features(namespace, mode)
                        self.assertEqual(set(observed),
                                         {AUTHORED_OPS[fid] for fid in expected})
                        for feature in expected:
                            # Mode mismatch shows a disabled button, not a
                            # hidden operator or false executable state.
                            required = ("EDIT_MESH" if feature in EDIT_FEATURES
                                        else "OBJECT")
                            self.assertEqual(observed[AUTHORED_OPS[feature]],
                                             mode == required)
                    self.assertEqual(namespace["_UI_OPTIONS"]["nudge_offset"]["size"], 3)

    def test_generated_all_recipe_invalid_contexts_and_execute_refusals_agree(self):
        with tempfile.TemporaryDirectory(prefix="cbdk-ui-r4-") as temp:
            name = "modular_all"
            recipe = ROOT / "recipes" / (name + ".json")
            archive_path = Path(temp) / "all.zip"
            build_addon(recipe, archive_path, root=ROOT, preview_unapproved=True)
            with ZipFile(archive_path) as archive:
                source = archive.read("cbdk_modular_preview/__init__.py").decode("utf-8")
            generated = _generated_panel_namespace(source)

            # Each row is a concrete *known-refusal* context. Readiness is
            # merely advisory; do not assert that positive readiness always
            # leads to success in a mutable Blender scene.
            cases = [
                ("no active data", "object_selection", mesh_context(data=False)),
                ("no selection collection", "object_selection", mesh_context()),
                ("empty mesh", "mesh_bounds", mesh_context(vertices=0)),
                ("invalid bounding corners", "mesh_bounds", mesh_context(bound_box=False)),
                ("invalid Object context", "modifier_summary", mesh_context(mode="EDIT_MESH")),
                ("two edit mesh datablocks", "edit_selection",
                 mesh_context(mode="EDIT_MESH", unique=2)),
                ("unknown edit objects", "edit_selection",
                 mesh_context(mode="EDIT_MESH", unique=1)),
                ("no nudge selection", "vertex_nudge",
                 mesh_context(mode="EDIT_MESH", selection=0)),
                ("two edit meshes for nudge", "vertex_nudge",
                 mesh_context(mode="EDIT_MESH", unique=2)),
            ]
            cases[1][2].selected_objects = None
            cases[6][2].objects_in_mode_unique_data = None
            for label, feature, context in cases:
                with self.subTest(label=label):
                    reason = generated["_preview_unavailable_reason"](feature, context)
                    self.assertIsInstance(reason, str)
                    self.assertTrue(reason)
                    observed, events = _draw(generated, context)
                    self.assertIn(AUTHORED_OPS[feature], observed)
                    self.assertFalse(observed[AUTHORED_OPS[feature]])
                    self.assertTrue(any(e[0] == "label" and reason in e[1]
                                        for e in events))
                    if label == "no nudge selection":
                        # Actual execute inspects fresh BMesh selection, which
                        # is Blender-only. Check its shared advisory contract
                        # here, leaving native CANCELLED to Blender smoke.
                        self.assertIn("Select at least one vertex",
                                      translation_unavailable_reason(
                                          context, (0.0, 0.0, 0.1)))
                    else:
                        _assert_rejected_with_no_result_change(
                            self, feature, context)

            # Bounds non-finite preview is a fixed-cost check, independent of
            # the size of mesh.vertices. Native mathutils/Blender refusal is
            # separate from this synthetic no-BMesh panel probe.
            for bad in (float("nan"), float("inf"), -float("inf")):
                ctx = mesh_context()
                ctx.active_object.bound_box[0] = (bad, 0.0, 0.0)
                reason = generated["_preview_unavailable_reason"]("mesh_bounds", ctx)
                self.assertIn("non-finite", reason)
                self.assertFalse(_draw(generated, ctx)[0][AUTHORED_OPS["mesh_bounds"]])

            ctx = mesh_context(mode="EDIT_MESH", selection=0)
            observed, events = _draw(generated, ctx)
            self.assertTrue(observed[AUTHORED_OPS["edit_selection"]])
            self.assertFalse(observed[AUTHORED_OPS["vertex_nudge"]])
            self.assertIn(("prop", "cbdk_modular_nudge_offset", True), events)

    def test_plan_catalog_cannot_add_unknown_operator_or_expand_nudge_range(self):
        # This is the same approved catalog's live contract, not a request to
        # grant additional execution authority to the preview generator.
        plan, opts = plan_ui_layout(list(AUTHORED_OPS), root=ROOT, include_options=True)
        self.assertEqual(len([f for _, buttons in plan for f, _ in buttons]), 5)
        self.assertEqual(opts["nudge_offset"]["min"], -10)
        self.assertEqual(opts["nudge_offset"]["max"], 10)
        self.assertNotIn("operator_id", json.dumps(opts))


if __name__ == "__main__":
    unittest.main()
