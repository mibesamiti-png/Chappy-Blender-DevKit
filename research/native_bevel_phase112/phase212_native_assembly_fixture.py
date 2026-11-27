"""Native two-track assembly fixture with deliberate failures."""
import json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase212_motion_spec import Knot,Track,MotionSpec
from phase212_radial_cam import CamConfig
from phase212_cam_assembly import Station,assemble,verify,observe
def main():
    assert bpy.app.version_string=='4.4.3'
    dest=ROOT/'results'/'phase212_cam_assembly';dest.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    t1=Track('stroke','model_unit',(Knot(0,0),Knot(.25,0),Knot(.5,1),Knot(.75,1),Knot(1,0)))
    t2=Track('secondary','model_unit',(Knot(0,0),Knot(.5,.6),Knot(1,0)),phase_offset=.25)
    spec=MotionSpec((t1,t2),4.)
    stations=(Station('stroke',CamConfig(7.,.25,.5,samples=360),.6,.8,.5,.4),
        Station('secondary',CamConfig(3.,.25,.5,samples=360),.8,.8,.5,.5,math.pi/2))
    a=assemble(spec,stations,.6,.3,.4)
    def phase_fault(a,u):a['stations'][1]['cam'].rotation_euler.z+=.2
    def axial_fault(a,u):a['stations'][1]['roller'].location.z+=.4
    bad=verify(a,17,mutation=phase_fault)
    bad2=verify(a,17,mutation=axial_fault)
    before=(len(bpy.data.objects),len(bpy.data.meshes))
    rejected=False
    try:assemble(spec,stations,.81,.3,.4)
    except ValueError:rejected=True
    controls=dict(phase_rejected=bad['evaluation']['metrics']['secondary:sync']['status']=='fail',
        axial_rejected=bad2['evaluation']['metrics']['secondary:axial_error']['status']=='fail',
        oversize_shaft_rejected=rejected,no_failed_objects=(len(bpy.data.objects),len(bpy.data.meshes))==before)
    r=verify(a,241,animate=True)
    sc=bpy.context.scene;sc.render.fps=60
    replay=[]
    for i in (1,31,61,91,121,151,181,211,241):
        sc.frame_set(i);rows,gap=observe(a,(i-1)/240)
        replay.append(dict(frame=i,rows=rows,gap=gap))
    replay_pass=all(abs(v['contact_gap'])<=.002 and v['tracking']<=1e-5 and v['sync']<=1e-5 and v['axial_error']<=1e-5
        for f in replay for v in f['rows']) and all(f['gap']>=.3-1e-5 for f in replay)
    gate=r['evaluation']['status']=='pass' and all(controls.values()) and replay_pass
    out=dict(complete=True,native_executed=True,gate=gate,assembly=r,controls=controls,
        replay_pass=replay_pass,replay=replay,spec=spec.to_dict(),objects=[o.name for o in a['objects']],
        station_z=[v['z'] for v in a['stations']],physical_motion_certified=False,torque_transfer_certified=False,
        manufacturing_certified=False,ideal_shared_rotation=True)
    (dest/'report.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    sc.frame_set(1)
    if gate:bpy.ops.wm.save_as_mainfile(filepath=str(dest/'cam_stack.blend'))
    print('PHASE212E_SUMMARY',json.dumps(dict(gate=gate,controls=controls,replay_pass=replay_pass,
        metrics=r['evaluation']['metrics'],objects=out['objects']),allow_nan=False),flush=True)
    assert gate
if __name__=='__main__':main()
