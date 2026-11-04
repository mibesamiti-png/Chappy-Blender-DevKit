"""Small Blender context helpers with no hidden mode changes or bpy.ops calls."""
from __future__ import annotations


class BlenderContextError(RuntimeError):
    """Raised when a helper cannot safely use the supplied Blender context."""


def require_active_mesh(context, *, mode: str | None = None):
    """Return the active mesh object without changing active object or mode.

    Args:
        context: Explicit bpy.context, not a global singleton.
        mode: Optional context mode, e.g. 'OBJECT' or 'EDIT_MESH'.

    Raises:
        BlenderContextError: If no mesh is active or the mode does not match.
    """
    if context is None:
        raise BlenderContextError('A Blender context must be provided')
    obj = getattr(context, 'active_object', None)
    if obj is None or getattr(obj, 'type', None) != 'MESH' or getattr(obj, 'data', None) is None:
        raise BlenderContextError('An active mesh object is required')
    if mode is not None and getattr(context, 'mode', None) != mode:
        raise BlenderContextError(f'Context mode {mode!r} is required')
    return obj


def selected_mesh_objects(context) -> tuple:
    """Snapshot selected mesh objects, preserving Blender's selection order."""
    if context is None:
        raise BlenderContextError('A Blender context must be provided')
    selected = getattr(context, 'selected_objects', None)
    if selected is None:
        raise BlenderContextError('Context does not expose selected_objects')
    return tuple(obj for obj in selected if getattr(obj, 'type', None) == 'MESH'
                 and getattr(obj, 'data', None) is not None)
