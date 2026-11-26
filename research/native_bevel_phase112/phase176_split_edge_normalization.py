"""Research only: conforming straight edge subdivision of the raw synthetic prism.
Exact construction certificate, strict protection, and comparison with local normalization.
No arbitrary retopology or unconditional degenerate mesh repair.
"""
import json,sys,time
from collections import Counter
from fractions import Fraction
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase171_planar_topology_variants import arrays,edge_counts
from phase169_combined_state_planner import fixture,inspect,operate,classify
from phase172_sharp_edge_and_triangle_audit import run
from phase173_alternate_diagonal import convex_planar,cycle,sub,dot,cross
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
PATTERNS={'single':(.5,), 'uniform':(.25,.5,.75), 'uneven':(.125,.625)}
def mesh(V,F,name):
    m=bpy.data.meshes.new(name)
    try:m.from_pydata(V,[],F);m.update();return m
    except Exception:bpy.data.meshes.remove(m);raise
def plan(base,pattern,both):
    V,F=arrays(base);W=list(V);G=[];chains={}
    edges=sorted({tuple(sorted((a,b))) for f in F for a,b in zip(f,f[1:]+f[:1])
                  if V[a][0]==V[b][0] and (V[a][0]==1. or both and V[a][0]==-1.)})
    if pattern=='single':
        edges=[e for side in ((-1.,1.) if both else (1.,)) for e in [next(e for e in edges if V[e[0]][0]==side)]]
    for a,b in edges:
        ids=[]
        for t in PATTERNS[pattern]:
            ids.append(len(W));W.append(tuple((1-t)*x+t*y for x,y in zip(V[a],V[b])))
        chains[(a,b)]=ids
    for f in F:
        g=[]
        for a,b in zip(f,f[1:]+f[:1]):
            g.append(a);key=tuple(sorted((a,b)));ids=chains.get(key,[])
            g.extend(ids if a<b else reversed(ids))
        G.append(tuple(g))
    return W,G,chains
def exact(v):return tuple(Fraction(float(x)) for x in v)
def covered(V,a,b,ids):
    A=exact(V[a]);B=exact(V[b]);d=sub(B,A);L=dot(d,d);prev=0
    for i in ids:
        u=sub(exact(V[i]),A);t=dot(u,d)
        if cross(u,d)!=(0,0,0) or not prev<t<L:return False
        prev=t
    return L>0
def certify(base,m,pattern,both):
    V,F=arrays(base);W,G=arrays(m);expectedV,expectedF,chains=plan(base,pattern,both)
    checks=dict(original_vertices=W[:len(V)]==V,vertex_count=len(W)==len(expectedV),
        oriented_face_boundaries=G==expectedF,source_convex_planar=all(convex_planar(V,f) for f in F),
        straight_coverage=len(W)==len(expectedV) and all(covered(W,a,b,ids) for (a,b),ids in chains.items()))
    return dict(passed=all(checks.values()),checks=checks,split_edges=len(chains),added_vertices=len(W)-len(V))
def normalize(m,protection,rounded_volume):
    V,F=arrays(m);a=inspect(m,protection)
    if classify(a,rounded_volume)!='raw':return None,dict(reason='not_eligible_state')
    # A removable edge vertex belongs to exactly two oriented polygon boundaries,
    # lies strictly inside both adjacent straight segments, and is in editable x=1.
    incident={i:[] for i in range(len(V))}
    for j,f in enumerate(F):
        for k,i in enumerate(f):incident[i].append((j,f[k-1],f[(k+1)%len(f)]))
    removable=set()
    for i,p in enumerate(V):
        uses=incident[i]
        if p[0]!=1. or len(uses)!=2:continue
        (_,a0,b0),(_,a1,b1)=uses
        if a0!=b1 or b0!=a1:continue
        if covered(V,a0,b0,[i]):removable.add(i)
    if not removable:return None,dict(reason='no_certified_vertices')
    keep=[i for i in range(len(V)) if i not in removable];remap={v:i for i,v in enumerate(keep)}
    reduced=[tuple(i for i in f if i not in removable) for f in F]
    # Independently verify every removed chain against its surviving endpoints.
    for f,g in zip(F,reduced):
        if len(g)<3:return None,dict(reason='invalid_reduced_boundary')
        if g==f:continue
        if not convex_planar(V,g):return None,dict(reason='not_convex_planar_quad')
        for u,v in zip(g,g[1:]+g[:1]):
            j=f.index(u);ids=[]
            for k in range(1,len(f)):
                w=f[(j+k)%len(f)]
                if w==v:break
                ids.append(w)
            else:return None,dict(reason='missing_endpoint')
            if any(i not in removable for i in ids) or not covered(V,u,v,ids):
                return None,dict(reason='coverage_failed')
    n=mesh([V[i] for i in keep],[tuple(remap[i] for i in f) for f in reduced],'p176_normalized')
    b=inspect(n,protection)
    checks=dict(clean=b['clean'] and b['closed'],protected=b['scope_ok'],
        state=classify(b,rounded_volume)=='raw',volume=abs(b['volume']-a['volume'])<=1e-5,
        input_unchanged=inspect(m,protection)['sha256']==a['sha256'])
    evidence=dict(reason='normalized' if all(checks.values()) else 'audit_failed',
                  removed=len(removable),checks=checks)
    if not all(checks.values()):bpy.data.meshes.remove(n);return None,evidence
    return n,evidence
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();base=mesh(*source,'p176_source');rows=[];controls=[]
    try:
        basehash=inspect(base,source)['sha256'];ref=operate(base,'bevel')
        try:rounded_volume=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        for pattern in PATTERNS:
            for both,policy in ((False,'original'),(True,'original'),(True,'explicit_input')):
                V,F,chains=plan(base,pattern,both);m=mesh(V,F,'p176_split');n=None
                try:
                    cert=certify(base,m,pattern,both);assert cert['passed']
                    protection=arrays(m) if policy=='explicit_input' else source
                    a=inspect(m,protection)
                    baseline=run(m,protection,rounded_volume,'sharp')
                    n,ev=normalize(m,protection,rounded_volume)
                    result=run(n,protection,rounded_volume,'sharp') if n is not None else baseline
                    expected='needs_review' if both and policy=='original' else 'goal_met'
                    def matched(r):return r['status']==expected and (not r['trace'] if expected=='needs_review' else [t['op'] for t in r['trace']]==['bevel','hole'])
                    row=dict(pattern=pattern,both=both,policy=policy,certificate=cert,
                        initial_clean=a['clean'],initial_degenerate=a['degenerate'],initial_edges=edge_counts(m),
                        baseline=baseline,normalization=ev,result=result,expected=expected,
                        baseline_matched=matched(baseline),matched=matched(result),
                        input_unchanged=inspect(m,protection)['sha256']==a['sha256'])
                    assert row['input_unchanged'] and result['input_unchanged']
                    if both and policy=='original':assert n is None and not result['trace']
                    rows.append(row);print('PHASE176_ROW',json.dumps(row,allow_nan=False),flush=True)
                finally:
                    if n is not None:bpy.data.meshes.remove(n)
                    bpy.data.meshes.remove(m)
        for defect in ('off_axis','nonconforming','duplicate_point'):
            V,F,chains=plan(base,'uniform',False);edge,ids=next(iter(chains.items()));i=ids[0]
            if defect=='off_axis':
                x,y,z=V[i];V[i]=(x-.005,y,z)
            elif defect=='nonconforming':
                j=next(j for j,f in enumerate(F) if i in f);F[j]=tuple(v for v in F[j] if v!=i)
            else:V[ids[1]]=V[i]
            m=mesh(V,F,'p176_defect')
            try:
                c=certify(base,m,'uniform',False)
                row=dict(defect=defect,rejected=not c['passed'],certificate=c,planner_invoked=False)
                assert row['rejected'];controls.append(row);print('PHASE176_CONTROL',json.dumps(row,allow_nan=False),flush=True)
            finally:bpy.data.meshes.remove(m)
        assert inspect(base,source)['sha256']==basehash
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,controls=controls,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase176_split_edge_normalization.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),baseline_matched=sum(r['baseline_matched'] for r in rows),
            matched=sum(r['matched'] for r in rows),normalized=sum(r['normalization']['reason']=='normalized' for r in rows),
            rejected_controls=sum(r['rejected'] for r in controls),preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
        print('PHASE176_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==9 and len(controls)==3 and all(r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
