"""Research only: reindex already-machined synthetic meshes before state planning.
Permute vertices, faces, and cyclic face starts without changing oriented connectivity.
This is not a remeshing, arbitrary topology, or arbitrary input adaptation claim.
"""
import json,random,sys,time
from collections import Counter
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase169_combined_state_planner import CASES,fixture,inspect,operate,execute
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
SEEDS=(17,61,103)
def arrays(m):
    return [tuple(v.co) for v in m.vertices],[tuple(p.vertices) for p in m.polygons]
def canonical(V,F):
    def cycle(f):
        a=tuple(V[i] for i in f)
        return min(a[j:]+a[:j] for j in range(len(a)))
    return Counter(V),Counter(cycle(f) for f in F)
def reindex(m,seed):
    V,F=arrays(m);rng=random.Random(seed)
    order=list(range(len(V)));rng.shuffle(order)
    remap={old:new for new,old in enumerate(order)}
    newV=[V[i] for i in order];newF=[]
    for f in F:
        j=rng.randrange(len(f));f=f[j:]+f[:j]
        newF.append(tuple(remap[i] for i in f))
    rng.shuffle(newF)
    assert canonical(V,F)==canonical(newV,newF)
    n=bpy.data.meshes.new('p170_reindexed')
    try:
        n.from_pydata(newV,[],newF);n.update()
        assert canonical(V,F)==canonical(*arrays(n))
        return n
    except Exception:bpy.data.meshes.remove(n);raise
def key(r):
    return (r['initial_state'],r['status'],r['final_state'],
            [(t['op'],t['accepted'],t['rollback_exact']) for t in r['trace']])
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p170_source');base.from_pydata(V,[],F);base.update()
    rows=[]
    try:
        initial=inspect(base,source);ref=operate(base,'bevel')
        try:rounded_volume=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        for name,prefix,intent,budget,probe,expected,expected_ops in CASES:
            m=base.copy()
            try:
                for op in prefix:
                    n=operate(m,op);bpy.data.meshes.remove(m);m=n
                original=inspect(m,source)
                reference=execute(m,source,rounded_volume,(),intent,budget,probe)
                assert reference['status']==expected and [t['op'] for t in reference['trace']]==expected_ops
                for seed in SEEDS:
                    n=reindex(m,seed)
                    try:
                        before=inspect(n,source)
                        result=execute(n,source,rounded_volume,(),intent,budget,probe)
                        same=key(result)==key(reference)
                        same_final_contract=(result['final']['faces']==reference['final']['faces']
                            and result['final']['euler']==reference['final']['euler']
                            and abs(result['final']['volume']-reference['final']['volume'])<=1e-4
                            and result['final']['scope_ok']==reference['final']['scope_ok']
                            and result['final']['hole']==reference['final']['hole'])
                        unchanged=inspect(n,source)['sha256']==before['sha256']
                        row=dict(name=name,seed=seed,same_decision=same,same_final_contract=same_final_contract,
                            reordered=before['sha256']!=original['sha256'],oriented_connectivity_equal=True,
                            input_unchanged=unchanged,reference_status=reference['status'],status=result['status'],
                            initial_state=result['initial_state'],final_state=result['final_state'],
                            final=result['final'],trace=result['trace'])
                        assert unchanged and result['input_unchanged']
                        assert all(t['accepted'] or t['rollback_exact'] for t in result['trace'])
                        rows.append(row);print('PHASE170_ROW',json.dumps(row,allow_nan=False),flush=True)
                    finally:bpy.data.meshes.remove(n)
                assert inspect(m,source)['sha256']==original['sha256']
            finally:bpy.data.meshes.remove(m)
        assert inspect(base,source)['sha256']==initial['sha256']
        out=dict(complete=True,native_executed=True,approved=False,seeds=SEEDS,rows=rows,elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase170_reindexed_state_planner.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        summary=dict(cases=len(rows),same_decisions=sum(r['same_decision'] for r in rows),
            same_final_contracts=sum(r['same_final_contract'] for r in rows),reordered=sum(r['reordered'] for r in rows),
            inputs_preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
        print('PHASE170_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
        assert len(rows)==33 and all(r['reordered'] and r['input_unchanged'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
