"""Trusted, Blender-only smoke test. Run in --background --factory-startup.

No third-party addons or collected code are imported here.
"""
import json
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new('CBDK_Smoke_Mesh')
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
mesh.update()
obj = bpy.data.objects.new('CBDK_Smoke_Object', mesh)
bpy.context.scene.collection.objects.link(obj)
assert len(obj.data.vertices) == 3
assert len(obj.data.polygons) == 1
assert obj.name in bpy.data.objects
name = obj.name
bpy.data.objects.remove(obj, do_unlink=True)
assert name not in bpy.data.objects
print('CBDK_BLENDER_SMOKE_PASS ' + json.dumps({'blender': bpy.app.version_string, 'vertex_count': 3}))
