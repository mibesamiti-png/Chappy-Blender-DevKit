"""Read the world-aligned base mesh bounds center (not centroid or origin)."""
import bpy

from ..helpers.context import BlenderContextError
from ..helpers.measure import mesh_world_bounds


class CBDK_OT_modular_mesh_center(bpy.types.Operator):
    bl_idname = "cbdk.modular_mesh_center"
    bl_label = "Inspect Mesh Bounds Center"
    bl_description = "Inspect world-space base mesh bounding-box center, not centroid"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        precision = getattr(context.scene, "cbdk_modular_center_precision", None)
        if type(precision) is not int or not 0 <= precision <= 6:
            self.report({"WARNING"}, "Center precision must be an integer from 0 to 6")
            return {"CANCELLED"}
        try:
            bounds = mesh_world_bounds(context)
        except BlenderContextError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        x, y, z = (lo * 0.5 + hi * 0.5
                   for lo, hi in zip(bounds.minimum, bounds.maximum))
        message = f"World bounds center (base): {x:.{precision}f}, {y:.{precision}f}, {z:.{precision}f}"
        context.scene.cbdk_modular_result = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


OPERATOR_CLASS = CBDK_OT_modular_mesh_center
