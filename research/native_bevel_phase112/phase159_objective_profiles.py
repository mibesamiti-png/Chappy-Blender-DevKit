"""Research only: replay measured Phase 158 candidates under explicit objective profiles.
No additional geometry operations, no tuning of Phase 157, no production adoption.
"""
import json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
P=ROOT/'results'
PROFILES=('sufficient','spacing','balanced','preserve','unknown')
SPACE=('space','axial','cubic',100,1)
RELAX=('relax','axial','cubic',100,3)
def eligible(base,candidate,profile):
    if not candidate['passed']:return False
    if not base['passed']:return True
    if candidate['max_edge_ratio']>.95*base['max_edge_ratio']:return False
    if any(a['edge_ratio_all']>b['edge_ratio_all']+1e-6 for a,b in zip(candidate['levels'][1:],base['levels'][1:])):return False
    if profile=='balanced':
        if candidate['max_turn']>base['max_turn']+2.:return False
        if candidate['extent_upper']>base['extent_upper']+.01:return False
    return True
def choose(base,options,profile):
    if profile in ('preserve','unknown') or (profile=='sufficient' and base['passed']):
        return base,1
    order=(RELAX,SPACE) if not base['passed'] and (base['max_turn'] is None or base['max_turn']>30) else (SPACE,RELAX)
    attempts=1
    for k in order:
        attempts+=1
        candidate=options[k]
        if eligible(base,candidate,profile):return candidate,attempts
    return base,attempts
def controls():
    base=dict(passed=True,max_turn=20.,extent_upper=.30,max_edge_ratio=40.,levels=[dict(edge_ratio_all=40.)]*3)
    good=dict(base,max_turn=21.,max_edge_ratio=20.,levels=[dict(edge_ratio_all=20.)]*3)
    turn=dict(good,max_turn=26.)
    extent=dict(good,extent_upper=.32)
    bad=dict(good,passed=False)
    minor=dict(good,max_edge_ratio=39.)
    subd=dict(good,levels=[dict(edge_ratio_all=41.)]*3)
    assert eligible(base,good,'balanced')
    assert eligible(base,turn,'spacing') and not eligible(base,turn,'balanced')
    assert eligible(base,extent,'spacing') and not eligible(base,extent,'balanced')
    assert not eligible(base,bad,'spacing')
    assert not eligible(base,minor,'spacing')
    assert not eligible(base,subd,'spacing')
    opts={SPACE:turn,RELAX:good}
    assert choose(base,opts,'balanced')==(good,3)
    assert choose(base,opts,'spacing')==(turn,2)
    for p in ('sufficient','unknown','preserve'):assert choose(base,{},p)==(base,1)
    return 11
def main():
    start=time.perf_counter();n=controls()
    src=json.loads((P/'phase158_selector_holdout.json').read_text())
    assert src['complete'] and src['native_executed'] and not src['approved'] and not src['selector_tuned']
    assert len(src['rows'])==9
    rows=[]
    for r in src['rows']:
        b=r['baseline'];opts={tuple(x['setting']):x for x in r['options']}
        assert set(opts)=={SPACE,RELAX}
        profiles={}
        for p in PROFILES:
            v,e=choose(b,opts,p)
            edited=v is not b
            assert not edited or eligible(b,v,p)
            z=dict(edited=edited,evaluations=e,passed=v['passed'],setting=v['setting'],
                ratio=v['max_edge_ratio'],ratio_reduction=1-v['max_edge_ratio']/b['max_edge_ratio'],
                turn_delta=v['max_turn']-b['max_turn'],extent_delta=v['extent_upper']-b['extent_upper'],
                fixed_error=v['fixed_error'],subd2_ratio=v['levels'][2]['edge_ratio_all'])
            profiles[p]=z
        row=dict(name=r['name'],variant=r['variant'],original_selector=r['status'],profiles=profiles)
        rows.append(row)
        print('PHASE159_ROW',json.dumps(row,allow_nan=False),flush=True)
    summary={}
    for p in PROFILES:
        z=[r['profiles'][p] for r in rows];edits=[v for v in z if v['edited']]
        summary[p]=dict(edits=len(edits),passed=sum(v['passed'] for v in z),evaluations=sum(v['evaluations'] for v in z),
            mean_ratio_reduction=sum(v['ratio_reduction'] for v in z)/len(z),max_turn_increase=max(v['turn_delta'] for v in z),
            max_extent_increase=max(v['extent_delta'] for v in z),fixed_error=max(v['fixed_error'] for v in z))
    assert all(summary[p]['edits']==0 and summary[p]['evaluations']==9 for p in ('preserve','unknown','sufficient'))
    out=dict(complete=True,approved=False,replay_only=True,native_source=True,independent_holdout=False,controls=n,
        experimental_thresholds=dict(min_ratio_reduction=.05,balanced_max_turn_increase_deg=2.,balanced_max_extent_increase=.01),
        rows=rows,summary=summary,elapsed=time.perf_counter()-start)
    (P/'phase159_objective_profiles.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE159_SUMMARY',json.dumps(dict(summary=summary,controls=n,elapsed=out['elapsed']),allow_nan=False),flush=True)
if __name__=='__main__':main()
