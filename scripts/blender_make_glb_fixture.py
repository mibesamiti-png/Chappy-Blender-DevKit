"""Create a tiny deterministic GLB fixture for CBDK Blender CI."""
from pathlib import Path
import sys
import bpy

if "--" not in sys.argv:
    raise RuntimeError("Missing output path")
args = sys.argv[sys.argv.index("--") + 1:]
if len(args) != 1:
    raise RuntimeError("Expected one output .glb path")
out = Path(args[0]).resolve()
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 0.0))
bpy.context.object.name = "CBDK_Test_Cube"
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.65, location=(1.8, 0.2, 0.5))
bpy.context.object.name = "CBDK_Test_Sphere"
bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=False)
print("CBDK_GLB_FIXTURE_PASS " + str(out))
