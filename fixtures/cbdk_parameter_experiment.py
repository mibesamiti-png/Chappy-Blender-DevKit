"""CBDK-owned, intentionally tiny Blender addon used ONLY in trusted CI.

Never replace this with arbitrary user-supplied source. This fixture proves that
the chosen settings can influence exported geometry in this synthetic addon,
not that static analyses identify causal edits in third-party addons.
"""
from __future__ import annotations

import bpy

FIXTURE_OPERATOR = "mesh.cbdk_parameter_experiment_build"


class CBDKParameterExperimentSettings(bpy.types.PropertyGroup):
    sphere_radius: bpy.props.FloatProperty(
        name="Synthetic sphere radius", default=0.75, min=0.2, max=2.0,
    )
    bevel_width: bpy.props.FloatProperty(
        name="Synthetic bevel width", default=0.08, min=0.0, max=0.45,
    )


class CBDK_OT_parameter_experiment_build(bpy.types.Operator):
    bl_idname = FIXTURE_OPERATOR
    bl_label = "Build CBDK Synthetic Parameter Experiment"

    def execute(self, context):
        settings = context.scene.cbdk_parameter_experiment
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=24, ring_count=12, radius=settings.sphere_radius,
            location=(-2.0, 0.0, 0.0),
        )
        sphere = context.object
        sphere.name = "CBDK_Param_Sphere"
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(2.0, 0.0, 0.0))
        cube = context.object
        cube.name = "CBDK_Param_BevelCube"
        bevel = cube.modifiers.new("CBDK_Bevel", "BEVEL")
        bevel.width = settings.bevel_width
        bevel.segments = 3
        # Apply the modifier before export, so different bevel widths really
        # change vertex coordinates in the GLB rather than relying on exporter
        # modifier settings.
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        return {"FINISHED"}


CLASSES = (CBDKParameterExperimentSettings, CBDK_OT_parameter_experiment_build)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cbdk_parameter_experiment = bpy.props.PointerProperty(
        type=CBDKParameterExperimentSettings,
    )


def unregister():
    if hasattr(bpy.types.Scene, "cbdk_parameter_experiment"):
        del bpy.types.Scene.cbdk_parameter_experiment
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
