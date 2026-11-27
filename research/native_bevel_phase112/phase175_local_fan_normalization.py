"""Research only: normalize a certified four-triangle fan in the editable end cap.
Do not dissolve arbitrary vertices or modify protected faces. Reuse original machining contracts.
"""
import json,sys,time
from collections import Counter
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase174_planar_vertex_insertion import build,certify,interior,POSITIONS
from phase173_alternate_diagonal import cycle,convex_planar
from phase171_planar_topology_variants import STATES,arrays
from phase169_combined_state_planner import fixture,inspect,operate,classify
from phase172_sharp_edge_and_triangle_audit import run
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def normalize(m,protection,rounded_volume):
    V,F=arrays(m);a=inspect(m,protection);state=classify(a,rounded_volume)
    if state not in ('raw','holed'):return None,dict(reason='not_eligible_state',state=state)
    ids=[i for i,f in enumerate(F) if all(V[j][0]==1. for j in f)]
    if len(ids)!=4 or any(len(F[i])!=3 for i in ids):return None,dict(reason='not_four_triangle_cap')
    center=set(F[ids[0]]).intersection(*(set(F[i]) for i in ids[1:]))
    if len(center)!=1:return None,dict(reason='not_single_fan')
    c=next(iter(center))
    if any(c in f for i,f in enumerate(F) if i not in ids):return None,dict(reason='shared_center')
    outer=[]
    for i in ids:
        f=F[i];k=f.index(c);outer.append((f[(k+1)%3],f[(k+2)%3]))
    if len({a for a,b in outer})!=4 or len({b for a,b in outer})!=4:return None,dict(reason='bad_boundary')
    next_vertex=dict(outer);first=min(next_vertex);q=[first]
    for _ in range(3):
        if q[-1] not in next_vertex:return None,dict(reason='open_boundary')
        q.append(next_vertex[q[-1]])
    q=tuple(q)
    if len(set(q))!=4 or next_vertex.get(q[-1])!=first:return None,dict(reason='bad_cycle')
    if not convex_planar(V,q) or not interior(V,q,V[c]):return None,dict(reason='invalid_planar_fan')
    if Counter(cycle(F[i]) for i in ids)!=Counter(cycle((q[j],q[(j+1)%4],c)) for j in range(4)):
        return None,dict(reason='fan_orientation')
    # Replace only the certified editable cap, preserve every other polygon and its winding.
    keep=[i for i in range(len(V)) if i!=c];remap={old:new for new,old in enumerate(keep)}
    G=[];unchanged=[]
    for i,f in enumerate(F):
        if i==ids[0]:G.append(tuple(remap[j] for j in q))
        if i in ids:continue
        unchanged.append((i,len(G)));G.append(tuple(remap[j] for j in f))
    n=bpy.data.meshes.new('p175_normalized')
    try:
        n.from_pydata([V[i] for i in keep],[],G);n.update()
        W,H=arrays(n);m.calc_loop_triangles();n.calc_loop_triangles()
        def bags(mesh,coords):
            out={}
            for t in mesh.loop_triangles:
                points=tuple(coords[i] for i in t.vertices)
                out.setdefault(t.polygon_index,Counter())[cycle(points)]+=1
            return out
        old=bags(m,V);new=bags(n,W)
        b=inspect(n,protection)
        checks=dict(other_tessellation=all(old[i]==new[j] for i,j in unchanged),
            faces_exact=H==G,vertices_exact=W==[V[i] for i in keep],protected=b['scope_ok'],
            clean=b['clean'] and b['closed'],same_state=classify(b,rounded_volume)==state,
            volume=abs(b['volume']-a['volume'])<=1e-5,
            source_unchanged=inspect(m,protection)['sha256']==a['sha256'])
        evidence=dict(reason='normalized' if all(checks.values()) else 'audit_failed',checks=checks,
            removed_vertex=1,removed_faces=3,source_unchanged=checks['source_unchanged'])
        if not all(checks.values()):
            bpy.data.meshes.remove(n);return None,evidence
        return n,evidence
    except Exception:bpy.data.meshes.remove(n);raise
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p175_source');base.from_pydata(V,[],F);base.update()
    rows=[]
    try:
        basehash=inspect(base,source)['sha256'];ref=operate(base,'bevel')
        try:rounded_volume=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        for name,prefix,expected_ops in STATES:
            m=base.copy()
            try:
                for op in prefix:
                    n=operate(m,op);bpy.data.meshes.remove(m);m=n
                for mode,policy in [('right_cap','original'),('both_caps','original'),('both_caps','explicit_input')]:
                    for position in POSITIONS:
                        n=build(m,mode,position);normalized=None
                        try:
                            assert certify(m,n,mode,position)['passed']
                            protection=arrays(n) if policy=='explicit_input' else source
                            a=inspect(n,protection)
                            baseline=run(n,protection,rounded_volume,'sharp')
                            normalized,ev=normalize(n,protection,rounded_volume)
                            result=run(normalized,protection,rounded_volume,'sharp') if normalized is not None else baseline
                            expected='needs_review' if mode=='both_caps' and policy=='original' else 'goal_met'
                            ops=[] if expected=='needs_review' else expected_ops
                            def match(r):return r['status']==expected and [t['op'] for t in r['trace']]==ops
                            row=dict(name=name,mode=mode,policy=policy,position=position,
                                baseline_matched=match(baseline),matched=match(result),normalization=ev,
                                baseline=baseline,result=result,expected=expected,
                                input_unchanged=inspect(n,protection)['sha256']==a['sha256'])
                            assert row['input_unchanged'] and result['input_unchanged']
                            if expected=='needs_review':assert normalized is None and not result['trace']
                            if name in ('rounded','complete'):assert normalized is None
                            rows.append(row);print('PHASE175_ROW',json.dumps(row,allow_nan=False),flush=True)
                        finally:
                            if normalized is not None:bpy.data.meshes.remove(normalized)
                            bpy.data.meshes.remove(n)
            finally:bpy.data.meshes.remove(m)
        assert inspect(base,source)['sha256']==basehash
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase175_local_fan_normalization.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),baseline_matched=sum(r['baseline_matched'] for r in rows),
            matched=sum(r['matched'] for r in rows),normalized=sum(r['normalization']['reason']=='normalized' for r in rows),
            preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
        print('PHASE175_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==24 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
