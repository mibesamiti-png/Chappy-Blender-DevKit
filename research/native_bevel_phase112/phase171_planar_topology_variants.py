"""Research only: planar triangulation variants of partially machined synthetic prisms.
Separate original strict protection from an explicitly captured new input reference.
Do not claim arbitrary remeshing, exact Hausdorff distance or general feature recognition.
"""
import json,math,sys,time
from pathlib import Path
import bpy,bmesh
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase169_combined_state_planner import fixture,inspect,operate,execute
from phase162_state_planner import distance
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
STATES=[('raw',(),['bevel','hole']),('rounded',('bevel',),['hole']),
        ('holed',('hole',),['bevel']),('complete',('bevel','hole'),[])]
MODES=[('editable_only','original'),('all_planar','original'),('all_planar','explicit_input')]
def arrays(m):
    return [tuple(v.co) for v in m.vertices],[tuple(p.vertices) for p in m.polygons]
def geometry(m):
    V,F=arrays(m);m.calc_loop_triangles()
    return np.asarray(V,dtype=float),F,[tuple(t.vertices) for t in m.loop_triangles]
def triangulate(m,mode):
    V,F=arrays(m);m.calc_loop_triangles()
    triangles={}
    for t in m.loop_triangles:triangles.setdefault(t.polygon_index,[]).append(tuple(t.vertices))
    newF=[];changed=0
    for p,f in zip(m.polygons,F):
        local=all(V[i][0]>=-1e-8 for i in f)
        planar=max(abs((m.vertices[i].co-m.vertices[f[0]].co).dot(p.normal)) for i in f)<=1e-6
        if len(f)>3 and planar and (local or mode=='all_planar'):
            ts=triangles[p.index];assert len(ts)==len(f)-2
            newF.extend(ts);changed+=1
        else:newF.append(f)
    n=bpy.data.meshes.new('p171_planar_variant')
    try:
        n.from_pydata(V,[],newF);n.update()
        assert changed>0 and len(n.polygons)>len(m.polygons)
        return n,changed
    except Exception:bpy.data.meshes.remove(n);raise
def edge_counts(m):
    bm=bmesh.new()
    try:
        bm.from_mesh(m);bm.normal_update()
        edges=[e for e in bm.edges if all(v.co.x>.99 for v in e.verts)]
        return dict(end_edges=len(edges),sharp=sum(e.is_manifold and e.calc_face_angle()>math.radians(30) for e in edges),
                    coplanar=sum(e.is_manifold and e.calc_face_angle()<1e-6 for e in edges))
    finally:bm.free()
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p171_source');base.from_pydata(V,[],F);base.update()
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
                original=inspect(m,source);g0=geometry(m)
                for mode,policy in MODES:
                    n,changed=triangulate(m,mode)
                    try:
                        g1=geometry(n);d0,k0=distance(g0,g1);d1,k1=distance(g1,g0)
                        original_audit=inspect(n,source)
                        # Explicit new capture for a separate experiment only; never reset a failed protection gate.
                        protection=arrays(n) if policy=='explicit_input' else source
                        a=inspect(n,protection);q=a['metrics'];oq=original['metrics']
                        equivalence=dict(clean=a['clean'],closed=a['closed'],same_euler=q['euler']==oq['euler'],
                            volume_error=abs(a['volume']-original['volume']),sampled_surface_error=max(d0,d1),samples=k0+k1)
                        equivalent=(equivalence['clean'] and equivalence['closed'] and equivalence['same_euler']
                            and equivalence['volume_error']<=1e-5 and equivalence['sampled_surface_error']<=1e-5)
                        r=execute(n,protection,rounded_volume,(),'finish',2,None) if equivalent else None
                        expected='needs_review' if mode=='all_planar' and policy=='original' else 'goal_met'
                        ops=[] if expected=='needs_review' else expected_ops
                        matched=bool(r and r['status']==expected and [t['op'] for t in r['trace']]==ops)
                        row=dict(name=name,mode=mode,protection_policy=policy,triangulated_faces=changed,
                            faces_before=oq['faces'],faces_after=q['faces'],equivalent=equivalent,equivalence=equivalence,
                            original_protection_ok=original_audit['scope_ok'],active_protection_ok=a['scope_ok'],
                            original_protected_faces=original_audit['protected_faces'],
                            active_protected_faces=a['protected_faces'],edge_counts=edge_counts(n),expected=expected,
                            expected_ops=ops,matched=matched,result=r,input_unchanged=inspect(n,protection)['sha256']==a['sha256'])
                        assert row['input_unchanged']
                        if r:assert r['input_unchanged'] and all(t['accepted'] or t['rollback_exact'] for t in r['trace'])
                        if expected=='needs_review' and r:
                            assert not r['trace'] and r['status']=='needs_review'
                        rows.append(row);print('PHASE171_ROW',json.dumps(row,allow_nan=False),flush=True)
                    finally:bpy.data.meshes.remove(n)
                assert inspect(m,source)['sha256']==original['sha256']
            finally:bpy.data.meshes.remove(m)
        assert inspect(base,source)['sha256']==basehash
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start,
                 scope='planar polygon triangulation, finite bidirectional samples, two explicit protection contracts')
        P.mkdir(exist_ok=True);(P/'phase171_planar_topology_variants.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),equivalent=sum(r['equivalent'] for r in rows),
            matched=sum(r['matched'] for r in rows),goal_met=sum(bool(r['result'] and r['result']['status']=='goal_met') for r in rows),
            strict_rejections=sum(bool(r['result'] and r['expected']=='needs_review' and r['matched']) for r in rows),
            preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
        print('PHASE171_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==12 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
