"""Phase 193: canonical index order before native semantic bevel.
No remeshing, no coordinate rounding, no face winding changes. Synthetic only.
Keep tessellation fixed; the separate tessellation discrepancy is not addressed.
"""
import json,sys,time,math
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase192_bevel_surface_repeatability import snapshot,compare,MODES
from phase191_semantic_rim_bevel import attempt
from phase190_semantic_cap_selection import plan,oracle,CASES,FRESH
from phase188_circular_frustum_recognition import build
from phase170_reindexed_state_planner import reindex,canonical
from phase171_planar_topology_variants import arrays
from phase167_protected_local_bevel import signature

ROOT=Path(__file__).resolve().parent
SEEDS=(1901,1922,1933)
def ordered(V,F):
    # Refuse coincident coordinates rather than invent an ambiguous tie-breaker.
    if len(set(V))!=len(V) or not all(math.isfinite(x) for v in V for x in v):
        return None
    order=sorted(range(len(V)),key=lambda i:V[i]);remap={i:j for j,i in enumerate(order)}
    W=[V[i] for i in order];G=[]
    for f in F:
        q=tuple(remap[i] for i in f)
        G.append(min(q[i:]+q[:i] for i in range(len(q))))
    G.sort()
    E=sorted({tuple(sorted((a,b))) for f in G for a,b in zip(f,f[1:]+f[:1])})
    return W,E,G

def normalize(m):
    V,F=arrays(m);before=signature(V,F);data=ordered(V,F)
    if data is None:return None
    W,E,G=data;n=bpy.data.meshes.new('p193_canonical')
    try:
        n.from_pydata(W,E,G);n.update()
        assert canonical(V,F)==canonical(*arrays(n))
        assert signature(*arrays(m))==before
        assert arrays(n)==(W,G)
        return n
    except Exception:
        bpy.data.meshes.remove(n);raise

def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter();rows=[];pairs=[]
    assert ordered([(0.,0.,0.)]*2,[]) is None
    assert ordered([(float('nan'),0.,0.)],[]) is None
    for name,n,r0,r1,h,axis,c,defect,expected in CASES+FRESH:
        if expected!='frustum':continue
        width=.01*min(h,r0,r1)
        for mode in MODES:
            m=build(n,r0,r1,h,axis,c,defect,mode)
            try:
                for role in ('small_end','large_end'):
                    outputs={}
                    for seed in SEEDS:
                        q=reindex(m,seed);proxy=None
                        try:
                            before=signature(*arrays(q));proxy=normalize(q)
                            assert proxy is not None
                            ph=signature(*arrays(proxy));p=plan(proxy,role)
                            cap,rim,other=oracle(proxy,r0,r1,h,axis,c,role)
                            target_correct=(p['reason']=='ready' and set(p['cap_faces'])==cap
                                and {tuple(e) for e in p['rim_edges']}==rim and set(p['protected_faces'])==other)
                            captures=[]
                            def observe(z):
                                captures.append((snapshot(z),signature(*arrays(z)),canonical(*arrays(z))))
                            result=attempt(proxy,role,p,width,observer=observe)
                            row=dict(name=name,mode=mode,role=role,seed=seed,canonical_signature=ph,
                                target_correct=target_correct,qualified=result['qualified'],
                                input_unchanged=signature(*arrays(q))==before,
                                proxy_unchanged=signature(*arrays(proxy))==ph,
                                persistent_edit=result['persistent_edit'],captured=len(captures)==1)
                            rows.append(row)
                            if len(captures)==1:outputs[seed]=(ph,*captures[0])
                            print('PHASE193_ROW',json.dumps(row,allow_nan=False),flush=True)
                        finally:
                            if proxy is not None:bpy.data.meshes.remove(proxy)
                            bpy.data.meshes.remove(q)
                    for seed in SEEDS[1:]:
                        pair=dict(name=name,mode=mode,role=role,seed=seed,measured=SEEDS[0] in outputs and seed in outputs)
                        if pair['measured']:
                            x,y=outputs[SEEDS[0]],outputs[seed]
                            pair.update(compare(x[1],y[1],width),canonical_input_equal=x[0]==y[0],
                                exact_output_order_equal=x[2]==y[2],exact_output_geometry_equal=x[3]==y[3])
                        pairs.append(pair);print('PHASE193_PAIR',json.dumps(pair,allow_nan=False),flush=True)
            finally:bpy.data.meshes.remove(m)
    gate=(len(rows)==108 and len(pairs)==72 and
          all(r['target_correct'] and r['qualified'] and r['input_unchanged'] and r['proxy_unchanged']
              and r['captured'] and not r['persistent_edit'] for r in rows)
          and all(p['measured'] and p['canonical_input_equal'] and p['screen_pass'] for p in pairs))
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,pairs=pairs,
             controls=dict(duplicate_coordinates_rejected=True,nonfinite_rejected=True),elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True)
    (p/'phase193_canonical_bevel_order.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE193_SUMMARY',json.dumps(dict(cases=len(rows),pairs=len(pairs),gate=gate,
        original_seed_pair_pass=sum(p.get('screen_pass',False) for p in pairs if p['seed']==1922),
        new_seed_pair_pass=sum(p.get('screen_pass',False) for p in pairs if p['seed']==1933),
        exact_output_geometry=sum(p.get('exact_output_geometry_equal',False) for p in pairs),
        exact_output_order=sum(p.get('exact_output_order_equal',False) for p in pairs),
        elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
