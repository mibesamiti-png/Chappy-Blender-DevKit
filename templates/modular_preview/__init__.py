"""CBDK v0.11 recipe-composed read-only development preview.

Only trusted authored feature modules are loaded, selected at build time.
Do not install two modular-preview variants simultaneously: they share class
and operator identifiers and are intended to replace one another.
"""
bl_info = {
    "name": __CBDK_DISPLAY_NAME__,
    "author": "Chappy Blender DevKit (private development preview)",
    "version": (0, 13, 0),
    "blender": (4, 4, 0),
    "location": "3D View > Sidebar > CBDK",
    "description": "Recipe-built mesh inspection preview; no topology editing",
    "category": "3D View",
}

import importlib
import bpy

_FEATURE_IDS = __CBDK_FEATURE_IDS__
_OPERATORS = [
    importlib.import_module("." + feature, __name__ + ".features").OPERATOR_CLASS
    for feature in _FEATURE_IDS
]


class VIEW3D_PT_cbdk_modular_preview(bpy.types.Panel):
    bl_label = "CBDK Modular Preview"
    bl_idname = "VIEW3D_PT_cbdk_modular_preview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CBDK"

    def draw(self, context):
        col = self.layout.column(align=True)
        for cls in _OPERATORS:
            col.operator(cls.bl_idname)
        col.label(text=context.scene.cbdk_modular_result)


_CLASSES = tuple(_OPERATORS) + (VIEW3D_PT_cbdk_modular_preview,)
_REGISTERED = []


def register():
    # Roll back even if a later operator/panel fails to register.
    bpy.types.Scene.cbdk_modular_result = bpy.props.StringProperty(
        name="Last CBDK preview result", default="No inspection yet"
    )
    try:
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
            _REGISTERED.append(cls)
    except Exception:
        for cls in reversed(_REGISTERED):
            bpy.utils.unregister_class(cls)
        _REGISTERED.clear()
        if hasattr(bpy.types.Scene, "cbdk_modular_result"):
            del bpy.types.Scene.cbdk_modular_result
        raise


def unregister():
    for cls in reversed(_REGISTERED):
        bpy.utils.unregister_class(cls)
    _REGISTERED.clear()
    if hasattr(bpy.types.Scene, "cbdk_modular_result"):
        del bpy.types.Scene.cbdk_modular_result
