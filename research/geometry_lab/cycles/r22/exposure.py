"""R22 revision 2: independent clipping/foreground proxy; not aesthetic scoring."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dir",required=True);a=p.parse_args();d=Path(a.dir)
    m=json.loads((d/"manifest.json").read_text()); e=json.loads((d/"evaluation.json").read_text())
    if m.get("render_revision")!=2 or not e["render_integrity_gate"]:raise ValueError("missing revision 2 evidence")
    rows=[]
    for r in m["renders"]:
        if r["mode"] not in ("flat","smooth"):continue
        im=np.array(Image.open(d/r["file"]).convert("RGB"))
        fg=im.max(2)>100
        n=int(fg.sum())
        ratio=float((im[fg]>=250).all(1).mean()) if n else 1.
        rows.append(dict(case=r["case"],mode=r["mode"],arm=r["arm"],azimuth=r["azimuth"],bright_foreground_pixels=n,near_white_fraction=ratio))
    # Approximate visible foreground mask, identical to retrospective revision 1 audit.
    # Threshold checks reduce clipping, but do not measure shading or aesthetic merit.
    gate=len(rows)==64 and all(r["bright_foreground_pixels"]>=256 and r["near_white_fraction"]<=.10 for r in rows)
    q=dict(cycle="R22",render_revision=2,approved=False,exposure_proxy_gate=gate,count=len(rows),near_white_max=max(r["near_white_fraction"] for r in rows),near_white_median=float(np.median([r["near_white_fraction"] for r in rows])),visual_quality_assessed=False,rows=rows)
    (d/"exposure.json").write_text(json.dumps(q,indent=2))
    print("R22_EXPOSURE",json.dumps({k:v for k,v in q.items() if k!="rows"}),flush=True)
    if not gate:raise SystemExit("R22 exposure proxy not met")
