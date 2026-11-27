"""Phase210-C1: stride cam under contact drive, isolated from lift.
Same fixture and gravity return as 210-B. Start at the analytic minimum of
the periodic displacement so motor-off does not intentionally backdrive.
Not a horizontal gravity-return actuator or a combined leg demonstration.
"""
import json,math,time,sys
from pathlib import Path
import numpy as np
import bpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase210_cam_contact import setup,FPS,FRAMES
from phase210_inverse_cam import law,ROLLER
BASE=7.
# On the return segment, derivative .8-96*q^2*(1-q)^2 vanishes.
Q=(1+math.sqrt(1-4*math.sqrt(.8/96)))/2
START=math.tau*(.75+.25*Q)
MIN=float(law(START,'stride'))
MAX=float(law(math.tau*(.75+.25*(1-Q)),'stride'))
SPAN=MAX-MIN
def run_case(name,offset,enabled,dest,impulse=10.):
    sc,cam,roller,c=setup(offset,enabled,'stride',BASE,START,3.,impulse)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/('phase210_stride_'+name+'.blend')))
    edge=np.roll(c,-1,axis=0)-c;den=np.sum(edge*edge,axis=1)
    rows=[];last=None;travel=0.
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        A=cam.evaluated_get(dg).matrix_world.copy();B=roller.evaluated_get(dg).matrix_world.copy()
        angle=math.atan2(A[1][0],A[0][0])
        if last is not None:travel+=math.atan2(math.sin(angle-last),math.cos(angle-last))
        last=angle
        local=A.inverted()@B.translation;p=np.array((local.x,local.y))
        delta=p-c;t=np.clip(np.sum(delta*edge,axis=1)/den,0.,1.)
        gap=float(np.linalg.norm(delta-t[:,None]*edge,axis=1).min()-ROLLER)
        phase=(START-travel)%math.tau;expected=float(law(phase,'stride'));actual=float(B.translation.x-BASE)
        rows.append(dict(frame=f,angle=travel,phase=phase,expected=expected,actual=actual,
            error=actual-expected,radial_gap=gap,axial_separation=abs(local.z),
            guide_drift=math.hypot(B.translation.y,B.translation.z-offset),cam_drift=A.translation.length))
    actual=[r['actual'] for r in rows];amp=max(actual)-min(actual)
    maxerr=max(abs(r['error']) for r in rows);drift=max(max(r['guide_drift'],r['cam_drift']) for r in rows)
    gapmax=max(abs(r['radial_gap']) for r in rows)
    stance=[(a,b) for a,b in zip(rows,rows[1:]) if a['phase']<=.75*math.tau and b['phase']<=.75*math.tau and b['phase']>=a['phase']]
    max_step_error=max((abs((b['actual']-a['actual'])-(b['expected']-a['expected'])) for a,b in stance),default=0.)
    stance_reverse=sum(max(0.,a['actual']-b['actual']) for a,b in stance)
    checks=dict(guide_and_bearing=drift<=.015)
    if name=='engaged':
        checks.update(full_cycle=travel<=-math.tau,stroke=abs(amp-SPAN)<=.05,tracking=maxerr<=.025,
            stance_increment=max_step_error<=.025,stance_reverse=stance_reverse<=.05,
            contact_gap=gapmax<=.025,axial_overlap=max(r['axial_separation'] for r in rows)<.05)
    elif name=='separated':
        checks.update(full_cycle=travel<=-math.tau,no_positive_lift=max(actual)<=MIN+.025,
            no_periodic_lift=max(actual[60:])-min(actual[60:])<=.025,
            axial_clearance=min(r['axial_separation'] for r in rows)>.5)
    else:
        # At a cam minimum, small settling rotation is permitted; no
        # external brake or position constraint is added to force it.
        checks.update(no_sustained_drive=abs(travel)<=.15,no_stroke=amp<=.025)
    out=dict(name=name,enabled=enabled,offset=offset,impulse=impulse,travel=travel,amplitude=amp,
        max_tracking_error=maxerr,max_radial_gap=gapmax,max_drift=drift,
        max_stance_step_error=max_step_error,stance_reverse=stance_reverse,stance_steps=len(stance),
        min_displacement=min(actual),max_displacement=max(actual),checks=checks,passed=all(checks.values()),rows=rows)
    print('PHASE210C1_CASE',json.dumps({k:v for k,v in out.items() if k!='rows'},allow_nan=False),flush=True)
    return out
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run_case(n,z,e,dest) for n,z,e in [('engaged',0.,True),('separated',1.,True),('motor_off',0.,False)]]
    out=dict(complete=True,native_executed=True,approved=False,physical_gate=all(c['passed'] for c in cases),
        nominal_stride=2.4,expected_min=MIN,expected_max=MAX,expected_span=SPAN,start_phase=START,
        cases=cases,ideal_guides=True,gravity_return=True,combined_motion_certified=False,walking_certified=False,
        elapsed=time.perf_counter()-start)
    (dest/'phase210_stride_contact.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE210C1_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='cases'},allow_nan=False),flush=True)
if __name__=='__main__':main()
