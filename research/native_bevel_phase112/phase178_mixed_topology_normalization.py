"""Research only: combine certified cap-fan and straight-edge normalization.
Fixed raw prism, editable right cap, explicit protection policies. No general remeshing claim.
"""
import json,sys,time
from collections import Counter
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase176_split_edge_normalization import mesh,plan,certify,covered,PATTERNS
from phase171_planar_topology_variants import arrays
from phase169_combined_state_planner import fixture,inspect,operate,classify
from phase174_planar_vertex_insertion import POSITIONS,interior
from phase173_alternate_diagonal import cycle,convex_planar
from phase177_valence_two_links import audit,normalize,run
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def signature(m):
    V,F=arrays(m)
    return Counter(V),Counter(cycle(tuple(V[i] for i in f)) for f in F)
def build(split,position,defect=None):
    V,F=arrays(split);k=next(j for j,f in enumerate(F) if all(V[i][0]==1. for i in f))
    boundary=F[k];c=len(V);y,z=POSITIONS[position];V.append((1.,y,z))
    fan=[(a,b,c) for a,b in zip(boundary,boundary[1:]+boundary[:1])]
    if defect=='lifted':V[c]=(1.005,y,z)
    elif defect=='outside':V[c]=(1.,2.,z)
    elif defect=='missing':fan.pop()
    elif defect=='reversed':fan[0]=tuple(reversed(fan[0]))
    return mesh(V,F[:k]+fan+F[k+1:],'p178_mixed')
def recover_cap(m):
    V,F=arrays(m);ids=[j for j,f in enumerate(F) if all(V[i][0]==1. for i in f)]
    if len(ids)<4 or any(len(F[j])!=3 for j in ids):return None,'not_planar_fan'
    common=set(F[ids[0]]).intersection(*(set(F[j]) for j in ids[1:]))
    if len(common)!=1:return None,'not_single_center'
    c=next(iter(common))
    if any(c in f for j,f in enumerate(F) if j not in ids):return None,'shared_center'
    edges=[]
    for j in ids:
        f=F[j];k=f.index(c);edges.append((f[(k+1)%3],f[(k+2)%3]))
    nxt=dict(edges)
    if len(nxt)!=len(edges) or len({b for a,b in edges})!=len(edges):return None,'branch'
    first=min(nxt);q=[first]
    for _ in range(len(edges)-1):
        if q[-1] not in nxt:return None,'open_boundary'
        q.append(nxt[q[-1]])
    q=tuple(q)
    if len(set(q))!=len(q) or nxt.get(q[-1])!=first:return None,'bad_cycle'
    corners=tuple(i for j,i in enumerate(q) if not covered(V,q[j-1],q[(j+1)%len(q)],[i]))
    if not convex_planar(V,corners) or not interior(V,corners,V[c]):return None,'invalid_convex_coverage'
    for a,b in zip(corners,corners[1:]+corners[:1]):
        j=q.index(a);chain=[]
        for t in range(1,len(q)):
            v=q[(j+t)%len(q)]
            if v==b:break
            chain.append(v)
        else:return None,'open_chain'
        if not covered(V,a,b,chain):return None,'invalid_chain'
    if Counter(cycle(F[j]) for j in ids)!=Counter(cycle((a,b,c)) for a,b in zip(q,q[1:]+q[:1])):
        return None,'bad_orientation'
    keep=[i for i in range(len(V)) if i!=c];remap={i:j for j,i in enumerate(keep)}
    G=[]
    for j,f in enumerate(F):
        if j==ids[0]:G.append(q)
        if j not in ids:G.append(f)
    return mesh([V[i] for i in keep],[tuple(remap[i] for i in f) for f in G],'p178_cap'), 'certified'
def matched(result,expected):
    return result['status']==expected and [t['op'] for t in result['trace']]==(['bevel','hole'] if expected=='goal_met' else [])
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();base=mesh(*source,'p178_source');rows=[];controls=[]
    try:
        bh=inspect(base,source)['sha256'];ref=operate(base,'bevel')
        try:rv=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        for pattern in PATTERNS:
            for both,policy in ((False,'original'),(True,'original'),(True,'explicit_input')):
                V,F,_=plan(base,pattern,both);split=mesh(V,F,'p178_split')
                try:
                    assert certify(base,split,pattern,both)['passed']
                    for position in POSITIONS:
                        m=build(split,position);cap=None;n=None
                        try:
                            protection=arrays(m) if policy=='explicit_input' else source
                            a=audit(m,protection)
                            expected='needs_review' if both and policy=='original' else 'goal_met'
                            stages=[];result=None;certificate=False
                            # Certificate recovery is diagnostic on an isolated copy, not an authorized edit.
                            cap,reason=recover_cap(m)
                            certificate=bool(cap is not None and signature(cap)==signature(split))
                            if classify(a,rv)=='raw' and certificate:
                                b=audit(cap,protection)
                                if classify(b,rv)=='raw' and abs(b['volume']-a['volume'])<=1e-5:
                                    stages.append('fan')
                                    n,nreason=normalize(cap,protection,rv)
                                    if n is not None:
                                        stages.append('edge')
                                        result=run(n,protection,rv)
                            if result is None:result=dict(status='needs_review',trace=[],input_unchanged=True)
                            row=dict(pattern=pattern,both=both,policy=policy,position=position,
                                fan_certificate=certificate,fan_reason=reason,initial_clean=a['clean'],
                                initial_state=classify(a,rv),stages=stages,result=result,expected=expected,
                                matched=matched(result,expected),input_unchanged=audit(m,protection)['sha256']==a['sha256'])
                            assert row['input_unchanged'] and result['input_unchanged']
                            if expected=='needs_review':assert not stages and not result['trace']
                            rows.append(row);print('PHASE178_ROW',json.dumps(row,allow_nan=False),flush=True)
                        finally:
                            if n is not None:bpy.data.meshes.remove(n)
                            if cap is not None:bpy.data.meshes.remove(cap)
                            bpy.data.meshes.remove(m)
                finally:bpy.data.meshes.remove(split)
        V,F,_=plan(base,'uniform',False);split=mesh(V,F,'p178_control_split')
        try:
            for defect in ('lifted','outside','missing','reversed'):
                m=build(split,'center',defect);cap=None
                try:
                    cap,reason=recover_cap(m)
                    rejected=cap is None or signature(cap)!=signature(split)
                    row=dict(defect=defect,rejected=rejected,reason=reason,planner_invoked=False)
                    assert rejected;controls.append(row);print('PHASE178_CONTROL',json.dumps(row,allow_nan=False),flush=True)
                finally:
                    if cap is not None:bpy.data.meshes.remove(cap)
                    bpy.data.meshes.remove(m)
        finally:bpy.data.meshes.remove(split)
        assert inspect(base,source)['sha256']==bh
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase178_mixed_topology_normalization.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),certified=sum(r['fan_certificate'] for r in rows),
            matched=sum(r['matched'] for r in rows),goal_met=sum(r['result']['status']=='goal_met' for r in rows),
            combined=sum(r['stages']==['fan','edge'] for r in rows),rejected_controls=sum(r['rejected'] for r in controls),
            preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
        print('PHASE178_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==18 and len(controls)==4 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
