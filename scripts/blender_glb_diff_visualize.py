"""Trusted GLB-020 Blender runner: color each original mesh part by sampled distance.

Executes only CBDK-authored code in factory-startup Blender with --disable-autoexec.
Private input mesh names are never exported or included in aggregate JSON.
Derived GLBs retain world-space geometry and MUST remain local/private.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_diff_colors import (  # noqa: E402
    COLOR_RGBA, MAX_PARTS, classify_faces, summarize_anonymous_parts,
)
from cbdk.glb_surface_distance import MAX_TRIANGLES  # noqa: E402
from cbdk.glb_diff_viewer import render_local_diff_viewer  # noqa: E402
from cbdk.glb_part_match import suggest_spatial_part_matches  # noqa: E402

MARKER = "CBDK_GLB_DIFF_VISUALIZE_PASS "


def _read_world_triangles(source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = sorted(
        (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
        key=lambda obj: obj.name,
    )
    if not objects:
        raise RuntimeError("No mesh objects in imported GLB")
    if len(objects) > MAX_PARTS:
        raise RuntimeError("GLB exceeds 64 mesh-object visualization limit")
    total = 0
    for obj in objects:
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
        if total > MAX_TRIANGLES:
            raise RuntimeError("GLB exceeds 512 triangle visualization limit")

    faces, face_counts = [], []
    for obj in objects:
        triangles = obj.data.loop_triangles
        if not triangles:
            continue
        face_counts.append(len(triangles))
        for triangle in triangles:
            faces.append([
                tuple(float(v) for v in (
                    obj.matrix_world @ obj.data.vertices[index].co
                ))
                for index in triangle.vertices
            ])
    if not face_counts:
        raise RuntimeError("GLB has no triangulated surface to visualize")
    return faces, face_counts


def _color_material(category):
    material = bpy.data.materials.new("CBDK_diff_" + category)
    material.diffuse_color = COLOR_RGBA[category]
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = COLOR_RGBA[category]
        bsdf.inputs["Roughness"].default_value = 0.85
    return material


def _write_overlay(faces, classes, face_counts, output, *, role):
    """Export one anonymized mesh per input part with original world coordinates.

    All materialized faces remain separate by object; no source object name,
    private path, material name or custom Blender property is copied.
    """
    if len(faces) != len(classes) or sum(face_counts) != len(faces):
        raise RuntimeError("Face/color/part boundaries do not match")
    if role not in ("Reference", "Candidate"):
        raise RuntimeError("Unexpected overlay role")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    palette = {name: _color_material(name) for name in COLOR_RGBA}
    material_indices = {name: i for i, name in enumerate(COLOR_RGBA)}
    start = 0
    for index, count in enumerate(face_counts, start=1):
        part_faces = faces[start:start + count]
        part_colors = classes[start:start + count]
        start += count
        vertices, polygons = [], []
        for face in part_faces:
            offset = len(vertices)
            vertices.extend(face)
            polygons.append((offset, offset + 1, offset + 2))
        name = f"CBDK_{role}_Part_{index:03d}"
        mesh = bpy.data.meshes.new(name + "_Mesh")
        mesh.from_pydata(vertices, [], polygons)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        for color in COLOR_RGBA:
            mesh.materials.append(palette[color])
        for polygon, color in zip(mesh.polygons, part_colors):
            polygon.material_index = material_indices[color]
        obj.select_set(True)
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

    ref_faces, ref_counts = _read_world_triangles(reference)
    cand_faces, cand_counts = _read_world_triangles(candidate)
    result = classify_faces(ref_faces, cand_faces)
    ref_parts = summarize_anonymous_parts(result["reference_labels"], ref_counts)
    cand_parts = summarize_anonymous_parts(result["candidate_labels"], cand_counts)
    _write_overlay(
        ref_faces, result["reference_labels"], ref_counts,
        output_dir / "reference_diff.glb", role="Reference",
    )
    _write_overlay(
        cand_faces, result["candidate_labels"], cand_counts,
        output_dir / "candidate_diff.glb", role="Candidate",
    )

    # The HTML intentionally contains local derived geometry. It is NOT a
    # sanitized aggregate report and must never be published for private GLBs.
    html = render_local_diff_viewer(
        ref_faces, cand_faces, result["reference_labels"],
        result["candidate_labels"], ref_counts, cand_counts,
    )
    (output_dir / "compare_viewer.html").write_text(html, encoding="utf-8")

    part_matches = suggest_spatial_part_matches(
        ref_faces, cand_faces, ref_counts, cand_counts,
    )
    report = {
        "schema_version": 1,
        "kind": "cbdk_glb_diff_visualization",
        "status": "review_only",
        "source": "local_blender_import_color_overlay",
        "blender_version": bpy.app.version_string,
        "outputs": ["reference_diff.glb", "candidate_diff.glb"],
        "viewer": "compare_viewer.html",
        "viewer_contains_derived_geometry": True,
        "viewer_local_only": True,
        "viewer_shared_camera": True,
        "viewer_browser_interaction_verified": False,
        "unobserved_regions_verified": False,
        "triangle_limit_per_scene": MAX_TRIANGLES,
        "part_count_limit_per_scene": MAX_PARTS,
        "reference": result["reference_counts"],
        "candidate": result["candidate_counts"],
        "parts": {"reference": ref_parts, "candidate": cand_parts},
        "part_id_scheme": "anonymous_sequential_by_imported_object_name",
        "cross_file_part_identity_proven": False,
        "part_match_candidates": part_matches,
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
            "Face colors measure 24 sparse samples, not an exact or complete surface",
            "Anonymous part indexes identify meshes within one GLB only",
            "Same part index across files is NOT verified object correspondence",
            "Spatial part candidates are uncertain heuristics, not verified identity",
            "Unmeasured regions are not localized or uniquely colored",
            "Only local derived GLBs contain private geometry; JSON is aggregate-only",
            "Source and candidate must share a coordinate system and units",
            "Offline two-canvas synchronized-view HTML is implemented but browser UI automation is not verified",
            "2D canvas painter uses approximate depth ordering, not a GPU depth buffer",
            "No cross-file part matching, automatic modification or parameter approval",
        ],
    }
    (output_dir / "review.json").write_text(
        json.dumps(
            report, ensure_ascii=False, indent=2, sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )
    print(MARKER + json.dumps({
        "kind": "cbdk_glb_diff_visualization", "status": "review_only",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
