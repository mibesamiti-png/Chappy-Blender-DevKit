"""CBDK Mesh Inspector — locally generated developer preview.

All features are read-only with respect to meshes, mode and selection. The last
status text is stored in an ephemeral Scene property for display in the panel.
This is NOT a licensed/published Blender extension.
"""
bl_info = {
    "name": "CBDK Mesh Inspector Preview",
    "author": "Chappy Blender DevKit (development preview)",
    "version": (0, 1, 0),
    "blender": (4, 4, 0),
    "location": "3D View > Sidebar > CBDK",
    "description": "Inspect selected meshes and Edit Mode selection without changing topology",
    "category": "3D View",
}

import bpy
from .helpers.context import BlenderContextError, require_active_mesh, selected_mesh_objects
from .helpers.edit_mesh import count_edit_selection


class CBDK_OT_inspect_mesh_selection(bpy.types.Operator):
    bl_idname = "cbdk.inspect_mesh_selection"
    bl_label = "Inspect Mesh Selection"
    bl_description = "Read selected mesh/element counts; do not modify meshes"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        try:
            obj = require_active_mesh(context)
            if context.mode == "EDIT_MESH":
                counts = count_edit_selection(context)
                status = (
                    f"Edit Mesh: V={counts.vertices} E={counts.edges} "
                    f"F={counts.faces}"
                )
            elif context.mode == "OBJECT":
                selected = selected_mesh_objects(context)
                status = f"Object Mode: {len(selected)} selected mesh(es); active={obj.name}"
            else:
                raise BlenderContextError("Only Object or Mesh Edit Mode is supported")
            context.scene.cbdk_mesh_inspector_result = status
            self.report({"INFO"}, status)
            return {"FINISHED"}
        except BlenderContextError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}


class VIEW3D_PT_cbdk_mesh_inspector(bpy.types.Panel):
    bl_label = "Mesh Inspector (Preview)"
    bl_idname = "VIEW3D_PT_cbdk_mesh_inspector"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CBDK"

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(CBDK_OT_inspect_mesh_selection.bl_idname, icon="VIEWZOOM")
        col.label(text=context.scene.cbdk_mesh_inspector_result)


_CLASSES = (CBDK_OT_inspect_mesh_selection, VIEW3D_PT_cbdk_mesh_inspector)


def register():
    # Register/unregister must work repeatedly (addon enable/disable).
    bpy.types.Scene.cbdk_mesh_inspector_result = bpy.props.StringProperty(
        name="Last CBDK Inspection",
        description="Read-only inspection summary",
        default="No inspection yet",
    )
    try:
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
    except Exception:
        for cls in reversed(_CLASSES):
            if bpy.types.Panel.bl_rna_get_subclass_py(cls.__name__) is cls or (
                issubclass(cls, bpy.types.Operator) and
                bpy.types.Operator.bl_rna_get_subclass_py(cls.bl_idname) is cls
            ):
                bpy.utils.unregister_class(cls)
        del bpy.types.Scene.cbdk_mesh_inspector_result
        raise


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "cbdk_mesh_inspector_result"):
        del bpy.types.Scene.cbdk_mesh_inspector_result
