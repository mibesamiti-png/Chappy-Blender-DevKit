"""Read-only edit-mode selection inspection (no topology edits or mode switches)."""
from __future__ import annotations

from dataclasses import dataclass

from .context import BlenderContextError, require_active_mesh


@dataclass(frozen=True)
class EditSelectionCounts:
    vertices: int
    edges: int
    faces: int


def count_edit_selection(context, *, require_single_mesh: bool = True) -> EditSelectionCounts:
    """Count selected BMesh elements on the active edit mesh without modifying it.

    Multi-object Edit Mode is rejected by default. Set require_single_mesh=False
    only if the caller explicitly intends to inspect the active object's mesh.
    The returned dataclass contains integer counts, not live BMesh references.
    """
    obj = require_active_mesh(context, mode='EDIT_MESH')
    if require_single_mesh:
        objects = getattr(context, 'objects_in_mode_unique_data', None)
        if objects is None:
            raise BlenderContextError('Cannot verify multi-object Edit Mode state')
        mesh_count = sum(1 for item in objects if getattr(item, 'type', None) == 'MESH')
        if mesh_count != 1:
            raise BlenderContextError('Exactly one unique mesh must be in Edit Mode')
    # Delay import so source inspection and ordinary Python unit tests do not
    # accidentally load Blender modules. Blender itself provides bmesh at run time.
    import bmesh

    bm = bmesh.from_edit_mesh(obj.data)
    return EditSelectionCounts(
        vertices=sum(bool(v.select) for v in bm.verts),
        edges=sum(bool(e.select) for e in bm.edges),
        faces=sum(bool(f.select) for f in bm.faces),
    )
