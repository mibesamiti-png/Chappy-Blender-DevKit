"""Phase211-C1: bounded two-axis positive-drive test with no return spring.
Ideal independent inner and outer wall attachments to one physical shaft.
Not a manufacturable closed groove or a free walking mechanism yet.
"""
import json,math,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from phase210_xy_cam import run_case
from phase210_inverse_cam import law
from phase211_groove_profile import wall,CLEARANCE
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    profiles=[dict(kind=k,**wall(k,r,.77)[2]) for k,r in [('stride',7.),('lift',2.5)]]
    cases=[];negative=None
    if all(q['passed'] for q in profiles):
        t=np.arange(36000)*math.tau/36000
        phase=float(t[np.argmin(law(t,'stride',.77))])
        sub=dest/'phase211_groove';sub.mkdir(exist_ok=True)
        cases=[run_case(n,s,e,sub,32,.77,phase,0.,0.,0,True) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
        sub=dest/'phase211_groove_open';sub.mkdir(exist_ok=True)
        negative=run_case('engaged',False,True,sub,32,.77,phase,0.)
    rejected=bool(negative and (not negative['checks']['contact'] or not negative['checks']['axis_tracking']))
    out=dict(complete=True,native_executed=True,approved=False,profile_gate=all(q['passed'] for q in profiles),
        positive_drive_gate=len(cases)==3 and all(c['passed'] for c in cases) and rejected,
        profiles=profiles,cases=cases,open_wall_control=negative,open_wall_rejected=rejected,
        nominal_clearance=CLEARANCE,duty=.77,gravity=[0.,-9.81,0.],spring=False,
        ideal_wall_attachment=True,manufacturable_groove_certified=False,physical_walk_certified=False,
        elapsed=time.perf_counter()-start)
    (dest/'phase211_groove_drive.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    brief=lambda c:{k:v for k,v in c.items() if k!='rows'}
    print('PHASE211C1_SUMMARY',json.dumps({**out,'cases':[brief(c) for c in cases],
        'open_wall_control':brief(negative) if negative else None},allow_nan=False),flush=True)
if __name__=='__main__':main()
