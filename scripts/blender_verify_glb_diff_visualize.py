"""GLB-020 CI: reimport color-coded outputs and verify individual mesh parts."""
from __future__ import annotations

from pathlib import Path
import sys
import bpy


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Missing trusted output GLBs")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) not in (2, 3):
        raise RuntimeError("Expected reference_diff.glb candidate_diff.glb [part-count]")
    if len(args) == 3:
        expected_parts = int(args[2])
        if not 1 <= expected_parts <= 64:
            raise RuntimeError("Invalid expected synthetic part count")
    else:
        expected_parts = None
    for filename in args[:2]:
        source = Path(filename).resolve()
        if not source.is_file():
            raise RuntimeError("Output GLB does not exist")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        meshes = sorted(
            (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
            key=lambda obj: obj.name,
        )
        if not meshes:
            raise RuntimeError("No colored mesh in exported GLB")
        if expected_parts is not None and len(meshes) != expected_parts:
            raise RuntimeError("Original mesh-part grouping was lost")
        if len(meshes) > 64:
            raise RuntimeError("Mesh-object cap violated")
        triangles = sum(len(obj.data.polygons) for obj in meshes)
        if not 1 <= triangles <= 512:
            raise RuntimeError("Unexpected colored triangle count")
        material_names = {
            mat.name
            for obj in meshes for mat in obj.data.materials if mat
        }
        if not any(name.startswith("CBDK_diff_") for name in material_names):
            raise RuntimeError("Color-coded materials were not exported")
        for obj in meshes:
            if not obj.name.startswith("CBDK_") or "_Part_" not in obj.name:
                raise RuntimeError("A source object's private name leaked")
            if not obj.data.polygons:
                raise RuntimeError("Exported a part with no faces")
        if expected_parts == 2:
            if len(meshes) != 2 or any(len(m.data.polygons) != 1 for m in meshes):
                raise RuntimeError("Synthetic two-part topology was not preserved")
            # Part_001 is unchanged; Part_002 is deliberately 0.30 units
            # offset from the comparison model, above the red threshold.
            for index, expected_material in (
                (0, "CBDK_diff_low"), (1, "CBDK_diff_high"),
            ):
                mesh = meshes[index].data
                face = mesh.polygons[0]
                material = mesh.materials[face.material_index]
                if expected_material not in material.name:
                    raise RuntimeError("Part-level color did not survive GLB export")
    print("CBDK_GLB_DIFF_VISUALIZATION_REIMPORT_PASS")


if __name__ == "__main__":
    main()
