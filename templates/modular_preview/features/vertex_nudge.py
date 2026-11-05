"""Small guarded local-space edit; relies on Blender native Undo operator."""
import bpy

from ..helpers.context import BlenderContextError
from ..helpers.edit_transform import translate_selected_vertices


class CBDK_OT_modular_vertex_nudge(bpy.types.Operator):
    bl_idname = "cbdk.modular_vertex_nudge"
    bl_label = "Nudge Selected Vertices"
    bl_description = "Move selected vertices locally (default +0.1 Z); supports Blender Undo"
    bl_options = {"REGISTER", "UNDO"}

    offset: bpy.props.FloatVectorProperty(
        name="Local offset",
        description="Local-space distance; move only selected vertices",
        size=3,
        default=(0.0, 0.0, 0.1),
        min=-10.0,
        max=10.0,
        subtype="TRANSLATION",
    )

    def execute(self, context):
        try:
            result = translate_selected_vertices(context, tuple(self.offset))
        except BlenderContextError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        message = f"Moved {result.moved_vertices} selected vertices (local)"
        context.scene.cbdk_modular_result = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


OPERATOR_CLASS = CBDK_OT_modular_vertex_nudge
