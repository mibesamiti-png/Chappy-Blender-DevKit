"""Phase211-D4: paired no-contact controls isolate passive settling.
Keep D3 geometry, masses, gravity, guides, initial positions and thresholds.
Only motor enable differs between the two separated trials. Raw D3 failures
remain visible; causal isolation is a separate gate, not a D3 pass override.
"""
import json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase211_four_leg_drive import run,PHASES
AXES=[f'L{j}_{kind}_' for j in range(4) for kind in ('stride','lift')]
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results'/'phase211_separated_diagnosis'
    dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for name,enabled in [('driven',True),('undriven',False)]:
        p=dest/name;p.mkdir(exist_ok=True)
        cases.append(run('separated',True,enabled,p,integrated=True))
    a,b=cases;metrics=[]
    for k in AXES:
        ar=a['rows'];br=b['rows']
        diff=lambda name:max(abs(x[k+name]-y[k+name]) for x,y in zip(ar,br))
        span=lambda rows:max(r[k+'output'] for r in rows[120:])-min(r[k+'output'] for r in rows[120:])
        q=dict(axis=k,output_difference=diff('output'),coupling_difference=diff('coupling'),
            max_driven_coupling=max(abs(r[k+'coupling']) for r in ar),
            max_undriven_coupling=max(abs(r[k+'coupling']) for r in br),
            driven_settled_span=span(ar),undriven_settled_span=span(br),
            min_axial=min(r[k+'axial'] for rows in (ar,br) for r in rows),
            driven_first_coupling_violation=next((r['frame'] for r in ar if abs(r[k+'coupling'])>.015),None),
            undriven_first_coupling_violation=next((r['frame'] for r in br if abs(r[k+'coupling'])>.015),None))
        q['passed']=q['output_difference']<=.015 and q['coupling_difference']<=.015 and q['min_axial']>.5
        metrics.append(q)
    checks=dict(driven_full_cycle=a['travel']<=-math.tau,undriven_no_rotation=abs(b['travel'])<=.4,
        paired_outputs=all(q['passed'] for q in metrics),
        shaft_drift=all(c['checks']['shaft_drift'] for c in cases))
    out=dict(complete=True,native_executed=True,approved=False,diagnosis_only=True,
        geometry_changed=False,gravity_changed=False,criteria_changed=False,
        raw_d3_separated_passed=a['passed'],causal_isolation_gate=all(checks.values()),
        checks=checks,metrics=metrics,cases=cases,physical_walk_certified=False,
        elapsed=time.perf_counter()-start)
    (dest/'phase211_separated_diagnosis.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211D4_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='cases'},allow_nan=False),flush=True)
if __name__=='__main__':main()
