"""Phase 208-C: three actual contact gears and four passive legs.
Fixed ideal bearing reference; ideal pin and gear/crank fixed constraints.
One motor on central gear, no gravity/floor, no animation or ratio constraint.
Frozen Phase207 geometry; no claim of physical shafts or free walking.
"""
import math,json,time,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase208_motor_contact import body,constraint
from phase208_single_leg import Z,START,hull,drilled
from phase207_walking_machine import motion
from phase204_four_bar import make_link_attempt,LINK_R
from phase206_hybrid_machine import gear,capsule,retry
FRAMES=601
def setup_case(separated,enabled,free=False,friction=.8,center_y=1.75):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.gravity=(0,0,0);scene.render.fps=60
    scene.frame_start=1;scene.frame_end=FRAMES
    # Local XY is the mechanism plane, local +Y is up in the free experiment.
    # The body is an explicit ideal rigid chassis surrogate, not a manufactured frame.
    R=Matrix.Rotation(math.pi/2,3,'X')
    if free:
        assert not separated
        scene.gravity=(0,0,-9.81)
        low=min(float(p[1]) for t in (START,START+math.pi) for p in motion(Z,t))
        H=max(1.4,-low+LINK_R+.03)
        def loc(p):return R@Vector(p)+Vector((0,0,H))
        def rot(a):return (R@Euler(a).to_matrix()).to_euler()
        bpy.ops.mesh.primitive_cube_add(size=1.,location=loc((0,center_y,0)))
        anchor=bpy.context.object;anchor.rotation_euler=rot((0,0,0));anchor.scale=(6.4,.32,1.)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        body(anchor);anchor.rigid_body.collision_shape='BOX';anchor.rigid_body.mass=3.
        anchor.rigid_body.friction=friction;anchor.name='free chassis'
    else:
        def loc(p):return p
        def rot(a):return a
        bpy.ops.mesh.primitive_cube_add(size=.5,location=(0,0,-5))
        anchor=body(bpy.context.object,True);anchor.name='ideal fixed frame'
        anchor.hide_render=True
    def joint(name,kind,a,b,p,rotation=(0.,0.,0.)):
        return constraint(name,kind,a,b,loc(p),rot(rotation))
    world_location=loc
    def obj(name,M,loc,ang,mass,color):
        ob=bpy.data.objects.new(name,M);bpy.context.collection.objects.link(ob)
        ob.location=world_location(loc);ob.rotation_euler=rot((0.,0.,ang));ob.color=color
        body(ob);ob.rigid_body.mass=mass
        if free:ob.rigid_body.friction=friction
        return ob
    gears=[]
    for j,x in enumerate((-2.4,0.,2.4)):
        M,a=gear(24);assert a['passed']
        y=4. if separated and j==1 else 0.
        ob=obj('gear_'+str(j),M,(x,y,0),START if j!=1 else math.pi/24-START,1.,(.8,.55,.15,1))
        joint('bearing_'+str(j),'HINGE',anchor,ob,(x,y,0))
        gears.append(ob)
    motor=joint('sole motor','MOTOR',anchor,gears[1],(0.,4. if separated else 0.,0.),(0,-math.pi/2,0))
    motor.use_motor_lin=False;motor.use_motor_ang=enabled
    motor.motor_ang_target_velocity=1.;motor.motor_ang_max_impulse=2. if not free else 20.
    r,d,l,m,u,v=Z
    outline=hull([(x+LINK_R*math.cos(i*math.tau/32),y+LINK_R*math.sin(i*math.tau/32)) for x,y in ((0.,0.),(l,0.),(u,v)) for i in range(32)])
    legs=[]
    for side in (-1,1):
        for end,j in (('F',0),('B',2)):
            name=('L' if side<0 else 'R')+end
            x=(-2.4,0.,2.4)[j]
            phase=math.pi if (side<0)==(end=='F') else 0.
            t=START+phase;B,C,F=motion(Z,t)
            meshes=[
                retry('crank',[lambda s=s:drilled('crank',capsule(0.,r),[(r,0.)],s,key=True) for s in (r/2,0.,.13)]),
                retry('rocker',[lambda mode=mode:make_link_attempt('rocker',m,mode) for mode in ('centered','baseline','reversed')]),
                retry('foot',[lambda s=s,o=o:drilled('foot',outline,[(0.,0.),(l,0.)],s,o) for s,o in ((l/2,False),(0.,True),(.37,True))])]
            assert all(a['passed'] for _,a in meshes)
            obs=[]
            for n,(M,a),p,ang,h,mass in zip(('crank','rocker','foot'),meshes,((0.,0.),(d,0.),B),(t,math.atan2(C[1],C[0]-d),math.atan2(C[1]-B[1],C[0]-B[0])),(1.07,1.07,1.39),(.2,.25,.4)):
                obs.append(obj(name+'_'+n,M,(x+float(p[0]),float(p[1]),side*h),ang,mass,(.2,.65,.45,1) if n=='foot' else (.3,.45,.7,1)))
            crank,rocker,foot=obs
            joint(name+' fixed drive','FIXED',gears[j],crank,(x,0,side*.5))
            joint(name+' rocker pivot','HINGE',anchor,rocker,(x+d,0,side*1.07))
            joint(name+' crank pin','HINGE',crank,foot,(x+float(B[0]),float(B[1]),side*1.23))
            joint(name+' rocker pin','HINGE',rocker,foot,(x+float(C[0]),float(C[1]),side*1.23))
            legs.append(dict(name=name,side=side,gear=j,x=x,phase=phase,obs=obs))
    if free:
        bpy.ops.mesh.primitive_cube_add(size=1.,location=(0,0,-.25))
        floor=bpy.context.object;floor.name='floor';floor.scale=(100.,100.,.5)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        body(floor,True);floor.rigid_body.friction=friction;floor.color=(.5,.5,.5,1)
        assert anchor.rigid_body.type=='ACTIVE' and not anchor.rigid_body.kinematic
    world=scene.rigidbody_world;world.substeps_per_frame=12;world.solver_iterations=80
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();scene.frame_set(1)
    cs=[ob.rigid_body_constraint for ob in scene.objects if ob.rigid_body_constraint]
    moving=gears+[ob for leg in legs for ob in leg['obs']]
    assert len(cs)==20 and sum(c.type=='MOTOR' and c.use_motor_ang for c in cs)==int(enabled)
    assert len(moving)==15 and all(ob.animation_data is None and not ob.rigid_body.kinematic for ob in moving)
    return scene,gears,legs
def wrap(a):return math.atan2(math.sin(a),math.cos(a))
def run_case(name,separated,enabled,dest):
    scene,gears,legs=setup_case(separated,enabled)
    if name=='engaged':bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase208_four_legs.blend'))
    obs=gears+[ob for leg in legs for ob in leg['obs']]
    r,d,l,m,u,v=Z;last=None;travel=[0.]*len(obs);rows=[];initial={}
    def xyz(M,x=0.,y=0.):return np.array(tuple(M@Vector((x,y,0.))))
    for frame in range(1,FRAMES+1):
        scene.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
        M=[ob.evaluated_get(dg).matrix_world.copy() for ob in obs]
        ang=[math.atan2(q[1][0],q[0][0]) for q in M]
        if last is not None:
            for i in range(len(obs)):travel[i]+=wrap(ang[i]-last[i])
        last=ang
        foot=[]
        for k,leg in enumerate(legs):
            i=3+3*k;x=leg['x'];s=leg['side'];j=leg['gear'];n=leg['name']
            B,C,F=motion(Z,ang[i])
            p=xyz(M[i+2],u,v);expected=np.array([x+F[0],F[1],s*1.39])
            P=xyz(M[i],r);Q=xyz(M[i+2]);R=xyz(M[i+1],m);S=xyz(M[i+2],l)
            offset=np.array([0,0,s*.32])
            joint=max(np.linalg.norm(P+offset-Q),np.linalg.norm(R+offset-S),
                      np.linalg.norm(xyz(M[i])-[x,0,s*1.07]),np.linalg.norm(xyz(M[i+1])-[x+d,0,s*1.07]))
            if n not in initial:initial[n]=p.copy()
            foot.append(dict(name=n,crank=travel[i],foot=p.tolist(),expected=expected.tolist(),
                error=float(np.linalg.norm(p-expected)),joint=float(joint),
                coupling=abs(travel[i]-travel[j]),phase_error=abs(wrap(ang[i]-ang[j]-leg['phase'])),
                displacement=float(np.linalg.norm(p-initial[n]))))
        drift=max(float(np.linalg.norm(xyz(M[j])-[x,4. if separated and j==1 else 0.,0.])) for j,x in enumerate((-2.4,0.,2.4)))
        rows.append(dict(frame=frame,gears=travel[:3],feet=foot,gear_center_drift=drift))
    stats={}
    for leg in legs:
        n=leg['name'];f=[p for q in rows for p in q['feet'] if p['name']==n]
        stats[n]=dict(crank=f[-1]['crank'],max_error=max(p['error'] for p in f),max_joint=max(p['joint'] for p in f),max_coupling=max(p['coupling'] for p in f),max_phase_error=max(p['phase_error'] for p in f),max_displacement=max(p['displacement'] for p in f))
    inp=travel[1];outs=[travel[0],travel[2]];ratios=[a/inp if abs(inp)>1e-8 else None for a in outs]
    phase_error=max(abs(q['gears'][1]+q['gears'][j]) for q in rows for j in (0,2))
    drift=max(q['gear_center_drift'] for q in rows)
    geometry=all(p['max_error']<=.08 and p['max_joint']<=.025 and p['max_coupling']<=.025 and p['max_phase_error']<=.025 for p in stats.values()) and drift<.02
    if name=='engaged':
        passed=geometry and abs(inp)>=6.3 and all(a is not None and -1.05<=a<=-.95 for a in ratios) and phase_error<=.20 and all(abs(p['crank'])>=6.3 and p['max_displacement']>=2. for p in stats.values())
    elif name=='separated':
        passed=geometry and abs(inp)>=6.3 and max(map(abs,outs))<.03 and all(abs(p['crank'])<.03 and p['max_displacement']<.08 for p in stats.values())
    else:
        passed=geometry and max(map(abs,[inp]+outs))<.03 and all(abs(p['crank'])<.03 and p['max_displacement']<.08 for p in stats.values())
    result=dict(name=name,input=inp,outputs=outs,ratios=ratios,max_gear_phase_error=phase_error,center_drift=drift,legs=stats,passed=bool(passed),rows=rows)
    print('PHASE208C_CASE',json.dumps({k:v for k,v in result.items() if k!='rows'},allow_nan=False),flush=True)
    return result
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run_case(n,s,e,dest) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
    gate=all(c['passed'] for c in cases)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,cases=cases,dimensions=Z,ideal_pins=True,ideal_fixed_frame=True,gravity=False,physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase208_four_legs.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE208C_SUMMARY',json.dumps(dict(gate=gate,passed=sum(c['passed'] for c in cases),count=len(cases),elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
