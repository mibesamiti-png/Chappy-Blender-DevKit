"""Phase 206: fixed hybrid mechanism, two spur gears + six-bar + slider.
Existing Blender mesh audits and native drilling. Explicit involute polygon
profiles with backlash, square-drive bores, sampled kinematics and BVH.
Not a physical simulation, continuous collision or manufacturing guarantee.
Guide is externally fixed; no bearings/retainers or structural certification.
"""
import json,math,time,sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase204_four_bar import (make_link_attempt,make_pin,prism,mesh,tree,LINK_R,HOLE_R,PIN_R,THICK,DZ,EPS)
from phase205_six_bar import pose as six_pose,verify as six_verify,transforms as six_transforms,PINS
from phase195_tapered_spacer import drill,basis,write_obj
from phase196_spacer_verification import Rays,ray_controls
from phase160_operation_contracts import measure
ROOT=Path(__file__).resolve().parent
GEAR_Z=-.55;INPUT_X=-3.6;KEY=.09;BORE=.094
ROD=4.5;GUIDE_Y=4.;SLIDER_Z=1.28;ROD_Z=1.60
PIN_LO=1.10;PIN_HI=1.78
def capsule(a,b):
    return [(b+LINK_R*math.cos(-math.pi/2+i*math.pi/16),LINK_R*math.sin(-math.pi/2+i*math.pi/16)) for i in range(17)]+[(a+LINK_R*math.cos(math.pi/2+i*math.pi/16),LINK_R*math.sin(math.pi/2+i*math.pi/16)) for i in range(17)]
def square(h):return [(-h,-h),(h,-h),(h,h),(-h,h)]
def box2(x0,x1,y0,y1):return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
def cut(m,co_mesh):
    ob=bpy.data.objects.new('operand206',m);co=bpy.data.objects.new('cutter206',co_mesh)
    bpy.context.scene.collection.objects.link(ob);bpy.context.scene.collection.objects.link(co)
    try:
        mod=ob.modifiers.new('cut','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=co
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
        out=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg);out.update();return out
    finally:
        bpy.data.objects.remove(ob,do_unlink=True);bpy.data.objects.remove(co,do_unlink=True);bpy.data.meshes.remove(co_mesh)
def area_circle(r):return 32*r*r*math.sin(math.pi/32)
def closed(m,holes,expected):
    a=measure(m,'cube');q=a['metrics']
    return dict(passed=a['clean'] and q['boundary_edges']==0 and q['euler']==2-2*holes and abs(a['volume']-expected)<max(EPS,1e-6*expected),
        audit=a,expected_volume=expected)
def bore_check(m,x,y,r=HOLE_R):
    ray=Rays(m)
    return all(ray.cast((x+dx,y+dy,.5),(0,0,-1),1.) is None for dx,dy in ((0,0),(.07,0),(-.07,0),(0,.07),(0,-.07))) and all((v:=ray.cast((x,y,0),d,1.)) is not None and abs(v-r)<EPS for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0)))
def key_check(m):
    ray=Rays(m)
    return all(ray.cast((x,y,.5),(0,0,-1),1.) is None for x,y in square(KEY)) and all((v:=ray.cast((0,0,0),d,1.)) is not None and abs(v-BORE)<.002 for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0)))
def base_attempt(shift):
    m=prism('base',capsule(INPUT_X-shift,5.-shift),-THICK/2,THICK/2)
    base=measure(m,'cube');stage=[]
    for x in (INPUT_X,0.,3.,5.):
        out=drill(m,np.array([x-shift,0.,0.]),basis((0,0,1)),.4,HOLE_R)
        bpy.data.meshes.remove(m);m=out;stage.append(measure(m,'cube'))
    for v in m.vertices:v.co.x+=shift
    m.update();a=closed(m,4,base['volume']-4*area_circle(HOLE_R)*THICK)
    a['bores']=all(bore_check(m,x,0.) for x in (INPUT_X,0.,3.,5.))
    a['stages_clean']=base['clean'] and all(s['clean'] for s in stage)
    a['passed'] &= a['bores'] and a['stages_clean'];return m,a
def crank_attempt(shift,order):
    m=prism('key_crank',capsule(-shift,1.-shift),-THICK/2,THICK/2)
    base=measure(m,'cube');stages=[]
    for kind in order:
        if kind=='key':
            co=prism('key_cut',[(x-shift,y) for x,y in square(BORE)],-.3,.3);out=cut(m,co)
        else:out=drill(m,np.array([1.-shift,0.,0.]),basis((0,0,1)),.4,HOLE_R)
        bpy.data.meshes.remove(m);m=out;stages.append(measure(m,'cube'))
    for v in m.vertices:v.co.x+=shift
    m.update();a=closed(m,2,base['volume']-(4*BORE**2+area_circle(HOLE_R))*THICK)
    a.update(key=key_check(m),round_bore=bore_check(m,1.,0.),stages_clean=base['clean'] and all(s['clean'] for s in stages))
    a['passed'] &= a['key'] and a['round_bore'] and a['stages_clean'];return m,a
def retry(name,fs):
    attempts=[]
    for i,f in enumerate(fs):
        m,a=f();attempts.append(dict(index=i,passed=a['passed']))
        print('PHASE206_ATTEMPT',json.dumps(dict(name=name,index=i,passed=a['passed']),allow_nan=False),flush=True)
        if a['passed'] or i==len(fs)-1:return m,dict(**a,attempts=attempts)
        bpy.data.meshes.remove(m)
def polygon_area(xy):
    return .5*sum(x*y1-y*x1 for (x,y),(x1,y1) in zip(xy,xy[1:]+xy[:1]))
def ring(name,outer,inner,h=THICK):
    # Radial tooth-root transitions can project two outer vertices onto
    # the same square-bore point. Preserve every outer vertex; collapse
    # only consecutive coincident inner points, with triangular end caps
    # at those transitions and no zero-width inner wall.
    n=len(outer);unique=[];idx=[]
    def same(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])<1e-10
    for p in inner:
        if not unique or not same(p,unique[-1]):unique.append(p)
        idx.append(len(unique)-1)
    if len(unique)>1 and same(unique[0],unique[-1]):
        last=len(unique)-1;unique.pop();idx=[0 if i==last else i for i in idx]
    stride=n+len(unique)
    v=[(x,y,z) for z in (-h/2,h/2) for xy in (outer,unique) for x,y in xy]
    f=[]
    for i in range(n):
        j=(i+1)%n;a=n+idx[i];b=n+idx[j]
        f.append((i,j,j+stride,i+stride))
        if a==b:continue
        f.append((a,a+stride,b+stride,b))
        if len(unique)==n:
            f.extend(((i,a,b,j),(i+stride,j+stride,b+stride,a+stride)))
            continue
        # A collapsed radial sector has no cap area. Instead split the
        # neighboring nonzero sector along its longer radial boundary,
        # retaining the nearer outer vertex as a conforming edge split.
        p=(i-1)%n;q=(j+1)%n
        radius=lambda k:math.hypot(*outer[k])
        if idx[p]==idx[i] and radius(p)<radius(i):
            caps=[(i,p,b),(p,a,b)]
        else:caps=[(i,a,b)]
        if idx[q]==idx[j] and radius(q)<radius(j):
            caps.extend(((i,b,q),(i,q,j)))
        else:caps.append((i,b,j))
        for tri in caps:
            f.append(tri)
            f.append(tuple(k+stride for k in reversed(tri)))
    m=mesh(name,v,f)
    audit=closed(m,1,(polygon_area(outer)-polygon_area(inner))*h)
    audit['collapsed_inner_vertices_per_layer']=n-len(unique)
    return m,audit
def gear(n):
    # 20-degree involute flank, finite polygon approximations and backlash.
    pa=math.pi/9;r=.1*n/2;b=r*math.cos(pa);root=r-.125;tip=r+.1;start=max(root,b);pitch=2*math.pi/n
    inv=lambda a:math.tan(a)-a
    half=lambda x:math.pi/(2*n)-.012/r+inv(pa)-inv(math.acos(min(1.,b/x)))
    xy=[]
    def put(a,x):xy.append((x*math.cos(a),x*math.sin(a)))
    for j in range(n):
        c=j*pitch;put(c-pitch/2,root)
        if root<start:put(c-half(start),root)
        for k in range(9):
            x=start+(tip-start)*k/8;put(c-half(x),x)
        put(c,tip)
        for k in range(8,-1,-1):
            x=start+(tip-start)*k/8;put(c+half(x),x)
        if root<start:put(c+half(start),root)
    inner=[(x*BORE/max(abs(x),abs(y)),y*BORE/max(abs(x),abs(y))) for x,y in xy]
    m,a=ring('gear_'+str(n),xy,inner);a['key']=key_check(m)
    a['passed'] &= a['key'];a['teeth']=n;a['pitch_radius']=r;return m,a
def shaft(name,lo,hi):
    m=prism(name,square(KEY),0.,hi-lo);return m,closed(m,0,4*KEY**2*(hi-lo))
def slider():
    m=prism('slider',box2(-.30,.30,-.22,.22),-THICK/2,THICK/2)
    out=drill(m,np.zeros(3),basis((0,0,1)),.4,HOLE_R);bpy.data.meshes.remove(m)
    a=closed(out,1,(.60*.44-area_circle(HOLE_R))*THICK);a['bore']=bore_check(out,0.,0.);a['passed'] &= a['bore'];return out,a
def guide():
    return ring('guide',box2(6.60,10.25,-.45,.45),box2(6.75,10.10,-.27,.27))
def pose(t):
    p=six_pose(t)
    if p is None:return None
    E=p['E'];d=GUIDE_Y-E[1]
    if abs(d)>=ROD:return None
    p['G']=np.array([E[0]+math.sqrt(ROD*ROD-d*d),GUIDE_Y])
    return p
def transforms(p,t):
    tr=six_transforms(p)
    tr['pin_A']=(0.,0.,GEAR_Z-.18,t)
    tr['pin_E']=(float(p['E'][0]),float(p['E'][1]),DZ-.18,0.)
    tr['gear_48']=(0.,0.,GEAR_Z,t)
    tr['gear_24']=(INPUT_X,0.,GEAR_Z,math.pi/24-2*t)
    tr['input_shaft']=(INPUT_X,0.,GEAR_Z-.18,math.pi/24-2*t)
    e,g=p['E'],p['G'];d=g-e
    tr['rod']=(float(e[0]),float(e[1]),ROD_Z,math.atan2(d[1],d[0]))
    tr['slider']=(float(g[0]),float(g[1]),SLIDER_Z,0.)
    tr['pin_G']=(float(g[0]),float(g[1]),PIN_LO,0.)
    tr['guide']=(0.,GUIDE_Y,SLIDER_Z,0.)
    return tr
def verify(p,t):
    a=six_verify(p);g=p['G']
    closure=max(a['closure_error'],abs(float(np.linalg.norm(g-p['E']))-ROD),abs(float(g[1])-GUIDE_Y))
    travel=min(float(g[0])-.30-6.75,10.10-float(g[0])-.30,.27-.22)
    tr=transforms(p,t);ratio=abs(tr['gear_24'][3]+2*tr['gear_48'][3]-math.pi/24)
    return dict(passed=a['passed'] and closure<1e-9 and travel>0 and ratio<1e-9,
        closure_error=closure,slider_x=float(g[0]),guide_gap=travel,ratio_error=ratio)
def collision(parts,tr):
    trees={n:tree(m,tr[n]) for n,m in parts.items()};names=list(trees)
    return [[a,b] for i,a in enumerate(names) for b in names[i+1:] if trees[a].overlap(trees[b])]
def save(parts,poses,angles,dest):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    obs={};colors=[(.20,.25,.32,1),(.10,.40,.82,1),(.20,.70,.35,1),(.9,.45,.12,1),(.64,.3,.8,1),(.15,.7,.75,1)]
    extra={'gear_48':(.85,.53,.13,1),'gear_24':(.7,.45,.12,1),'rod':(.7,.24,.35,1),'slider':(.15,.64,.66,1),'guide':(.24,.28,.34,1)}
    for i,(n,m) in enumerate(parts.items()):
        ob=bpy.data.objects.new(n,m);bpy.context.collection.objects.link(ob);obs[n]=ob
        mat=bpy.data.materials.new(n+'_mat');mat.diffuse_color=extra.get(n,colors[i] if i<6 else (.64,.68,.73,1));m.materials.append(mat);ob.color=mat.diffuse_color
    last={}
    for i,(p,t) in enumerate(zip(poses,angles)):
        for n,(x,y,z,a) in transforms(p,t).items():
            if n in last:a=last[n]+math.atan2(math.sin(a-last[n]),math.cos(a-last[n]))
            last[n]=a;ob=obs[n];ob.location=(x,y,z);ob.rotation_euler=(0,0,a)
            ob.keyframe_insert(data_path='location',frame=i+1);ob.keyframe_insert(data_path='rotation_euler',frame=i+1)
    for ob in obs.values():
        for fc in ob.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
    scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=len(poses);scene.render.fps=30;scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase206_hybrid_machine.blend'))
    for n,m in parts.items():write_obj(m,dest/f'phase206_{n}.obj')
def main():
    assert bpy.app.version_string=='4.4.3' and ray_controls()
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True);parts={};audits={}
    def add(n,result):
        parts[n],audits[n]=result
        print('PHASE206_PART',json.dumps(dict(name=n,passed=audits[n]['passed']),allow_nan=False),flush=True)
    add('ground',retry('ground',[lambda s=s:base_attempt(s) for s in (.7,0.)]))
    add('crank',retry('crank',[lambda s=s,o=o:crank_attempt(s,o) for s,o in ((.5,('key','round')),(.5,('round','key')),(0.,('key','round')))]))
    for n,l in (('coupler',3.),('rocker',2.5),('transfer',2.5),('output',2.),('rod',ROD)):
        add(n,retry(n,[lambda mode=mode,n=n,l=l:make_link_attempt(n,l,mode) for mode in ('centered','baseline','reversed')]))
    for n,lo,hi in PINS:
        if n=='A':add('pin_A',shaft('drive_shaft',GEAR_Z-.18,DZ+.18))
        else:add('pin_'+n,make_pin('pin_'+n,(PIN_HI if n=='E' else hi)-lo))
    add('pin_G',make_pin('pin_G',PIN_HI-PIN_LO))
    add('input_shaft',shaft('input_shaft',GEAR_Z-.18,.18))
    add('gear_48',gear(48));add('gear_24',gear(24));add('slider',slider());add('guide',guide())
    angles=[math.radians(i) for i in range(361)];poses=[pose(t) for t in angles];assert all(p is not None for p in poses)
    samples=[verify(p,t) for p,t in zip(poses,angles)]
    hits=[dict(angle=i,pairs=collision(parts,transforms(p,t))) for i,(p,t) in enumerate(zip(poses,angles))]
    tr=transforms(poses[0],angles[0]);bad=dict(tr);x,y,z,a=bad['gear_24'];bad['gear_24']=(x,y,z,a+math.pi/24)
    phase_hits=collision(parts,bad)
    # Controls operate on isolated transforms, not the exported geometry.
    bad=dict(tr);x,y,z,a=bad['slider'];bad['slider']=(x,y+.16,z,a)
    slider_hits=collision(parts,bad)
    bad=dict(tr);x,y,z,a=bad['pin_A'];bad['pin_A']=(x,y,z,a+math.pi/4)
    key_hits=collision(parts,bad)
    p=poses[0].copy();p['G']=p['G']+np.array([.1,0.])
    controls=dict(wrong_gear_phase=['gear_48','gear_24'] in phase_hits or ['gear_24','gear_48'] in phase_hits,
        guide_collision=any(set(x)=={'slider','guide'} for x in slider_hits),
        wrong_key_orientation=any(set(x)=={'crank','pin_A'} for x in key_hits),
        broken_rod=not verify(p,0.)['passed'])
    gate=len(parts)==19 and all(a['passed'] for a in audits.values()) and all(s['passed'] for s in samples) and not any(h['pairs'] for h in hits) and all(controls.values())
    if gate:save(parts,poses,angles,dest)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,parts=audits,samples=samples,mesh_collisions=hits,
        controls=controls,control_hits=dict(phase=phase_hits,slider=slider_hits,key=key_hits),
        continuous_certified=False,physical_drive_certified=False,externally_fixed_guide=True,retention_designed=False,elapsed=time.perf_counter()-start)
    (dest/'phase206_hybrid_machine.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE206_SUMMARY',json.dumps(dict(gate=gate,parts=sum(a['passed'] for a in audits.values()),part_count=len(parts),
        poses=len(samples),passed_poses=sum(s['passed'] for s in samples),mesh_poses=len(hits),collision_poses=sum(bool(h['pairs']) for h in hits),
        collision_examples=[h for h in hits if h['pairs']][:5],max_closure_error=max(s['closure_error'] for s in samples),
        slider_range=[min(s['slider_x'] for s in samples),max(s['slider_x'] for s in samples)],
        min_guide_gap=min(s['guide_gap'] for s in samples),controls=controls,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
