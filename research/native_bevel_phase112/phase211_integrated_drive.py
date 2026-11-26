"""Phase211-D3: remove eight numerically unstable cam-to-shaft joints.
Same physical cam surfaces and total mass, one dynamic mesh instead of nine.
The cam phase is now a structural identity, not independent joint evidence.
"""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase211_four_leg_drive import run,PHASES,DUTY,IMPULSE
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results'/'phase211_integrated';dest.mkdir(parents=True,exist_ok=True)
    cases=[run(n,s,e,dest,integrated=True) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
    out=dict(complete=True,native_executed=True,approved=False,integrated_drive_gate=all(c['passed'] for c in cases),
        cases=cases,phases=PHASES,duty=DUTY,cam_count=8,active_bodies=21,constraint_count=30,
        removed_fixed_joints=8,motor_count=1,impulse=IMPULSE,camshaft_mass=28.8,
        identical_cam_surfaces=True,structural_phase_identity=True,ideal_rigid_assembly=True,
        welded_solid_certified=False,fixed_fixture=True,physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_integrated_drive.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211D3_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='cases'},allow_nan=False),flush=True)
if __name__=='__main__':main()
