"""Bounded Blender BMesh snapshots and post-edit invariant checks.

An audit is a local safety check, not a crash-safe transaction or a replacement
for Blender's built-in Undo. It checks coordinates, selections and topology
connectivity before/after a known, allowlisted edit; it never runs user code.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .context import BlenderContextError

MAX_AUDIT_ELEMENTS = 200_000
ABS_TOLERANCE = 2e-5
REL_TOLERANCE = 2e-6


@dataclass(frozen=True)
class MeshEditSnapshot:
    coordinates: tuple[tuple[float, float, float], ...]
    selected: tuple[bool, ...]
    edges: tuple[tuple[int, int], ...]
    faces: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class MeshEditDiff:
    moved_vertices: tuple[int, ...]
    unexpected_vertices: tuple[int, ...]
    selection_changed: bool
    topology_changed: bool
    expected_delta_matched: bool

    @property
    def valid(self) -> bool:
        return (not self.unexpected_vertices and not self.selection_changed
                and not self.topology_changed and self.expected_delta_matched)


def capture_edit_snapshot(bm) -> MeshEditSnapshot:
    """Capture bounded, immutable geometry and selection for an existing BMesh.

    Returns no live references. The vertex enumeration fixes indices within the
    snapshot. It also captures edge and face connectivity so equal element counts
    alone cannot hide accidental topology changes.
    """
    try:
        verts = tuple(bm.verts)
        edges = tuple(bm.edges)
        faces = tuple(bm.faces)
        if len(verts) + len(edges) + len(faces) > MAX_AUDIT_ELEMENTS:
            raise BlenderContextError("Mesh exceeds the audited preview size limit")
        mapping = {vert: i for i, vert in enumerate(verts)}
        coords = tuple(tuple(float(vertex.co[i]) for i in range(3)) for vertex in verts)
        if not all(isfinite(x) for coord in coords for x in coord):
            raise BlenderContextError("Snapshot found non-finite vertex coordinates")
        selected = tuple(bool(vertex.select) for vertex in verts)
        # Normalize undirected edges; preserve face winding, where relevant.
        edge_keys = tuple(sorted(tuple(sorted((mapping[edge.verts[0]], mapping[edge.verts[1]])))
                                 for edge in edges))
        face_keys = tuple(tuple(mapping[vert] for vert in face.verts) for face in faces)
        return MeshEditSnapshot(coords, selected, edge_keys, face_keys)
    except BlenderContextError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as exc:
        raise BlenderContextError("Failed to inspect BMesh snapshot safely") from exc


def _near(a: float, b: float) -> bool:
    return abs(a - b) <= ABS_TOLERANCE + REL_TOLERANCE * max(abs(a), abs(b))


def audit_vertex_translation(before: MeshEditSnapshot, after: MeshEditSnapshot,
                             delta: tuple[float, float, float]) -> MeshEditDiff:
    """Verify that exactly preselected vertices moved by the requested delta."""
    topology_changed = (
        len(before.coordinates) != len(after.coordinates)
        or before.edges != after.edges or before.faces != after.faces
    )
    selection_changed = before.selected != after.selected
    if not isinstance(delta, tuple) or len(delta) != 3 or not all(isfinite(x) for x in delta):
        raise BlenderContextError("Audit requires a finite translation delta")
    moved = []
    unexpected = []
    matched = True
    for i in range(min(len(before.coordinates), len(after.coordinates))):
        old, new = before.coordinates[i], after.coordinates[i]
        changed = any(not _near(old[j], new[j]) for j in range(3))
        if changed:
            moved.append(i)
        target = tuple(old[j] + delta[j] if before.selected[i] else old[j] for j in range(3))
        if any(not _near(target[j], new[j]) for j in range(3)):
            unexpected.append(i)
            matched = False
    if len(before.coordinates) != len(after.coordinates):
        matched = False
    return MeshEditDiff(tuple(moved), tuple(unexpected), selection_changed,
                        topology_changed, matched)


def restore_edit_snapshot(bm, snapshot: MeshEditSnapshot) -> None:
    """Best-effort coordinate+selection recovery; reject different connectivity.

    This does not rebuild deleted vertices or faces. If topology is different
    from the snapshot, recovery cannot be guaranteed; report that explicitly.
    """
    current = capture_edit_snapshot(bm)
    if (len(current.coordinates) != len(snapshot.coordinates)
            or current.edges != snapshot.edges or current.faces != snapshot.faces):
        raise BlenderContextError("Topology changed: coordinate rollback cannot restore original mesh")
    failures = []
    for index, vert in enumerate(bm.verts):
        try:
            vert.co = snapshot.coordinates[index]
            if bool(vert.select) != snapshot.selected[index]:
                vert.select_set(snapshot.selected[index])
        except Exception as exc:
            failures.append(f"vertex {index}: {type(exc).__name__}")
    if failures:
        raise BlenderContextError("Snapshot restoration incomplete: " + ", ".join(failures[:5]))
