"""R9 official Blender benchmark: conservative face-only flips vs frozen R8/native."""
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
from cbdk_geometry.flip_loft import conservative_flip_loft
from cbdk_geometry.tapered_loft import tapered_radial_loft

saved=sys.modules.get("cycles")
pkg=types.ModuleType("cycles")
pkg.__path__=[str(ROOT/"cycles")]
sys.modules["cycles"]=pkg
try:
    from cycles.r9.fixtures import cases
    from cycles.r6.blender_run import native_bridge
finally:
    sys.modules.pop("cycles",None)
    if saved is not None:
        sys.modules["cycles"]=saved

METHODS=("flipped_r9","tapered_r8","native_3_linear")


def generate(a,b,method):
    if method=="flipped_r9":
        m=conservative_flip_loft(a,b)["mesh"]
        return dict(vertices=m.vertices.tolist(),faces=m.faces.tolist())
    if method=="tapered_r8":
        m=tapered_radial_loft(a,b)["mesh"]
        return dict(vertices=m.vertices.tolist(),faces=m.faces.tolist())
    if method=="native_3_linear":
        return native_bridge(a,b,3,"LINEAR")
    raise ValueError("unknown R9 method")


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
                generate(a,b,method)
                outputs=[]
                timings=[]
                for _ in range(3):
                    begin=time.perf_counter()
                    out=generate(a,b,method)
                    timings.append(time.perf_counter()-begin)
                    outputs.append(out)
                if any(x!=outputs[0] for x in outputs[1:]):
                    raise RuntimeError("R9 non-deterministic generated geometry")
                if max(timings)>10:
                    raise TimeoutError("R9 generation exceeded 10-second budget")
                if len(outputs[0]["vertices"])>60000 or len(outputs[0]["faces"])>20000:
                    raise RuntimeError("R9 mesh budget exceeded")
                row.update(generation_status="generated",**outputs[0],
                           samples_seconds=timings,median_seconds=median(timings))
            except Exception as exc:
                row.update(generation_status="generation_error",
                           reason=type(exc).__name__+": "+str(exc))
            rows.append(row)
            print("R9_GENERATE",json.dumps({k:v for k,v in row.items()
                if k in ("name","split","method","generation_status","reason")}),flush=True)
    after=(set(bpy.data.objects),set(bpy.data.meshes),set(bpy.context.selected_objects),
           bpy.context.view_layer.objects.active,tuple(bpy.context.tool_settings.mesh_select_mode))
    if before!=after:
        raise RuntimeError("R9 temporary Blender scene cleanup mismatch")
    sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
             for p in ("cbdk_geometry/flip_loft.py","cbdk_geometry/tapered_loft.py",
                       "cycles/r9/fixtures.py","cycles/r9/blender_run.py")}
    return dict(cycle="R9",synthetic_only=True,scene_preserved=True,
                blender=bpy.app.version_string,build_hash=bpy.app.build_hash.decode(),
                numpy=np.__version__,methods=list(METHODS),
                source_sha256=sources,cases=rows,approved=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    opts=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    data=run()
    dest=Path(opts.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x") as handle:
        json.dump(data,handle,indent=2)
    print("R9_RAW",len(data["cases"]),data["blender"],flush=True)
