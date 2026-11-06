"""Trusted GLB-020 Blender runner: color each original face by sampled distance.

Executes only CBDK-authored code in factory-startup Blender with --disable-autoexec.
The two derived colored GLBs stay on local disk; JSON contains aggregates only.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_diff_colors import COLOR_RGBA, classify_faces
from cbdk.glb_surface_distance import MAX_TRIANGLES

MARKER = "CBDK_GLB_DIFF_VISUALIZE_PASS "


def _read_world_triangles(source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = sorted((o for o in bpy.context.scene.objects if o.type == "MESH"),
                     key=lambda o: o.name)
    if not objects:
        raise RuntimeError("No mesh objects in imported GLB")
    total = 0
    for obj in objects:
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
        if total > MAX_TRIANGLES:
            raise RuntimeError("GLB exceeds 512 triangle visualization limit")
    faces = []
    for obj in objects:
        for triangle in obj.data.loop_triangles:
            faces.append([
                tuple(float(v) for v in (obj.matrix_world @ obj.data.vertices[index].co))
                for index in triangle.vertices
            ])
    return faces


def _color_material(category):
    mat = bpy.data.materials.new("CBDK_diff_" + category)
    mat.diffuse_color = COLOR_RGBA[category]
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = COLOR_RGBA[category]
        bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def _write_overlay(faces, classes, output):
    """Export a new derived GLB, never editing the input GLB or source addons."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if len(faces) != len(classes):
        raise RuntimeError("Face/color alignment mismatch")
    vertices = []
    polygons = []
    for face in faces:
        offset = len(vertices)
        vertices.extend(face)
        polygons.append((offset, offset + 1, offset + 2))
    mesh = bpy.data.meshes.new("CBDK_Diff_Faces")
    mesh.from_pydata(vertices, [], polygons)
    mesh.update()
    obj = bpy.data.objects.new("CBDK_Colored_Comparison", mesh)
    bpy.context.collection.objects.link(obj)
    palette = {name: _color_material(name) for name in COLOR_RGBA}
    for name in COLOR_RGBA:
        mesh.materials.append(palette[name])
    index = {name: i for i, name in enumerate(COLOR_RGBA)}
    for polygon, category in zip(mesh.polygons, classes):
        polygon.material_index = index[category]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(output), export_format="GLB", use_selection=True,
    )
    if not output.is_file() or output.stat().st_size < 100:
        raise RuntimeError("No usable GLB overlay was generated")


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Missing trusted GLB visualization argument separator")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise RuntimeError("Provide reference.glb candidate.glb new_output_folder")
    reference, candidate, output_dir = (Path(x).resolve() for x in args)
    if not output_dir.is_dir():
        raise RuntimeError("Output folder has not been initialized by trusted launcher")
    ref_faces = _read_world_triangles(reference)
    cand_faces = _read_world_triangles(candidate)
    result = classify_faces(ref_faces, cand_faces)
    _write_overlay(ref_faces, result["reference_labels"], output_dir / "reference_diff.glb")
    _write_overlay(cand_faces, result["candidate_labels"], output_dir / "candidate_diff.glb")
    report = {
        "schema_version": 1,
        "kind": "cbdk_glb_diff_visualization",
        "status": "review_only",
        "source": "local_blender_import_color_overlay",
        "blender_version": bpy.app.version_string,
        "outputs": ["reference_diff.glb", "candidate_diff.glb"],
        "triangle_limit_per_scene": MAX_TRIANGLES,
        "reference": result["reference_counts"],
        "candidate": result["candidate_counts"],
        "reference_sampled_max": result["reference_sampled_max"],
        "candidate_sampled_max": result["candidate_sampled_max"],
        "thresholds": result["thresholds"],
        "legend": result["legend"],
        "sampled_only": True,
        "complete_surface_equivalence_proven": False,
        "auto_apply": False,
        "safety": {
            "executes_addon_code": False,
            "uploads_private_glb": False,
            "saves_raw_mesh_vertices_in_json": False,
            "changes_source_glbs": False,
        },
        "limitations": [
            "Each 3D mesh is colored by coarse per-triangle sampled proximity",
            "Only local derived GLBs contain coordinates; no geometry is saved in JSON",
            "Color is not proof of a defect and unobserved gaps may remain",
            "Reference and candidate must be aligned in the same space and units",
            "No separate object identity match and no automatic fixes",
            "Sampled zero or grey is not exact surface or volume equivalence",
        ],
    }
    (output_dir / "review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True,
                   allow_nan=False) + "\n", encoding="utf-8",
    )
    print(MARKER + json.dumps({
        "kind": "cbdk_glb_diff_visualization", "status": "review_only",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
