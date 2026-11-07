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
_OPERATORS = [
    importlib.import_module("." + feature, __name__ + ".features").OPERATOR_CLASS
    for feature in _FEATURE_IDS
]
_OPERATORS_BY_FEATURE = dict(zip(_FEATURE_IDS, _OPERATORS))
# Fixed context map for the five reviewed CBDK-authored operators.
# Recipes/JSON cannot inject a new context or an arbitrary operator.
_OBJECT_MODE_FEATURES = frozenset(("object_selection", "mesh_bounds", "modifier_summary"))
_EDIT_MODE_FEATURES = frozenset(("edit_selection", "vertex_nudge"))
assert set(_FEATURE_IDS) <= _OBJECT_MODE_FEATURES | _EDIT_MODE_FEATURES



class VIEW3D_PT_cbdk_modular_preview(bpy.types.Panel):
    bl_label = "CBDK Modular Preview"
    bl_idname = "VIEW3D_PT_cbdk_modular_preview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CBDK"

    def draw(self, context):
        col = self.layout.column(align=True)
        for index, (title, buttons) in enumerate(_UI_SECTIONS):
            style = _UI_OPTIONS["section_styles"][index]
            group = col.box() if style["boxed"] else col.column(align=True)
            group.label(text=title)
            body = group.row(align=True) if style["layout"] == "row" else group
            for feature_id, label in buttons:
                button_row = body.row(align=True)
                active = context.active_object
                has_mesh = active is not None and active.type == "MESH"
                mode = "EDIT_MESH" if feature_id in _EDIT_MODE_FEATURES else "OBJECT"
                button_row.enabled = has_mesh and context.mode == mode
                if feature_id == "vertex_nudge":
                    # The built-in RNA property limits local offsets to +/-10.
                    # This edits only the chosen operator arguments, never
                    # executes user-supplied Python or alters the source mesh.
                    button_row.prop(context.scene, "cbdk_modular_nudge_offset", text="XYZ")
                    button = button_row.operator(
                        _OPERATORS_BY_FEATURE[feature_id].bl_idname, text=label
                    )
                    button.offset = context.scene.cbdk_modular_nudge_offset
                else:
                    button_row.operator(_OPERATORS_BY_FEATURE[feature_id].bl_idname, text=label)
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
    except Exception:
        unregister()
        raise


def unregister():
    for cls in reversed(_REGISTERED):
        bpy.utils.unregister_class(cls)
    _REGISTERED.clear()
    for name in reversed(_OWNED_PROPERTIES):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    _OWNED_PROPERTIES.clear()
