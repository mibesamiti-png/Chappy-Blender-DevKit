"""Phase211-C2: connected groove solid in the same motor-only XY fixture."""
import json,math,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from phase210_xy_cam import run_case
from phase210_inverse_cam import law
from phase211_backed_groove import backed_mesh,FLOOR,BACK,TOP
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry=[]
    for k,r,phi,side in [('stride',7.,0.,1.),('lift',2.5,math.pi/2,-1.)]:
        rot=np.array([[math.cos(phi),-math.sin(phi)],[math.sin(phi),math.cos(phi)]])
        m,a,_,_=backed_mesh(k,r,.77,rot,side)
        geometry.append(dict(kind=k,passed=a['passed'],key=a['key'],expected_volume=a['expected_volume'],metrics=a['audit']['metrics']))
        bpy.data.meshes.remove(m)
    cases=[]
    if all(q['passed'] for q in geometry):
        t=np.arange(36000)*math.tau/36000
        phase=float(t[np.argmin(law(t,'stride',.77))])
        sub=dest/'phase211_backed';sub.mkdir(exist_ok=True)
        cases=[run_case(n,s,e,sub,32,.77,phase,0.,0.,0,True,True) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
    out=dict(complete=True,native_executed=True,approved=False,geometry_gate=all(q['passed'] for q in geometry),
        backed_drive_gate=len(cases)==3 and all(c['passed'] for c in cases),
        geometry=geometry,cases=cases,nominal_axial_gap=FLOOR-.12,backing_thickness=BACK-FLOOR,
        wall_height=TOP+FLOOR,cam_mass=3.5,duty=.77,gravity=[0.,-9.81,0.],spring=False,
        independent_wall_constraint=False,ideal_shaft_coupling=True,manufacturing_certified=False,
        physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_backed_drive.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211C2_SUMMARY',json.dumps({**out,'cases':[{**{k:v for k,v in c.items() if k!='rows'},
        'min_back_gap':{k:min(r[k+'_back_gap'] for r in c['rows']) for k in ('stride','lift')}} for c in cases]},allow_nan=False),flush=True)
if __name__=='__main__':main()
