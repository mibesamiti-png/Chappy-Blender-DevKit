"""Fixed CBDK Blender runner: compare two locally supplied GLBs without addons.

Runs only from the trusted Python launcher in factory-startup Blender with
auto-execution disabled. World-coordinate triangles stay in memory; only
aggregate measurements are written. A 512-face cap is per imported scene.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_surface_distance import (  # noqa: E402
    MAX_TRIANGLES, compare_triangle_surfaces,
)
from cbdk.glb_multires_surface import (  # noqa: E402
    compare_multires_triangle_surfaces,
)

from cbdk.glb_part_hints import count_based_part_hints  # noqa: E402

MARKER = "CBDK_GLB_SURFACE_REVIEW_PASS "


def _read_world_triangles(source: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    mesh_objects = sorted(
        (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
        key=lambda obj: obj.name,
    )
    if not mesh_objects:
        raise RuntimeError("Imported GLB has no mesh objects")
    face_total = 0
    part_counts = []
    for obj in mesh_objects:
        mesh = obj.data
        if hasattr(mesh, "calc_loop_triangles"):
            mesh.calc_loop_triangles()
        count = len(mesh.loop_triangles)
        part_counts.append(count)
        face_total += count
    if face_total > MAX_TRIANGLES:
        return None, face_total, part_counts

    triangles = []
    for obj in mesh_objects:
        mesh = obj.data
        for tri in mesh.loop_triangles:
            triangles.append([
                tuple(float(v) for v in (
                    obj.matrix_world @ mesh.vertices[index].co))
                for index in tri.vertices
            ])
    return triangles, face_total, part_counts


def _safe_report(ref_faces, cand_faces, *, ref_count, cand_count, ref_parts=None, cand_parts=None):
    report = {
        "schema_version": 1,
        "kind": "cbdk_glb_surface_review",
        "source": "local_blender_import_aggregate_only",
        "blender_version": bpy.app.version_string,
        "reference_triangles": ref_count,
        "candidate_triangles": cand_count,
        "triangle_limit_per_scene": MAX_TRIANGLES,
        "complete_surface_equivalence_proven": False,
        "auto_apply": False,
        "safety": {
            "executes_addon_code": False,
            "uploads_private_glb": False,
            "saves_raw_mesh_vertices": False,
            "changes_source_glbs": False,
        },
        "limitations": [
            "Two GLBs must be aligned in the same coordinate system and units",
            "Triangle cap is strict: over-limit models are skipped, not simplified",
            "Sampling can miss small holes, internal cavities and thin details",
            "Sampled distance zero does not prove exact surface or volume equivalence",
            "No automatic source changes or parameter approvals",
        ],
    }
    # Anonymous counts preserve a useful inventory without leaking mesh names.
    # Sorted counts are not a correspondence proof between GLB objects.
    if ref_parts is not None and cand_parts is not None:
        report["part_inventory"] = {
            "reference_object_count": len(ref_parts),
            "candidate_object_count": len(cand_parts),
            "reference_triangle_counts": sorted(ref_parts, reverse=True)[:32],
            "candidate_triangle_counts": sorted(cand_parts, reverse=True)[:32],
            "max_listed_per_side": 32,
            "correspondence_verified": False,
            "identifies_changed_part": False,
            "notes": "Anonymous size-ranked inventory, not matched objects",
        }
        report["part_count_hints"] = count_based_part_hints(
            report["part_inventory"]["reference_triangle_counts"],
            report["part_inventory"]["candidate_triangle_counts"],
            reference_total=len(ref_parts), candidate_total=len(cand_parts),
        )
    if ref_faces is None or cand_faces is None:
        report.update({
            "status": "skipped",
            "reason": "triangle_limit",
            "surface_observation": "not_measured",
        })
        return report
    fixed = compare_triangle_surfaces(ref_faces, cand_faces)
    adaptive = compare_multires_triangle_surfaces(ref_faces, cand_faces)
    observed = max(
        fixed["symmetric_sampled_max"],
        adaptive["refined_symmetric_sampled_max"],
    ) > 1e-6
    report.update({
        "status": "review_only",
        "surface_observation": (
            "sampled_difference_detected" if observed
            else "no_difference_observed_at_samples"
        ),
        "fixed_surface": fixed,
        "adaptive_surface": adaptive,
    })
    return report


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Missing -- separator for trusted GLB surface arguments")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise RuntimeError("Provide reference.glb, candidate.glb, output.json")
    ref, cand, output = (Path(value).resolve() for value in args)
    # No user source scripts are imported or executed in this runner.
    reference, ref_count, ref_parts = _read_world_triangles(ref)
    candidate, cand_count, cand_parts = _read_world_triangles(cand)
    report = _safe_report(
        reference, candidate, ref_count=ref_count, cand_count=cand_count,
        ref_parts=ref_parts, cand_parts=cand_parts,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2,
                   allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(MARKER + json.dumps({
        "kind": report["kind"], "status": report["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
