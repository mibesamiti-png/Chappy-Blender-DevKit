"""Phase 202: round the existing L-bracket before four orthogonal bores.
Reuse Phase 167 native edge bevel and Phase 201 hole audit, adjusting only
its volume reference to the measured rounded blank. Fixed fixtures only.
"""
import json,math,sys,time
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase201_l_bracket import blank,holes,preflight,frame,audit,T,MIN,EPS
from phase167_protected_local_bevel import apply,signature
from phase195_tapered_spacer import drill,write_obj
from phase196_spacer_verification import Rays,ray_controls
from phase160_operation_contracts import measure
from phase171_planar_topology_variants import arrays
ROOT=Path(__file__).resolve().parent

def edge_samples(m):
    rays=Rays(m)
    return [rays.cast(o,d,1.) for o,d in (
        ((2.2,0,.7),(-1,0,-1)),
        ((2.2,0,-.2),(-1,0,1)),
        ((.7,0,2.2),(-1,0,-1)),
        ((-.2,0,2.2),(1,0,-1)))]

def run(hs,w,probe,path):
    pre=preflight(hs);m=blank();before=signature(*arrays(m));current=m;stages=[]
    if path.exists():path.unlink()
    def finish(status,**kw):
        return dict(status=status,preflight=pre,stages=stages,source_unchanged=signature(*arrays(m))==before,
                    exported=path.exists(),**kw)
    try:
        if not pre['passed']:return finish('hole_preflight')
        # Fixed-fixture conservative budget, not arbitrary-mesh thickness certification.
        if not math.isfinite(w) or w<=0 or w>=T/4 or min(pre['margins'])-2*w<MIN-1e-9:
            return finish('rounding_preflight')
        original=measure(m,'cube');raw=edge_samples(m);current=m.copy()
        count=apply(current,'all',w) if probe!='skip_rounding' else 0
        rounded=measure(current,'cube');samples=edge_samples(current)
        q=rounded['metrics']
        round_checks=dict(clean=rounded['clean'],closed=q['boundary_edges']==0 and q['euler']==2,
            bounds=bool(np.max(np.abs(np.asarray(rounded['bounds'])-original['bounds']))<=EPS),
            changed=count>0 and rounded['oblique_faces']>0 and .95*original['volume']<=rounded['volume']<original['volume']-EPS,
            edge_samples=all(a is not None and b is not None and b-a>w*.1 for a,b in zip(raw,samples)))
        stages.append(dict(step='rounding',checks=round_checks,edges=count,volume=rounded['volume'],samples=samples))
        if not all(round_checks.values()):return finish('rounding_rejected')
        for i,h in enumerate(hs):
            c,M=frame(h)
            new=drill(current,c,M,.6,h['r']*(.8 if probe=='wrong_radius' and i==0 else 1))
            bpy.data.meshes.remove(current);current=new
            a=measure(current,'cube');stages.append(dict(step='drill',clean=a['clean'],euler=a['metrics']['euler']))
        a=audit(current,hs)
        a['expected_volume']+=rounded['volume']-original['volume']
        a['checks']['volume']=abs(a['volume']-a['expected_volume'])<=EPS
        after=edge_samples(current)
        a['checks']['rounding_retained']=all(x is not None and y is not None and abs(x-y)<=EPS for x,y in zip(samples,after))
        a['passed']=all(a['checks'].values()) and all(s['clean'] for s in stages[1:])
        if a['passed'] and probe=='normal':write_obj(current,path)
        return finish('complete' if a['passed'] else 'audit_rejected',audit=a,edge_samples_after=after)
    finally:
        if current!=m:bpy.data.meshes.remove(current)
        bpy.data.meshes.remove(m)

def main():
    assert bpy.app.version_string=='4.4.3';assert ray_controls()
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    bad=holes();bad[0]['u']=1.85
    cases=[('rounded',holes(),.04,'normal','complete'),
           ('oversize',holes(),.15,'normal','rounding_preflight'),
           ('invalid_hole',bad,.04,'normal','hole_preflight'),
           ('skip_rounding',holes(),.04,'skip_rounding','rounding_rejected'),
           ('wrong_radius',holes(),.04,'wrong_radius','audit_rejected')]
    rows=[]
    for name,hs,w,probe,expected in cases:
        r=run(hs,w,probe,dest/f'phase202_{name}.obj')
        row=dict(name=name,width=w,expected=expected,matched=r['status']==expected,**r)
        rows.append(row);print('PHASE202_ROW',json.dumps(row,allow_nan=False),flush=True)
    gate=len(rows)==5 and all(r['matched'] and r['source_unchanged'] and r['exported']==(r['expected']=='complete')
        and (r['expected'] not in ('hole_preflight','rounding_preflight') or not r['stages']) for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,elapsed=time.perf_counter()-start)
    (dest/'phase202_rounded_bracket.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE202_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        parts=sum(r['exported'] for r in rows),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
