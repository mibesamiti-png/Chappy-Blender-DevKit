"""Blender CI-only GLB roundtrip evidence for bounded triangle surface distance.

This script constructs SEVEN CBDK-authored planar meshes. Nothing in this script
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
from cbdk.surface_benchmark import benchmark_surface_search  # noqa: E402
from cbdk.glb_multires_surface import compare_multires_triangle_surfaces  # noqa: E402

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
    if variant in ("with_open_hole", "with_narrow_hole"):
        # The narrow version has a known 24-sample blind spot on the
        # filled square and is used only as a bounded synthetic test.
        h = 0.45 if variant == "with_open_hole" else 0.22
        inner = [
            (-h, -h, 0.0), (h, -h, 0.0),
            (h, h, 0.0), (-h, h, 0.0),
        ]
        faces = []
        for i in range(4):
            j = (i + 1) % 4
            faces.extend(((i, j, j + 4), (i, j + 4, i + 4)))
        return _outer(0.0) + inner, faces
    if variant in ("grid_256", "grid_512"):
        # Spatially separated 256/512-triangle grids, only authored here.
        # Never read a user's source files or arbitrary GLBs in public CI.
        cols = 16 if variant == "grid_256" else 32
        verts, faces = [], []
        for y in range(16):
            for x in range(cols):
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
    names = ("filled_main", "filled_other", "with_open_hole",
             "with_narrow_hole", "raised", "grid_256", "grid_512")
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
    # Narrow hole: baseline 24-point scan misses it, but bounded
    # coarse+selective-refinement 48-point scan should see it.
    narrow_legacy = compare_triangle_surfaces(
        baseline, surfaces["with_narrow_hole"])
    narrow_multires = compare_multires_triangle_surfaces(
        baseline, surfaces["with_narrow_hole"])
    if narrow_legacy["symmetric_sampled_max"] != 0.0:
        raise AssertionError("Narrow-hole fixture no longer tests original blind spot")
    if narrow_multires["coarse_symmetric_sampled_max"] != 0.0:
        raise AssertionError("Coarse narrow-hole fixture unexpectedly detected an offset")
    if not narrow_multires["refined_symmetric_sampled_max"] > .005:
        raise AssertionError("Refined surface sampler missed the narrow opening")
    if not narrow_multires["new_nonzero_sample_after_refinement"]:
        raise AssertionError("No new narrow-opening signal was found by refinement")
    if narrow_multires["complete_surface_coverage"] or narrow_multires["auto_approve"]:
        raise AssertionError("Refinement must never auto-certify exact geometry")
    raised = compare_triangle_surfaces(baseline, surfaces["raised"])
    grid = compare_triangle_surfaces(surfaces["grid_256"], surfaces["grid_256"])
    grid_large = compare_triangle_surfaces(surfaces["grid_512"], surfaces["grid_512"])
    # Small identical post-GLB-import inputs permit a fair BVH/brute trial;
    # large meshes only time BVH to avoid making every CI run expensive.
    benchmark_small = benchmark_surface_search(
        surfaces["grid_256"][:64], surfaces["grid_256"][:64], repeats=3)
    benchmark_large = benchmark_surface_search(
        surfaces["grid_512"], surfaces["grid_512"],
        repeats=3, include_brute_force=False)
    exact_evaluations = grid["reference_to_candidate"]["triangle_distance_evaluations"]
    brute_evaluations = grid["reference_to_candidate"]["brute_force_evaluations"]
    if len(surfaces["grid_256"]) != 256:
        raise AssertionError("Imported synthetic benchmark GLB lost its triangles")
    if grid["symmetric_mean"] != 0.0 or grid["symmetric_sampled_max"] != 0.0:
        raise AssertionError("256-face identical mesh must have zero sampled distance")
    if not 0 < exact_evaluations < brute_evaluations // 4:
        raise AssertionError("BVH did not reduce exact triangle checks by at least 4x")
    if len(surfaces["grid_512"]) != 512:
        raise AssertionError("Imported 512-face synthetic GLB lost triangles")
    if grid_large["symmetric_mean"] != 0.0:
        raise AssertionError("512-face identical GLB must have zero sampled score")
    if not benchmark_small["scores_agree_with_brute_force"]:
        raise AssertionError("Same-input timed BVH and brute results disagree")
    if benchmark_small["performance_regression_gate"] or benchmark_large["performance_regression_gate"]:
        raise AssertionError("Wall-clock speed must remain observational only")
    for bench in (benchmark_small, benchmark_large):
        for measured in bench["benchmarks"].values():
            if measured["median_elapsed_ms"] < 0:
                raise AssertionError("Invalid measured elapsed time")


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
    if any(x["safety"]["auto_approves"] for x in (same, hole, raised, grid, grid_large)):
        raise AssertionError("Sampled distance must never auto-approve geometry")
    if any(x["exact_surface_equivalence_verified"] for x in (same, hole, raised, grid, grid_large)):
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
            "all_six_glbs_roundtripped": True,
            "all_seven_glbs_roundtripped": True,
            "narrow_hole_only_detected_after_targeted_refinement": True,
            "bvh_512_face_glb_zero": True,
            "wall_clock_observations_recorded_without_speed_assertions": True,
            "bvh_256_face_glb_zero_and_pruned": True,
            "no_exact_surface_equivalence_claims": True,
        },
        "comparisons": {
            "alternate_triangulation": same,
            "open_hole": hole,
            "narrow_hole_legacy": narrow_legacy,
            "raised": raised,
            "grid_256": grid,
            "grid_512": grid_large,
        },
        "multires": {
            "narrow_hole": narrow_multires,
        },
        "timings": {
            "grid_64_same_input_bvh_vs_bruteforce": benchmark_small,
            "grid_512_bvh_only": benchmark_large,
        },
        "safety": {
            "user_addon_executed": False,
            "private_glb_uploaded": False,
            "auto_edits_source": False,
            "auto_approves": False,
        },
        "limitations": [
            "Only seven repository-authored planar GLBs were evaluated in Blender",
            "Open planar cutout detection is not enclosed-cavity or watertightness proof",
            "Sampled maximum is not an exact Hausdorff distance",
            "Bounded CPU comparator rejects >512 triangles; synthetic observations are not production benchmarks",
            "Observed elapsed times depend on runner CPU load; never require a speed ratio",
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
        "narrow_hole_legacy_max": narrow_legacy["symmetric_sampled_max"],
        "narrow_hole_refined_max": narrow_multires["refined_symmetric_sampled_max"],
        "offset_mean": raised["symmetric_mean"],
        "bvh_grid_triangles": len(surfaces["grid_256"]),
        "benchmark_64_bvh_ms": benchmark_small["benchmarks"]["bvh"]["median_elapsed_ms"],
        "benchmark_64_bruteforce_ms": benchmark_small["benchmarks"]["brute_force"]["median_elapsed_ms"],
        "benchmark_512_bvh_ms": benchmark_large["benchmarks"]["bvh"]["median_elapsed_ms"],
        "bvh_triangle_evaluations": exact_evaluations,
        "brute_triangle_evaluations": brute_evaluations,
    }))


if __name__ == "__main__":
    main()
