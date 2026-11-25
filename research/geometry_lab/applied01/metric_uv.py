"""Metric chart scaling of the frozen panel grids; no XYZ/face edits."""
import argparse,json
from pathlib import Path
import numpy as np
from applied01.generate import generate

def metric(p):
    nu,nv=p["nu"],p["nv"];g=np.asarray(p["vertices"],float).reshape(nv+1,nu+1,3)
    x=np.r_[0,np.cumsum(np.linalg.norm(np.diff(g,axis=1),axis=2).mean(0))]
    y=np.r_[0,np.cumsum(np.linalg.norm(np.diff(g,axis=0),axis=2).mean(1))]
    scale=max(x[-1],y[-1])
    if not np.isfinite(scale) or scale<=0 or np.any(np.diff(x)<=0) or np.any(np.diff(y)<=0):raise ValueError("degenerate grid metric")
    return {**p,"uv":[[float(xx/scale),float(yy/scale)] for yy in y for xx in x]}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps({"baseline":[metric(p) for p in generate()],"changed":[metric(p) for p in generate(.075)]},indent=2))
