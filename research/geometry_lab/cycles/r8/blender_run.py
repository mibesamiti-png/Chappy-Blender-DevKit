"""R8 official Blender same-input comparison: tapered R8, frozen R7, native3."""
import argparse
import hashlib
import json
import sys
import time
import types
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from cbdk_geometry.tapered_loft import tapered_radial_loft
from cbdk_geometry.warped_loft import warped_radial_loft

# Blender has a built-in cycles module, so route only research fixtures here.
saved=sys.modules.get("cycles")
pkg=types.ModuleType("cycles")
pkg.__path__=[str(ROOT/"cycles")]
sys.modules["cycles"]=pkg
try:
    from cycles.r8.fixtures import cases
    from cycles.r6.blender_run import native_bridge
finally:
    sys.modules.pop("cycles",None)
    if saved is not None:
        sys.modules["cycles"]=saved

METHODS=("tapered_r8","warped_r7","native_3_linear")


def generate(a,b,method):
    if method=="tapered_r8":
        m=tapered_radial_loft(a,b)["mesh"]
        return {"vertices":m.vertices.tolist(),"faces":m.faces.tolist()}
    if method=="warped_r7":
        m=warped_radial_loft(a,b)["mesh"]
        return {"vertices":m.vertices.tolist(),"faces":m.faces.tolist()}
    if method=="native_3_linear":
        return native_bridge(a,b,3,"LINEAR")
    raise ValueError("unknown method")


def run():
    before=(set(bpy.data.objects),set(bpy.data.meshes),set(bpy.context.selected_objects),
            bpy.context.view_layer.objects.active,tuple(bpy.context.tool_settings.mesh_select_mode))
    rows=[]
    for case in cases():
        a=case["a"].astype(np.float32).astype(float)
        b=case["b"].astype(np.float32).astype(float)
        for method in METHODS:
            row=dict(name=case["name"],split=case["split"],method=method,
                     generation_status="not_run")
            try:
                generate(a,b,method) # one warmup per method/case
                outputs=[]
                times=[]
                for _ in range(3):
                    start=time.perf_counter()
                    result=generate(a,b,method)
                    times.append(time.perf_counter()-start)
                    outputs.append(result)
                if any(x!=outputs[0] for x in outputs[1:]):
                    raise RuntimeError("nondeterministic geometry")
                if any(duration>10 for duration in times):
                    raise TimeoutError("R8 10-second per-generation budget exceeded")
                if len(outputs[0]["vertices"])>60000 or len(outputs[0]["faces"])>20000:
                    raise RuntimeError("R8 mesh budget exceeded")
                row.update(generation_status="generated",**outputs[0],
                           median_seconds=median(times),samples_seconds=times)
            except Exception as exc:
                row.update(generation_status="generation_error",
                           reason=type(exc).__name__+": "+str(exc))
            rows.append(row)
            print("R8_GENERATE",json.dumps({k:v for k,v in row.items()
                  if k in ("name","split","method","generation_status","reason")}),flush=True)
    after=(set(bpy.data.objects),set(bpy.data.meshes),set(bpy.context.selected_objects),
           bpy.context.view_layer.objects.active,tuple(bpy.context.tool_settings.mesh_select_mode))
    if before!=after:
        raise RuntimeError("Blender temporary objects were not completely removed")
    filenames=("cbdk_geometry/tapered_loft.py","cbdk_geometry/warped_loft.py",
               "cycles/r8/fixtures.py","cycles/r8/blender_run.py")
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in filenames}
    return dict(cycle="R8",blender=bpy.app.version_string,
                build_hash=bpy.app.build_hash.decode(),numpy=np.__version__,
                synthetic_only=True,scene_preserved=True,source_sha256=hashes,
                methods=list(METHODS),cases=rows,approved=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    arg=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    result=run()
    dest=Path(arg.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x") as f:json.dump(result,f,indent=2)
    print("R8_RAW",len(result["cases"]),result["blender"],flush=True)
