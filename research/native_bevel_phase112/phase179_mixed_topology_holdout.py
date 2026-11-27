"""Research only: stress previously verified mixed-topology normalization.
New clustered boundary samples, near-corner centers and reordered input data.
Same fixed synthetic prism and strict protection. No general remeshing claim.
"""
import json,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase176_split_edge_normalization import mesh,plan,certify,PATTERNS
from phase171_planar_topology_variants import arrays
from phase169_combined_state_planner import fixture,inspect,operate,classify
from phase170_reindexed_state_planner import reindex
from phase177_valence_two_links import audit,normalize,run
from phase178_mixed_topology_normalization import recover_cap,signature,matched
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
CENTERS={'near_corner':(.875,.875),'near_edge':(-.875,.125),'asymmetric':(.375,-.625)}
MODES=((False,'original'),(True,'original'),(True,'explicit_input'))
def fan(split,y,z):
    V,F=arrays(split);j=next(j for j,f in enumerate(F) if all(V[i][0]==1. for i in f))
    q=F[j];c=len(V);V.append((1.,y,z))
    return mesh(V,F[:j]+[(a,b,c) for a,b in zip(q,q[1:]+q[:1])]+F[j+1:],'p179_fan')
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();base=mesh(*source,'p179_source');rows=[]
    assert 'clustered' not in PATTERNS
    PATTERNS['clustered']=(.0625,.125,.1875,.875)
    try:
        bh=inspect(base,source)['sha256'];ref=operate(base,'bevel')
        try:rv=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        for pattern in ('uniform','uneven','clustered'):
            for both,policy in MODES:
                V,F,_=plan(base,pattern,both);split=mesh(V,F,'p179_split')
                try:
                    assert certify(base,split,pattern,both)['passed']
                    for j,(position,(y,z)) in enumerate(CENTERS.items()):
                        m=fan(split,y,z);shuffled=None;cap=None;n=None
                        try:
                            shuffled=reindex(m,211+37*j)
                            assert signature(m)==signature(shuffled)
                            protection=arrays(m) if policy=='explicit_input' else source
                            before=audit(shuffled,protection)
                            raw_hash=inspect(m,protection)['sha256']
                            assert before['sha256']!=raw_hash
                            expected='needs_review' if both and policy=='original' else 'goal_met'
                            cap,reason=recover_cap(shuffled)
                            certificate=bool(cap is not None and signature(cap)==signature(split))
                            stages=[];result=None
                            if classify(before,rv)=='raw' and certificate:
                                a=audit(cap,protection)
                                if classify(a,rv)=='raw' and abs(a['volume']-before['volume'])<=1e-5:
                                    stages.append('fan')
                                    n,nreason=normalize(cap,protection,rv)
                                    if n is not None:
                                        stages.append('edge')
                                        result=run(n,protection,rv)
                            if result is None:result=dict(status='needs_review',trace=[],input_unchanged=True)
                            row=dict(pattern=pattern,both=both,policy=policy,position=position,seed=211+37*j,
                                vertices=len(shuffled.vertices),faces=len(shuffled.polygons),fan_certificate=certificate,
                                fan_reason=reason,initial_state=classify(before,rv),initial_clean=before['clean'],
                                stages=stages,expected=expected,result=result,matched=matched(result,expected),
                                input_unchanged=audit(shuffled,protection)['sha256']==before['sha256'],
                                original_unchanged=inspect(m,protection)['sha256']==raw_hash)
                            assert row['input_unchanged'] and row['original_unchanged'] and result['input_unchanged']
                            if expected=='needs_review':assert not stages and not result['trace']
                            rows.append(row);print('PHASE179_ROW',json.dumps(row,allow_nan=False),flush=True)
                        finally:
                            for obj in (n,cap,shuffled,m):
                                if obj is not None:bpy.data.meshes.remove(obj)
                finally:bpy.data.meshes.remove(split)
        assert inspect(base,source)['sha256']==bh
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase179_mixed_topology_holdout.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),certified=sum(r['fan_certificate'] for r in rows),
            matched=sum(r['matched'] for r in rows),goal_met=sum(r['result']['status']=='goal_met' for r in rows),
            combined=sum(r['stages']==['fan','edge'] for r in rows),preserved=sum(r['input_unchanged'] for r in rows),
            elapsed=out['elapsed'])
        print('PHASE179_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==27 and all(r['input_unchanged'] and r['original_unchanged'] for r in rows)
    finally:
        del PATTERNS['clustered']
        bpy.data.meshes.remove(base)
if __name__=='__main__':main()
