"""Phase 191: bounded semantic rim bevel on disposable meshes.
Frozen Phase 190 plan. No output adoption; synthetic geometry only.
Gate: all 12 quad trials qualify, all 36 trials measured, all refusal
controls pass. Triangulated and mixed results are diagnostic, not guaranteed.
"""
import json,sys,time,math
from pathlib import Path
from collections import Counter
import numpy as np
import bpy,bmesh
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase190_semantic_cap_selection import plan,applicable,robust_classify,oracle,CASES,FRESH
from phase189_directional_end_roles import bind
from phase188_circular_frustum_recognition import build
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature
from phase160_operation_contracts import measure

ROOT=Path(__file__).resolve().parent
def face_key(V,f):
    q=tuple(tuple(float(x) for x in V[i]) for i in f)
    return min(q[i:]+q[:i] for i in range(len(q)))
def vec(v):return tuple(float(x) for x in v)
def attempt(m,role,p,width,observer=None):
    V,F=arrays(m);before=signature(V,F)
    def finish(reason,**kw):
        return dict(reason=reason,qualified=reason=='qualified',
                    input_unchanged=signature(*arrays(m))==before,
                    persistent_edit=False,**kw)
    if p['role']!=role or not applicable(m,p):return finish('invalid_or_stale_plan')
    if p!=plan(m,role):return finish('plan_mismatch')
    r=bind(m,classifier=robust_classify)['result']
    if r['reason']!='small_to_large':return finish('role_unavailable')
    a=np.asarray(r['directed_axis']);target=np.asarray(r[role]['center'])
    other_key='large_end' if role=='small_end' else 'small_end'
    other=np.asarray(r[other_key]['center'])
    h=float(np.linalg.norm(target-other));c=(target+other)*.5
    if role=='small_end':a=-a
    limit=.02*min(h,r['small_end']['radius'])
    if not math.isfinite(width) or not 0<width<=limit*(1+1e-10):
        return finish('width_out_of_scope')
    base=measure(m,'cube')
    if not base['clean']:return finish('baseline_not_clean')
    protected=Counter(face_key(V,F[i]) for i in p['protected_faces'])
    fixed={vec(v) for v in V if float((np.asarray(v)-c)@a)<0}
    old={vec(v) for v in V}
    rim={tuple(e) for e in p['rim_edges']}
    candidate=m.copy();bm=bmesh.new()
    try:
        bm.from_mesh(candidate);bm.verts.ensure_lookup_table();bm.verts.index_update()
        geom=[e for e in bm.edges if tuple(sorted(v.index for v in e.verts)) in rim]
        if len(geom)!=len(rim) or not all(e.is_manifold for e in geom):
            return finish('rim_not_applicable')
        result=bmesh.ops.bevel(bm,geom=geom,offset=width,offset_type='OFFSET',
            segments=3,profile=.5,affect='EDGES',clamp_overlap=True,loop_slide=True)
        new_faces=[f for f in result['faces'] if f.is_valid]
        local=bool(new_faces) and all(float((np.asarray(tuple(v.co))-c)@a)>0
                                    for f in new_faces for v in f.verts)
        bm.normal_update();bm.to_mesh(candidate);candidate.update()
        W,G=arrays(candidate);new={vec(v) for v in W}
        actual=Counter(face_key(W,f) for f in G if all(float((np.asarray(W[i])-c)@a)<0 for i in f))
        post=measure(candidate,'cube');q=post['metrics']
        new_points=new-old
        loss=base['volume']-post['volume']
        checks=dict(clean=post['clean'],closed=q['boundary_edges']==0 and q['euler']==2,
            protected_exact=protected==actual,fixed_vertices=fixed<=new,
            localized_new_vertices=bool(new_points) and all(float((np.asarray(v)-c)@a)>0 for v in new_points),
            localized_bevel_faces=local,changed=signature(W,G)!=before,
            volume_loss=1e-8*base['volume']<loss<=.05*base['volume'])
        if observer is not None and all(checks.values()):observer(candidate)
        return finish('qualified' if all(checks.values()) else 'discarded',
            checks=checks,width=width,selected_edges=len(geom),bevel_faces=len(new_faces),
            source_volume=base['volume'],candidate_volume=post['volume'],
            candidate_faces=q['faces'],candidate_audit=post)
    except (RuntimeError,ValueError) as exc:
        return finish('native_error',error=str(exc))
    finally:
        bm.free();bpy.data.meshes.remove(candidate)

def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter();rows=[];controls=[]
    for name,n,r0,r1,h,axis,c,defect,expected in CASES+FRESH:
        for mode in ('quad','diag_a','mixed'):
            m=build(n,r0,r1,h,axis,c,defect,mode)
            try:
                q=reindex(m,1901)
                try:
                    before=signature(*arrays(q))
                    width=.01*min(h,r0,r1)
                    for role in ('small_end','large_end'):
                        p=plan(q,role)
                        if expected!='frustum':
                            out=attempt(q,role,p,width)
                            controls.append(dict(name=name,mode=mode,role=role,
                                kind='unavailable',passed=out['reason']=='invalid_or_stale_plan' and out['input_unchanged']))
                            continue
                        cap,rim,other=oracle(q,r0,r1,h,axis,c,role)
                        target_correct=(p['reason']=='ready' and set(p['cap_faces'])==cap
                            and {tuple(e) for e in p['rim_edges']}==rim and set(p['protected_faces'])==other)
                        out=attempt(q,role,p,width) if target_correct else dict(reason='selection_failed',qualified=False,input_unchanged=True,persistent_edit=False)
                        row=dict(name=name,mode=mode,role=role,target_correct=target_correct,**out)
                        rows.append(row);print('PHASE191_ROW',json.dumps(row,allow_nan=False),flush=True)
                        bad=dict(p,rim_edges=p['rim_edges'][:-1])
                        wrong='small_end' if role=='large_end' else 'large_end'
                        checks=[(attempt(q,role,bad,width),'plan_mismatch'),
                                (attempt(q,wrong,p,width),'invalid_or_stale_plan'),
                                (attempt(q,role,p,0.),'width_out_of_scope')]
                        stale=reindex(q,1912)
                        try:checks.append((attempt(stale,role,p,width),'invalid_or_stale_plan'))
                        finally:bpy.data.meshes.remove(stale)
                        for (result,reason),kind in zip(checks,('tampered','wrong_role','zero_width','stale')):
                            controls.append(dict(name=name,mode=mode,role=role,kind=kind,
                                passed=target_correct and result['reason']==reason and result['input_unchanged'] and not result['persistent_edit']))
                    assert signature(*arrays(q))==before
                finally:bpy.data.meshes.remove(q)
            finally:bpy.data.meshes.remove(m)
    quad=[r for r in rows if r['mode']=='quad']
    gate=(len(rows)==36 and len(quad)==12 and all(r['qualified'] for r in quad)
        and all(r['target_correct'] and r['input_unchanged'] and not r['persistent_edit'] for r in rows)
        and len(controls)==204 and all(r['passed'] for r in controls))
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,controls=controls,
        elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True)
    (p/'phase191_semantic_rim_bevel.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE191_SUMMARY',json.dumps(dict(cases=len(rows),qualified=sum(r['qualified'] for r in rows),
        modes={mode:sum(r['qualified'] for r in rows if r['mode']==mode) for mode in ('quad','diag_a','mixed')},
        controls=len(controls),controls_passed=sum(r['passed'] for r in controls),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
