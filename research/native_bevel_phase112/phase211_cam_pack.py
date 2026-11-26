"""Phase211-B1: eight indexed cam disks on one transverse shaft.
Actual cam, roller and shaft meshes; sampled envelope/COM checks for this
subassembly only. No connecting rods, guides, chassis or physical motor.
Rear stride outputs require a direction-reversing transmission. The large
diameter and high axis are deliberately retained, not a compact walker.
"""
import json,math,sys,time
from pathlib import Path
import numpy as np
import bpy
from mathutils import Matrix
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase210_inverse_cam import profile,audit,law,ROLLER
from phase206_hybrid_machine import ring,BORE,KEY,key_check
DUTY=.77;HEIGHT=10.;THICK=.24;FRAMES=721
# Order and phase fixed by Phase211-A.
LEGS=[('LF',0,2.4,2.8,0.),('LB',270,3.2,3.6,math.pi),
      ('RF',180,-2.4,-2.8,0.),('RB',90,-3.2,-3.6,math.pi)]
BASE=Matrix.Rotation(math.pi/2,3,'X')
def rotation(a):
    return np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
def centroid(m):
    m.calc_loop_triangles()
    volume=0.;moment=np.zeros(3)
    for t in m.loop_triangles:
        a,b,c=(np.array(m.vertices[i].co) for i in t.vertices)
        v=float(np.dot(a,np.cross(b,c))/6.)
        volume+=v;moment+=v*(a+b+c)/4.
    assert abs(volume)>1e-8
    return abs(volume),moment/volume
def object_of(name,m,y,color):
    ob=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(ob)
    ob.location=(0.,y,HEIGHT);ob.rotation_euler=BASE.to_euler();ob.color=color
    return ob
def lane_gap(lanes):
    return min(abs(a-b)-THICK for i,a in enumerate(lanes) for b in lanes[i+1:])
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    items=[];profiles={}
    for k,r in [('stride',7.),('lift',2.5)]:
        c,a=audit(k,r,duty=DUTY);assert a['passed'];profiles[k]=(c,a)
    for leg,deg,ys,yl,phi in LEGS:
        phase=math.radians(deg)
        for kind,y,axis,r in [('stride',ys,phi,7.),('lift',yl,math.pi/2,2.5)]:
            c=profiles[kind][0]@rotation(axis-phase).T
            m,a=ring(leg+'_'+kind,[tuple(v) for v in c],[tuple(v*BORE/max(abs(v))) for v in c])
            assert a['passed'] and key_check(m)
            ob=object_of(leg+' '+kind+' indexed cam',m,y,(.3,.55,.85,1) if kind=='stride' else (.85,.55,.2,1))
            vol,com=centroid(m)
            # Use equal nominal cam masses as in Phase210, not equal density.
            er=np.array([math.cos(axis),math.sin(axis)])
            pos=er*(r+float(law(phase,kind,DUTY)))
            bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=ROLLER,depth=THICK,location=(pos[0],y,HEIGHT+pos[1]))
            roller=bpy.context.object;roller.name=leg+' '+kind+' roller';roller.rotation_euler=BASE.to_euler();roller.color=(.2,.8,.4,1)
            items.append(dict(leg=leg,kind=kind,y=y,phase=phase,axis=axis,r=r,c=c,
                volume=vol,com=com,cam=ob,roller=roller))
    bpy.ops.mesh.primitive_cube_add(size=1.,location=(0.,0.,HEIGHT))
    shaft=bpy.context.object;shaft.name='common square shaft';shaft.dimensions=(2*KEY,8.,2*KEY)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);shaft.color=(.5,.5,.55,1)
    lanes=[it['y'] for it in items];axial=lane_gap(lanes)
    radius=max(float(np.linalg.norm(it['c'],axis=1).max()) for it in items)
    # Circumscribed swept disk bound is valid at every rotation.
    floor=HEIGHT-radius
    bore_clear=BORE-KEY
    t=np.arange(FRAMES)*math.tau/(FRAMES-1)
    mass=8*(3.+.25)+.2
    rows=[];min_roller_floor=float('inf');min_roller_shaft=float('inf')
    for f,theta in enumerate(t):
        moment=np.zeros(3);cam_moment=np.zeros(3)
        for it in items:
            c=rotation(-theta)@it['com'][:2]
            cm=np.array([c[0],it['y']-it['com'][2],c[1]+HEIGHT])
            pos=(it['r']+float(law(theta+it['phase'],it['kind'],DUTY)))*np.array([math.cos(it['axis']),math.sin(it['axis'])])
            rm=np.array([pos[0],it['y'],HEIGHT+pos[1]])
            cam_moment+=3.*cm;moment+=3.*cm+.25*rm
            min_roller_floor=min(min_roller_floor,float(rm[2]-ROLLER))
            min_roller_shaft=min(min_roller_shaft,float(np.linalg.norm(pos)-ROLLER-math.sqrt(2)*KEY))
        moment+=.2*np.array([0.,0.,HEIGHT])
        cm=moment/mass;cc=cam_moment/24.
        rows.append(dict(frame=f,angle=float(theta),com=cm.tolist(),cam_com=cc.tolist()))
    max_xy=max(math.hypot(r['com'][0],r['com'][1]) for r in rows)
    max_cam_xy=max(math.hypot(r['cam_com'][0],r['cam_com'][1]) for r in rows)
    controls=dict(overlapping_lane=lane_gap([lanes[0],lanes[0]]+lanes[2:])<0,
        oversize_key=BORE-(BORE+.01)<0,low_axis=(radius-.01)-radius<0)
    checks=dict(axial_separation=axial>=.1,cam_floor_clearance=floor>=.2,
        roller_floor_clearance=min_roller_floor>=.2,roller_shaft_clearance=min_roller_shaft>=.1,
        key_clearance=bore_clear>0,shaft_reach=max(abs(y)+THICK/2 for y in lanes)<4.,
        subassembly_com_xy=max_xy<=.1,cam_com_xy=max_cam_xy<=.01)
    out=dict(complete=True,native_executed=True,approved=False,pack_gate=all(checks.values()) and all(controls.values()),
        checks=checks,controls=controls,cam_count=8,roller_count=8,shaft_count=1,
        duty=DUTY,phases=[x[1] for x in LEGS],lanes=lanes,cam_thickness=THICK,
        axis_height=HEIGHT,max_cam_radius=radius,min_axial_gap=axial,min_cam_floor=floor,
        min_roller_floor=min_roller_floor,min_roller_shaft=min_roller_shaft,key_clearance=bore_clear,
        cam_volumes=[it['volume'] for it in items],nominal_mass=mass,max_subassembly_com_xy=max_xy,
        max_cam_com_xy=max_cam_xy,com_z_range=[min(r['com'][2] for r in rows),max(r['com'][2] for r in rows)],
        rows=rows,transmission_certified=False,whole_machine_com_certified=False,physical_walk_certified=False,
        elapsed=time.perf_counter()-start)
    (dest/'phase211_cam_pack.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase211_cam_pack.blend'))
    print('PHASE211B1_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'},allow_nan=False),flush=True)
if __name__=='__main__':main()
