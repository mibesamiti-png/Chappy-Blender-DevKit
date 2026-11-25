"""R20 joint refinement retrospective evaluation of all 12 R18 R17-arm assembled meshes."""
import argparse,hashlib,json,time
from pathlib import Path
from cycles.r17.fixtures import cases
from cycles.r14.audit import controls
from cycles.r20.refine import refine

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    path=Path(a.input); raw=json.loads(path.read_text())
    if raw["cycle"]!="R18" or raw["approved"] or not raw["synthetic_only"] or raw["blender"]!="4.4.3" or len(raw["rows"])!=24: raise ValueError("invalid R18 provenance")
    if len({(r["case"],r["arm"]) for r in raw["rows"]})!=24: raise ValueError("duplicate rows")
    controls(); by={r["name"]:r for r in cases()}; rows=[]
    for row in raw["rows"]:
        if row["arm"]!="candidate": continue
        try:
            if row["status"]!="generated": raise ValueError("missing source output")
            start=time.perf_counter(); result=refine(row,by[row["case"]]); result.update(seconds=time.perf_counter()-start,case=row["case"])
        except Exception as exc: result=dict(case=row["case"],passed=False,error=type(exc).__name__+": "+str(exc))
        rows.append(result)
        print("R20_ROW",json.dumps({k:v for k,v in result.items() if k not in ("vertices","triangles","corner_uv","face_ids","materials","seam_flags")}),flush=True)
    improved=sum(r.get("p95_gain",0)>=.05 for r in rows)
    gate=len(rows)==12 and all(r["passed"] for r in rows) and improved>=6
    out=dict(cycle="R20",approved=False,retrospective=True,detached_only=True,synthetic_only=True,gate=gate,improved_at_least_5pct=improved,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ("cycles/r20/refine.py","cycles/r20/run.py")},rows=rows)
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x") as f: json.dump(out,f,indent=2,allow_nan=False)
    print("R20_SUMMARY",json.dumps(dict(gate=gate,passed=sum(r["passed"] for r in rows),total=len(rows),improved=improved,source_sha256=out["source_sha256"])),flush=True)
    if not gate: raise SystemExit("R20 scoped gate not met; preserve results")
