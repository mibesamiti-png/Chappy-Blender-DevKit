"""Phase 198: make a three-hole mounting block using existing Phase 164 machinery.
Two through bores and one blind bore; no new machining or checking algorithms.
Fixed synthetic geometry. Only preflight-qualified, audited meshes are exported.
"""
import json,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase164_multi_hole_clearance import hole,preflight,execute
from phase195_tapered_spacer import write_obj

ROOT=Path(__file__).resolve().parent
def layout(floor=.45,right=.55,blind_y=.45):
    return [hole(-.55,-.35,.18),hole(right,-.35,.18),hole(0,blind_y,.22,floor)]

def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter()
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[('mounting_block',layout(),True),
           ('thin_floor',layout(floor=.10),False),
           ('thin_outer_wall',layout(right=.75),False),
           ('thin_web',layout(blind_y=-.35),False)]
    rows=[]
    for name,hs,expected in cases:
        p=preflight(hs);path=dest/f'phase198_{name}.obj';captures=[]
        def observe(m):
            captures.append(True)
            write_obj(m,path)
        a=execute(hs,observer=observe) if p['passed'] else None
        accepted=bool(a and a['passed'] and a['rollback_exact'] and all(x['clean'] for x in a['stages']) and len(captures)==1)
        row=dict(name=name,holes=hs,expected=expected,accepted=accepted,
                 preflight=p,native=a,exported=path.exists(),matched=accepted==expected and p['passed']==expected)
        rows.append(row);print('PHASE198_ROW',json.dumps(row,allow_nan=False),flush=True)
    gate=len(rows)==4 and all(r['matched'] and r['exported']==r['expected'] for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,elapsed=time.perf_counter()-start)
    (dest/'phase198_mounting_block.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE198_SUMMARY',json.dumps(dict(cases=len(rows),parts=sum(r['accepted'] for r in rows),
        rejected_before_machining=sum(not r['preflight']['passed'] for r in rows),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
