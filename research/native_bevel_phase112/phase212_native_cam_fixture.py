"""Native Phase212-D fixtures. Save geometry only, not a simulated machine."""
import sys,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase212_motion_spec import Knot,Track
from phase212_radial_cam import CamConfig
from phase212_cam_part import build
from phase195_tapered_spacer import write_obj
def main():
    assert bpy.app.version_string=='4.4.3'
    dest=ROOT/'results'/'phase212_cam_part';dest.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    duty=.77;v=2.4/duty
    stride=Track('stride','model_unit',(Knot(0,0,v),Knot(duty,2.4,v),Knot(1,0,v)))
    dwell=Track('dwell','model_unit',(Knot(0,0),Knot(1,0)))
    fixtures=[(stride,CamConfig(7.,.25,.5,samples=360),.6,.8,.5),
        (dwell,CamConfig(3.,.25,.5,samples=360),1.2,.6,.5)]
    reports=[]
    for i,(t,c,h,b,w) in enumerate(fixtures):
        m,r=build(t,c,h,b,w);reports.append(r)
        print('PHASE212D_PART',json.dumps(r,allow_nan=False),flush=True)
        if m is not None:
            ob=bpy.data.objects.new(t.name,m);bpy.context.collection.objects.link(ob)
            ob.location.x=i*16.;write_obj(m,dest/(t.name+'.obj'))
    before=len(bpy.data.meshes)
    m,bad=build(dwell,fixtures[1][1],1.2,2.5,.5)
    m2,bad2=build(stride,CamConfig(2.,.25,.5,samples=360),.6,.8,.5)
    controls=dict(wall_rejected=m is None and bad['reason']=='wall',
        geometry_rejected=m2 is None and bad2['reason']=='profile_gate',
        no_failed_mesh_leak=len(bpy.data.meshes)==before)
    gate=all(r['status']=='pass' for r in reports) and all(controls.values())
    out=dict(complete=True,native_executed=True,gate=gate,parts=reports,controls=controls,
        physical_contact_certified=False,assembly_certified=False,manufacturing_certified=False)
    (dest/'report.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    if gate:bpy.ops.wm.save_as_mainfile(filepath=str(dest/'cam_parts.blend'))
    print('PHASE212D_SUMMARY',json.dumps(dict(gate=gate,controls=controls,parts=[dict(status=r['status'],checks=r.get('checks')) for r in reports])),flush=True)
    assert gate
if __name__=='__main__':main()
