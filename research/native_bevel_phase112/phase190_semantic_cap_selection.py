"""Phase 190: bind semantic ends to verified cap faces and rim edges.
Read-only plan, tied to exact mesh signature. No bevel or persistent edit.
"""
import json,sys,time
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase189_directional_end_roles import bind,CASES,FRESH
from phase188_circular_frustum_recognition import build,classify,hypothesis
from phase185_triangulated_caps import regions
from phase160_operation_contracts import measure
import itertools
from phase182_cylinder_recognition import REL
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature

ROOT=Path(__file__).resolve().parent
def edge(a,b):return tuple(sorted((a,b)))
def edges(f):return [edge(a,b) for a,b in zip(f,f[1:]+f[:1])]
def refit_regions(m):
    V,F=arrays(m);P=np.asarray(V,dtype=float)
    scale=float(np.max(np.linalg.norm(P-P.mean(0),axis=1)))
    result=[]
    for reg in regions(m):
        Q=P[list(reg['boundary'])]
        origin=Q.mean(0);X=Q-origin
        # Area-weighted boundary normal; no dependence on a single triangle.
        n=np.cross(X,np.roll(X,-1,axis=0)).sum(0)
        length=float(np.linalg.norm(n))
        if length<=1e-12*scale*scale:continue
        n/=length
        if float(n@reg['normal'])<1-1e-7:continue
        ids=set(reg['boundary'])|set(reg['inner'])
        if float(np.max(np.abs((P[sorted(ids)]-origin)@n)))>REL*scale:continue
        E=np.roll(Q,-1,axis=0)-Q
        if np.any(np.cross(E,np.roll(E,-1,axis=0))@n<=1e-12*scale*scale):continue
        result.append(dict(reg,normal=n))
    return result

def robust_classify(m):
    # Frozen recognition remains the default. Narrow repair of a rejected
    # frustum hypothesis, not a fallback for arbitrary unknown geometry.
    base=classify(m)
    if (base['result']['kind']!='unknown' or base['cylinder_reference'] or
        base['hypotheses']!=0 or base['reasons']!=['not_coaxial']):
        return base
    V,F=arrays(m);P=np.asarray(V,dtype=float);hits=[];reasons=[]
    for a,b in itertools.combinations(refit_regions(m),2):
        if a['ids']&b['ids'] or set(a['boundary'])&set(b['boundary']):continue
        if float(a['normal']@b['normal'])> -1+1e-7:continue
        r,reason=hypothesis(P,F,a,b);reasons.append(reason)
        if r is not None:hits.append(r)
    # Keep original mesh audit, circle, taper, correspondence, orientation,
    # side-coverage and tolerance checks unchanged.
    if len(hits)==1 and hits[0]['kind']=='frustum':
        return dict(base,result=hits[0],hypotheses=1,reasons=reasons,
                    refit_used=True,baseline_reasons=base['reasons'])
    return dict(base,refit_used=False,refit_reasons=reasons)

def plan(m,role):
    V,F=arrays(m);before=signature(V,F);classification={}
    def finish(reason,faces=(),rim=(),protected=()):
        return dict(reason=reason,role=role,source_signature=before,
                    cap_faces=sorted(faces),rim_edges=sorted(rim),
                    protected_faces=sorted(protected),
                    refit_used=bool(classification.get('refit_used',False)),
                    input_unchanged=signature(*arrays(m))==before,persistent_edit=False)
    if role not in ('small_end','large_end'):return finish('invalid_role')
    classification=robust_classify(m)
    r=bind(m,classifier=lambda _:classification)['result']
    if r['kind']!='frustum' or r['reason']!='small_to_large':return finish('role_unavailable')
    P=np.asarray(V,dtype=float);a=np.asarray(r['directed_axis']);eps=REL*r['large_end']['radius']
    rr=refit_regions(m);selected={}
    for key,sign in [('small_end',-1),('large_end',1)]:
        c=np.asarray(r[key]['center']);radius=r[key]['radius']
        hits=[]
        for reg in rr:
            X=P[list(reg['boundary'])]-c
            z=X@a
            rad=np.linalg.norm(X-z[:,None]*a,axis=1)
            if (float(reg['normal']@a)*sign>1-1e-7 and
                np.max(np.abs(z))<=2*eps and np.max(np.abs(rad-radius))<=2*eps):
                hits.append(reg)
        if len(hits)!=1:return finish('ambiguous_cap')
        selected[key]=hits[0]
    target=selected[role];other=selected['large_end' if role=='small_end' else 'small_end']
    rim=set(edges(target['boundary']))
    uses=defaultdict(list)
    for i,f in enumerate(F):
        for e in edges(f):uses[e].append(i)
    if (target['ids']&other['ids'] or set(target['boundary'])&set(other['boundary']) or
        not all(len(uses[e])==2 and sum(i in target['ids'] for i in uses[e])==1 for e in rim)):
        return finish('rim_not_certified')
    return finish('ready',target['ids'],rim,other['ids'])

def diagnose(m):
    V,F=arrays(m);P=np.asarray(V,dtype=float);rr=regions(m)
    candidates=[]
    for a,b in itertools.combinations(rr,2):
        if a['ids']&b['ids'] or set(a['boundary'])&set(b['boundary']):continue
        dot=float(a['normal']@b['normal'])
        if dot> -1+1e-7:continue
        result,reason=hypothesis(P,F,a,b)
        candidates.append(dict(reason=reason,normal_dot=dot,
            boundary_counts=[len(a['boundary']),len(b['boundary'])],result=result))
    return dict(classification=classify(m),binding=bind(m),
        refit_classification=robust_classify(m),audit=measure(m,'cube'),regions=[dict(normal=r['normal'].tolist(),
            boundary_count=len(r['boundary']),face_count=len(r['ids']),
            area_error=r['area_error']) for r in rr],candidates=candidates)

def applicable(m,p):
    return p['reason']=='ready' and signature(*arrays(m))==p['source_signature']

def oracle(m,r0,r1,h,axis,c,role):
    # Independent fixture-coordinate and polygon-incidence oracle, not regions().
    V,F=arrays(m);P=np.asarray(V,dtype=float);a=np.asarray(axis,dtype=float);a/=np.linalg.norm(a)
    if r1<r0:a=-a
    z=(P-np.asarray(c))@a;sign=-1 if role=='small_end' else 1
    cap={i for i,f in enumerate(F) if np.all(np.abs(z[list(f)]-sign*h*.5)<1e-5)}
    other={i for i,f in enumerate(F) if np.all(np.abs(z[list(f)]+sign*h*.5)<1e-5)}
    cap_uses=Counter(e for i in cap for e in edges(F[i]))
    rim={e for e,n in cap_uses.items() if n==1}
    return cap,rim,other

def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter();rows=[];controls=[]
    for name,n,r0,r1,h,axis,c,defect,expected in CASES+FRESH:
        for mode in ('quad','diag_a','mixed'):
            m=build(n,r0,r1,h,axis,c,defect,mode)
            try:
                for seed in (1901,1902):
                    q=reindex(m,seed)
                    try:
                        for role in ('small_end','large_end'):
                            p=plan(q,role)
                            if expected=='frustum':
                                cap,rim,other=oracle(q,r0,r1,h,axis,c,role)
                                matched=(p['reason']=='ready' and bool(cap and rim and other)
                                    and set(p['cap_faces'])==cap and {tuple(e) for e in p['rim_edges']}==rim
                                    and set(p['protected_faces'])==other and applicable(q,p))
                            else:
                                matched=(p['reason']=='role_unavailable' and not applicable(q,p)
                                    and not any(p[k] for k in ('cap_faces','rim_edges','protected_faces')))
                            row=dict(name=name,mode=mode,seed=seed,expected=expected,matched=matched,**p)
                            if not matched:row['diagnostic']=diagnose(q)
                            rows.append(row);print('PHASE190_ROW',json.dumps(row,allow_nan=False),flush=True)
                        if expected=='frustum':
                            p=plan(q,'small_end');reordered=reindex(q,1903)
                            try:
                                control=dict(name=name,mode=mode,seed=seed,
                                    baseline_applicable=applicable(q,p),
                                    stale_rejected=applicable(q,p) and not applicable(reordered,p),
                                    invalid_role_rejected=plan(q,'top')['reason']=='invalid_role',
                                    input_unchanged=signature(*arrays(q))==p['source_signature'])
                                controls.append(control)
                            finally:bpy.data.meshes.remove(reordered)
                    finally:bpy.data.meshes.remove(q)
            finally:bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,
             elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True)
    (p/'phase190_semantic_cap_selection.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE190_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        ready=sum(r['reason']=='ready' for r in rows),refit_used=sum(r['refit_used'] for r in rows),preserved=sum(r['input_unchanged'] for r in rows),
        controls=len(controls),stale_rejected=sum(r['stale_rejected'] for r in controls),
        elapsed=out['elapsed'])),flush=True)
    assert len(rows)==192 and len(controls)==36
    assert all(r['matched'] and r['input_unchanged'] and not r['persistent_edit'] for r in rows)
    assert all(r['stale_rejected'] and r['invalid_role_rejected'] and r['input_unchanged'] for r in controls)
if __name__=='__main__':main()
