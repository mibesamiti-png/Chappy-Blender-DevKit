"""Object selection inspector; requires BLCTX-001 + BLCTX-002."""
import bpy
from ..helpers.context import BlenderContextError, require_active_mesh, selected_mesh_objects


class CBDK_OT_modular_selected_meshes(bpy.types.Operator):
    bl_idname = "cbdk.modular_selected_meshes"
    bl_label = "Count Selected Meshes"
    bl_description = "Read Object Mode mesh selection; leave selection unchanged"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        try:
            obj = require_active_mesh(context, mode="OBJECT")
            selected = selected_mesh_objects(context)
            message = f"Selected meshes: {len(selected)}; active={obj.name}"
        except BlenderContextError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        context.scene.cbdk_modular_result = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


OPERATOR_CLASS = CBDK_OT_modular_selected_meshes
