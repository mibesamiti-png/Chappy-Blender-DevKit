"""Trusted Blender-side GLB renderer for CBDK.

Renders front/right/top/isometric PNGs from one local GLB under factory-startup.
The source .blend/project is never opened or saved.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

MARKER = "CBDK_GLB_RENDER_PASS "


def _args():
    if "--" not in sys.argv:
        raise RuntimeError("Missing arguments after --")
    values = sys.argv[sys.argv.index("--") + 1:]
    if len(values) != 3:
        raise RuntimeError("Expected input.glb output_dir resolution")
    source = Path(values[0]).resolve()
    output = Path(values[1]).resolve()
    resolution = int(values[2])
    if source.suffix.lower() != ".glb" or not source.is_file():
        raise RuntimeError("Input must be an existing .glb file")
    if not 256 <= resolution <= 2048:
        raise RuntimeError("Resolution outside 256..2048")
    return source, output, resolution


def _visible_meshes(objects):
    return [obj for obj in objects if obj.type == "MESH" and not obj.hide_get()]


def _bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        raise RuntimeError("Imported GLB contains no visible mesh bounds")
    mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (mins + maxs) * 0.5
    size = maxs - mins
    radius = max(size.length * 0.5, max(size.x, size.y, size.z) * 0.5, 1e-4)
    return mins, maxs, center, size, radius, points


def _look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _setup_studio(center, radius):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.035, 0.045)
    directions = [Vector((1.5, -1.8, 2.2)), Vector((-1.7, -0.8, 1.2)), Vector((0.2, 1.9, 2.0))]
    energies = (1200.0, 800.0, 500.0)
    sizes = (5.0, 4.0, 3.0)
    for i, (direction, energy, size) in enumerate(zip(directions, energies, sizes)):
        data = bpy.data.lights.new(f"CBDK_Area_{i}", type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(f"CBDK_Area_{i}", data)
        scene.collection.objects.link(light)
        light.location = center + direction.normalized() * radius * 4.0
        _look_at(light, center)


def _make_camera():
    data = bpy.data.cameras.new("CBDK_GLB_Camera")
    data.type = "ORTHO"
    camera = bpy.data.objects.new("CBDK_GLB_Camera", data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def _projected_extent(points, camera):
    inv = camera.matrix_world.inverted()
    local = [inv @ p for p in points]
    width = max(p.x for p in local) - min(p.x for p in local)
    height = max(p.y for p in local) - min(p.y for p in local)
    return max(width, height, 1e-4)


def _render_view(camera, center, points, radius, direction, output_path, resolution):
    camera.location = center + Vector(direction).normalized() * radius * 4.0
    _look_at(camera, center)
    camera.data.ortho_scale = _projected_extent(points, camera) * 1.18
    scene = bpy.context.scene
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def _object_row(obj):
    mesh = obj.data
    return {
        "name": obj.name,
        "mesh": mesh.name,
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        "location": [float(v) for v in obj.location],
        "rotation_euler": [float(v) for v in obj.rotation_euler],
        "scale": [float(v) for v in obj.scale],
        "dimensions": [float(v) for v in obj.dimensions],
        "world_matrix": [[float(v) for v in row] for row in obj.matrix_world],
    }


def main():
    source, output, resolution = _args()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = _visible_meshes(list(bpy.context.scene.objects))
    if not meshes:
        raise RuntimeError("No mesh objects imported from GLB")
    mins, maxs, center, size, radius, points = _bounds(meshes)
    _setup_studio(center, radius)
    camera = _make_camera()
    views = {
        "front.png": (0.0, -1.0, 0.0),
        "right.png": (1.0, 0.0, 0.0),
        "top.png": (0.0, 0.0, 1.0),
        "iso.png": (1.0, -1.0, 0.8),
    }
    for filename, direction in views.items():
        _render_view(camera, center, points, radius, direction, output / filename, resolution)
    metadata = {
        "schema_version": 1,
        "kind": "cbdk_glb_blender_scene_metadata",
        "source_name": source.name,
        "blender_version": bpy.app.version_string,
        "object_count": len(meshes),
        "bounds": {"min": list(mins), "max": list(maxs), "center": list(center), "size": list(size)},
        "objects": [_object_row(obj) for obj in sorted(meshes, key=lambda x: x.name)],
        "views": list(views),
        "safety": {"factory_startup": True, "source_blend_modified": False, "saved_blend": False},
    }
    (output / "scene_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    payload = {"metadata": "scene_metadata.json", "views": list(views),
               "blender_version": bpy.app.version_string, "object_count": len(meshes)}
    print(MARKER + json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
