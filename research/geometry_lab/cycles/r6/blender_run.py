"""R6: generate R5 and Blender standard bridge variants on identical rings.

Run only with official Blender 4.4.3 background factory-startup. Outputs raw
synthetic meshes to an ignored run file for external CGAL validation.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import bpy
import bmesh
import numpy as np
from cbdk_geometry.radial_loft import radial_loft

# Blender ships its own 'cycles' module; temporarily load the Geometry Lab
# namespace package only to import the synthetic fixture modules.
saved_cycles = sys.modules.pop("cycles", None)
try:
    from cycles.r6.fixtures import cases
finally:
    sys.modules.pop("cycles", None)
    if saved_cycles is not None:
        sys.modules["cycles"] = saved_cycles

METHODS = ("r5_radial", "native_0_path", "native_3_linear",
           "native_3_path", "native_3_surface")
NATIVE_OPTIONS = {
    "native_0_path": (0, "PATH"),
    "native_3_linear": (3, "LINEAR"),
    "native_3_path": (3, "PATH"),
    "native_3_surface": (3, "SURFACE"),
}


def native_bridge(a, b, cuts, interpolation):
    """Create and remove one temporary object, leaving the user's scene intact."""
    original_selection = tuple(bpy.context.selected_objects)
    original_active = bpy.context.view_layer.objects.active
    original_mode = tuple(bpy.context.tool_settings.mesh_select_mode)
    data = None
    obj = None
    try:
        data = bpy.data.meshes.new("GEOMETRY_R6_TEMP")
        vertices = [tuple(map(float, v)) for v in np.vstack((a, b))]
        n, m = len(a), len(b)
        edges = ([(i, (i + 1) % n) for i in range(n)]
                 + [(n + i, n + (i + 1) % m) for i in range(m)])
        data.from_pydata(vertices, edges, [])
        data.update()
        obj = bpy.data.objects.new("GEOMETRY_R6_TEMP", data)
        bpy.context.scene.collection.objects.link(obj)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.tool_settings.mesh_select_mode = (False, True, False)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        retval = bpy.ops.mesh.bridge_edge_loops(
            type="SINGLE", use_merge=False, twist_offset=0, number_cuts=cuts,
            interpolation=interpolation, smoothness=1.0,
            profile_shape_factor=0.0, profile_shape="SMOOTH")
        if "FINISHED" not in retval:
            raise RuntimeError("bridge_edge_loops returned " + str(retval))
        bpy.ops.object.mode_set(mode="OBJECT")
        bm = bmesh.new()
        try:
            bm.from_mesh(data)
            if not bm.faces:
                raise RuntimeError("native generated no faces")
            bmesh.ops.triangulate(bm, faces=list(bm.faces),
                                  quad_method="BEAUTY", ngon_method="BEAUTY")
            bm.verts.index_update()
            result = {
                "vertices": [list(v.co) for v in bm.verts],
                "faces": [[int(v.index) for v in face.verts] for face in bm.faces],
            }
            return result
        finally:
            bm.free()
    finally:
        if obj is not None:
            if obj.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
        bpy.context.tool_settings.mesh_select_mode = original_mode
        bpy.ops.object.select_all(action="DESELECT")
        for selected in original_selection:
            if selected.name in bpy.data.objects:
                selected.select_set(True)
        bpy.context.view_layer.objects.active = original_active


def generate(a, b, method):
    if method == "r5_radial":
        mesh = radial_loft(a, b)["mesh"]
        return {"vertices": mesh.vertices.tolist(), "faces": mesh.faces.tolist()}
    cuts, interpolation = NATIVE_OPTIONS[method]
    return native_bridge(a, b, cuts, interpolation)


def run():
    before = (set(bpy.data.objects), set(bpy.data.meshes),
              set(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
    rows = []
    for case in cases():
        a = case["a"].astype(np.float32).astype(float)
        b = case["b"].astype(np.float32).astype(float)
        for method in METHODS:
            row = {"name": case["name"], "split": case["split"],
                   "origin": case["origin"], "method": method,
                   "generation_status": "not_run"}
            try:
                # Ignore the first run as an explicit warmup, keeping same budget.
                generate(a, b, method)
                outputs = []
                durations = []
                for repeat in range(3):
                    start = time.perf_counter()
                    output = generate(a, b, method)
                    durations.append(time.perf_counter() - start)
                    outputs.append(output)
                if any(x["vertices"] != outputs[0]["vertices"]
                       or x["faces"] != outputs[0]["faces"] for x in outputs[1:]):
                    raise RuntimeError("nondeterministic coordinates or face order")
                if not all(len(x["faces"]) <= 20000
                           and len(x["vertices"]) <= 60000 for x in outputs):
                    raise RuntimeError("mesh budget exceeded")
                if any(t > 10.0 for t in durations):
                    raise TimeoutError("generation exceeded 10-second budget")
                row.update(generation_status="generated", **outputs[0],
                           median_seconds=median(durations), samples_seconds=durations)
            except Exception as error:
                row.update(generation_status="generation_error",
                           reason=type(error).__name__ + ": " + str(error))
            rows.append(row)
            print("R6_GENERATE", json.dumps(
                {k: v for k, v in row.items()
                 if k in ("name", "split", "method", "generation_status", "reason", "median_seconds")},
                ensure_ascii=False), flush=True)
    after = (set(bpy.data.objects), set(bpy.data.meshes),
             set(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
    if before != after:
        raise RuntimeError("Blender scene/data/selection was not restored")
    sha = {}
    for filename in ("cycles/r6/fixtures.py", "cycles/r6/blender_run.py",
                     "cbdk_geometry/radial_loft.py", "cycles/r5/fixtures.py"):
        sha[filename] = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
    return {"cycle": "R6", "synthetic_only": True,
            "blender": bpy.app.version_string, "build_hash": bpy.app.build_hash.decode(),
            "numpy_blender": np.__version__, "scene_preserved": True,
            "method_order": list(METHODS),
            "run_note": "native includes bpy context setup and triangulation; R5 pure Python is not comparable as equivalent UI work",
            "source_sha256": sha, "cases": rows, "approved": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    options = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    out = run()
    path = Path(options.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(out, handle, indent=2, ensure_ascii=False)
    print("R6 RAW", len(out["cases"]), "cases, Blender", out["blender"], flush=True)
