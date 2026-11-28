"""Synthetic AST-only Blender property declarations for GLB-021 CI.

This file MUST NEVER be imported or executed by GLB-021. It exists solely
to test how a human-labelled GLB-020 observation maps to static declarations.
"""
from bpy.props import FloatProperty, IntProperty


class SyntheticJointSettings:
    socket_opening_diameter: FloatProperty(name="Socket opening", default=1.7)
    ball_diameter: FloatProperty(name="Ball diameter", default=1.26)
    shaft_diameter: FloatProperty(name="Shaft diameter", default=0.44)
    clearance: FloatProperty(name="Joint clearance", default=0.2)
    segment_count: IntProperty(name="Segments", default=12)

    def synthetic_socket(self):
        # This is syntactic evidence only and must never execute.
        import bpy
        bpy.ops.mesh.primitive_cylinder_add(radius=self.socket_opening_diameter)
