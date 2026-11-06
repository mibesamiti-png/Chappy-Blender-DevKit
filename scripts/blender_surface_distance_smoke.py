"""Blender CI-only GLB roundtrip evidence for bounded triangle surface distance.

This script constructs FIVE CBDK-authored planar meshes. Nothing in this script
opens, imports, evaluates, or runs any user-supplied addon or geometry.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from cbdk.glb_surface_distance import compare_triangle_surfaces  # noqa: E402

MESH_NAME = "CBDK_Surface_Fixture"


def _outer(z):
    return [
        (-1.0, -1.0, z), (1.0, -1.0, z),
        (1.0, 1.0, z), (-1.0, 1.0, z),
    ]


def _mesh_fixture(variant):
    if variant == "filled_main":
        return _outer(0.0), [(0, 1, 2), (0, 2, 3)]
    if variant == "filled_other":
        # The same square, but with the opposite diagonal and different
        # vertex winding/order. No exact vertex correspondence is presumed.
        return _outer(0.0), [(0, 1, 3), (1, 2, 3)]
    if variant == "raised":
        return _outer(0.25), [(0, 1, 2), (0, 2, 3)]
    if variant == "with_open_hole":
        inner = [
            (-0.45, -0.45, 0.0), (0.45, -0.45, 0.0),
            (0.45, 0.45, 0.0), (-0.45, 0.45, 0.0),
        ]
        faces = []
        for i in range(4):
            j = (i + 1) % 4
            faces.extend(((i, j, j + 4), (i, j + 4, i + 4)))
        return _outer(0.0) + inner, faces
    if variant == "grid_256":
        # 256 spatially separated triangles to test actual GLB import and
        # BVH pruning. Not a production-sized user asset.
        verts, faces = [], []
        for y in range(16):
            for x in range(16):
                ox, oy = x * 2.75, y * 2.75
                idx = len(verts)
                verts.extend(((ox, oy, 0.0), (ox + 1.0, oy, 0.0),
                              (ox, oy + 1.0, 0.0)))
                faces.append((idx, idx + 1, idx + 2))
        return verts, faces
    raise RuntimeError("Unknown CBDK-owned fixture")


def _clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _create(variant):
    verts, faces = _mesh_fixture(variant)
    mesh = bpy.data.meshes.new("CBDK_Surface_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(MESH_NAME, mesh)
    bpy.context.collection.objects.link(obj)


def _world_triangles():
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(objects) != 1:
        raise AssertionError("Expected exactly one CBDK-generated mesh")
    obj = objects[0]
    mesh = obj.data
    return [
        [
            tuple(float(c) for c in (obj.matrix_world @ mesh.vertices[index].co))
            for index in triangle.vertices
        ]
        for triangle in mesh.loop_triangles
    ]


def _bounds_xy(triangles):
    xyz = [p for face in triangles for p in face]
    return tuple(round(v, 6) for v in (
        min(p[0] for p in xyz), max(p[0] for p in xyz),
        min(p[1] for p in xyz), max(p[1] for p in xyz)))


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Expected exactly one CI output directory after --")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise RuntimeError("Expected exactly one CI output directory")
    root = Path(args[0]).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    surfaces = {}
    names = ("filled_main", "filled_other", "with_open_hole", "raised",
             "grid_256")
    for variant in names:
        _clear()
        _create(variant)
        glb = root / (variant + ".glb")
        bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB")
        if not glb.is_file() or glb.stat().st_size < 100:
            raise AssertionError("CBDK synthetic surface GLB was not exported")
        _clear()
        bpy.ops.import_scene.gltf(filepath=str(glb))
        surfaces[variant] = _world_triangles()
    _clear()

    baseline = surfaces["filled_main"]
    same = compare_triangle_surfaces(baseline, surfaces["filled_other"])
    hole = compare_triangle_surfaces(surfaces["with_open_hole"], baseline)
    raised = compare_triangle_surfaces(baseline, surfaces["raised"])
    grid = compare_triangle_surfaces(surfaces["grid_256"], surfaces["grid_256"])
    exact_evaluations = grid["reference_to_candidate"]["triangle_distance_evaluations"]
    brute_evaluations = grid["reference_to_candidate"]["brute_force_evaluations"]
    if len(surfaces["grid_256"]) != 256:
        raise AssertionError("Imported synthetic benchmark GLB lost its triangles")
    if grid["symmetric_mean"] != 0.0 or grid["symmetric_sampled_max"] != 0.0:
        raise AssertionError("256-face identical mesh must have zero sampled distance")
    if not 0 < exact_evaluations < brute_evaluations // 4:
        raise AssertionError("BVH did not reduce exact triangle checks by at least 4x")


    if same["symmetric_mean"] > 1e-6 or same["symmetric_sampled_max"] > 1e-6:
        raise AssertionError("Identical planar surface differs after alternate triangulation")
    if _bounds_xy(baseline) != _bounds_xy(surfaces["with_open_hole"]):
        raise AssertionError("Hole fixture must preserve the outer XY bounds")
    if not hole["candidate_to_reference"]["mean"] > 0.01:
        raise AssertionError("Bidirectional surface comparison missed the open center hole")
    if not hole["symmetric_sampled_max"] > 0.10:
        raise AssertionError("Missing center region is too weakly represented")
    if not 0.249 <= raised["symmetric_mean"] <= 0.251:
        raise AssertionError("World-space Z displacement was not measured correctly")
    if any(x["safety"]["auto_approves"] for x in (same, hole, raised, grid)):
        raise AssertionError("Sampled distance must never auto-approve geometry")
    if any(x["exact_surface_equivalence_verified"] for x in (same, hole, raised, grid)):
        raise AssertionError("Sampled comparison cannot prove exact equivalence")

    output = {
        "schema_version": 1,
        "kind": "cbdk_trusted_glb_surface_distance_experiment",
        "source": "repository_authored_synthetic_only",
        "blender_version": bpy.app.version_string,
        "variants": list(names),
        "triangles": {name: len(faces) for name, faces in surfaces.items()},
        "checks": {
            "same_surface_alternate_triangulation_zero": True,
            "open_hole_same_outer_bounds_detected": True,
            "real_world_z_offset_detected": True,
            "all_four_glbs_roundtripped": True,
            "all_five_glbs_roundtripped": True,
            "bvh_256_face_glb_zero_and_pruned": True,
            "no_exact_surface_equivalence_claims": True,
        },
        "comparisons": {
            "alternate_triangulation": same,
            "open_hole": hole,
            "raised": raised,
            "grid_256": grid,
        },
        "safety": {
            "user_addon_executed": False,
            "private_glb_uploaded": False,
            "auto_edits_source": False,
            "auto_approves": False,
        },
        "limitations": [
            "Only five repository-authored planar GLBs were evaluated in Blender",
            "Open planar cutout detection is not enclosed-cavity or watertightness proof",
            "Sampled maximum is not an exact Hausdorff distance",
            "Bounded CPU comparator rejects >512 triangles; no large asset benchmark yet",
        ],
    }
    (root / "surface_distance_experiment.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("CBDK_SURFACE_DISTANCE_PASS " + json.dumps({
        "blender": bpy.app.version_string,
        "alternate_mean": same["symmetric_mean"],
        "hole_mean": hole["symmetric_mean"],
        "offset_mean": raised["symmetric_mean"],
        "bvh_grid_triangles": len(surfaces["grid_256"]),
        "bvh_triangle_evaluations": exact_evaluations,
        "brute_triangle_evaluations": brute_evaluations,
    }))


if __name__ == "__main__":
    main()
