"""Research only: interior-vertex fans in exact convex planar end caps.
Certify strict interior point, oriented covering triangles and all untouched tessellation.
Fixed synthetic prism; not general remeshing or density invariance.
"""
import json,sys,time
from collections import Counter
from fractions import Fraction
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase171_planar_topology_variants import STATES,arrays,edge_counts
from phase169_combined_state_planner import fixture,inspect,operate
from phase172_sharp_edge_and_triangle_audit import triangle_evidence,run
from phase173_alternate_diagonal import MODES,convex_planar,sub,dot,cross,cycle,triangles
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
POSITIONS={'center':(0.,0.),'offcenter':(.125,-.25)}
def exact(v):return tuple(Fraction(float(x)) for x in v)
def interior(V,f,p):
    if not convex_planar(V,f):return False
    a=[exact(V[i]) for i in f];q=exact(p)
    e=[sub(a[(i+1)%4],a[i]) for i in range(4)]
    normal=cross(e[0],e[1])
    return bool(dot(normal,sub(q,a[0]))==0 and
        all(dot(normal,cross(e[i],sub(q,a[i])))>0 for i in range(4)))
def fan_plan(m,mode,position):
    V,F=arrays(m);W=list(V);G=[];groups=[];changes=[]
    for i,f in enumerate(F):
        x=[V[j][0] for j in f]
        side='right' if all(v>.99 for v in x) else 'left' if all(v<-.99 for v in x) else None
        start=len(G)
        if side and (side=='right' or mode=='both_caps') and convex_planar(V,f):
            assert len(set(x))==1
            y,z=POSITIONS[position];p=(x[0],y,z)
            assert interior(V,f,p)
            k=len(W);W.append(p)
            fan=[(f[j],f[(j+1)%4],k) for j in range(4)]
            G.extend(fan);groups.append((i,start,4))
            changes.append(dict(face=i,side=side,point=k,fan=fan))
        else:
            G.append(f);groups.append((i,start,1))
    assert len(changes)==(1 if mode=='right_cap' else 2)
    return W,G,groups,changes
def build(m,mode,position,defect=None):
    W,G,groups,changes=fan_plan(m,mode,position)
    k=changes[0]['point'];j=next(j for i,j,n in groups if n==4)
    x,y,z=W[k]
    if defect=='lifted':W[k]=(x+.005,y,z)
    elif defect=='outside':W[k]=(x,2.,z)
    elif defect=='on_boundary':
        V,F=arrays(m);W[k]=V[F[changes[0]['face']][0]]
    elif defect=='missing':G.pop(j)
    elif defect=='reversed':G[j]=tuple(reversed(G[j]))
    n=bpy.data.meshes.new('p174_fan')
    try:n.from_pydata(W,[],G);n.update();return n
    except Exception:bpy.data.meshes.remove(n);raise
def certify(m,n,mode,position):
    V,F=arrays(m);W,G=arrays(n)
    _,expected,groups,changes=fan_plan(m,mode,position)
    checks=dict(old_vertices_exact=W[:len(V)]==V,new_vertex_count=len(W)==len(V)+len(changes),
        oriented_faces_exact=G==expected,
        strict_interior=all(c['point']<len(W) and interior(V,F[c['face']],W[c['point']]) for c in changes))
    unchanged=False;replacement=False
    if all(checks.values()):
        A=triangles(m);B=triangles(n)
        unchanged=all(Counter(A[i])==Counter(B[j]) for i,j,k in groups if k==1)
        replacement=all(Counter(t for k in range(j,j+4) for t in B[k])==
                        Counter(cycle(t) for t in expected[j:j+4]) for i,j,nf in groups if nf==4)
    checks.update(unchanged_tessellation=unchanged,replacement_tessellation=replacement)
    return dict(passed=all(checks.values()),checks=checks,changes=changes)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p174_source');base.from_pydata(V,[],F);base.update()
    rows=[];controls=[]
    try:
        basehash=inspect(base,source)['sha256'];ref=operate(base,'bevel')
        try:rounded_volume=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        for name,prefix,expected_ops in STATES:
            m=base.copy()
            try:
                for op in prefix:
                    n=operate(m,op);bpy.data.meshes.remove(m);m=n
                orig=inspect(m,source)
                for mode,policy in MODES:
                    for position in POSITIONS:
                        n=build(m,mode,position)
                        try:
                            cert=certify(m,n,mode,position);tri=triangle_evidence(m,n)
                            protection=arrays(n) if policy=='explicit_input' else source
                            a=inspect(n,protection)
                            equivalent=bool(cert['passed'] and a['clean'] and a['closed']
                                and a['metrics']['euler']==orig['metrics']['euler']
                                and abs(a['volume']-orig['volume'])<=1e-5)
                            r=run(n,protection,rounded_volume,'sharp') if equivalent else None
                            expected='needs_review' if mode=='both_caps' and policy=='original' else 'goal_met'
                            ops=[] if expected=='needs_review' else expected_ops
                            row=dict(name=name,mode=mode,policy=policy,position=position,certificate=cert,
                                triangle_identity=tri,equivalent=equivalent,expected=expected,result=r,
                                counts_before=dict(vertices=len(m.vertices),faces=len(m.polygons)),
                                counts_after=dict(vertices=len(n.vertices),faces=len(n.polygons)),
                                edge_counts=edge_counts(n),
                                matched=bool(r and r['status']==expected and [t['op'] for t in r['trace']]==ops),
                                input_unchanged=inspect(n,protection)['sha256']==a['sha256'])
                            assert row['input_unchanged']
                            if r:assert r['input_unchanged']
                            if expected=='needs_review' and r:assert not r['trace'] and r['status']=='needs_review'
                            rows.append(row);print('PHASE174_ROW',json.dumps(row,allow_nan=False),flush=True)
                        finally:bpy.data.meshes.remove(n)
                assert inspect(m,source)['sha256']==orig['sha256']
            finally:bpy.data.meshes.remove(m)
        for defect in ('lifted','outside','on_boundary','missing','reversed'):
            n=build(base,'right_cap','center',defect)
            try:
                cert=certify(base,n,'right_cap','center')
                row=dict(defect=defect,certificate=cert,rejected=not cert['passed'],planner_invoked=False)
                assert row['rejected'];controls.append(row)
                print('PHASE174_CONTROL',json.dumps(row,allow_nan=False),flush=True)
            finally:bpy.data.meshes.remove(n)
        assert inspect(base,source)['sha256']==basehash
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase174_planar_vertex_insertion.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),certified=sum(r['certificate']['passed'] for r in rows),
            equivalent=sum(r['equivalent'] for r in rows),matched=sum(r['matched'] for r in rows),
            rejected_controls=sum(r['rejected'] for r in controls),preserved=sum(r['input_unchanged'] for r in rows),
            elapsed=out['elapsed'])
        print('PHASE174_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==24 and len(controls)==5 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
