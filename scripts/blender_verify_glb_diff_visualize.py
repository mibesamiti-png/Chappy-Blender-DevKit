"""GLB-020 CI: reimport both locally generated color-coded GLB artifacts."""
from __future__ import annotations

from pathlib import Path
import sys
import bpy


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Missing arguments")
    filenames = sys.argv[sys.argv.index("--") + 1:]
    if len(filenames) != 2:
        raise RuntimeError("Expected exactly two local GLB artifacts")
    for filename in filenames:
        source = Path(filename).resolve()
        if not source.is_file():
            raise RuntimeError("Output GLB does not exist")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        if not meshes:
            raise RuntimeError("No colored mesh in exported GLB")
        triangles = sum(len(o.data.polygons) for o in meshes)
        if not 1 <= triangles <= 512:
            raise RuntimeError("Unexpected colored triangle count")
        material_names = {m.name for o in meshes for m in o.data.materials if m}
        if not any(name.startswith("CBDK_diff_") for name in material_names):
            raise RuntimeError("Color-coded materials were not exported")
    print("CBDK_GLB_DIFF_VISUALIZATION_REIMPORT_PASS")


if __name__ == "__main__":
    main()
