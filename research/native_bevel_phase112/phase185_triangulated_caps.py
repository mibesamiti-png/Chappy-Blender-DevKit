"""Research only: recover convex planar end-cap boundaries without n-gon markers.
Two-ring cylinders, cap fans or triangulations, mixed side layouts.
Approximate coplanarity and projected coverage; no general CAD reconstruction or mesh edits.
"""
import json,sys,time,itertools
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase182_cylinder_recognition import CASES,make_case,REL
from phase184_triangulated_cylinder_recognition import analyze,variant
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature
from phase160_operation_contracts import measure
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def normal(P,f):
    q=P[list(f)];q=q-q[0];n=np.cross(q,np.roll(q,-1,axis=0)).sum(0)
    l=float(np.linalg.norm(n));return n/l if l>0 else None
def regions(m):
    V,F=arrays(m);P=np.asarray(V,dtype=float);scale=float(np.max(np.linalg.norm(P-P.mean(0),axis=1)))
    eps=REL*scale;normals=[normal(P,f) for f in F];seen=set();out=[]
    m.calc_loop_triangles();tris=defaultdict(list)
    for t in m.loop_triangles:tris[t.polygon_index].append(tuple(t.vertices))
    for j,f in enumerate(F):
        n=normals[j]
        if n is None:continue
        origin=P[f[0]]
        ids=frozenset(i for i,g in enumerate(F) if normals[i] is not None and float(n@normals[i])>1-1e-7
            and float(np.max(np.abs((P[list(g)]-origin)@n)))<=eps)
        if ids in seen:continue
        seen.add(ids);uses=defaultdict(list);vertices=set()
        for i in ids:
            g=F[i];vertices.update(g)
            for a,b in zip(g,g[1:]+g[:1]):uses[tuple(sorted((a,b)))].append((a,b))
        if any(len(u)>2 or len(u)==2 and u[0]!=u[1][::-1] for u in uses.values()):continue
        edges=[u[0] for u in uses.values() if len(u)==1]
        if len(edges)<8:continue
        nxt=dict(edges)
        if len(nxt)!=len(edges) or len({b for a,b in edges})!=len(edges):continue
        first=min(nxt);q=[first]
        for _ in range(len(edges)-1):
            if q[-1] not in nxt:break
            q.append(nxt[q[-1]])
        if len(q)!=len(edges) or len(set(q))!=len(q) or nxt.get(q[-1])!=first:continue
        q=tuple(q);Q=P[list(q)];E=np.roll(Q,-1,axis=0)-Q
        if np.any(np.cross(E,np.roll(E,-1,axis=0))@n<=1e-12*scale*scale):continue
        # Verify all region vertices lie inside the convex projected boundary.
        inside=True
        for a,e in zip(Q,E):
            if float(np.min(np.cross(e,P[list(vertices)]-a)@n)) < -eps*float(np.linalg.norm(e)):
                inside=False;break
        if not inside:continue
        local=Q-Q[0];area2=float(np.cross(local,np.roll(local,-1,axis=0)).sum(0)@n)
        areas=[float(np.cross(P[b]-P[a],P[c]-P[a])@n) for i in ids for a,b,c in tris[i]]
        if not areas or min(areas)<=0 or abs(sum(areas)-area2)>REL*area2:continue
        inner=vertices-set(q)
        if any(inner.intersection(g) for i,g in enumerate(F) if i not in ids):continue
        out.append(dict(ids=ids,boundary=q,normal=n,inner=inner,area_error=abs(sum(areas)-area2)))
    return out
def recognize_caps(m):
    V,F=arrays(m);bh=signature(V,F)
    def finish(r,**kw):
        return dict(result=r,input_unchanged=signature(*arrays(m))==bh,persistent_edit=False,**kw)
    a=measure(m,'cube');top=a['metrics']
    if not a['clean'] or top['boundary_edges'] or top['euler']!=2:
        return finish(dict(recognized=False,reason='mesh_audit'),regions=0,hypotheses=0)
    rr=regions(m);hits=[];reasons=[]
    for a,b in itertools.combinations(rr,2):
        if a['ids']&b['ids'] or set(a['boundary'])&set(b['boundary']):continue
        if len(a['boundary'])!=len(b['boundary']) or float(a['normal']@b['normal'])> -1+1e-7:continue
        drop=a['inner']|b['inner'];keep=[i for i in range(len(V)) if i not in drop]
        remap={i:j for j,i in enumerate(keep)}
        G=[a['boundary'],b['boundary']]+[f for i,f in enumerate(F) if i not in a['ids']|b['ids']]
        if any(i not in remap for f in G for i in f):continue
        proxy=mesh([V[i] for i in keep],[tuple(remap[i] for i in f) for f in G],'p185_caps_proxy')
        try:
            result=analyze(proxy);r=result['result'];reasons.append(r['reason'])
            if r['recognized']:
                hits.append((r,dict(cap_faces=[len(a['ids']),len(b['ids'])],
                    interior_vertices=len(drop),area_error=max(a['area_error'],b['area_error']),
                    side_coverage=result['coverage'])))
        finally:bpy.data.meshes.remove(proxy)
    if len(hits)!=1:
        return finish(dict(recognized=False,reason='ambiguous' if hits else 'no_valid_cylinder'),
            regions=len(rr),hypotheses=len(reasons),rejections=reasons)
    r,e=hits[0];return finish(r,regions=len(rr),hypotheses=len(reasons),evidence=e)
def cap_variant(m,mode,defect=None):
    V,F=arrays(m);G=[];cap=0;triids=[]
    for f in F:
        if len(f)<8:G.append(f);continue
        if mode=='one_cap' and cap==1:G.append(f);cap+=1;continue
        if mode=='center':
            c=len(V);V.append(tuple(np.mean(np.asarray([V[i] for i in f]),axis=0)))
            tris=[(a,b,c) for a,b in zip(f,f[1:]+f[:1])]
        else:tris=[(f[0],f[j],f[j+1]) for j in range(1,len(f)-1)]
        triids.extend(range(len(G),len(G)+len(tris)));G.extend(tris);cap+=1
    if defect=='missing':G.pop(triids[0])
    elif defect=='reversed':G[triids[0]]=tuple(reversed(G[triids[0]]))
    elif defect=='duplicate':G.append(G[triids[0]])
    elif defect=='lifted':
        x,y,z=V[-1];V[-1]=(x,y,z+.02)
    return mesh(V,G,'p185_cap_variant')
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[];controls=[]
    for name,n,r,h,axis,c,defect,_ in CASES:
        if defect=='missing':continue
        m=make_case(n,r,h,axis,c,defect)
        try:
            for sides in ('diag_a','mixed'):
                v=variant(m,sides)
                try:
                    for caps in ('one_cap','corner_fan','center'):
                        w=cap_variant(v,caps);q=None
                        try:
                            q=reindex(w,1127);result=recognize_caps(q);a=result['result']
                            expected=defect in (None,'uneven');accurate=False
                            if a['recognized']:
                                unit=np.asarray(axis,dtype=float);unit/=np.linalg.norm(unit)
                                accurate=bool(abs(a['radius']-r)<=1e-5 and abs(a['height']-h)<=1e-5
                                    and np.linalg.norm(np.asarray(a['center'])-c)<=1e-5
                                    and abs(abs(float(np.dot(a['axis'],unit)))-1)<=1e-8)
                            row=dict(name=name,sides=sides,caps=caps,expected=expected,accurate=accurate,
                                matched=a['recognized']==expected and (not expected or accurate),**result)
                            assert row['input_unchanged'] and not row['persistent_edit']
                            rows.append(row);print('PHASE185_ROW',json.dumps(row,allow_nan=False),flush=True)
                        finally:
                            if q is not None:bpy.data.meshes.remove(q)
                            bpy.data.meshes.remove(w)
                finally:bpy.data.meshes.remove(v)
        finally:bpy.data.meshes.remove(m)
    m=make_case(16,1.,2.,(0,0,1),(0,0,0),None);v=variant(m,'diag_a')
    try:
        for defect in ('missing','reversed','duplicate','lifted'):
            w=cap_variant(v,'center',defect)
            try:
                a=recognize_caps(w);row=dict(defect=defect,rejected=not a['result']['recognized'],**a)
                assert row['rejected'] and row['input_unchanged'];controls.append(row)
                print('PHASE185_CONTROL',json.dumps(row,allow_nan=False),flush=True)
            finally:bpy.data.meshes.remove(w)
    finally:bpy.data.meshes.remove(v);bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase185_triangulated_caps.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    summary=dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        recognized=sum(r['result']['recognized'] for r in rows),rejected_controls=sum(r['rejected'] for r in controls),
        preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
    print('PHASE185_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
    assert len(rows)==66 and len(controls)==4 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
