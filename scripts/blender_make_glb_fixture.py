"""Create tiny deterministic GLB fixtures for CBDK Blender CI."""
from pathlib import Path
import sys
import bpy

if "--" not in sys.argv:
    raise RuntimeError("Missing output path")
args = sys.argv[sys.argv.index("--") + 1:]
if len(args) not in {1, 2}:
    raise RuntimeError("Expected output.glb [reference|silhouette-drift]")
out = Path(args[0]).resolve()
variant = args[1] if len(args) == 2 else "reference"
if variant not in {"reference", "silhouette-drift"}:
    raise RuntimeError("Unknown GLB fixture variant")
out.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
if variant == "reference":
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 0.0))
    bpy.context.object.name = "CBDK_Test_Cube"
else:
    mesh = bpy.data.meshes.new("CBDK_Test_Cube_Mesh")
    vertices = [
        (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0), (0.0, -1.0, 0.0),
        (0.0, 0.0, 1.0), (0.0, 0.0, -1.0),
    ]
    faces = [
        (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
        (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5),
    ]
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("CBDK_Test_Cube", mesh)
    bpy.context.scene.collection.objects.link(obj)

bpy.ops.mesh.primitive_uv_sphere_add(
    segments=16, ring_count=8, radius=0.65, location=(1.8, 0.2, 0.5)
)
bpy.context.object.name = "CBDK_Test_Sphere"

bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=False)
print("CBDK_GLB_FIXTURE_PASS " + variant + " " + str(out))
