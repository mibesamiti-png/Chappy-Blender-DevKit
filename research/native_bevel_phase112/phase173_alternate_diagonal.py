"""Research only: alternate diagonals of exact convex planar end-cap quads.
A construction-specific certificate checks oriented coverage, unchanged other polygons
and their tessellation. Not a general arbitrary-retopology equivalence algorithm.
"""
import json,sys,time
from collections import Counter
from fractions import Fraction
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase171_planar_topology_variants import STATES,arrays
from phase169_combined_state_planner import fixture,inspect,operate
from phase172_sharp_edge_and_triangle_audit import triangle_evidence,run
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
MODES=[('right_cap','original'),('both_caps','original'),('both_caps','explicit_input')]
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def convex_planar(V,f):
    if len(f)!=4 or len(set(f))!=4:return False
    a=[tuple(Fraction(float(x)) for x in V[i]) for i in f]
    e=[sub(a[(i+1)%4],a[i]) for i in range(4)]
    n=cross(e[0],e[1])
    return bool(dot(n,n)>0 and dot(n,sub(a[3],a[0]))==0
                and all(dot(n,cross(e[i],e[(i+1)%4]))>0 for i in range(4)))
def cycle(f):return min(f[i:]+f[:i] for i in range(len(f)))
def triangles(m):
    m.calc_loop_triangles();out={}
    for t in m.loop_triangles:out.setdefault(t.polygon_index,[]).append(cycle(tuple(t.vertices)))
    return out
def splits(f):
    a,b,c,d=f
    return [((a,b,c),(a,c,d)),((a,b,d),(b,c,d))]
def plan(m,mode):
    V,F=arrays(m);T=triangles(m);expected=[];changes=[];groups=[]
    for i,f in enumerate(F):
        x=[V[j][0] for j in f]
        side='right' if all(v>.99 for v in x) else 'left' if all(v<-.99 for v in x) else None
        start=len(expected)
        if side and (side=='right' or mode=='both_caps') and convex_planar(V,f):
            options=splits(f);actual=Counter(T[i])
            matching=[s for s in options if Counter(cycle(t) for t in s)==actual]
            if len(matching)!=1:raise RuntimeError('unexpected original tessellation')
            replacement=next(s for s in options if s!=matching[0])
            expected.extend(replacement);changes.append(dict(face=i,side=side,old=list(matching[0]),new=list(replacement)))
            groups.append((i,start,2))
        else:
            expected.append(f);groups.append((i,start,1))
    assert len(changes)==(1 if mode=='right_cap' else 2)
    return expected,changes,groups
def certify(original,candidate,mode):
    V,F=arrays(original);W,G=arrays(candidate)
    expected,changes,groups=plan(original,mode)
    checks=dict(vertices_exact=V==W,oriented_faces_exact=G==expected,
                exact_convex_planar=all(convex_planar(V,F[c['face']]) for c in changes))
    unchanged=False;replacement=False
    if checks['oriented_faces_exact'] and checks['vertices_exact']:
        A=triangles(original);B=triangles(candidate)
        unchanged=all(Counter(A[i])==Counter(B[j]) for i,j,n in groups if n==1)
        replacement=all(Counter(B[j]+B[j+1])==Counter(cycle(t) for t in expected[j:j+2])
                        for i,j,n in groups if n==2)
    checks.update(unchanged_tessellation=unchanged,replacement_tessellation=replacement)
    return dict(passed=all(checks.values()),checks=checks,changes=changes)
def build(m,mode,defect=None):
    V,F=arrays(m);G,changes,groups=plan(m,mode)
    if defect=='shift_vertex':
        i=changes[0]['new'][0][0];x,y,z=V[i];V[i]=(x+.005,y,z)
    elif defect=='missing_triangle':
        j=next(j for i,j,n in groups if n==2);G.pop(j)
    elif defect=='reversed_triangle':
        j=next(j for i,j,n in groups if n==2);G[j]=tuple(reversed(G[j]))
    n=bpy.data.meshes.new('p173_alternate_diagonal')
    try:n.from_pydata(V,[],G);n.update();return n
    except Exception:bpy.data.meshes.remove(n);raise
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p173_source');base.from_pydata(V,[],F);base.update()
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
                    n=build(m,mode)
                    try:
                        cert=certify(m,n,mode);tri=triangle_evidence(m,n)
                        protection=arrays(n) if policy=='explicit_input' else source
                        a=inspect(n,protection)
                        equivalent=bool(cert['passed'] and a['clean'] and a['closed']
                            and a['metrics']['euler']==orig['metrics']['euler']
                            and abs(a['volume']-orig['volume'])<=1e-5)
                        r=run(n,protection,rounded_volume,'sharp') if equivalent else None
                        expected='needs_review' if mode=='both_caps' and policy=='original' else 'goal_met'
                        ops=[] if expected=='needs_review' else expected_ops
                        row=dict(name=name,mode=mode,policy=policy,certificate=cert,triangle_identity=tri,
                            equivalent=equivalent,expected=expected,result=r,
                            matched=bool(r and r['status']==expected and [t['op'] for t in r['trace']]==ops),
                            input_unchanged=inspect(n,protection)['sha256']==a['sha256'])
                        assert row['input_unchanged']
                        if r:assert r['input_unchanged']
                        if expected=='needs_review' and r:assert not r['trace'] and r['status']=='needs_review'
                        rows.append(row);print('PHASE173_ROW',json.dumps(row,allow_nan=False),flush=True)
                    finally:bpy.data.meshes.remove(n)
                assert inspect(m,source)['sha256']==orig['sha256']
            finally:bpy.data.meshes.remove(m)
        for defect in ('shift_vertex','missing_triangle','reversed_triangle'):
            n=build(base,'right_cap',defect)
            try:
                cert=certify(base,n,'right_cap')
                row=dict(defect=defect,certificate=cert,rejected=not cert['passed'],planner_invoked=False)
                assert row['rejected'];controls.append(row)
                print('PHASE173_CONTROL',json.dumps(row,allow_nan=False),flush=True)
            finally:bpy.data.meshes.remove(n)
        assert inspect(base,source)['sha256']==basehash
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase173_alternate_diagonal.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),exact_triangle_matches=sum(r['triangle_identity']['exact'] for r in rows),
            certified=sum(r['certificate']['passed'] for r in rows),equivalent=sum(r['equivalent'] for r in rows),
            matched=sum(r['matched'] for r in rows),rejected_controls=sum(r['rejected'] for r in controls),
            preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
        print('PHASE173_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==12 and len(controls)==3 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
