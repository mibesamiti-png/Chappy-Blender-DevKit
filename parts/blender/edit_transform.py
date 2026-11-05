"""Guarded vertex translation in one Edit Mode mesh.

Designed for an operator with Blender REGISTER/UNDO flags, not a standalone
permanent edit command. Validate *all* input before changing BMesh coordinates.
If a write/update fails, restore the saved coordinates on a best-effort basis
and raise BlenderContextError. Does not create/destroy vertices, switch modes
or touch selection, object transform, modifiers or external files.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .context import BlenderContextError, require_active_mesh


MAX_OFFSET = 10.0
MAX_ABS_COORD = 1_000_000_000.0


@dataclass(frozen=True)
class VertexTranslationResult:
    moved_vertices: int
    offset: tuple[float, float, float]


def translate_selected_vertices(context, offset) -> VertexTranslationResult:
    """Move only currently selected BMesh vertices by a *local-space* delta.

    Reject multi-object edit, linked/shared mesh data and shape keys, so one
    operation never unexpectedly changes other objects or shape keys.
    The calling bpy Operator must use UNDO. Direct scripting calls are NOT
    automatically undoable unless the caller creates an undo step.
    """
    if not isinstance(offset, (tuple, list)) or len(offset) != 3:
        raise BlenderContextError("Offset must have exactly three local-space components")
    try:
        delta = tuple(float(value) for value in offset)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BlenderContextError("Offset must contain finite numbers") from exc
    if (not all(isfinite(x) and abs(x) <= MAX_OFFSET for x in delta)
            or all(x == 0.0 for x in delta)):
        raise BlenderContextError("Offset must be finite, nonzero and within +/-10 units")

    obj = require_active_mesh(context, mode="EDIT_MESH")
    objects = getattr(context, "objects_in_mode_unique_data", None)
    if objects is None or len([o for o in objects if getattr(o, "type", None) == "MESH"]) != 1:
        raise BlenderContextError("Exactly one unique mesh must be in Edit Mode")
    mesh = obj.data
    if getattr(mesh, "library", None) is not None or getattr(obj, "library", None) is not None:
        raise BlenderContextError("Linked-library data cannot be edited by this preview")
    if getattr(mesh, "users", 1) != 1:
        raise BlenderContextError("Shared mesh datablocks are not supported")
    if getattr(mesh, "shape_keys", None) is not None:
        raise BlenderContextError("Meshes with shape keys are not supported")

    import bmesh

    bm = bmesh.from_edit_mesh(mesh)
    chosen = tuple(vertex for vertex in bm.verts if vertex.select)
    if not chosen:
        raise BlenderContextError("Select at least one vertex before translating")

    # The whole change is planned before the first write, so a bad coordinate
    # or offset cannot leave a partially translated mesh.
    planned = []
    for vertex in chosen:
        try:
            old = tuple(float(vertex.co[i]) for i in range(3))
            new = tuple(old[i] + delta[i] for i in range(3))
        except (ValueError, TypeError, OverflowError, IndexError) as exc:
            raise BlenderContextError("Invalid selected vertex coordinates") from exc
        if not all(isfinite(x) and abs(x) <= MAX_ABS_COORD for x in (*old, *new)):
            raise BlenderContextError("Vertex translation would create invalid coordinates")
        planned.append((vertex, old, new))

    changed = []
    try:
        for vertex, old, new in planned:
            # Also track the current vertex; a data API setter might fail after
            # changing only some of its coordinate components.
            changed.append((vertex, old))
            vertex.co = new
        bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
    except Exception as exc:
        errors = []
        for vertex, old in reversed(changed):
            try:
                vertex.co = old
            except Exception as rollback_exc:
                errors.append(type(rollback_exc).__name__)
        try:
            bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
        except Exception as rollback_exc:
            errors.append(type(rollback_exc).__name__)
        if errors:
            raise BlenderContextError(
                "Translation failed and rollback was incomplete: " + ", ".join(errors)
            ) from exc
        raise BlenderContextError("Translation failed; original vertex positions restored") from exc
    return VertexTranslationResult(len(chosen), delta)
