"""Create CBDK-only closed/open tetrahedron pair to test boundary review.

Never uses user models or private addon sources. Files stay in CI workspace.
"""
from __future__ import annotations

from pathlib import Path
import sys
import bpy


def export_tetra(target, *, open_cap):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    vertices = [
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
    ]
    faces = [
        (0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2),
    ]
    if open_cap:
        faces = faces[1:]
    mesh = bpy.data.meshes.new("SYNTHETIC_BOUNDARY_TEST_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("SYNTHETIC_BOUNDARY_TEST", mesh)
    bpy.context.collection.objects.link(obj)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(target), export_format="GLB", use_selection=True,
    )
    if not target.is_file() or target.stat().st_size < 100:
        raise RuntimeError("Synthetic tetrahedron GLB not exported")


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Missing trusted output directory")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise RuntimeError("Expected one local directory")
    target = Path(args[0]).resolve()
    target.mkdir(parents=True, exist_ok=True)
    export_tetra(target / "closed_tetra.glb", open_cap=False)
    export_tetra(target / "open_tetra.glb", open_cap=True)
    print("CBDK_BOUNDARY_GLBS_GENERATED_PASS")


if __name__ == "__main__":
    main()
