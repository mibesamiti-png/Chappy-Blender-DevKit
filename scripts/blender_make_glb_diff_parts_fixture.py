"""Create two CBDK-authored synthetic, multipart GLBs for GLB-020 CI.

No private user sources, third-party addon execution or imported unknown data.
"""
from __future__ import annotations

from pathlib import Path
import sys

import bpy


def _write_pair(output, *, changed):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Source names are intentionally private-looking; the GLB-020 output
    # must replace them with anonymous object IDs.
    for label, x, z in (
        ("PRIVATE_SOURCE_ALPHA", 0.0, 0.0),
        ("PRIVATE_SOURCE_BETA", 3.0, 0.30 if changed else 0.0),
    ):
        mesh = bpy.data.meshes.new(label + "_mesh")
        mesh.from_pydata(
            [(x, 0.0, z), (x + 1.0, 0.0, z), (x, 1.0, z)],
            [], [(0, 1, 2)],
        )
        mesh.update()
        obj = bpy.data.objects.new(label, mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(output), export_format="GLB", use_selection=True,
    )
    if not output.is_file() or output.stat().st_size < 100:
        raise RuntimeError("Synthetic GLB generation failed")


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Provide new temporary output directory")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise RuntimeError("Expected one output directory")
    dest = Path(args[0]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    _write_pair(dest / "multipart_reference.glb", changed=False)
    _write_pair(dest / "multipart_candidate.glb", changed=True)
    print("CBDK_GLB_DIFF_PARTS_FIXTURE_PASS")


if __name__ == "__main__":
    main()
