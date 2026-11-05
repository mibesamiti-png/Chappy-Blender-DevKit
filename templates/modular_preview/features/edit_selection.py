"""Edit selection counter; requires BLCTX-001 + BME-001."""
import bpy
from ..helpers.context import BlenderContextError
from ..helpers.edit_mesh import count_edit_selection


class CBDK_OT_modular_edit_selection(bpy.types.Operator):
    bl_idname = "cbdk.modular_edit_selection"
    bl_label = "Count Edit Selection"
    bl_description = "Read Edit Mesh selection; leave topology and mode unchanged"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        try:
            counts = count_edit_selection(context)
            message = f"Edit selection: V={counts.vertices} E={counts.edges} F={counts.faces}"
        except BlenderContextError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        context.scene.cbdk_modular_result = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


OPERATOR_CLASS = CBDK_OT_modular_edit_selection
