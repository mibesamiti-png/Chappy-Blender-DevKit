"""Research only: exact oriented loop-triangle comparison and sharp-edge-only local bevel.
Keep all prior dimensional/protection thresholds. No arbitrary retopology equivalence claim.
"""
import json,math,sys,time
from collections import Counter
from pathlib import Path
import bpy,bmesh
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase171_planar_topology_variants import STATES,MODES,triangulate,arrays,geometry,edge_counts
from phase169_combined_state_planner import fixture,inspect,operate,classify
from phase168_combined_local_operations import WIDTH,compact
from phase162_state_planner import distance
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def triangle_bag(m):
    m.calc_loop_triangles()
    V=[tuple(v.co) for v in m.vertices]
    def key(t):
        a=tuple(V[i] for i in t.vertices)
        return min(a[i:]+a[:i] for i in range(3))
    return Counter(key(t) for t in m.loop_triangles)
def triangle_evidence(a,b):
    x,y=triangle_bag(a),triangle_bag(b)
    return dict(exact=x==y,triangles_before=sum(x.values()),triangles_after=sum(y.values()),
        missing=sum((x-y).values()),added=sum((y-x).values()))
def sharp_bevel(m):
    n=m.copy();bm=bmesh.new()
    try:
        bm.from_mesh(n);bm.normal_update()
        end=[e for e in bm.edges if all(v.co.x>.99 for v in e.verts)]
        edges=[e for e in end if e.is_manifold and e.calc_face_angle()>math.radians(30)]
        if not edges:raise RuntimeError('no qualifying sharp edges')
        bmesh.ops.bevel(bm,geom=edges,offset=WIDTH,offset_type='OFFSET',segments=3,
            profile=.5,affect='EDGES',clamp_overlap=True,loop_slide=True)
        bm.normal_update();bm.to_mesh(n);n.update()
        return n,dict(end_edges=len(end),selected=len(edges),excluded=len(end)-len(edges))
    except Exception:bpy.data.meshes.remove(n);raise
    finally:bm.free()
def run(m,protection,rounded_volume,mode):
    initial=inspect(m,protection);state=classify(initial,rounded_volume)
    work=m.copy();trace=[]
    try:
        for _ in range(2):
            if state in ('complete','invalid'):break
            op={'raw':'bevel','holed':'bevel','rounded':'hole'}[state]
            expected={('raw','bevel'):'rounded',('holed','bevel'):'complete',('rounded','hole'):'complete'}[(state,op)]
            before=inspect(work,protection);selection=None
            if op=='bevel' and mode=='sharp':candidate,selection=sharp_bevel(work)
            else:candidate=operate(work,op)
            accepted=False
            try:
                a=inspect(candidate,protection);after=classify(a,rounded_volume)
                accepted=after==expected and a['sha256']!=before['sha256']
                if accepted:
                    bpy.data.meshes.remove(work);work=candidate;state=after
                rollback=not accepted and inspect(work,protection)['sha256']==before['sha256']
                assert accepted or rollback
                trace.append(dict(op=op,selected=selection,accepted=accepted,candidate_state=after,
                                  rollback_exact=rollback,summary=compact(a)))
            finally:
                if not accepted:bpy.data.meshes.remove(candidate)
            if not accepted:break
        return dict(status='goal_met' if state=='complete' else 'needs_review',
            initial_state=classify(initial,rounded_volume),final_state=state,trace=trace,
            input_unchanged=inspect(m,protection)['sha256']==initial['sha256'])
    finally:bpy.data.meshes.remove(work)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p172_source');base.from_pydata(V,[],F);base.update()
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
                original=inspect(m,source)
                for mode,policy in MODES:
                    n,changed=triangulate(m,mode)
                    try:
                        protection=arrays(n) if policy=='explicit_input' else source
                        a=inspect(n,protection)
                        tri=triangle_evidence(m,n)
                        d0,k0=distance(geometry(m),geometry(n));d1,k1=distance(geometry(n),geometry(m))
                        # Exact oriented triangle multiset equality proves the same tessellated surface.
                        # Other inputs remain unresolved; no looser BVH tolerance is introduced.
                        equivalent=bool(tri['exact'] and a['clean'] and a['closed']
                            and a['metrics']['euler']==original['metrics']['euler']
                            and abs(a['volume']-original['volume'])<=1e-5)
                        baseline=run(n,protection,rounded_volume,'old') if equivalent else None
                        sharp=run(n,protection,rounded_volume,'sharp') if equivalent else None
                        expected='needs_review' if mode=='all_planar' and policy=='original' else 'goal_met'
                        ops=[] if expected=='needs_review' else expected_ops
                        def matched(r):
                            return bool(r and r['status']==expected and [t['op'] for t in r['trace']]==ops)
                        row=dict(name=name,mode=mode,policy=policy,triangulated_faces=changed,
                            triangles=tri,sampled_surface_error=max(d0,d1),samples=k0+k1,equivalent=equivalent,
                            edge_counts=edge_counts(n),baseline=baseline,sharp=sharp,expected=expected,
                            old_matched=matched(baseline),sharp_matched=matched(sharp),
                            input_unchanged=inspect(n,protection)['sha256']==a['sha256'])
                        assert row['input_unchanged']
                        for result in (baseline,sharp):
                            if result:
                                assert result['input_unchanged']
                                if expected=='needs_review':assert not result['trace'] and result['status']=='needs_review'
                        rows.append(row);print('PHASE172_ROW',json.dumps(row,allow_nan=False),flush=True)
                    finally:bpy.data.meshes.remove(n)
                assert inspect(m,source)['sha256']==original['sha256']
            finally:bpy.data.meshes.remove(m)
        assert inspect(base,source)['sha256']==basehash
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase172_sharp_edge_and_triangle_audit.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),exact_triangle_matches=sum(r['triangles']['exact'] for r in rows),
            equivalent=sum(r['equivalent'] for r in rows),old_matched=sum(r['old_matched'] for r in rows),
            sharp_matched=sum(r['sharp_matched'] for r in rows),preserved=sum(r['input_unchanged'] for r in rows),
            elapsed=out['elapsed'])
        print('PHASE172_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==12 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
