"""Read-only world-space bounding box for the active mesh in Object Mode.

This uses the object's own mesh bounding box (unapplied modifiers are NOT
evaluated); a rotated/non-uniformly scaled object yields a world-aligned box.
No bpy.ops, mode switches, selection changes or mesh modifications.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .context import BlenderContextError, require_active_mesh


@dataclass(frozen=True)
class MeshWorldBounds:
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]
    dimensions: tuple[float, float, float]
    vertex_count: int


def mesh_world_bounds(context) -> MeshWorldBounds:
    """Return world-axis-aligned bounds for the active mesh's base geometry.

    Only OBJECT mode is supported. Blender Edit Mode can hold unsynchronized
    BMesh edits, so this rejects Edit Mode rather than reading stale mesh data.
    """
    obj = require_active_mesh(context, mode="OBJECT")
    verts = getattr(obj.data, "vertices", None)
    if verts is None or len(verts) == 0:
        raise BlenderContextError("Active mesh must contain vertices")
    corners = getattr(obj, "bound_box", None)
    if corners is None or len(corners) != 8:
        raise BlenderContextError("Active mesh has no valid bounding box")

    # Imported lazily: pure Python unit tests and catalog inspection should
    # not require or import Blender's mathutils package.
    from mathutils import Vector

    transformed = [obj.matrix_world @ Vector(corner) for corner in corners]
    minimum = tuple(float(min(p[i] for p in transformed)) for i in range(3))
    maximum = tuple(float(max(p[i] for p in transformed)) for i in range(3))
    if not all(isfinite(v) for v in (*minimum, *maximum)):
        raise BlenderContextError("Mesh bounding box contains non-finite coordinates")
    dimensions = tuple(maximum[i] - minimum[i] for i in range(3))
    return MeshWorldBounds(minimum, maximum, dimensions, len(verts))
