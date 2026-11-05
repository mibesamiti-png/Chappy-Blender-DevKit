"""Read object-world bounds; requires BLCTX-001 and BLGEO-001."""
import bpy

from ..helpers.context import BlenderContextError
from ..helpers.measure import mesh_world_bounds


class CBDK_OT_modular_mesh_bounds(bpy.types.Operator):
    bl_idname = "cbdk.modular_mesh_bounds"
    bl_label = "Measure Mesh Bounds"
    bl_description = "Inspect world-space bounds of base mesh (modifiers not evaluated)"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        try:
            bounds = mesh_world_bounds(context)
        except BlenderContextError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        x, y, z = bounds.dimensions
        message = f"World bounds (base): {x:.3f} x {y:.3f} x {z:.3f}"
        context.scene.cbdk_modular_result = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


OPERATOR_CLASS = CBDK_OT_modular_mesh_bounds
