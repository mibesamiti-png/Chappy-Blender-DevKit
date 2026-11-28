"""CBDK-authored AST-only ambiguity fixture; NEVER import or execute."""
from bpy.props import FloatProperty


class ActiveLookingSettings:
    socket_opening_diameter: FloatProperty(default=1.7)

    def possible_geometry_path(self):
        import bpy
        bpy.ops.mesh.primitive_cylinder_add(radius=self.socket_opening_diameter)


class AnotherSettings:
    socket_opening_diameter: FloatProperty(default=0.78)


raise RuntimeError("AST fixture must never execute")
