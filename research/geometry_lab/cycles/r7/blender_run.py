"""R7: Blender 4.4.3 independent synthetic nonplanar boundary comparison."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from statistics import median
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import bpy
import numpy as np
from cbdk_geometry.warped_loft import warped_radial_loft

# Blender's own 'cycles' module collides with Geometry Lab's cycles directory.
saved = sys.modules.get("cycles")
pkg = types.ModuleType("cycles")
pkg.__path__ = [str(ROOT / "cycles")]
sys.modules["cycles"] = pkg
try:
    from cycles.r7.fixtures import cases
    from cycles.r6.blender_run import native_bridge
finally:
    sys.modules.pop("cycles", None)
    if saved is not None:
        sys.modules["cycles"] = saved

METHODS = ("warped_r7", "native_3_linear", "native_0_path")


def generate(a, b, method):
    if method == "warped_r7":
        mesh = warped_radial_loft(a, b)["mesh"]
        return {"vertices": mesh.vertices.tolist(), "faces": mesh.faces.tolist()}
    if method == "native_3_linear":
        return native_bridge(a, b, 3, "LINEAR")
    if method == "native_0_path":
        return native_bridge(a, b, 0, "PATH")
    raise ValueError("invalid R7 method")


def run():
    scene = (set(bpy.data.objects), set(bpy.data.meshes),
             set(bpy.context.selected_objects), bpy.context.view_layer.objects.active,
             tuple(bpy.context.tool_settings.mesh_select_mode))
    rows = []
    for case in cases():
        a = case["a"].astype(np.float32).astype(float)
        b = case["b"].astype(np.float32).astype(float)
        for method in METHODS:
            row = dict(name=case["name"], split=case["split"], method=method,
                       generation_status="not_run")
            try:
                generate(a, b, method)  # warmup
                outputs = []
                durations = []
                for _ in range(3):
                    start = time.perf_counter()
                    result = generate(a, b, method)
                    durations.append(time.perf_counter() - start)
                    outputs.append(result)
                if any(x != outputs[0] for x in outputs[1:]):
                    raise RuntimeError("non-deterministic output")
                if any(x > 10. for x in durations):
                    raise TimeoutError("10-second generation budget exceeded")
                if len(outputs[0]["vertices"]) > 60000 or len(outputs[0]["faces"]) > 20000:
                    raise RuntimeError("mesh budget exceeded")
                row.update(generation_status="generated", **outputs[0],
                           samples_seconds=durations, median_seconds=median(durations))
            except Exception as exc:
                row.update(generation_status="generation_error",
                           reason=type(exc).__name__ + ": " + str(exc))
            rows.append(row)
            print("R7_GENERATE", json.dumps({
                k: v for k, v in row.items()
                if k in ("name", "split", "method", "generation_status", "reason")
            }), flush=True)
    after = (set(bpy.data.objects), set(bpy.data.meshes),
             set(bpy.context.selected_objects), bpy.context.view_layer.objects.active,
             tuple(bpy.context.tool_settings.mesh_select_mode))
    if scene != after:
        raise RuntimeError("temporary Blender scene cleanup failed")
    source = {}
    for p in ("cbdk_geometry/warped_loft.py", "cycles/r7/fixtures.py",
              "cycles/r7/blender_run.py", "cycles/r6/blender_run.py"):
        source[p] = hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    return dict(cycle="R7", synthetic_only=True, scene_preserved=True,
                blender=bpy.app.version_string, build_hash=bpy.app.build_hash.decode(),
                numpy=np.__version__, source_sha256=source, methods=list(METHODS),
                cases=rows, approved=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    opts = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    data = run()
    path = Path(opts.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as target:
        json.dump(data, target, indent=2)
    print("R7_RAW", len(data["cases"]), data["blender"], flush=True)
