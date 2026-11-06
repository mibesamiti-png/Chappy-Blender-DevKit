"""Blender runtime experiment for a CBDK-AUTHORED synthetic addon only.

This file is an allowlisted CI fixture, NOT a launcher for user addons.
It changes one synthetic Blender PropertyGroup setting at a time, generates
seven real GLBs, reimports them and measures changed mesh coordinates.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bpy

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from fixtures import cbdk_parameter_experiment as fixture  # noqa: E402
from cbdk.parameter_experiment_metrics import vertex_displacement  # noqa: E402
from cbdk.parameter_direction import choose_review_direction  # noqa: E402

VARIANTS = (
    ("baseline", 0.75, 0.08),
    ("sphere_radius_changed", 1.15, 0.08),
    ("bevel_width_changed", 0.75, 0.35),
    # Deliberately bracket the baseline for direction evidence. The reference
    # is held fixed, and all values are allowed by the trusted fixture.
    ("sphere_probe_up", 0.95, 0.08),
    ("sphere_probe_down", 0.55, 0.08),
    ("bevel_probe_up", 0.75, 0.20),
    ("bevel_probe_down", 0.75, 0.03),
)


def _clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _meshes() -> dict:
    objects = {obj.name: obj for obj in bpy.context.scene.objects if obj.type == "MESH"}
    if set(objects) != {"CBDK_Param_Sphere", "CBDK_Param_BevelCube"}:
        raise RuntimeError("Trusted fixture generated an unexpected object set")
    return objects


def _mesh_stats(obj) -> dict:
    vertices = [[round(float(axis), 6) for axis in vertex.co] for vertex in obj.data.vertices]
    digest = hashlib.sha256(
        json.dumps(vertices, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "mesh_vertex_count": len(vertices),
        "mesh_polygon_count": len(obj.data.polygons),
        "mesh_coordinate_sha256": digest,
        "local_vertices_for_trusted_fixture": vertices,
        "world_dimensions": [round(float(value), 6) for value in obj.dimensions],
    }


def _snapshot() -> dict:
    return {name: _mesh_stats(obj) for name, obj in sorted(_meshes().items())}


def _assert_real_effects(snapshots: dict) -> None:
    base = snapshots["baseline"]
    bigger = snapshots["sphere_radius_changed"]
    bevel = snapshots["bevel_width_changed"]
    sphere = "CBDK_Param_Sphere"
    cube = "CBDK_Param_BevelCube"

    if (bigger[sphere]["world_dimensions"][0] -
            base[sphere]["world_dimensions"][0] < 0.65):
        raise AssertionError("Sphere radius change did not affect evaluated shape")
    if bigger[sphere]["mesh_coordinate_sha256"] == base[sphere]["mesh_coordinate_sha256"]:
        raise AssertionError("Sphere mesh stayed unchanged after changing radius")
    if bevel[cube]["mesh_coordinate_sha256"] == base[cube]["mesh_coordinate_sha256"]:
        raise AssertionError("Applied Bevel modifier did not affect mesh coordinates")
    if base[cube]["mesh_coordinate_sha256"] != bigger[cube]["mesh_coordinate_sha256"]:
        raise AssertionError("Radius-only change unexpectedly altered cube mesh")
    if base[sphere]["mesh_coordinate_sha256"] != bevel[sphere]["mesh_coordinate_sha256"]:
        raise AssertionError("Bevel-only change unexpectedly altered sphere mesh")
    if any(base[cube]["world_dimensions"][i] != bevel[cube]["world_dimensions"][i]
           for i in range(3)):
        raise AssertionError("Cube bounds changed; bevel fixture should preserve dimensions")


def main() -> None:
    if "--" not in sys.argv:
        raise RuntimeError("Expected output folder after --")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise RuntimeError("Expected exactly one output folder")
    root = Path(args[0]).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    fixture.register()
    generated = {}
    imported = {}
    try:
        for variant, radius, bevel_width in VARIANTS:
            _clean_scene()
            settings = bpy.context.scene.cbdk_parameter_experiment
            settings.sphere_radius = radius
            settings.bevel_width = bevel_width
            status = bpy.ops.mesh.cbdk_parameter_experiment_build()
            if "FINISHED" not in status:
                raise AssertionError("Trusted fixture operator did not finish")
            generated[variant] = _snapshot()
            glb = root / f"{variant}.glb"
            bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB")
            if not glb.is_file() or glb.stat().st_size < 100:
                raise RuntimeError("Trusted fixture did not produce GLB")
            _clean_scene()
            bpy.ops.import_scene.gltf(filepath=str(glb))
            imported[variant] = _snapshot()
            for name in generated[variant]:
                original = generated[variant][name]["world_dimensions"]
                roundtrip = imported[variant][name]["world_dimensions"]
                if max(abs(x - y) for x, y in zip(original, roundtrip)) > 1e-4:
                    raise AssertionError("GLB roundtrip altered object dimensions")
        _assert_real_effects(generated)
        _assert_real_effects(imported)
    finally:
        _clean_scene()
        fixture.unregister()

    # Only synthetic repository-owned meshes enter this metric. Drop raw XYZ
    # coordinates from the final JSON: report only aggregate evidence.
    displacement = {}
    for stage, snapshots in (("generated", generated), ("imported", imported)):
        base = snapshots["baseline"]
        displacement[stage] = {}
        for changed in ("sphere_radius_changed", "bevel_width_changed"):
            displacement[stage][changed] = {
                name: vertex_displacement(
                    base[name]["local_vertices_for_trusted_fixture"],
                    snapshots[changed][name]["local_vertices_for_trusted_fixture"])
                for name in sorted(base)
            }
    # Compare each deliberate probe against the SAME target reference and
    # baseline. The geometry evidence is real Blender GLB roundtrip data,
    # not a fabricated estimate or an inferred user-addon setting.
    direction_evidence = {}
    sphere = "CBDK_Param_Sphere"
    cube = "CBDK_Param_BevelCube"
    groups = (
        ("sphere_radius", "sphere_radius_changed", "sphere_probe_up",
         "sphere_probe_down", sphere, cube),
        ("bevel_width", "bevel_width_changed", "bevel_probe_up",
         "bevel_probe_down", cube, sphere),
    )
    for stage_name, snapshots in (("generated", generated), ("imported", imported)):
        direction_evidence[stage_name] = {}
        for prop, target, up, down, affected, unrelated in groups:
            ref = snapshots[target][affected]["local_vertices_for_trusted_fixture"]
            distances = {
                label: vertex_displacement(
                    ref, snapshots[variant][affected]["local_vertices_for_trusted_fixture"]
                )["mean_local_displacement"]
                for label, variant in (("baseline", "baseline"),
                                       ("increase_probe", up),
                                       ("decrease_probe", down))
            }
            direction = choose_review_direction(
                distances["baseline"], distances["increase_probe"],
                distances["decrease_probe"])
            # Independent negative controls for both probe directions.
            unchanged = {}
            for variant in (up, down):
                unchanged[variant] = vertex_displacement(
                    snapshots["baseline"][unrelated]["local_vertices_for_trusted_fixture"],
                    snapshots[variant][unrelated]["local_vertices_for_trusted_fixture"]
                )["changed_vertex_count"]
                if unchanged[variant] != 0:
                    raise AssertionError(prop + " probe modified unrelated fixture mesh")
            if direction["decision"] != "increase":
                raise AssertionError(prop + " did not improve toward known synthetic reference")
            if not distances["decrease_probe"] > distances["baseline"] + 1e-5:
                raise AssertionError(prop + " wrong-direction probe did not increase reference error")
            direction_evidence[stage_name][prop] = {
                **direction,
                "affected_fixture_object": affected,
                "unrelated_fixture_object": unrelated,
                "unrelated_probe_changed_vertices": unchanged,
                "known_reference_variant": target,
                "no_user_addon_assumptions": True,
            }

    for stage in (generated, imported):
        for variant in stage.values():
            for stats in variant.values():
                del stats["local_vertices_for_trusted_fixture"]

    cube = "CBDK_Param_BevelCube"
    for stage, rows in displacement.items():
        radius = rows["sphere_radius_changed"]
        bevel = rows["bevel_width_changed"]
        if not radius[sphere]["max_local_displacement"] > 0.2:
            raise AssertionError("Radius did not produce measurable sphere vertex displacement")
        if radius[cube]["changed_vertex_count"] != 0:
            raise AssertionError("Sphere radius changed an unrelated bevel cube")
        if not bevel[cube]["max_local_displacement"] > 0.01:
            raise AssertionError("Bevel width did not move cube vertices measurably")
        if bevel[sphere]["changed_vertex_count"] != 0:
            raise AssertionError("Bevel width changed an unrelated sphere")

    result = {
        "kind": "cbdk_trusted_blender_parameter_experiment",
        "schema_version": 1,
        "blender_version": bpy.app.version_string,
        "source_fixture": "cbdk_authored_only",
        "variables_changed_one_at_a_time": True,
        "variants": [
            {"id": name, "parameters": {"sphere_radius": radius, "bevel_width": width},
             "glb": f"{name}.glb"}
            for name, radius, width in VARIANTS
        ],
        "generated_mesh": generated,
        "imported_glb_mesh": imported,
        "quantified_vertex_displacement": displacement,
        "direction_probe_evidence": direction_evidence,
        "controls": {
            "sphere_radius_changes_sphere": True,
            "sphere_radius_does_not_change_bevel_cube": True,
            "bevel_width_changes_bevel_cube": True,
            "bevel_width_does_not_change_sphere": True,
            "bevel_width_preserves_cube_bounds": True,
            "all_three_glbs_reimported": True,
            "all_seven_glbs_reimported": True,
            "both_parameter_directions_tested": True,
            "unrelated_meshes_unchanged_for_all_probes": True,
        },
        "limitations": [
            "Only repository-owned trusted synthetic addon was executed",
            "This proves the fixture parameters change geometry, not arbitrary user-addon behavior",
            "Geometry coordinate hashes are test evidence, not equivalence proofs for real assets",
            "A one-step direction result is not an optimum numeric setting for arbitrary geometry",
        ],
        "safety": {
            "user_addon_executed": False,
            "user_source_modified": False,
            "private_glb_uploaded": False,
            "auto_approves": False,
        },
    }
    destination = root / "parameter_experiment.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("CBDK_PARAMETER_EXPERIMENT_PASS " +
          json.dumps({"blender_version": bpy.app.version_string,
                      "variants": len(VARIANTS), "report": destination.name}))


if __name__ == "__main__":
    main()
