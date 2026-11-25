"""Reuse frozen R18 execute on new R21 geometry and selected strip."""
import argparse,json,sys,types,hashlib
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
saved=sys.modules.get("cycles"); pkg=types.ModuleType("cycles"); pkg.__path__=[str(ROOT/"cycles")]; sys.modules["cycles"]=pkg
try:
    from cycles.r18.blender_run import execute
    from cycles.r21.fixtures import cases
finally:
    sys.modules.pop("cycles",None)
    if saved is not None: sys.modules["cycles"]=saved

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    path=Path(a.input); raw=json.loads(path.read_text())
    if raw["cycle"]!="R21" or raw["approved"] or len(raw["rows"])!=8: raise ValueError("unexpected input")
    by={c["name"]:c for c in cases()}; rows=[]
    for r in raw["rows"]:
        try:
            if r["status"]!="prepared": raise ValueError(r.get("error","missing input"))
            out=execute(r,by[r["case"]],"candidate")
        except Exception as e: out=dict(case=r["case"],status="error",reason=type(e).__name__+": "+str(e))
        rows.append(out); print("R21_BLENDER",raw["stage"],out["case"],out["status"],out.get("reason",""),flush=True)
    with Path(a.output).open("x") as f: json.dump(dict(cycle="R21",stage=raw["stage"],approved=False,blender=bpy.app.version_string,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=rows),f,allow_nan=False)
