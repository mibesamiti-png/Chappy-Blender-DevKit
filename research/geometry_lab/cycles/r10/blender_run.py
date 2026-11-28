"""R10 official Blender 4.4.3 benchmark of conditional vs always/never repairs."""
import argparse
import hashlib
import json
import sys
import time
import types
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import bpy
import numpy as np
from cbdk_geometry.quality_router import conditional_flip_loft
from cbdk_geometry.flip_loft import conservative_flip_loft
from cbdk_geometry.tapered_loft import tapered_radial_loft

# Blender's own 'cycles' module clashes with the research cycles package.
saved = sys.modules.get("cycles")
lab = types.ModuleType("cycles")
lab.__path__ = [str(ROOT / "cycles")]
sys.modules["cycles"] = lab
try:
    from cycles.r10.fixtures import cases
    from cycles.r6.blender_run import native_bridge
finally:
    sys.modules.pop("cycles", None)
    if saved is not None:
        sys.modules["cycles"] = saved

METHODS = ("conditional_r10", "tapered_r8", "flipped_r9", "native_3_linear")


def generate(a, b, method):
    if method == "conditional_r10":
        obj = conditional_flip_loft(a, b)
        return dict(vertices=obj["mesh"].vertices.tolist(),
                    faces=obj["mesh"].faces.tolist(),
                    path=obj["path"], flips=obj["flips"], passes=obj["passes"],
                    initial_min_quality=obj["initial_min_quality"],
                    final_min_quality=obj["final_min_quality"])
    if method == "tapered_r8":
        mesh = tapered_radial_loft(a, b)["mesh"]
        return dict(vertices=mesh.vertices.tolist(), faces=mesh.faces.tolist())
    if method == "flipped_r9":
        mesh = conservative_flip_loft(a, b)["mesh"]
        return dict(vertices=mesh.vertices.tolist(), faces=mesh.faces.tolist())
    if method == "native_3_linear":
        return native_bridge(a, b, 3, "LINEAR")
    raise ValueError("unsupported R10 method")


def run():
    before = (set(bpy.data.objects), set(bpy.data.meshes),
              set(bpy.context.selected_objects), bpy.context.view_layer.objects.active,
              tuple(bpy.context.tool_settings.mesh_select_mode))
    records = []
    for case in cases():
        a = case["a"].astype(np.float32).astype(float)
        b = case["b"].astype(np.float32).astype(float)
        for method in METHODS:
            record = dict(name=case["name"], split=case["split"],
                          method=method, generation_status="not_run")
            try:
                generate(a, b, method)  # warm-up
                measurements = []
                outputs = []
                for repeat in range(3):
                    started = time.perf_counter()
                    mesh = generate(a, b, method)
                    measurements.append(time.perf_counter() - started)
                    outputs.append(mesh)
                if any(item != outputs[0] for item in outputs[1:]):
                    raise RuntimeError("non-deterministic XYZ/indices/dispatch")
                if max(measurements) > 10:
                    raise TimeoutError("generation exceeded 10-second budget")
                if len(outputs[0]["vertices"]) > 60000 or len(outputs[0]["faces"]) > 20000:
                    raise RuntimeError("generated mesh exceeds research budget")
                record.update(generation_status="generated", **outputs[0],
                              samples_seconds=measurements,
                              median_seconds=median(measurements))
            except Exception as error:
                record.update(generation_status="generation_error",
                              reason=type(error).__name__ + ": " + str(error))
            records.append(record)
            print("R10_GENERATE", json.dumps({
                k: v for k, v in record.items()
                if k in ("name", "split", "method", "generation_status", "reason", "path")
            }), flush=True)
    after = (set(bpy.data.objects), set(bpy.data.meshes),
             set(bpy.context.selected_objects), bpy.context.view_layer.objects.active,
             tuple(bpy.context.tool_settings.mesh_select_mode))
    if before != after:
        raise RuntimeError("temporary Blender scene state was not fully restored")
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "cbdk_geometry/quality_router.py", "cbdk_geometry/tapered_loft.py",
        "cbdk_geometry/flip_loft.py", "cycles/r10/fixtures.py",
        "cycles/r10/blender_run.py")}
    return dict(cycle="R10", blender=bpy.app.version_string,
                build_hash=bpy.app.build_hash.decode(), synthetic_only=True,
                scene_preserved=True, source_sha256=hashes,
                method_order=list(METHODS), cases=records, approved=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    opts = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    data = run()
    dest = Path(opts.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x") as file:
        json.dump(data, file, indent=2)
    print("R10_RAW", len(data["cases"]), data["blender"], flush=True)
