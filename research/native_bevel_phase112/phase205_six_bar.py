"""Phase 205: two closed loops, one crank, six links and six removable pins.
Reuse Phase 204 link production, mesh transforms and audits.
Fixed geometry, sampled motion, no retention/strength/continuous certification.
"""
import json,math,time,sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase204_four_bar import (pose as first_pose,make_link_attempt,make_pin,prism,
    tree,pdist,gap_z,LINK_R,HOLE_R,PIN_R,THICK,DZ,EPS)
from phase195_tapered_spacer import drill,basis,write_obj
from phase196_spacer_verification import Rays,ray_controls
from phase160_operation_contracts import measure
ROOT=Path(__file__).resolve().parent
LINKS=(('ground','A','F',0.,5.),('crank','A','B',DZ,1.),
       ('coupler','B','C',2*DZ,3.),('rocker','D','C',DZ,2.5),
       ('transfer','C','E',3*DZ,2.5),('output','F','E',DZ,2.))
PINS=(('A',-.18,DZ+.18),('D',-.18,DZ+.18),('F',-.18,DZ+.18),
      ('B',DZ-.18,2*DZ+.18),('C',DZ-.18,3*DZ+.18),
      ('E',DZ-.18,3*DZ+.18))
def incident(n,a,b,p):return p in (a,b) or n=='ground' and p=='D'
def pose(t,r=2.5,s=2.):
    p=first_pose(t);p['F']=np.array([5.,0.])
    d=p['F']-p['C'];l=float(np.linalg.norm(d))
    if l<=1e-10 or l>=r+s or l<=abs(r-s):return None
    e=d/l;u=(r*r-s*s+l*l)/(2*l);h=math.sqrt(r*r-u*u)
    p['E']=p['C']+u*e+h*np.array([-e[1],e[0]])
    return p
def ground_attempt(mode):
    l=5.;shift=l/2 if mode=='centered' else 0.
    xy=[(l+LINK_R*math.cos(-math.pi/2+i*math.pi/16)-shift,LINK_R*math.sin(-math.pi/2+i*math.pi/16)) for i in range(17)]
    xy.extend((LINK_R*math.cos(math.pi/2+i*math.pi/16)-shift,LINK_R*math.sin(math.pi/2+i*math.pi/16)) for i in range(17))
    m=prism('ground',xy,-THICK/2,THICK/2);base=measure(m,'cube');stages=[]
    for x in (0.,3.,5.):
        n=drill(m,np.array([x-shift,0.,0.]),basis((0,0,1)),.4,HOLE_R)
        bpy.data.meshes.remove(m);m=n;stages.append(measure(m,'cube'))
    if shift:
        for v in m.vertices:v.co.x+=shift
        m.update()
    a=measure(m,'cube');q=a['metrics'];rays=Rays(m)
    bore=all(rays.cast((x+dx,dy,.5),(0,0,-1),1.) is None for x in (0.,3.,5.) for dx,dy in ((0,0),(.08,0),(-.08,0),(0,.08),(0,-.08)))
    radii=[rays.cast((x,0.,0.),d,1.) for x in (0.,3.,5.) for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0))]
    expected=base['volume']-3*32*HOLE_R**2*math.sin(math.pi/32)*THICK
    checks=dict(clean=base['clean'] and all(x['clean'] for x in stages) and a['clean'],
        topology=q['boundary_edges']==0 and q['euler']==-4,bore=bore,
        radius=all(x is not None and abs(x-HOLE_R)<EPS for x in radii),
        volume=abs(a['volume']-expected)<EPS,
        bounds=bool(np.max(np.abs(np.asarray(a['bounds'])-[[-LINK_R,-LINK_R,-THICK/2],[l+LINK_R,LINK_R,THICK/2]]))<=EPS))
    return m,dict(passed=all(checks.values()),checks=checks,mode=mode,faces=q['faces'],stages=stages,final=a)
def segment_dist(a,b,c,d):
    v=b-a;w=d-c
    cross=lambda x,y:float(x[0]*y[1]-x[1]*y[0])
    det=cross(v,w)
    if abs(det)>1e-12:
        s=cross(c-a,w)/det;t=cross(c-a,v)/det
        if 0<=s<=1 and 0<=t<=1:return 0.
    return min(pdist(a,c,d),pdist(b,c,d),pdist(c,a,b),pdist(d,a,b))
def verify(p,r=PIN_R,layer=DZ):
    links=[(n,a,b,z*layer/DZ,l) for n,a,b,z,l in LINKS]
    gaps=[];errors=[abs(float(np.linalg.norm(p[a]-p[b]))-l) for _,a,b,z,l in links]
    errors.extend((abs(float(np.linalg.norm(p['A']-p['D']))-3.),abs(float(np.linalg.norm(p['D']-p['F']))-2.)))
    for i,(n,a,b,z,l) in enumerate(links):
        for _,c,d,w,_ in links[i+1:]:
            gaps.append(max(abs(z-w)-THICK,segment_dist(p[a],p[b],p[c],p[d])-2*LINK_R))
    for n,lo,hi in PINS:
        for ln,a,b,z,l in links:
            if incident(ln,a,b,n):
                gaps.append(HOLE_R*math.cos(math.pi/64)-r)
                gaps.append(min(z-THICK/2-lo,hi-z-THICK/2))
            else:gaps.append(max(gap_z((lo,hi),(z-THICK/2,z+THICK/2)),pdist(p[n],p[a],p[b])-r-LINK_R))
    for i,(a,lo,hi) in enumerate(PINS):
        for b,l,h in PINS[i+1:]:
            gaps.append(max(gap_z((lo,hi),(l,h)),float(np.linalg.norm(p[a]-p[b]))-2*r))
    return dict(passed=max(errors)<1e-9 and min(gaps)>0.,closure_error=max(errors),min_gap=min(gaps))
def transforms(p):
    tr={}
    for n,a,b,z,l in LINKS:
        d=p[b]-p[a];tr[n]=(float(p[a][0]),float(p[a][1]),z,math.atan2(d[1],d[0]))
    for n,lo,hi in PINS:tr['pin_'+n]=(float(p[n][0]),float(p[n][1]),lo,0.)
    return tr
def collisions(parts,p):
    tr=transforms(p);trees={n:tree(m,tr[n]) for n,m in parts.items()};names=list(trees)
    return [[a,b] for i,a in enumerate(names) for b in names[i+1:] if trees[a].overlap(trees[b])]
def insertion(p):
    out={}
    for n,lo,hi in PINS:
        bottom=n in ('A','D','F');gaps=[]
        for ln,a,b,z,l in LINKS:
            if incident(ln,a,b,n):gaps.append(HOLE_R*math.cos(math.pi/64)-PIN_R);continue
            if (z-THICK/2<=hi if bottom else z+THICK/2>=lo):
                gaps.append(pdist(p[n],p[a],p[b])-PIN_R-LINK_R)
        for q,l,h in PINS:
            if q!=n:gaps.append(float(np.linalg.norm(p[n]-p[q]))-2*PIN_R)
        out[n]=min(gaps)
    return out
def save(parts,poses,dest):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    obs={};colors=[(.2,.25,.3,1),(.12,.45,.8,1),(.2,.65,.35,1),(.9,.45,.12,1),(.65,.3,.8,1),(.15,.7,.75,1)]
    for i,(n,m) in enumerate(parts.items()):
        ob=bpy.data.objects.new(n,m);bpy.context.collection.objects.link(ob);obs[n]=ob
        mat=bpy.data.materials.new(n+'_material');mat.diffuse_color=colors[i] if i<6 else (.62,.65,.7,1)
        m.materials.append(mat);ob.color=mat.diffuse_color
    last={}
    for i,p in enumerate(poses):
        for n,(x,y,z,a) in transforms(p).items():
            if n in last:a=last[n]+math.atan2(math.sin(a-last[n]),math.cos(a-last[n]))
            last[n]=a;ob=obs[n];ob.location=(x,y,z);ob.rotation_euler=(0,0,a)
            ob.keyframe_insert(data_path='location',frame=i+1);ob.keyframe_insert(data_path='rotation_euler',frame=i+1)
    for ob in obs.values():
        for fc in ob.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
    scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=len(poses);scene.render.fps=30;scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase205_six_bar.blend'))
    for n,m in parts.items():write_obj(m,dest/f'phase205_{n}.obj')
def main():
    assert bpy.app.version_string=='4.4.3' and ray_controls()
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True);parts={};audits={}
    for n,a,b,z,l in LINKS:
        attempts=[]
        for mode in ('centered','baseline','reversed') if n!='ground' else ('centered','baseline'):
            m,q=ground_attempt(mode) if n=='ground' else make_link_attempt(n,l,mode)
            attempts.append(q)
            print('PHASE205_PART',json.dumps(dict(name=n,mode=mode,passed=q['passed'],checks=q['checks']),allow_nan=False),flush=True)
            if q['passed']:break
            if mode!=('baseline' if n=='ground' else 'reversed'):bpy.data.meshes.remove(m)
        parts[n]=m;audits[n]=dict(**q,attempts=attempts)
    for n,lo,hi in PINS:parts['pin_'+n],audits['pin_'+n]=make_pin(n,hi-lo)
    poses=[pose(math.radians(i)) for i in range(361)];assert all(p is not None for p in poses)
    samples=[verify(p) for p in poses]
    hits=[dict(angle=i,pairs=collisions(parts,p)) for i,p in enumerate(poses)]
    ins=insertion(poses[0])
    controls=dict(impossible_second_loop=pose(0.,.1,.1) is None,oversized_pin=not verify(poses[0],r=.19)['passed'],
                  overlapping_layers=not verify(poses[0],layer=.1)['passed'])
    bad=poses[0].copy();bad['E']=bad['E']+np.array([.1,0.]);controls['broken_closure']=not verify(bad)['passed']
    gate=all(x['passed'] for x in audits.values()) and all(x['passed'] for x in samples) and not any(x['pairs'] for x in hits) and all(x>0 for x in ins.values()) and all(controls.values())
    if gate:save(parts,poses,dest)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,parts=audits,
        samples=samples,mesh_collisions=hits,insertion_gaps=ins,controls=controls,
        continuous_certified=False,retention_designed=False,elapsed=time.perf_counter()-start)
    (dest/'phase205_six_bar.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE205_SUMMARY',json.dumps(dict(gate=gate,parts=sum(x['passed'] for x in audits.values()),
        poses=len(samples),passed_poses=sum(x['passed'] for x in samples),mesh_poses=len(hits),
        collision_poses=sum(bool(x['pairs']) for x in hits),min_gap=min(x['min_gap'] for x in samples),
        max_closure_error=max(x['closure_error'] for x in samples),insertion_gaps=ins,controls=controls,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
