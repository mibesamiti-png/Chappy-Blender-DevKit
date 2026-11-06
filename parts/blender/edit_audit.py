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


def preflight_audit_size(bm) -> tuple[int, int, int]:
    """Reject oversized/invalid BMesh before copying *any* coordinates.

    BMesh element sequences expose constant-time len. In the previous
    implementation, all three sequences were copied before the limit was
    checked, leading to avoidable allocation on very large meshes.
    """
    try:
        sizes = (len(bm.verts), len(bm.edges), len(bm.faces))
    except (TypeError, AttributeError, ValueError, OverflowError) as exc:
        raise BlenderContextError("Cannot determine BMesh element counts") from exc
    if any(n < 0 for n in sizes) or sum(sizes) > MAX_AUDIT_ELEMENTS:
        raise BlenderContextError("Mesh exceeds the audited preview size limit")
    return sizes


def capture_edit_snapshot(bm) -> MeshEditSnapshot:
    """Capture bounded, immutable geometry and selection for an existing BMesh.

    Returns no live references. The vertex enumeration fixes indices within the
    snapshot. It also captures edge and face connectivity so equal element counts
    alone cannot hide accidental topology changes.
    """
    try:
        preflight_audit_size(bm)
        verts = tuple(bm.verts)
        edges = tuple(bm.edges)
        faces = tuple(bm.faces)
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


def _axis_matches(old: float, new: float, delta: float) -> bool:
    """Verify each axis, including axes that must not change.

    A whole-vertex 'any axis changed' check can incorrectly accept a missing
    tiny Y translation when X moved correctly. Exact unchanged comparisons
    prevent edits to unselected vertices and zero-delta axes from passing.
    For nonzero deltas use a tight, delta-relative error budget as well as
    the existing absolute bound; float32 quantization beyond this is safely
    rejected instead of being misreported as a successful edit.
    """
    if delta == 0.0:
        return new == old
    if new == old:
        return False
    expected = old + delta
    if not isfinite(expected):
        return False
    tolerance = min(
        ABS_TOLERANCE + REL_TOLERANCE * max(1.0, abs(delta)),
        abs(delta) * 0.15,
    )
    return abs(new - expected) <= tolerance


def _validate_translation_delta(delta) -> None:
    """Use the same strict input contract for snapshot and streaming audits."""
    if (not isinstance(delta, tuple) or len(delta) != 3
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                       and isfinite(x) for x in delta)):
        raise BlenderContextError("Audit requires a finite translation delta")


def audit_vertex_translation(before: MeshEditSnapshot, after: MeshEditSnapshot,
                             delta: tuple[float, float, float]) -> MeshEditDiff:
    """Verify that exactly preselected vertices moved by the requested delta."""
    topology_changed = (
        len(before.coordinates) != len(after.coordinates)
        or before.edges != after.edges or before.faces != after.faces
    )
    selection_changed = before.selected != after.selected
    _validate_translation_delta(delta)
    moved = []
    unexpected = []
    matched = True
    for i in range(min(len(before.coordinates), len(after.coordinates))):
        old, new = before.coordinates[i], after.coordinates[i]
        changed = any(old[j] != new[j] for j in range(3))
        if changed:
            moved.append(i)
        if any(not _axis_matches(old[j], new[j], delta[j] if before.selected[i] else 0.0)
               for j in range(3)):
            unexpected.append(i)
            matched = False
    if len(before.coordinates) != len(after.coordinates):
        matched = False
    # Match the streaming audit: a nonzero move must be observable. A
    # too-small delta can disappear in float32 coordinates and must not be
    # reported as successful, even if it lies within numeric tolerance.
    if any(value != 0.0 for value in delta) and not moved:
        matched = False
    return MeshEditDiff(tuple(moved), tuple(unexpected), selection_changed,
                        topology_changed, matched)


def audit_live_vertex_translation(before: MeshEditSnapshot, bm,
                                  delta: tuple[float, float, float]) -> MeshEditDiff:
    """Stream coordinates/selection from the live BMesh after a translation.

    Avoid allocating a second snapshot of all vertex coordinates and selection.
    Connectivity is still checked exactly: edge key multiplicity and face
    winding/order must match the before-image. This is a safety audit, not an
    editable Blender undo stack or a topology-recovery mechanism.
    """
    _validate_translation_delta(delta)
    preflight_audit_size(bm)
    try:
        verts = bm.verts
        n = len(verts)
        if n != len(before.coordinates) or n != len(before.selected):
            return MeshEditDiff((), (), True, True, False)
        mapping = {vertex: i for i, vertex in enumerate(verts)}
        if len(mapping) != n:
            raise BlenderContextError("Repeated vertex identity in edited mesh")
        edges = tuple(sorted(
            tuple(sorted((mapping[e.verts[0]], mapping[e.verts[1]])))
            for e in bm.edges
        ))
        faces = tuple(tuple(mapping[v] for v in face.verts) for face in bm.faces)
        topo = edges != before.edges or faces != before.faces
        selection_changed = False
        moved: list[int] = []
        unexpected: list[int] = []
        for i, vertex in enumerate(verts):
            old = before.coordinates[i]
            now = tuple(float(vertex.co[j]) for j in range(3))
            if bool(vertex.select) != before.selected[i]:
                selection_changed = True
            if not all(isfinite(value) for value in now):
                unexpected.append(i)
                continue
            if any(old[j] != now[j] for j in range(3)):
                moved.append(i)
            if any(not _axis_matches(old[j], now[j], delta[j] if before.selected[i] else 0.0)
                   for j in range(3)):
                unexpected.append(i)
        # A valid nonzero translation must produce observable changes.
        # This also rejects edits lost to float32 precision at huge coordinates.
        if any(x != 0.0 for x in delta) and not moved:
            return MeshEditDiff(tuple(moved), tuple(unexpected),
                                selection_changed, topo, False)
        return MeshEditDiff(tuple(moved), tuple(unexpected),
                            selection_changed, topo, not unexpected)
    except BlenderContextError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as exc:
        raise BlenderContextError("Failed to audit live edited BMesh") from exc


def _topology_matches_snapshot(bm, snapshot: MeshEditSnapshot) -> bool:
    """Check connectivity without reading potentially invalid vertex coordinates.

    Recovery must remain possible when an edit produces NaN/Inf coordinates.
    Taking a new full snapshot would fail its finite-value guard before the
    original valid coordinates could be written back.
    """
    try:
        vertices, edges, faces = preflight_audit_size(bm)
        if (vertices != len(snapshot.coordinates) or vertices != len(snapshot.selected)
                or edges != len(snapshot.edges) or faces != len(snapshot.faces)):
            return False
        indices = {vertex: i for i, vertex in enumerate(bm.verts)}
        if len(indices) != vertices:
            return False
        live_edges = tuple(sorted(
            tuple(sorted((indices[edge.verts[0]], indices[edge.verts[1]])))
            for edge in bm.edges
        ))
        if live_edges != snapshot.edges:
            return False
        live_faces = tuple(tuple(indices[vertex] for vertex in face.verts)
                           for face in bm.faces)
        return live_faces == snapshot.faces
    except BlenderContextError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as exc:
        raise BlenderContextError("Cannot verify BMesh connectivity for rollback") from exc


def restore_edit_snapshot(bm, snapshot: MeshEditSnapshot) -> None:
    """Best-effort coordinate+selection recovery; reject different connectivity.

    This does not rebuild deleted vertices or faces. If topology is different
    from the snapshot, recovery cannot be guaranteed; report that explicitly.
    """
    if not _topology_matches_snapshot(bm, snapshot):
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
    # Treat silent setters/partial restoration as failures too; error recovery
    # must never claim that original coordinates were restored without proof.
    for index, vert in enumerate(bm.verts):
        try:
            restored = tuple(float(vert.co[j]) for j in range(3))
            if restored != snapshot.coordinates[index] or bool(vert.select) != snapshot.selected[index]:
                failures.append(f"vertex {index}: restoration mismatch")
        except Exception as exc:
            failures.append(f"vertex {index}: verification {type(exc).__name__}")
    if not _topology_matches_snapshot(bm, snapshot):
        raise BlenderContextError("Snapshot restoration incomplete: topology changed")
    if failures:
        raise BlenderContextError("Snapshot restoration incomplete: " + ", ".join(failures[:5]))
