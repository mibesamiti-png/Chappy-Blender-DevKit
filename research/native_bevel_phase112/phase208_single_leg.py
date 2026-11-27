"""Phase 208-B: a passive four-bar leg driven by actual tooth contact.
Frozen Phase207 dimensions; ideal bearings/pins, rigid gear-crank coupling.
No prescribed angles, animation, gravity, floor, or physical pin retention.
Compare evaluated Bullet transforms with analytic geometry using measured
crank angle, never the target motor angle. Negative controls are independent.
"""
import math,json,time,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase208_motor_contact import setup,body,constraint
from phase207_walking_machine import motion
from phase204_four_bar import make_link_attempt,prism,LINK_R,HOLE_R,THICK
from phase206_hybrid_machine import capsule,square,cut,closed,area_circle,bore_check,key_check,retry
from phase195_tapered_spacer import drill,basis
Z=(0.6929126433990895,1.495141205001622,2.1626974924188103,1.4865368241155517,3.298077477756888,-1.0078676866004241)
START=1.4660765716752369
FRAMES=601
def hull(pts):
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    def half(p):
        H=[]
        for q in p:
            while len(H)>1 and cross(H[-2],H[-1],q)<=1e-12:H.pop()
            H.append(q)
        return H
    p=sorted(set(pts));return half(p)[:-1]+half(p[::-1])[:-1]
def drilled(name,outline,holes,shift,reverse=False,key=False):
    from phase160_operation_contracts import measure
    M=prism(name,[(x-shift,y) for x,y in outline],-THICK/2,THICK/2)
    base=measure(M,'cube');stages=[]
    for x,y in (list(reversed(holes)) if reverse else holes):
        out=drill(M,np.array([x-shift,y,0.]),basis((0,0,1)),.4,HOLE_R)
        bpy.data.meshes.remove(M);M=out;stages.append(measure(M,'cube'))
    if key:
        out=cut(M,prism('key',[(x-shift,y) for x,y in square(.094)],-.3,.3));bpy.data.meshes.remove(M);M=out;stages.append(measure(M,'cube'))
    for w in M.vertices:w.co.x+=shift
    M.update();a=closed(M,len(holes)+int(key),base['volume']-(len(holes)*area_circle(HOLE_R)+int(key)*4*.094**2)*THICK)
    a['passed'] &= base['clean'] and all(s['clean'] for s in stages) and all(bore_check(M,x,y) for x,y in holes) and (not key or key_check(M))
    return M,a
def setup_leg(distance,enabled):
    scene,gears=setup(distance,enabled)
    scene.frame_end=FRAMES;scene.rigidbody_world.point_cache.frame_end=FRAMES
    anchor=bpy.data.objects['fixed bearing reference'];r,d,l,m,u,v=Z
    B,C,F=motion(Z,START)
    outline=hull([(x+LINK_R*math.cos(i*math.tau/32),y+LINK_R*math.sin(i*math.tau/32)) for x,y in ((0.,0.),(l,0.),(u,v)) for i in range(32)])
    meshes=[
        retry('crank',[lambda s=s:drilled('crank',capsule(0.,r),[(r,0.)],s,key=True) for s in (r/2,0.,.13)]),
        retry('rocker',[lambda mode=mode:make_link_attempt('rocker',m,mode) for mode in ('centered','baseline','reversed')]),
        retry('foot',[lambda s=s,o=o:drilled('foot',outline,[(0.,0.),(l,0.)],s,o) for s,o in ((l/2,False),(0.,True),(.37,True))])]
    assert all(a['passed'] for _,a in meshes)
    legs=[]
    for name,(M,a),p,ang,h,mass in zip(('crank','rocker','foot'),meshes,((0.,0.),(d,0.),B),(START,math.atan2(C[1],C[0]-d),math.atan2(C[1]-B[1],C[0]-B[0])),(.32,.32,.64),(.2,.25,.4)):
        ob=bpy.data.objects.new(name,M);bpy.context.collection.objects.link(ob)
        ob.location=(distance+float(p[0]),float(p[1]),h);ob.rotation_euler.z=ang
        ob.color=(.2,.65,.45,1);body(ob);ob.rigid_body.mass=mass;legs.append(ob)
    crank,rocker,foot=legs
    constraint('rigid output to crank','FIXED',gears[1],crank,(distance,0.,.16))
    constraint('rocker pivot','HINGE',anchor,rocker,(distance+d,0.,.32))
    constraint('crank foot pin','HINGE',crank,foot,(distance+float(B[0]),float(B[1]),.48))
    constraint('rocker foot pin','HINGE',rocker,foot,(distance+float(C[0]),float(C[1]),.48))
    scene.rigidbody_world.substeps_per_frame=12;scene.rigidbody_world.solver_iterations=80
    bpy.context.view_layer.update();scene.frame_set(1)
    cs=[o.rigid_body_constraint for o in scene.objects if o.rigid_body_constraint]
    assert len(cs)==7 and sum(c.type=='MOTOR' and c.use_motor_ang for c in cs)==int(enabled)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in gears+legs)
    return scene,gears+legs
def run_case(name,distance,enabled,dest):
    scene,obs=setup_leg(distance,enabled);r,d,l,m,u,v=Z
    if name=='engaged':
        bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase208_single_leg.blend'))
    rows=[];last=None;travel=[0.]*5
    def xy(M,x,y=0.):return np.array(tuple(M@Vector((x,y,0.)))[:2])
    O=np.array([distance,0.]);initial=None
    for frame in range(1,FRAMES+1):
        scene.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
        M=[o.evaluated_get(dg).matrix_world.copy() for o in obs]
        angles=[math.atan2(q[1][0],q[0][0]) for q in M]
        if last is not None:
            for i in range(5):travel[i]+=math.atan2(math.sin(angles[i]-last[i]),math.cos(angles[i]-last[i]))
        last=angles
        B,C,F=motion(Z,angles[2]);P=xy(M[4],u,v)-O
        joint=max(float(np.linalg.norm(xy(M[2],r)-xy(M[4],0.))),float(np.linalg.norm(xy(M[3],m)-xy(M[4],l))),float(np.linalg.norm(xy(M[2],0.)-O)),float(np.linalg.norm(xy(M[3],0.)-(O+[d,0.]))))
        err=float(np.linalg.norm(P-F))
        if initial is None:initial=P.copy()
        rows.append(dict(frame=frame,input=travel[0],output=travel[1],crank=travel[2],foot=P.tolist(),expected=F.tolist(),foot_error=err,joint_error=joint,coupling_error=abs(travel[1]-travel[2]),foot_displacement=float(np.linalg.norm(P-initial))))
    a,b,c=travel[:3];ratio=b/a if abs(a)>1e-8 else None
    max_foot=max(q['foot_error'] for q in rows);max_joint=max(q['joint_error'] for q in rows)
    max_coupling=max(q['coupling_error'] for q in rows);max_move=max(q['foot_displacement'] for q in rows)
    phase_error=max(abs(q['input']+q['output']) for q in rows)
    if name=='engaged':
        passed=abs(a)>=6.3 and abs(c)>=6.3 and ratio is not None and -1.05<=ratio<=-.95 and phase_error<=.20 and max_foot<=.08 and max_joint<=.025 and max_coupling<=.025 and max_move>=2.
    elif name=='separated':
        passed=abs(a)>=6.3 and abs(b)<.03 and abs(c)<.03 and max_move<.08
    else:
        passed=max(abs(a),abs(b),abs(c))<.03 and max_move<.08
    result=dict(name=name,input=a,output=b,crank=c,ratio=ratio,max_phase_error=phase_error,max_foot_error=max_foot,max_joint_error=max_joint,max_coupling_error=max_coupling,max_foot_displacement=max_move,passed=bool(passed),rows=rows)
    print('PHASE208B_CASE',json.dumps({k:v for k,v in result.items() if k!='rows'},allow_nan=False),flush=True)
    return result
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run_case(n,d,e,dest) for n,d,e in [('engaged',2.4,True),('separated',3.,True),('motor_off',2.4,False)]]
    gate=all(c['passed'] for c in cases)
    result=dict(complete=True,native_executed=True,approved=False,gate=gate,dimensions=Z,cases=cases,ideal_pins=True,gravity=False,physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase208_single_leg.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print('PHASE208B_SUMMARY',json.dumps(dict(gate=gate,passed=sum(c['passed'] for c in cases),count=len(cases),elapsed=result['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
