"""Research only: recognize cylinders with quad/triangle side topology.
Recover oriented virtual quads from two n-gon caps and validate each side's coverage.
Do not alter the input mesh. Approximate plane/translation checks, not exact equality.
"""
import json,sys,time
from collections import Counter
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase182_cylinder_recognition import CASES,make_case,recognize,REL
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature
from phase173_alternate_diagonal import cycle,splits
from phase160_operation_contracts import measure
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def recover(m):
    V,F=arrays(m);P=np.asarray(V,dtype=float)
    caps=[f for f in F if len(f)>=8]
    def fail(reason,**kw):return None,dict(reason=reason,**kw)
    if len(caps)!=2 or len(caps[0])!=len(caps[1]):return fail('cap_structure')
    a,b=caps;n=len(a)
    if len(V)!=2*n or set(a)&set(b) or set(a)|set(b)!=set(range(len(V))):return fail('ring_structure')
    A=P[list(a)];B=P[list(b)];d=B.mean(0)-A.mean(0)
    scale=float(np.max(np.linalg.norm(P-P.mean(0),axis=1)));eps=REL*scale
    if np.linalg.norm(d)<=eps:return fail('degenerate_axis')
    distances=np.linalg.norm(A[:,None,:]+d-B[None,:,:],axis=2)
    js=np.argmin(distances,axis=1)
    if len(set(map(int,js)))!=n or float(np.max(distances[np.arange(n),js]))>eps:return fail('nontranslated_rings')
    order=tuple(reversed(a));mapping={a[i]:b[int(js[i])] for i in range(n)}
    top=tuple(mapping[i] for i in order)
    if cycle(top)!=cycle(b):return fail('cap_orientation')
    actual=Counter(cycle(f) for f in F if f!=a and f!=b)
    Q=[a,b];quad_count=0;tri_pairs=0;max_plane=0.
    for i,j in zip(order,order[1:]+order[:1]):
        q=(i,j,mapping[j],mapping[i]);p=P[list(q)]
        normal=np.cross(p[1]-p[0],p[3]-p[0]);length=float(np.linalg.norm(normal))
        if length<=1e-15:return fail('degenerate_side')
        normal/=length
        plane=float(np.max(np.abs((p-p[0])@normal)));max_plane=max(max_plane,plane)
        if plane>eps:return fail('nonplanar_side',plane_error=plane)
        # Each accepted alternative uses only the four expected corner indices.
        options=[Counter([cycle(q)])]+[Counter(cycle(t) for t in s) for s in splits(q)]
        hits=[c for c in options if all(actual[t]>=k for t,k in c.items())]
        if len(hits)!=1:return fail('side_coverage',matching_options=len(hits))
        chosen=hits[0];actual.subtract(chosen)
        if len(chosen)==1:quad_count+=1
        else:tri_pairs+=1
        Q.append(q)
    if any(actual.values()):return fail('extra_or_duplicate_faces')
    audit=measure(m,'cube');topology=audit['metrics']
    if not audit['clean'] or topology['boundary_edges'] or topology['euler']!=2:return fail('mesh_audit')
    proxy=mesh(V,Q,'p184_virtual')
    return proxy,dict(reason='coverage_verified',quad_count=quad_count,triangle_pairs=tri_pairs,
                      max_plane_error=max_plane,tolerance=eps)
def analyze(m):
    bh=signature(*arrays(m));proxy,coverage=recover(m)
    try:
        r=recognize(proxy) if proxy is not None else dict(recognized=False,reason=coverage['reason'])
        return dict(result=r,coverage=coverage,input_unchanged=signature(*arrays(m))==bh,persistent_edit=False)
    finally:
        if proxy is not None:bpy.data.meshes.remove(proxy)
def variant(m,mode,defect=None):
    V,F=arrays(m);G=[];side=0
    for f in F:
        if len(f)!=4:G.append(f);continue
        if mode=='quad' or mode=='mixed' and side%2==0:G.append(f)
        else:G.extend(splits(f)[side%2 if mode=='mixed' else int(mode=='diag_b')])
        side+=1
    ids=[i for i,f in enumerate(G) if len(f)==3]
    if defect=='missing':G.pop(ids[0])
    elif defect=='reversed':G[ids[0]]=tuple(reversed(G[ids[0]]))
    elif defect=='duplicate':G.append(G[ids[0]])
    elif defect=='wrong_pair':
        f=list(G[ids[0]]);f[1]=next(i for i in range(len(V)) if i not in f);G[ids[0]]=tuple(f)
    return mesh(V,G,'p184_variant')
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    rows=[]
    for name,n,r,h,axis,c,defect,_ in CASES:
        if defect=='missing':continue
        m=make_case(n,r,h,axis,c,defect)
        try:
            bh=signature(*arrays(m))
            for mode in ('quad','diag_a','diag_b','mixed'):
                v=variant(m,mode);q=None
                try:
                    q=reindex(v,941);result=analyze(q);a=result['result']
                    expected=defect in (None,'uneven')
                    accurate=False
                    if a['recognized']:
                        unit=np.asarray(axis,dtype=float);unit/=np.linalg.norm(unit)
                        accurate=bool(abs(a['radius']-r)<=1e-5 and abs(a['height']-h)<=1e-5
                            and np.linalg.norm(np.asarray(a['center'])-c)<=1e-5
                            and abs(abs(float(np.dot(a['axis'],unit)))-1)<=1e-8)
                    row=dict(name=name,mode=mode,expected=expected,accurate=accurate,
                        matched=a['recognized']==expected and (not expected or accurate),**result)
                    assert row['input_unchanged'] and not row['persistent_edit']
                    rows.append(row);print('PHASE184_ROW',json.dumps(row,allow_nan=False),flush=True)
                finally:
                    if q is not None:bpy.data.meshes.remove(q)
                    bpy.data.meshes.remove(v)
            assert signature(*arrays(m))==bh
        finally:bpy.data.meshes.remove(m)
    controls=[]
    m=make_case(16,1.,2.,(0,0,1),(0,0,0),None)
    try:
        for defect in ('missing','reversed','duplicate','wrong_pair'):
            v=variant(m,'diag_a',defect)
            try:
                result=analyze(v);row=dict(defect=defect,rejected=not result['result']['recognized'],**result)
                assert row['rejected'] and row['input_unchanged'];controls.append(row)
                print('PHASE184_CONTROL',json.dumps(row,allow_nan=False),flush=True)
            finally:bpy.data.meshes.remove(v)
    finally:bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase184_triangulated_cylinder_recognition.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    summary=dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        recognized=sum(r['result']['recognized'] for r in rows),rejected_controls=sum(r['rejected'] for r in controls),
        preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
    print('PHASE184_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
    assert len(rows)==44 and len(controls)==4 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
