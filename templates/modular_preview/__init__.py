"""CBDK v0.11 recipe-composed read-only development preview.

Only trusted authored feature modules are loaded, selected at build time.
Do not install two modular-preview variants simultaneously: they share class
and operator identifiers and are intended to replace one another.
"""
bl_info = {
    "name": __CBDK_DISPLAY_NAME__,
    "author": "Chappy Blender DevKit (private development preview)",
    "version": (0, 16, 0),
    "blender": (4, 4, 0),
    "location": "3D View > Sidebar > CBDK",
    "description": "Recipe-built mesh inspection preview; no topology editing",
    "category": "3D View",
}

import importlib
import bpy

_FEATURE_IDS = __CBDK_FEATURE_IDS__
_UI_SECTIONS = __CBDK_UI_SECTIONS__
_UI_OPTIONS = __CBDK_UI_OPTIONS__
_FEATURE_MODULES = {feature: importlib.import_module("." + feature, __name__ + ".features")
                    for feature in _FEATURE_IDS}
_OPERATORS = [_FEATURE_MODULES[feature].OPERATOR_CLASS for feature in _FEATURE_IDS]
_OPERATORS_BY_FEATURE = dict(zip(_FEATURE_IDS, _OPERATORS))
# Fixed context map for the five reviewed CBDK-authored operators.
# Recipes/JSON cannot inject a new context or an arbitrary operator.
_OBJECT_MODE_FEATURES = frozenset(("object_selection", "mesh_bounds", "modifier_summary"))
_EDIT_MODE_FEATURES = frozenset(("edit_selection", "vertex_nudge"))
assert set(_FEATURE_IDS) <= _OBJECT_MODE_FEATURES | _EDIT_MODE_FEATURES



# This is only a cheap panel hint; every operator must revalidate its live
# context and geometry during execute(). Never scan BMesh in Panel.draw.
def _preview_unavailable_reason(feature_id, context):
    active = getattr(context, "active_object", None)
    mesh = getattr(active, "data", None)
    if active is None or getattr(active, "type", None) != "MESH" or mesh is None:
        return "An active mesh object is required"
    required_mode = "EDIT_MESH" if feature_id in _EDIT_MODE_FEATURES else "OBJECT"
    if getattr(context, "mode", None) != required_mode:
        return "Switch to " + required_mode + " mode"

    if feature_id == "mesh_bounds":
        vertices = getattr(mesh, "vertices", None)
        if vertices is None or len(vertices) == 0:
            return "Active mesh must contain vertices"
        corners = getattr(active, "bound_box", None)
        if corners is None or len(corners) != 8:
            return "Active mesh has no valid bounding box"
    elif feature_id == "edit_selection":
        objects = getattr(context, "objects_in_mode_unique_data", None)
        if objects is None:
            return "Cannot verify multi-object Edit Mode state"
        if sum(1 for obj in objects if getattr(obj, "type", None) == "MESH") != 1:
            return "Exactly one unique mesh must be in Edit Mode"
    elif feature_id == "vertex_nudge":
        return _FEATURE_MODULES[feature_id].ui_unavailable_reason(context)
    return None


class VIEW3D_PT_cbdk_modular_preview(bpy.types.Panel):
    bl_label = "CBDK Modular Preview"
    bl_idname = "VIEW3D_PT_cbdk_modular_preview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CBDK"

    def draw(self, context):
        col = self.layout.column(align=True)
        visible_sections = 0
        for index, (title, buttons) in enumerate(_UI_SECTIONS):
            style = _UI_OPTIONS["section_styles"][index]
            if style["visible_in"] not in ("always", context.mode.lower()):
                continue
            control_modes = _UI_OPTIONS["control_visibility"][index]
            visible_buttons = [(feature_id, label) for (feature_id, label), mode in
                               zip(buttons, control_modes)
                               if mode in ("always", context.mode.lower())]
            if not visible_buttons:
                continue
            visible_sections += 1
            group = col.box() if style["boxed"] else col.column(align=True)
            group.label(text=title)
            body = group.row(align=True) if style["layout"] == "row" else group
            for feature_id, label in visible_buttons:
                button_row = body.row(align=True)
                reason = _preview_unavailable_reason(feature_id, context)
                if feature_id == "vertex_nudge":
                    # A disabled nudge action must not also disable its XYZ
                    # editor. Only disable the input for invalid mesh/mode.
                    active = getattr(context, "active_object", None)
                    button_row.enabled = (
                        getattr(active, "type", None) == "MESH"
                        and getattr(active, "data", None) is not None
                        and getattr(context, "mode", None) == "EDIT_MESH"
                    )
                    button_row.prop(context.scene, "cbdk_modular_nudge_offset", text="XYZ")
                    action = button_row.row(align=True)
                    action.enabled = reason is None
                    button = action.operator(
                        _OPERATORS_BY_FEATURE[feature_id].bl_idname, text=label
                    )
                    button.offset = context.scene.cbdk_modular_nudge_offset
                else:
                    button_row.enabled = reason is None
                    button_row.operator(_OPERATORS_BY_FEATURE[feature_id].bl_idname, text=label)
                if reason is not None:
                    body.label(text=label + ": " + reason)
        if not visible_sections:
            col.label(text="No preview controls for this mode")
        col.label(text=context.scene.cbdk_modular_result)


_CLASSES = tuple(_OPERATORS) + (VIEW3D_PT_cbdk_modular_preview,)
_REGISTERED = []


_PROPERTY_NAMES = ("cbdk_modular_result", "cbdk_modular_nudge_offset")
_OWNED_PROPERTIES = []


def register():
    # Refuse collisions before touching another add-on's Scene data.
    if _REGISTERED or _OWNED_PROPERTIES or any(hasattr(bpy.types.Scene, name) for name in _PROPERTY_NAMES):
        raise RuntimeError("CBDK preview is already registered or Scene properties conflict")
    try:
        bpy.types.Scene.cbdk_modular_result = bpy.props.StringProperty(
            name="Last CBDK preview result", default="No inspection yet"
        )
        _OWNED_PROPERTIES.append("cbdk_modular_result")
        parameter = _UI_OPTIONS["nudge_offset"]
        bpy.types.Scene.cbdk_modular_nudge_offset = bpy.props.FloatVectorProperty(
            name="Local Nudge XYZ", description="Local-space offset for selected vertices",
            size=parameter["size"], default=parameter["default"],
            min=parameter["min"], max=parameter["max"], subtype="TRANSLATION",
        )
        _OWNED_PROPERTIES.append("cbdk_modular_nudge_offset")
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
            _REGISTERED.append(cls)
    except Exception as error:
        try:
            unregister()
        except Exception as cleanup_error:
            # Keep the original registration error and retain failed entries
            # in the ownership lists so a later cleanup can be retried.
            error.add_note("CBDK preview rollback was incomplete; retry unregister()")
            raise error from cleanup_error
        raise


def unregister():
    # A failing operator unregister must not prevent owned Scene property
    # cleanup. Entries are removed only after a successful detach so a caller
    # can retry without touching foreign add-on registrations.
    failures = []
    for cls in reversed(tuple(_REGISTERED)):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as error:
            failures.append(error)
        else:
            _REGISTERED.remove(cls)
    for name in reversed(tuple(_OWNED_PROPERTIES)):
        try:
            if hasattr(bpy.types.Scene, name):
                delattr(bpy.types.Scene, name)
        except Exception as error:
            failures.append(error)
        else:
            _OWNED_PROPERTIES.remove(name)
    if failures:
        raise RuntimeError("CBDK preview cleanup incomplete; retry unregister()") from failures[0]
