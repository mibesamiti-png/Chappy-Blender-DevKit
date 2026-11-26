"""Phase 197: try the user's simple local-frame approach, once.
Reuse the qualified spacer fabrication; no new machining or geometry algorithms.
Keep Phase 196 as the baseline. Synthetic meshes only.
"""
import json,sys,time
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase195_tapered_spacer import CASES,build,reindex,bind,robust_classify,basis,fabricate,arrays,signature,measure,write_obj
from phase190_semantic_cap_selection import plan

ROOT=Path(__file__).resolve().parent
def execute(m,role,r,w,wall,probe,path):
    V,F=arrays(m);before=signature(V,F);P=np.asarray(V,dtype=float)
    b=bind(m,classifier=robust_classify)['result']
    if b['reason']!='small_to_large':return dict(reason='unavailable',source_unchanged=True,accepted=False)
    c=(np.asarray(b['small_end']['center'])+np.asarray(b['large_end']['center']))*.5
    R=basis(b['directed_axis'])
    scale=max(1.,float(np.max(np.linalg.norm(P-c,axis=1))))
    tol=2e-6*scale
    proxy=m.copy();evidence={}
    try:
        for v,x in zip(proxy.vertices,(P-c)@R):v.co=tuple(x)
        proxy.update()
        Q,G=arrays(proxy);local_hash=signature(Q,G)
        roundtrip=float(np.max(np.linalg.norm(np.asarray(Q)@R.T+c-P,axis=1)))
        original_plan=plan(m,role)
        # End-face interior vertices may disappear during drilling; protect its rim.
        ids={i for f in original_plan['protected_faces'] for i in F[f]}
        axis=R[:,2];X=P-c
        radial=np.linalg.norm(X-(X@axis)[:,None]*axis,axis=1)
        fixed=P[sorted(i for i in ids if radial[i]>r+wall)]
        def restore(z):
            restored=z.copy()
            try:
                Z,H=arrays(z)
                for v,x in zip(restored.vertices,np.asarray(Z)@R.T+c):v.co=tuple(x)
                restored.update()
                W,J=arrays(restored);W=np.asarray(W)
                error=float(np.max(np.linalg.norm(W@R-c@R-np.asarray(Z),axis=1)))
                fixed_error=float(np.max(np.min(np.linalg.norm(fixed[:,None,:]-W[None,:,:],axis=2),axis=1))) if len(fixed) else None
                a=measure(restored,'cube');local=measure(z,'cube')
                checks=dict(roundtrip=roundtrip<=tol,faces_unchanged=H==J,
                    restored_coordinates=error<=tol,protected_rim=fixed_error is not None and fixed_error<=tol,
                    closed=a['clean'] and a['metrics']['boundary_edges']==0 and a['metrics']['euler']==0,
                    volume=abs(a['volume']-local['volume'])<=2e-5*max(1.,local['volume']))
                evidence.update(checks=checks,passed=all(checks.values()),restore_error=error,
                    protected_error=fixed_error,world_audit=a)
                if evidence['passed'] and path is not None:write_obj(restored,path)
            finally:bpy.data.meshes.remove(restored)
        result=fabricate(proxy,role,r,w,wall,probe=probe,observer=restore)
        ok=result['accepted'] and evidence.get('passed',False)
        reason='complete' if ok else 'restore_rejected' if result['accepted'] else result['reason']
        return dict(reason=reason,accepted=ok,source_unchanged=signature(*arrays(m))==before,
            proxy_unchanged=signature(*arrays(proxy))==local_hash,roundtrip=roundtrip,tolerance=tol,
            local_axis=bind(proxy,classifier=robust_classify)['result']['directed_axis'],
            restore=evidence,local_reason=result['reason'],local_checks=result.get('checks'),
            local_ray_disagreements=len(result.get('ray_disagreements',[])),
            preparation=result.get('preparation',{}).get('reason'),persistent_edit=False)
    finally:bpy.data.meshes.remove(proxy)

def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter();rows=[]
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    for name,n,r0,r1,h,axis,c,role in CASES:
        for mode in ('quad','mixed'):
            m=build(n,r0,r1,h,axis,c,None,mode);q=None
            try:
                q=reindex(m,1951);r=.35*min(r0,r1);w=.01*min(h,r0,r1);wall=.25*min(r0,r1)
                for kind,rad,expected in [('normal',r,'complete'),('oversize',.95*min(r0,r1),'clearance_preflight'),
                    ('skip_bevel',r,'discarded'),('skip_bore',r,'discarded'),('wrong_radius',r,'discarded')]:
                    path=dest/f'phase197_{name}_{mode}.obj' if kind=='normal' else None
                    result=execute(q,role,rad,w,wall,kind,path)
                    row=dict(name=name,mode=mode,kind=kind,expected=expected,matched=result['reason']==expected,**result)
                    rows.append(row);print('PHASE197_ROW',json.dumps(row,allow_nan=False),flush=True)
            finally:
                if q is not None:bpy.data.meshes.remove(q)
                bpy.data.meshes.remove(m)
    # A negative comparison is useful evidence, but no unsafe candidate may be accepted.
    gate=len(rows)==30 and all(r['source_unchanged'] and r.get('proxy_unchanged',False) and not r.get('persistent_edit',True)
        and (r['kind']=='normal' or not r['accepted']) for r in rows)
    qualified=all(r['matched'] for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,qualified=qualified,rows=rows,
        elapsed=time.perf_counter()-start)
    (dest/'phase197_local_frame_spacer.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE197_SUMMARY',json.dumps(dict(cases=len(rows),parts=sum(r['accepted'] for r in rows),
        matched=sum(r['matched'] for r in rows),gate=gate,qualified=qualified,
        local_ray_disagreements=sum(r.get('local_ray_disagreements',0) for r in rows if r['kind']=='normal'),
        elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
