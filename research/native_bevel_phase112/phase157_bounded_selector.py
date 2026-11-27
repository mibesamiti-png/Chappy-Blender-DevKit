"""Research-only bounded tool selection, calibrated on Phase 154/156 fixtures.
No generalization claim. No editing when the user's intent is unknown.
"""
import json,sys,time
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase154_looptools import RINGS,load_extension,unload_extension
from phase156_looptools_subdiv import run
from phase120_native_sections import planes,evaluate
ROOT=Path(__file__).resolve().parent
P=ROOT/'results'
KEEP=('keep','axial','linear',0,0)
SPACE=('space','axial','cubic',100,1)
RELAX=('relax','axial','cubic',100,3)
def plan(base,intent):
    if intent!='optimize_collar':return []
    if base['passed'] and base['max_edge_ratio']<=30:return []
    if not base['passed'] and (base['max_turn'] is None or base['max_turn']>30):
        return [RELAX,SPACE]
    return [SPACE,RELAX]
def accept(base,candidate):
    if not candidate['passed']:return False
    if not base['passed']:return True
    return (candidate['max_edge_ratio']<=.95*base['max_edge_ratio']
            and all(a['edge_ratio_all']<=b['edge_ratio_all']+1e-6 for a,b in zip(candidate['levels'][1:],base['levels'][1:])))
def select(base,intent,trial):
    attempts=[]
    for setting in plan(base,intent):
        candidate=trial(setting)
        attempts.append(candidate)
        if accept(base,candidate):return candidate,attempts,'accepted_edit'
    return base,attempts,'keep' if base['passed'] else 'needs_review'
def controls():
    good=dict(passed=True,max_edge_ratio=20,max_turn=25,levels=[dict(edge_ratio_all=20)]*3)
    bad=dict(passed=False,max_edge_ratio=80,max_turn=37,levels=[dict(edge_ratio_all=80)]*3)
    def no_trial(_):raise AssertionError('unexpected edit')
    assert select(good,'unknown',no_trial)[2]=='keep'
    assert select(bad,'unknown',no_trial)[2]=='needs_review'
    assert select(good,'preserve',no_trial)[2]=='keep'
    assert select(good,'optimize_collar',no_trial)[2]=='keep'
    assert plan(bad,'optimize_collar')==[RELAX,SPACE]
    assert select(bad,'optimize_collar',lambda _:bad)[2]=='needs_review'
    high=dict(good,max_edge_ratio=70)
    minor=dict(good,max_edge_ratio=69)
    assert not accept(high,minor)
    worse=dict(good,levels=[dict(edge_ratio_all=81)]*3)
    assert not accept(high,worse)
    return 8
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    ncontrols=controls()
    prior=json.loads((P/'phase156_looptools_subdiv.json').read_text())
    assert prior['complete'] and prior['native_executed'] and not prior['approved']
    expected={r['name']:r for r in prior['rows']}
    fixtures={r['fixture']['name']:r['fixture'] for r in json.loads((ROOT/'phase133_holdout_frozen.json').read_text())['cases']}
    data={r['name']:r for r in json.loads((ROOT/'phase141_frozen_meshes.json').read_text())['cases']}
    module=load_extension();rows=[]
    try:
        for name,label in [('offset_single','offset_single'),('low_wide','low_wide'),('corner_two','corner_before'),('corner_two','corner_after')]:
            c=data[name];F=[tuple(f) for f in c['faces']];V=np.asarray(c['vertices'],dtype=np.float32).astype(float)
            if label=='corner_after':
                lines=(ROOT/'phase142_corner_two_selected.obj').read_text().splitlines()
                V=np.asarray([list(map(float,l.split()[1:])) for l in lines if l.startswith('v ')],dtype=np.float32).astype(float)
                assert F==[tuple(int(i)-1 for i in l.split()[1:]) for l in lines if l.startswith('f ')]
            nb,a,b=RINGS[name];n=len(a);steps=c['config']['steps'];assert len(V)==nb+(steps-1)*n
            ring=np.vstack([a,np.arange(nb,len(V)).reshape(steps-1,n),b])
            sharp=fixtures[name]['sharp'];orig=evaluate(sharp['vertices'],sharp['faces'],planes(fixtures[name]));assert orig['complete']
            base,coords=run(c,V,F,sharp,orig,ring,nb,KEEP)
            assert base['geometry_sha256']==expected[label]['baseline']['geometry_sha256']
            def trial(setting):return run(c,V,F,sharp,orig,ring,nb,setting,coords)[0]
            selected,attempts,status=select(base,'optimize_collar',trial)
            row=dict(name=label,status=status,baseline=base,selected=selected,attempts=attempts,evaluations=1+len(attempts),unknown_plan=plan(base,'unknown'))
            rows.append(row)
            print('PHASE157_ROW',json.dumps(dict(name=label,status=status,evaluations=row['evaluations'],setting=selected['setting'],passed=selected['passed'],ratio=selected['max_edge_ratio'],turn=selected['max_turn'],subd2_ratio=selected['levels'][2]['edge_ratio_all'],fixed_error=selected['fixed_error'])),flush=True)
    finally:unload_extension(module)
    out=dict(complete=True,approved=False,native_executed=True,calibrated=True,independent_holdout=False,controls=ncontrols,rows=rows,elapsed=time.perf_counter()-start)
    (P/'phase157_bounded_selector.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE157_SUMMARY',json.dumps(dict(cases=len(rows),evaluations=sum(r['evaluations'] for r in rows),edits=sum(r['status']=='accepted_edit' for r in rows),passed=sum(r['selected']['passed'] for r in rows),controls=ncontrols,elapsed=out['elapsed'])),flush=True)
    assert len(rows)==4 and all(r['evaluations']<=3 and not r['unknown_plan'] for r in rows)
if __name__=='__main__':main()
