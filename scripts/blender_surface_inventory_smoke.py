"""Synthetic-only end-to-end inventory evidence; no user GLBs or addons.

Run in factory-startup Blender. Each case is exported, then reimported by the
trusted surface-review subprocess. Only aggregate assertions enter stdout.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_surface_pipeline import run_glb_surface_review  # noqa: E402
from cbdk.glb_part_match import suggest_spatial_part_matches  # noqa: E402
from cbdk.glb_boundary_audit import boundary_audit  # noqa: E402


def _topology_count_roundtrip(output):
    """Verify numeric boundary guard after genuine Blender GLB export/import."""
    vertices = [
        (0., 0., 0.), (1., 0., 0.), (0., 1., 0.),
        (1., 1., 0.), (.4, .7, 0.),
    ]
    variants = (
        ("connected", [(0, 1, 2), (1, 3, 2)]),
        ("disconnected", [(0, 1, 2), (0, 3, 4)]),
    )
    imported = []
    for label, polygons in variants:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new("CBDK_Synthetic_Topology")
        mesh.from_pydata(vertices, [], polygons)
        mesh.update()
        obj = bpy.data.objects.new("CBDK_Synthetic_Topology", mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        source = output / ("topology_" + label + ".glb")
        bpy.ops.export_scene.gltf(
            filepath=str(source), export_format="GLB", use_selection=True,
        )
        digest = hashlib.sha256(source.read_bytes()).digest()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        assert hashlib.sha256(source.read_bytes()).digest() == digest
        meshes = [item for item in bpy.context.scene.objects
                  if item.type == "MESH"]
        assert len(meshes) == 1, "Unexpected synthetic import mesh count"
        item = meshes[0]
        item.data.calc_loop_triangles()
        faces = [[tuple(float(x) for x in
                 (item.matrix_world @ item.data.vertices[index].co))
                  for index in face.vertices]
                 for face in item.data.loop_triangles]
        assert len(faces) == 2, "Synthetic triangles did not survive GLB"
        imported.append(faces)

    reference, candidate = imported
    ref_edges = boundary_audit(reference, [2])["parts"][0]
    cand_edges = boundary_audit(candidate, [2])["parts"][0]
    assert (ref_edges["boundary_edges"], cand_edges["boundary_edges"]) == (4, 6)
    assert ref_edges["observed_boundary"] and cand_edges["observed_boundary"]
    match = suggest_spatial_part_matches(reference, candidate, [2], [2])
    row = match["reference_parts"][0]
    assert row["status"] == "ambiguous", row
    assert row["topology_review_reasons"] == ["boundary_edge_count_mismatch"], row
    assert match["unpaired_candidate_part_ids"] == ["part_001"], match
    assert match["cross_file_part_identity_proven"] is False
    print("CBDK synthetic GLB topology-count roundtrip passed")


def _boundary_layout_roundtrip(output):
    """End-to-end equal-count moved-hole and retessellation negative controls."""
    from time import perf_counter

    outer = [(-1., -1., 0.), (1., -1., 0.),
             (1., 1., 0.), (-1., 1., 0.)]

    def make_faces(*, opening_shift=0., opening_half_width=.3,
                   alternate=False, mirrored=False):
        inner = [
            (opening_shift - opening_half_width, -.3, 0.),
            (opening_shift + opening_half_width, -.3, 0.),
            (opening_shift + opening_half_width, .3, 0.),
            (opening_shift - opening_half_width, .3, 0.),
        ]
        vertices = outer + inner
        if mirrored:
            vertices = [(-x, y, z) for x, y, z in vertices]
        polygons = []
        for index in range(4):
            nxt = (index + 1) % 4
            if alternate:
                polygons.extend(((index, nxt, index + 4),
                                 (nxt, nxt + 4, index + 4)))
            else:
                polygons.extend(((index, nxt, nxt + 4),
                                 (index, nxt + 4, index + 4)))
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new("CBDK_Synthetic_Hole_Layout")
        mesh.from_pydata(vertices, [], polygons)
        mesh.update()
        obj = bpy.data.objects.new("CBDK_Synthetic_Hole_Layout", mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        return obj

    variants = (
        ("reference", {}),
        ("moved", {"opening_shift": .24}),
        ("wider", {"opening_half_width": .5}),
        ("retessellated", {"alternate": True}),
        ("symmetric", {"alternate": True, "mirrored": True}),
    )
    loaded = {}
    for label, kwargs in variants:
        make_faces(**kwargs)
        source = output / ("layout_" + label + ".glb")
        bpy.ops.export_scene.gltf(
            filepath=str(source), export_format="GLB", use_selection=True,
        )
        before = hashlib.sha256(source.read_bytes()).digest()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        assert hashlib.sha256(source.read_bytes()).digest() == before
        meshes = [obj for obj in bpy.context.scene.objects
                  if obj.type == "MESH"]
        assert len(meshes) == 1
        mesh = meshes[0]
        mesh.data.calc_loop_triangles()
        faces = [[tuple(float(x) for x in
                  (mesh.matrix_world @ mesh.data.vertices[idx].co))
                  for idx in tri.vertices]
                 for tri in mesh.data.loop_triangles]
        assert len(faces) == 8
        assert boundary_audit(faces, [8])["parts"][0]["boundary_edges"] == 8
        loaded[label] = faces

    reference = loaded["reference"]
    for label, expected, reasons in (
        ("reference", "suggested", []),
        ("moved", "ambiguous", ["boundary_spatial_layout_mismatch"]),
        ("wider", "ambiguous", ["boundary_spatial_layout_mismatch"]),
        ("retessellated", "suggested", []),
        ("symmetric", "suggested", []),
    ):
        start = perf_counter()
        report = suggest_spatial_part_matches(
            reference, loaded[label], [8], [8],
        )
        elapsed_ms = (perf_counter() - start) * 1000
        row = report["reference_parts"][0]
        assert row["status"] == expected, (label, row)
        assert row["topology_review_reasons"] == reasons, (label, row)
        assert row["normalized_score"] == 0., (label, row)
        assert report["cross_file_part_identity_proven"] is False
        assert report["auto_apply"] is False
        print(f"CBDK boundary-layout synthetic {label}: {expected} "
              f"({elapsed_ms:.3f} ms)")
    print("CBDK_GLB_BOUNDARY_LAYOUT_ROUNDTRIP_PASS")


def _boundary_component_roundtrip(output):
    """CBDK-only near-contact graph negative after real GLB reimport."""
    from time import perf_counter

    variants = (
        ("apart", False, False),
        ("touch", True, False),
        ("apart_reversed", False, True),
        ("touch_reversed", True, True),
    )
    loaded = {}
    for label, touch, reverse in variants:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        vertices = [
            (0., 0., 0.), (1., 0., 0.), (0., 1., 0.),
            (0., 0., 0.) if touch else (.0002, -.0002, 0.),
            (-1., 0., 0.), (0., -1., 0.),
        ]
        polygons = [(0, 1, 2), (3, 4, 5)]
        if reverse:
            polygons = [tuple(reversed(p)) for p in reversed(polygons)]
        mesh = bpy.data.meshes.new("CBDK_Synthetic_Graph")
        mesh.from_pydata(vertices, [], polygons)
        mesh.update()
        obj = bpy.data.objects.new("CBDK_Synthetic_Graph", mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        source = output / ("component_" + label + ".glb")
        bpy.ops.export_scene.gltf(
            filepath=str(source), export_format="GLB", use_selection=True,
        )
        before = hashlib.sha256(source.read_bytes()).digest()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        assert hashlib.sha256(source.read_bytes()).digest() == before
        imported = [item for item in bpy.context.scene.objects
                    if item.type == "MESH"]
        assert len(imported) == 1, "Synthetic component mesh regrouped"
        item = imported[0]
        item.data.calc_loop_triangles()
        faces = [[tuple(float(x) for x in
                  (item.matrix_world @ item.data.vertices[index].co))
                  for index in face.vertices]
                 for face in item.data.loop_triangles]
        assert len(faces) == 2, "Synthetic graph GLB lost triangles"
        assert boundary_audit(faces, [2])["parts"][0]["boundary_edges"] == 6
        loaded[label] = faces

    for left, right, expected, reasons in (
        ("apart", "touch", "ambiguous",
         ["boundary_component_count_mismatch"]),
        ("touch", "apart", "ambiguous",
         ["boundary_component_count_mismatch"]),
        ("apart", "apart_reversed", "suggested", []),
        ("touch", "touch_reversed", "suggested", []),
    ):
        start = perf_counter()
        report = suggest_spatial_part_matches(
            loaded[left], loaded[right], [2], [2],
        )
        elapsed_ms = (perf_counter() - start) * 1000
        row = report["reference_parts"][0]
        assert row["status"] == expected, (left, right, row)
        assert row["topology_review_reasons"] == reasons, (left, right, row)
        assert row["normalized_score"] == 0., (left, right, row)
        assert report["cross_file_part_identity_proven"] is False
        assert report["auto_apply"] is False
        print(f"CBDK graph synthetic {left}/{right}: {expected} "
              f"({elapsed_ms:.3f} ms)")
    print("CBDK_GLB_BOUNDARY_COMPONENT_ROUNDTRIP_PASS")


def _boundary_budget_roundtrip(output):
    """R4 self-authored GLB: exact 255/256/257 open-edge budget boundaries."""
    from time import perf_counter

    for target_edges in (255, 256, 257):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        vertices, polygons = [], []

        def add_tri(a, b, c):
            first = len(vertices)
            vertices.extend((a, b, c))
            polygons.append((first, first + 1, first + 2))

        for i in range(85 if target_edges == 255 else 84):
            x = 3. * i
            add_tri((x, 0., 0.), (x + 1., 0., 0.), (x, 1., 0.))
        if target_edges == 256:
            a, b, c, d = ((300., 0., 0.), (301., 0., 0.),
                          (300., 1., 0.), (301., 1., 0.))
            add_tri(a, b, c)
            add_tri(b, d, c)
        if target_edges == 257:
            a, b, c, d, e = ((300., 0., 0.), (301., 0., 0.),
                             (302., 1., 0.), (301., 2., 0.),
                             (300., 2., 0.))
            for face in ((a, b, c), (a, c, d), (a, d, e)):
                add_tri(*face)
        mesh = bpy.data.meshes.new("CBDK_R4_Edge_Budget")
        mesh.from_pydata(vertices, [], polygons)
        mesh.update()
        obj = bpy.data.objects.new("CBDK_R4_Edge_Budget", mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        source = output / ("r4_boundary_" + str(target_edges) + ".glb")
        bpy.ops.export_scene.gltf(
            filepath=str(source), export_format="GLB", use_selection=True,
        )
        before = hashlib.sha256(source.read_bytes()).digest()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        assert hashlib.sha256(source.read_bytes()).digest() == before
        meshes = [item for item in bpy.context.scene.objects if item.type == "MESH"]
        assert len(meshes) == 1, "R4 boundary fixture import split object"
        item = meshes[0]
        item.data.calc_loop_triangles()
        faces = [[tuple(float(x) for x in
                  (item.matrix_world @ item.data.vertices[i].co))
                  for i in tri.vertices]
                 for tri in item.data.loop_triangles]
        assert len(faces) == len(polygons), "R4 fixture count changed"
        audit = boundary_audit(faces, [len(faces)])
        assert audit["parts"][0]["boundary_edges"] == target_edges
        start = perf_counter()
        result = suggest_spatial_part_matches(
            faces, faces, [len(faces)], [len(faces)],
        )
        elapsed_ms = (perf_counter() - start) * 1000
        row = result["reference_parts"][0]
        expected = "ambiguous" if target_edges == 257 else "suggested"
        reason = ["boundary_layout_budget_exceeded"] if target_edges == 257 else []
        assert (row["status"], row["topology_review_reasons"]) == (expected, reason), row
        assert result["auto_apply"] is False
        assert result["cross_file_part_identity_proven"] is False
        print(f"CBDK R4 budget {target_edges}: {expected} ({elapsed_ms:.3f} ms)")

    print("CBDK_GLB_BOUNDARY_BUDGET_ROUNDTRIP_PASS")


def _boundary_many_parts_roundtrip(output):
    """64 actual GLB objects / 512 triangles, reversible anonymous inventory."""
    from time import perf_counter

    bpy.ops.wm.read_factory_settings(use_empty=True)
    outer = [(-1., -1., 0.), (1., -1., 0.),
             (1., 1., 0.), (-1., 1., 0.)]
    inner = [(-.3, -.3, 0.), (.3, -.3, 0.),
             (.3, .3, 0.), (-.3, .3, 0.)]
    for index in range(64):
        grid_x = (index % 4) * 12.
        grid_y = ((index // 4) % 4) * 12.
        grid_z = (index // 16) * 12.
        points = [
            (x + grid_x, y + grid_y, z + grid_z)
            for x, y, z in outer + inner
        ]
        triangles = []
        for i in range(4):
            j = (i + 1) % 4
            triangles.extend(((i, j, j + 4), (i, j + 4, i + 4)))
        mesh = bpy.data.meshes.new("CBDK_R4_Frame")
        mesh.from_pydata(points, [], triangles)
        mesh.update()
        obj = bpy.data.objects.new(f"CBDK_R4_{index:03d}", mesh)
        bpy.context.collection.objects.link(obj)

    source = output / "r4_parts_64_faces_512.glb"
    bpy.ops.export_scene.gltf(filepath=str(source), export_format="GLB")
    before = hashlib.sha256(source.read_bytes()).digest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    assert hashlib.sha256(source.read_bytes()).digest() == before
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    assert len(meshes) == 64, "R4 multipart GLB failed to preserve object count"
    groups = []
    for obj in meshes:
        obj.data.calc_loop_triangles()
        faces = [
            [tuple(float(x) for x in
             (obj.matrix_world @ obj.data.vertices[i].co))
             for i in tri.vertices]
            for tri in obj.data.loop_triangles
        ]
        assert len(faces) == 8, "R4 multipart GLB triangulation changed"
        groups.append(faces)
    assert sum(len(group) for group in groups) == 512
    reference = [face for group in groups for face in group]
    candidate = [face for group in reversed(groups) for face in group]
    start = perf_counter()
    result = suggest_spatial_part_matches(reference, candidate, [8] * 64, [8] * 64)
    elapsed_ms = (perf_counter() - start) * 1000
    assert [row["candidate_part_ids"] for row in result["reference_parts"]] == [
        [f"part_{64 - i:03d}"] for i in range(64)
    ], "R4 multipart reversed-order pairing changed"
    assert all(row["status"] == "suggested"
               and not row["topology_review_reasons"]
               for row in result["reference_parts"])
    assert result["auto_apply"] is False
    assert result["cross_file_part_identity_proven"] is False
    print(f"CBDK R4 multipart 64 parts / 512 faces: suggested ({elapsed_ms:.3f} ms)")
    print("CBDK_GLB_BOUNDARY_MULTIPART_ROUNDTRIP_PASS")



def _expanded_surface_roundtrip(output):
    """R20 synthetic GLBs through the real parent process, not just arrays."""
    from statistics import median
    from time import perf_counter
    import json

    def export(label, width, height, *, z=0., alternate=False, hole=False,
               extra=False, dense=False):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        vertices, faces = [], []
        def triangle(points):
            i = len(vertices)
            vertices.extend(points)
            faces.append((i, i + 1, i + 2))
        for y in range(height):
            for x in range(width):
                if hole and 4 <= x < 6 and 4 <= y < 6:
                    continue
                if dense:
                    points = ((0., 0., z), (1., 0., z), (0., 1., z))
                    if alternate:
                        points = ((1., 1., z), (1., 0., z), (0., 1., z))
                    triangle(points)
                    triangle(points)
                    continue
                a, b = (x, y, z), (x+1, y, z)
                c, d = (x+1, y+1, z), (x, y+1, z)
                if alternate:
                    triangle((a, b, d))
                    triangle((b, c, d))
                else:
                    triangle((a, b, c))
                    triangle((a, c, d))
        if extra:
            triangle(((100., 0., z), (101., 0., z), (100., 1., z)))
        mesh = bpy.data.meshes.new("CBDK_R20_Synthetic")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new("CBDK_R20_Synthetic", mesh)
        bpy.context.collection.objects.link(obj)
        source = output / ("r20_" + label + ".glb")
        bpy.ops.export_scene.gltf(filepath=str(source), export_format="GLB")
        return source

    def compare(label, a, b, *, profile="expanded_2048"):
        hashes = [hashlib.sha256(p.read_bytes()).digest() for p in (a, b)]
        start = perf_counter()
        result = run_glb_surface_review(
            bpy.app.binary_path, a, b, output / ("r20_" + label + ".json"),
            profile=profile)
        elapsed = (perf_counter() - start) * 1000
        assert [hashlib.sha256(p.read_bytes()).digest() for p in (a, b)] == hashes
        assert result["auto_apply"] is False
        return result, elapsed

    observations = {}
    for width, height in ((16, 16), (32, 16), (32, 32)):
        n = 2 * width * height
        ref = export(str(n) + "_base", width, height)
        cand = export(str(n) + "_raised", width, height, z=.25, alternate=True)
        samples = []
        for trial in range(4):  # first warmup, then three same-condition timings
            result, elapsed = compare(str(n) + "_offset_" + str(trial), ref, cand)
            assert result["status"] == "review_only", result
            assert result["reference_triangles"] == result["candidate_triangles"] == n
            assert abs(result["fixed_surface"]["symmetric_mean"] - .25) < 1e-6
            assert abs(result["adaptive_surface"]["refined_symmetric_mean"] - .25) < 1e-6
            if trial:
                samples.append(elapsed)
        observations[str(n)] = {
            "median_parent_roundtrip_ms": round(median(samples), 3),
            "work": result["work_budget"]["used"],
        }
        if n == 512:
            legacy, _ = compare("legacy_parity", ref, cand, profile="legacy_512")
            for group in ("fixed_surface", "adaptive_surface"):
                for direction in ("reference_to_candidate", "candidate_to_reference"):
                    assert result[group][direction] == legacy[group][direction]
        if n == 2048:
            same = export("retessellated", width, height, alternate=True)
            same_result, _ = compare("same", ref, same)
            assert same_result["status"] == "review_only", same_result
            assert same_result["fixed_surface"]["symmetric_sampled_max"] < 1e-6
            assert same_result["adaptive_surface"]["refined_symmetric_sampled_max"] < 1e-6
            cut = export("opening", width, height, hole=True)
            cut_result, _ = compare("cut", ref, cut)
            assert cut_result["status"] == "review_only", cut_result
            assert 0 < cut_result["fixed_surface"]["symmetric_sampled_max"] <= 1.000001
            assert 0 < cut_result["adaptive_surface"]["refined_symmetric_sampled_max"] <= 1.000001
            assert cut_result["fixed_surface"]["candidate_to_reference"]["sampled_max"] < 1e-6
            over = export("over_limit", width, height, extra=True)
            over_result, _ = compare("over", ref, over)
            assert over_result["status"] == "skipped"
            assert over_result["reason"] == "triangle_limit"
            assert over_result["candidate_triangles"] == 2049
            old_over, _ = compare("old_cap", ref, ref, profile="legacy_512")
            assert old_over["status"] == "skipped"
    # Positive point-to-triangle distance inside overlapping AABBs prevents
    # nearest pruning from concealing the deliberately expensive fixture.
    dense_ref = export("dense_ref", 32, 32, dense=True)
    dense_cand = export("dense_cand", 32, 32, dense=True, alternate=True)
    exhausted, elapsed = compare("dense", dense_ref, dense_cand)
    assert exhausted["status"] == "skipped", exhausted
    assert exhausted["reason"] == "work_budget"
    assert exhausted["surface_observation"] == "not_measured"
    assert "fixed_surface" not in exhausted and "adaptive_surface" not in exhausted
    observations["dense"] = {"work": exhausted["work_budget"]["used"],
                              "stopped_stage": exhausted["stopped_stage"],
                              "elapsed_ms": round(elapsed, 3)}
    print("CBDK_R20_EXPANDED_SURFACE_PASS " + json.dumps(observations, sort_keys=True))



def _expanded_part_review_roundtrip(output):
    """R21: native export/import, independent local shape difference, caps."""
    import json
    from statistics import median
    from time import perf_counter

    def export(label, groups, reverse_names=False):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for i, group in enumerate(groups):
            vertices, polygons = [], []
            for face in group:
                pos = len(vertices)
                vertices.extend(face)
                polygons.append((pos,pos+1,pos+2))
            mesh = bpy.data.meshes.new("CBDK_R21_Synthetic")
            mesh.from_pydata(vertices, [], polygons)
            mesh.update()
            idx = len(groups)-i if reverse_names else i
            obj = bpy.data.objects.new(f"CBDK_R21_{idx:03d}", mesh)
            bpy.context.collection.objects.link(obj)
        path = output / ("r21_" + label + ".glb")
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB")
        return path

    def compare(label, left, right, profile="expanded_2048_parts"):
        hashes = [hashlib.sha256(p.read_bytes()).digest() for p in (left,right)]
        start = perf_counter()
        report = run_glb_surface_review(bpy.app.binary_path,left,right,
            output / ("r21_" + label + ".json"),profile=profile)
        ms = (perf_counter()-start)*1000
        assert hashes == [hashlib.sha256(p.read_bytes()).digest() for p in (left,right)]
        return report,ms

    def tetra(inverted):
        v = [(0.,0.,0.),(1.,1.,0.),(1.,0.,1.),(0.,1.,1.)]
        if inverted:
            v = [tuple(1-x for x in p) for p in v]
        return [tuple(v[i] for i in f) for f in ((0,1,2),(0,3,1),(0,2,3),(1,3,2))]

    closed_a = export("closed_a",[tetra(False)])
    closed_b = export("closed_b",[tetra(True)])
    report,_ = compare("closed_diff",closed_a,closed_b)
    row = report["part_review"]["reference_parts"][0]
    assert row["spatial_status"] == "suggested",row
    assert row["status"] == "ambiguous",row
    assert row["observations"][0]["surface_difference_observed"] is True
    tied = export("tied",[tetra(False),tetra(False)])
    report,_ = compare("tie",closed_a,tied)
    assert report["part_review"]["reference_parts"][0]["status"] == "ambiguous"

    def panel(i, alternate=False):
        ox,oy = (i%8)*10.,(i//8)*10.
        result = []
        for y in range(4):
            for x in range(4):
                a,b=(ox+x,oy+y,0.),(ox+x+1,oy+y,0.)
                c,d=(ox+x+1,oy+y+1,0.),(ox+x,oy+y+1,0.)
                result.extend(((a,b,d),(b,c,d)) if alternate else ((a,b,c),(a,c,d)))
        return result

    groups = [panel(i) for i in range(64)]
    left = export("large_a",groups)
    right = export("large_b",[panel(i,True) for i in range(64)],reverse_names=True)
    times = []
    for trial in range(4):
        report,ms = compare("large_"+str(trial),left,right)
        assert report["status"] == "review_only",report
        assert report["reference_triangles"] == report["candidate_triangles"] == 2048
        part = report["part_review"]
        assert part["status"] == "review_only",part
        assert part["reference_triangle_counts"] == part["candidate_triangle_counts"] == [32]*64
        assert len(part["reference_parts"]) == 64
        assert all(r["status"] == "suggested" for r in part["reference_parts"]),part
        assert [r["candidate_part_ids"] for r in part["reference_parts"]] == [
            [f"part_{64-i:03d}"] for i in range(64)]
        assert all(not o["surface_difference_observed"] for r in part["reference_parts"] for o in r["observations"])
        if trial:
            times.append(ms)
    stats = {"median_parent_ms":round(median(times),3),
             "part_work":part["work_budget"]["used"],
             "global_work":report["work_budget"]["used"],
             "pairs":part["pair_attempts"],"bvh_builds":part["bvh_build_count"],
             "boundary_reserved":part["boundary_comparison_reservation"],
             "suggested":sum(r["status"]=="suggested" for r in part["reference_parts"]),
             "closed_old_false_suggestion":1,"closed_remaining_false_suggestion":0,
             "tie_ambiguous":1}
    too_many = export("65",[[group[0]] for group in groups]+[[groups[0][1]]])
    report,_ = compare("part_cap",too_many,too_many)
    assert report["status"] == "review_only"
    assert report["part_review"]["reason"] == "part_limit"
    over = export("2049",groups+[[groups[0][0]]])
    report,_ = compare("face_cap",left,over)
    assert report["status"] == "skipped"
    assert report["part_review"]["reason"] == "global_surface_not_measured"
    dense_a = output / "r20_dense_ref.glb"
    dense_b = output / "r20_dense_cand.glb"
    dense, _ = compare("global_budget",dense_a,dense_b)
    assert dense["status"] == "skipped" and dense["reason"] == "work_budget"
    assert dense["part_review"]["reason"] == "global_surface_not_measured"
    print("CBDK_R21_PART_REVIEW_PASS " + json.dumps(stats,sort_keys=True))


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 1:
        raise ValueError("Expected one fresh reports/ci output directory")
    output = Path(args[0]).resolve()
    if not output.is_relative_to(ROOT / "reports" / "ci"):
        raise ValueError("Synthetic evidence must stay in reports/ci")
    output.mkdir(parents=True, exist_ok=False)
    cases = (
        ("unique", [1, 2], "review_only", [1, 2]),
        ("ambiguous", [1, 1], "review_only", []),
        ("truncated", [1] * 33, "review_only", []),
        ("over_limit_truncated", [17] * 33, "skipped", []),
    )
    for label, counts, status, candidates in cases:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for index, count in enumerate(counts):
            vertices, faces = [], []
            for face in range(count):
                start = len(vertices)
                x, y = 3.0 * face, 3.0 * index
                vertices.extend(((x, y, 0), (x + 1, y, 0), (x, y + 1, 0)))
                faces.append((start, start + 1, start + 2))
            mesh = bpy.data.meshes.new("CBDK_Owned_Inventory")
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            obj = bpy.data.objects.new(f"CBDK_Test_{index:03d}", mesh)
            bpy.context.collection.objects.link(obj)
        source = output / (label + ".glb")
        bpy.ops.export_scene.gltf(filepath=str(source), export_format="GLB")
        before = hashlib.sha256(source.read_bytes()).digest()
        result = run_glb_surface_review(
            bpy.app.binary_path, source, source, output / (label + ".json"))
        assert hashlib.sha256(source.read_bytes()).digest() == before
        assert result["status"] == status
        for side in ("reference", "candidate"):
            assert result[side + "_triangles"] == sum(counts)
            assert result["part_inventory"][side + "_object_count"] == len(counts)
            assert result["part_inventory"][side + "_triangle_counts"] == sorted(
                counts, reverse=True)[:32]
        hints = result["part_count_hints"]
        assert hints["weak_candidate_triangle_counts"] == candidates
        assert hints["complete_inventories"] is (len(counts) <= 32)
        assert hints["correspondence_verified"] is False
        assert hints["auto_apply"] is False
        if status == "review_only":
            assert result["surface_observation"] == "no_difference_observed_at_samples"
        else:
            assert result["surface_observation"] == "not_measured"
            assert "fixed_surface" not in result
        print("CBDK inventory synthetic case passed: " + label)
    _topology_count_roundtrip(output)
    _boundary_layout_roundtrip(output)
    _boundary_component_roundtrip(output)
    _boundary_budget_roundtrip(output)
    _boundary_many_parts_roundtrip(output)
    _expanded_surface_roundtrip(output)
    _expanded_part_review_roundtrip(output)
    print("CBDK_SURFACE_INVENTORY_PASS")


if __name__ == "__main__":
    main()
