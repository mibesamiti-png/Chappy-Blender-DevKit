"""Phase211-D1: four independently phased XY outputs on one motor shaft.
Axial test fixture, not the final spatial foot layout. No floor or free body.
One-piece cams, passive rollers, ideal bearings and cross-slide constraints.
"""
import json,math,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from mathutils import Vector
from phase208_motor_contact import body,constraint
from phase210_xy_cam import box,limits,wrap,az
from phase210_inverse_cam import law,ROLLER
from phase211_backed_groove import backed_mesh,FLOOR
from phase211_groove_profile import nearest
DUTY=.77;PHASES=[0,270,180,90];FRAMES=601;IMPULSE=240.
START=float((t:=np.arange(36000)*math.tau/36000)[np.argmin(law(t,'stride',DUTY))])
SPAN=float(np.ptp(law(t,'stride',DUTY)))
def setup(separated,enabled,integrated=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.gravity=(0.,-9.81,0.);sc.render.fps=60;sc.frame_end=FRAMES
    anchor=box('fixed fixture',(0.,0.,-4.),(.5,.5,.5),1.)
    anchor.rigid_body.type='PASSIVE'
    shaft=box('common shaft',(0.,0.,6.5),(.18,.18,15.),.8);shaft.rotation_euler.z=-START
    constraint('shaft bearing','HINGE',anchor,shaft,(0.,0.,6.5))
    motor=constraint('only motor','MOTOR',anchor,shaft,(0.,0.,6.5),(0.,-math.pi/2,0.))
    motor.use_motor_lin=False;motor.use_motor_ang=enabled;motor.motor_ang_target_velocity=1.;motor.motor_ang_max_impulse=IMPULSE
    zero={a:(0.,0.) for a in 'xyz'};legs=[]
    for j,deg in enumerate(PHASES):
        items=[];offset=math.radians(deg);initial_phase=START+offset
        for kind,axis,base,dz,phi,side in [('stride','x',7.,0.,0.,-1.),('lift','y',2.5,1.,math.pi/2,1.)]:
            z=3.5*j+dz;name=f'L{j} {kind}'
            rot=np.array([[math.cos(phi),-math.sin(phi)],[math.sin(phi),math.cos(phi)]])
            m,a,core,outer=backed_mesh(kind,base,DUTY,rot,-side)
            assert a['passed']
            cam=bpy.data.objects.new(name+' groove',m);sc.collection.objects.link(cam)
            cam.location=(0.,0.,z);cam.rotation_euler.z=-initial_phase
            body(cam);cam.rigid_body.mass=3.5;cam.color=(.25,.55,.8,1) if axis=='x' else (.8,.55,.15,1)
            constraint(name+' shaft coupling','FIXED',shaft,cam,(0.,0.,z))
            s=float(law(initial_phase,kind,DUTY));initial=base+s
            rz=z+side*.75 if separated else z
            pos=(initial,0.,rz) if axis=='x' else (0.,initial,rz)
            bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=ROLLER,depth=.24,location=pos)
            roller=body(bpy.context.object);roller.name=name+' roller';roller.rigid_body.collision_shape='CONVEX_HULL';roller.rigid_body.mass=.25;roller.rigid_body.friction=.2
            spos=(pos[0],pos[1],rz+side*.4)
            slide=box(name+' slider',spos,(.18,.18,.18),.1)
            constraint(name+' roller bearing','HINGE',slide,roller,pos)
            lin=dict(zero);lo=float(np.min(law(t,kind,DUTY)));hi=float(np.max(law(t,kind,DUTY)))
            lin[axis]=(lo-s-.15,hi-s+.15)
            limits(constraint(name+' guide','GENERIC',anchor,slide,spos),lin,zero)
            items.append(dict(kind=kind,axis=axis,base=base,z=z,rz=rz,initial=initial,cam=cam,roller=roller,slide=slide,core=core,outer=outer,side=side))
        opos=(items[0]['initial'],items[1]['initial'],3.5*j+2.5)
        out=box(f'L{j} output',opos,(.32,.32,.25),.1);out.color=(.9,.3,.2,1)
        limits(constraint(f'L{j} plane','GENERIC',anchor,out,opos),{'z':(0.,0.)},zero)
        for it in items:
            limits(constraint(f'L{j} '+it['kind']+' cross-slide','GENERIC',it['slide'],out,opos),{it['axis']:(0.,0.)},{})
        legs.append(dict(offset=offset,items=items,out=out,oz=opos[2]))
    if integrated:
        # Assemble actual collision triangles in shaft-local coordinates.
        # No cam-to-shaft constraints remain. Separate connected shells
        # represent an ideally rigid keyed assembly, not a welded solid.
        bpy.context.view_layer.update()
        inverse=shaft.matrix_world.inverted()
        vertices=[tuple(v.co) for v in shaft.data.vertices]
        faces=[tuple(p.vertices) for p in shaft.data.polygons]
        cams=[it for L in legs for it in L['items']]
        for it in cams:
            cam=it['cam'];local=inverse@cam.matrix_world
            it['cam_local']=local.copy()
            n=len(vertices)
            vertices.extend(tuple(local@v.co) for v in cam.data.vertices)
            faces.extend(tuple(n+i for i in p.vertices) for p in cam.data.polygons)
        names={it['cam'].name for it in cams}
        for o in list(sc.objects):
            c=o.rigid_body_constraint
            if c and c.type=='FIXED' and c.object1==shaft and c.object2.name in names:
                bpy.data.objects.remove(o,do_unlink=True)
        for it in cams:
            bpy.data.objects.remove(it['cam'],do_unlink=True)
            it['cam']=None
        m=bpy.data.meshes.new('rigid shaft and eight groove cams')
        m.from_pydata(vertices,[],faces);m.update()
        shaft.data=m;shaft.rigid_body.collision_shape='MESH';shaft.rigid_body.mass=28.8
        shaft.name='integrated camshaft'
        bpy.context.view_layer.update()
    world=sc.rigidbody_world;world.substeps_per_frame=32;world.solver_iterations=100
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();sc.frame_set(1)
    cs=[o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint]
    bodies=[o for o in sc.objects if o.rigid_body and o.rigid_body.type=='ACTIVE']
    assert len(cs)==(30 if integrated else 38) and len(bodies)==(21 if integrated else 29) and sum(c.type=='MOTOR' and c.use_motor_ang for c in cs)==int(enabled)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in bodies)
    return sc,shaft,legs
def run(name,separated,enabled,dest,integrated=False):
    sc,shaft,legs=setup(separated,enabled,integrated)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/('phase211_four_leg_'+name+'.blend')))
    rows=[];last=None;travel=0.
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        mat=lambda o:o.evaluated_get(dg).matrix_world.copy()
        S=mat(shaft);a=az(S)
        if last is not None:travel+=wrap(a-last)
        last=a
        row=dict(frame=f,travel=travel,shaft_drift=(S.translation-Vector((0.,0.,6.5))).length)
        for j,L in enumerate(legs):
            phase=(START-travel+L['offset'])%math.tau;O=mat(L['out']);pfx=f'L{j}_'
            row[pfx+'phase']=phase;row[pfx+'out_drift']=abs(O.translation.z-L['oz'])
            for i,it in enumerate(L['items']):
                A=S@it['cam_local'] if integrated else mat(it['cam']);B=mat(it['roller']);D=mat(it['slide']);rel=A.inverted()@B;v=rel.translation
                p=np.array((v.x,v.y));k=pfx+it['kind']+'_'
                out=float(O.translation[i]-it['base']);expected=float(law(phase,it['kind'],DUTY))
                reach=.12*abs(rel[2][2])+ROLLER*math.hypot(rel[2][0],rel[2][1])
                row.update({k+'output':out,k+'error':out-expected,k+'gap':nearest(p,it['core'])-ROLLER,
                    k+'outer_gap':nearest(p,it['outer'])-ROLLER,k+'back_gap':FLOOR+it['side']*v.z-reach,
                    k+'sync':abs(wrap(az(A)-a+L['offset'])),k+'axial':abs(v.z),
                    k+'coupling':out-float(B.translation[i]-it['base']),
                    k+'drift':max((A.translation-Vector((0.,0.,it['z']))).length,math.hypot(B.translation[1-i],B.translation.z-it['rz']),abs(D.translation[1-i]))})
        rows.append(row)
    peak=lambda k:max(abs(r[k]) for r in rows)
    span=lambda k,skip=0:max(r[k] for r in rows[skip:])-min(r[k] for r in rows[skip:])
    checks=dict(shaft_drift=peak('shaft_drift')<=.015)
    if enabled:checks['full_cycle']=travel<=-math.tau
    else:checks['no_sustained_drive']=abs(travel)<=.4
    outputs=[]
    for j in range(4):
        p=f'L{j}_';ks=[p+k+'_' for k in ('stride','lift')]
        q=dict(sync=all(peak(k+'sync')<=.015 for k in ks),coupling=all(peak(k+'coupling')<=.015 for k in ks),
            drift=max(peak(p+'out_drift'),*(peak(k+'drift') for k in ks))<=.015)
        amp=[span(k+'output') for k in ks]
        err=[peak(k+'error') for k in ks]
        xy=max(math.hypot(r[ks[0]+'error'],r[ks[1]+'error']) for r in rows)
        gap=max(peak(k+'gap') for k in ks);outer=max(peak(k+'outer_gap') for k in ks)
        bg=min(r[k+'back_gap'] for r in rows for k in ks)
        if name=='engaged':
            stance=[r for r in rows if r[p+'phase']<=DUTY*math.tau]
            q.update(axis_tracking=max(err)<=.025,xy_tracking=xy<=.04,stride=abs(amp[0]-SPAN)<=.05,
                lift=.55<=amp[1]<=.65,stance=bool(stance) and max(abs(r[ks[1]+'output']) for r in stance)<=.025,
                contact=gap<=.025,outer_clearance=outer<=.025,axial_overlap=all(peak(k+'axial')<.05 for k in ks),backplate=bg>=.02)
        elif separated:
            q.update(no_periodic_output=all(span(k+'output',120)<=.025 for k in ks),
                axial_clearance=all(min(r[k+'axial'] for r in rows)>.5 for k in ks))
        else:
            q.update(no_large_output=amp[0]<=.25 and amp[1]<=.15,backplate=bg>=.02)
        outputs.append(dict(leg=j,phase=PHASES[j],amplitude=amp,max_axis_error=err,max_xy_error=xy,max_gap=gap,max_outer_gap=outer,min_back_gap=bg,checks=q,passed=all(q.values())))
    c=dict(name=name,separated=separated,enabled=enabled,integrated=integrated,travel=travel,checks=checks,legs=outputs,
        passed=all(checks.values()) and all(v['passed'] for v in outputs),rows=rows)
    print('PHASE211D1_CASE',json.dumps({k:v for k,v in c.items() if k!='rows'},allow_nan=False),flush=True)
    return c
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run(n,s,e,dest) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
    out=dict(complete=True,native_executed=True,approved=False,four_leg_drive_gate=all(c['passed'] for c in cases),
        cases=cases,phases=PHASES,duty=DUTY,cam_count=8,active_bodies=29,motor_count=1,impulse=IMPULSE,
        fixed_fixture=True,axial_test_layout=True,ideal_guides=True,physical_foot_layout=False,
        physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_four_leg_drive.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211D1_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='cases'},allow_nan=False),flush=True)
if __name__=='__main__':main()
