"""Independent render existence/integrity/negative-control checks, not aesthetic scoring."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--dir",required=True); a=p.parse_args(); d=Path(a.dir)
    m=json.loads((d/"manifest.json").read_text()); size=m["size"]; seen={}; results=[]
    for r in m["renders"]:
        path=d/r["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=r["sha256"]: raise ValueError("image hash")
        with Image.open(path) as im: arr=np.array(im.convert("RGB"))
        if arr.shape!=(size,size,3) or arr.std()<3: raise ValueError("empty or invalid image")
        key=(r["case"],r["mode"],r["azimuth"],r["arm"])
        if key in seen: raise ValueError("duplicate")
        seen[key]=arr
    modes=("checker","flat","smooth"); cases=m["cases"]
    expected={(r["case"],mode,az,arm) for r in cases for mode in modes for az in (0,180) for arm in ("baseline","selected")}
    if set(seen)!=expected or len(seen)!=96: raise ValueError("missing render")
    for r in cases:
        case=r["case"]
        # Contact sheets: columns baseline/selected; rows checker, flat, smooth for each view.
        for az in (0,180):
            sheet=Image.new("RGB",(size*2,size*3+100),(27,30,35)); draw=ImageDraw.Draw(sheet)
            draw.text((10,8),f"{case} | view {az} | p95 gain {100*r['p95_gain']:.1f}%",fill="white")
            draw.text((10,30),"Baseline",fill="white"); draw.text((size+10,30),"Selected",fill="white")
            for i,mode in enumerate(modes):
                x=seen[case,mode,az,"baseline"]; y=seen[case,mode,az,"selected"]
                delta=np.abs(x.astype(float)-y.astype(float))
                mae=float(delta.mean()/255)
                results.append(dict(case=case,mode=mode,azimuth=az,mae=mae,changed_pixel_fraction=float(np.mean(np.max(delta,axis=2)>0)),fallback=r["method"]=="baseline"))
                ypos=50+i*(size+16); draw.text((10,ypos),mode,fill="white")
                sheet.paste(Image.fromarray(x),(0,ypos+16)); sheet.paste(Image.fromarray(y),(size,ypos+16))
            sheet.save(d/f"{case}_view{az}_comparison.png")
    for r in m["blend_files"]:
        if hashlib.sha256((d/r["file"]).read_bytes()).hexdigest()!=r["sha256"]: raise ValueError("blend hash")
    fallback=[r for r in results if r["fallback"]]
    gate=len(fallback)==18 and all(r["mae"]<=1/255 for r in fallback) and len(m["blend_files"])==2
    result=dict(cycle="R22",approved=False,render_integrity_gate=gate,render_count=len(seen),pair_count=len(results),fallback_pairs=len(fallback),fallback_mae_max=max(r["mae"] for r in fallback),rows=results,visual_quality_assessed=False)
    (d/"evaluation.json").write_text(json.dumps(result,indent=2)); print("R22_SUMMARY",json.dumps({k:v for k,v in result.items() if k!="rows"}),flush=True)
    if not gate: raise SystemExit("R22 render integrity gate failed")
