"""Research only: distinguish legitimate two-edge vertex links from duplicate links.
Correct only the proven straight, two-face interior subtype in the isolated audit.
No modification to shared metrics, no blanket waiver of invalid meshes.
"""
import json,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase176_split_edge_normalization import mesh,plan,certify,covered,PATTERNS
from phase171_planar_topology_variants import arrays
from phase169_combined_state_planner import fixture,inspect,operate,classify
from phase172_sharp_edge_and_triangle_audit import sharp_bevel
from phase168_combined_local_operations import compact
from phase173_alternate_diagonal import convex_planar
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
BAD=('bad_boundary_vertices','nonmanifold_edges','orientation_errors','zero_area_faces','duplicate_faces','unused_vertices')
def links(m):
    V,F=arrays(m);incident={i:[] for i in range(len(V))}
    for j,f in enumerate(F):
        for k,i in enumerate(f):incident[i].append((j,f[k-1],f[(k+1)%len(f)]))
    certified=[]
    for i,u in incident.items():
        if len(u)!=2:continue
        (j,a,b),(k,c,d)=u
        if j!=k and a!=b and a==d and b==c and covered(V,a,b,[i]):certified.append(i)
    return certified
def audit(m,protection):
    a=inspect(m,protection);q=a['metrics'];ids=links(m)
    old=q['bad_vertex_links']
    assert old>=len(ids)
    # Other checks remain unchanged; corrected count must be zero.
    residual=old-len(ids)
    a['clean']=bool(q['components']==1 and not any(q[k] for k in BAD)
        and residual==0 and a['nonincident_overlap']==0 and a['degenerate']==0)
    a['link_evidence']=dict(original_bad=old,certified_straight=len(ids),remaining_bad=residual,
        nonincident_overlap=a['nonincident_overlap'],degenerate=a['degenerate'],other_bad={k:q[k] for k in BAD if q[k]})
    return a
def normalize(m,protection,rv):
    V,F=arrays(m);a=audit(m,protection)
    if classify(a,rv)!='raw':return None,'not_eligible'
    remove={i for i in links(m) if V[i][0]==1.}
    if not remove:return None,'no_editable_chain'
    keep=[i for i in range(len(V)) if i not in remove];remap={i:j for j,i in enumerate(keep)}
    G=[tuple(i for i in f if i not in remove) for f in F]
    for f,g in zip(F,G):
        if f==g:continue
        if not convex_planar(V,g):return None,'not_convex_planar_quad'
        for u,v in zip(g,g[1:]+g[:1]):
            j=f.index(u);chain=[]
            for k in range(1,len(f)):
                w=f[(j+k)%len(f)]
                if w==v:break
                chain.append(w)
            else:return None,'open_chain'
            if any(i not in remove for i in chain) or not covered(V,u,v,chain):return None,'coverage_failed'
    n=mesh([V[i] for i in keep],[tuple(remap[i] for i in f) for f in G],'p177_normalized')
    b=audit(n,protection)
    if classify(b,rv)!='raw' or abs(b['volume']-a['volume'])>1e-5:
        bpy.data.meshes.remove(n);return None,'post_audit_failed'
    return n,'normalized'
def run(m,protection,rv):
    work=m.copy();initial=audit(m,protection);a=initial;state=classify(a,rv);trace=[]
    try:
        for _ in range(2):
            if state in ('invalid','complete'):break
            op='hole' if state=='rounded' else 'bevel'
            candidate=sharp_bevel(work)[0] if op=='bevel' else operate(work,op)
            adopted=False
            try:
                b=audit(candidate,protection);after=classify(b,rv)
                expected={('raw','bevel'):'rounded',('holed','bevel'):'complete',('rounded','hole'):'complete'}[(state,op)]
                adopted=after==expected and b['sha256']!=a['sha256']
                if adopted:bpy.data.meshes.remove(work);work=candidate;a=b;state=after
                else:assert audit(work,protection)['sha256']==a['sha256']
                trace.append(dict(op=op,accepted=adopted,state=after,summary=compact(b),links=b['link_evidence']))
            finally:
                if not adopted:bpy.data.meshes.remove(candidate)
            if not adopted:break
        return dict(status='goal_met' if state=='complete' else 'needs_review',trace=trace,
            input_unchanged=audit(m,protection)['sha256']==initial['sha256'])
    finally:bpy.data.meshes.remove(work)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();base=mesh(*source,'p177_source');rows=[];controls=[]
    try:
        ref=operate(base,'bevel')
        try:rv=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        basehash=inspect(base,source)['sha256']
        for pattern in PATTERNS:
            for both,policy in ((False,'original'),(True,'original'),(True,'explicit_input')):
                V,F,_=plan(base,pattern,both);m=mesh(V,F,'p177_split');n=None
                try:
                    assert certify(base,m,pattern,both)['passed']
                    protection=arrays(m) if policy=='explicit_input' else source
                    before=inspect(m,protection);a=audit(m,protection)
                    n,reason=normalize(m,protection,rv)
                    result=run(n if n is not None else m,protection,rv)
                    expected='needs_review' if both and policy=='original' else 'goal_met'
                    matched=result['status']==expected and ([t['op'] for t in result['trace']]==(['bevel','hole'] if expected=='goal_met' else []))
                    row=dict(pattern=pattern,both=both,policy=policy,old_clean=before['clean'],new_clean=a['clean'],
                        links=a['link_evidence'],normalization=reason,result=result,expected=expected,matched=matched,
                        input_unchanged=inspect(m,protection)['sha256']==before['sha256'])
                    assert row['input_unchanged'] and result['input_unchanged']
                    if expected=='needs_review':assert n is None and not result['trace']
                    rows.append(row);print('PHASE177_ROW',json.dumps(row,allow_nan=False),flush=True)
                finally:
                    if n is not None:bpy.data.meshes.remove(n)
                    bpy.data.meshes.remove(m)
        # Same valence, but an actual non-collinear change must never get the exemption.
        V,F,chains=plan(base,'single',False);i=next(iter(chains.values()))[0];x,y,z=V[i];V[i]=(x-.005,y,z)
        m=mesh(V,F,'p177_off_axis')
        try:
            row=dict(defect='off_axis',exempted=i in links(m),certificate=certify(base,m,'single',False)['passed'])
            assert not row['exempted'] and not row['certificate'];controls.append(row)
            print('PHASE177_CONTROL',json.dumps(row,allow_nan=False),flush=True)
        finally:bpy.data.meshes.remove(m)
        assert inspect(base,source)['sha256']==basehash
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase177_valence_two_links.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        print('PHASE177_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
            clean=sum(r['new_clean'] for r in rows),normalized=sum(r['normalization']=='normalized' for r in rows),
            preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed']),allow_nan=False),flush=True)
        assert len(rows)==9 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
