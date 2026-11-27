"""Research only: frozen selector transfer to three previously unused collar fixtures.
The meshes already existed in the research corpus; perturbations are new synthetic tests.
No tuning, no production adoption, no unknown-intent editing.
"""
import json,sys,time
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase154_looptools import load_extension,unload_extension
from phase156_looptools_subdiv import run
from phase157_bounded_selector import KEEP,SPACE,RELAX,select,accept
from phase120_native_sections import planes,evaluate
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
CASES={'vertical_two':12,'deep_small':8,'narrow_tall':16}
def ring_indices(c,n):
    F=np.asarray(c['faces']);steps=c['config']['steps'];nv=len(c['vertices']);nb=nv-(steps-1)*n
    a=F[-steps*n:-(steps-1)*n,0];b=F[-n:,3]
    ring=np.vstack([a,np.arange(nb,nv).reshape(steps-1,n),b])
    assert len(set(ring.ravel()))==ring.size and np.all(a<nb) and np.all(b<nb)
    expected=[]
    for k in range(steps):
        for j in range(n):
            i=(j+1)%n
            expected.append([ring[k,j],ring[k,i],ring[k+1,i],ring[k+1,j]])
    assert np.array_equal(F[-steps*n:],expected)
    return nb,ring
def perturb(V,ring,mode):
    Y=V.copy();t=np.arange(len(ring),dtype=float)
    if mode=='crowded':
        u=t.copy();k=len(t)//2;u[k]=k+.8
    elif mode=='alternating':
        # Preserve strict ordering (alternating gaps 0.35 and 1.65).
        u=t.copy();u[1:-1]+=.325*np.where(np.arange(1,len(t)-1)%2,1.,-1.)
    elif mode=='original':return Y
    else:raise ValueError(mode)
    assert np.all(np.diff(u)>0) and u[0]==t[0] and u[-1]==t[-1]
    for path in ring.T:
        for axis in range(3):Y[path,axis]=np.interp(u,t,V[path,axis])
    return Y.astype(np.float32).astype(float)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    data={r['name']:r for r in json.loads((ROOT/'phase141_frozen_meshes.json').read_text())['cases']}
    fixtures={r['fixture']['name']:r['fixture'] for r in json.loads((ROOT/'phase133_holdout_frozen.json').read_text())['cases']}
    module=load_extension();rows=[]
    try:
        for name,n in CASES.items():
            c=data[name];F=[tuple(f) for f in c['faces']];V=np.asarray(c['vertices'],dtype=np.float32).astype(float)
            nb,ring=ring_indices(c,n)
            sharp=fixtures[name]['sharp'];orig=evaluate(sharp['vertices'],sharp['faces'],planes(fixtures[name]));assert orig['complete']
            for mode in ('original','crowded','alternating'):
                Y=perturb(V,ring,mode);assert np.array_equal(Y[:nb],V[:nb])
                base,coords=run(c,Y,F,sharp,orig,ring,nb,KEEP)
                cache={}
                def trial(setting):
                    if setting not in cache:cache[setting]=run(c,Y,F,sharp,orig,ring,nb,setting,coords)[0]
                    return cache[setting]
                def forbidden(_):raise AssertionError('unknown or preserve intent attempted an edit')
                for intent in ('unknown','preserve'):
                    v,a,status=select(base,intent,forbidden);assert v is base and not a
                selected,attempts,status=select(base,'optimize_collar',trial)
                used=1+len(attempts)
                # Audit both frozen options on isolated copies, regardless of selector's early exit.
                options=[trial(k) for k in (SPACE,RELAX)]
                feasible=[x for x in options if accept(base,x)]
                missed=bool(status!='accepted_edit' and feasible)
                row=dict(name=name,variant=mode,status=status,evaluations=used,baseline=base,selected=selected,options=options,
                         eligible_edits=len(feasible),missed_eligible=missed,
                         input_max_displacement=float(np.linalg.norm(Y-V,axis=1).max()))
                rows.append(row)
                print('PHASE158_ROW',json.dumps(dict(name=name,variant=mode,status=status,evaluations=used,
                    baseline_pass=base['passed'],baseline_ratio=base['max_edge_ratio'],baseline_turn=base['max_turn'],
                    selected_pass=selected['passed'],setting=selected['setting'],ratio=selected['max_edge_ratio'],
                    turn=selected['max_turn'],eligible_edits=len(feasible),missed_eligible=missed,
                    fixed_error=selected['fixed_error']),allow_nan=False),flush=True)
    finally:unload_extension(module)
    out=dict(complete=True,approved=False,native_executed=True,selector_tuned=False,
             new_geometry_corpus=False,held_out_from_selector_calibration=True,rows=rows,elapsed=time.perf_counter()-start)
    (P/'phase158_selector_holdout.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE158_SUMMARY',json.dumps(dict(cases=len(rows),evaluations=sum(r['evaluations'] for r in rows),
          audit_evaluations=3*len(rows),baseline_passed=sum(r['baseline']['passed'] for r in rows),
          selected_passed=sum(r['selected']['passed'] for r in rows),
          edits=sum(r['status']=='accepted_edit' for r in rows),
          missed_eligible=sum(r['missed_eligible'] for r in rows),intent_controls=2*len(rows),elapsed=out['elapsed'])),flush=True)
    assert len(rows)==9 and all(1<=r['evaluations']<=3 for r in rows)
if __name__=='__main__':main()
