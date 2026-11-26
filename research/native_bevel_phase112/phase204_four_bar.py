"""Phase 204: whole four-bar assembly, not a new generic constraint solver.
Fixed crank-rocker, native drilled links, removable plain pins, 361 sampled
poses plus actual mesh BVH at 73 poses. No continuous or physical certification.
"""
import json,math,sys,time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase195_tapered_spacer import drill,basis,write_obj
from phase196_spacer_verification import Rays,ray_controls
from phase160_operation_contracts import measure
from phase171_planar_topology_variants import arrays
ROOT=Path(__file__).resolve().parent
LENGTHS=(3.,1.,3.,2.5)
LINK_R=.27;HOLE_R=.17;PIN_R=.12;THICK=.24;DZ=.32;EPS=1e-4
LINKS=(('ground','A','D',0.),('crank','A','B',DZ),('coupler','B','C',2*DZ),('rocker','D','C',DZ))
PINS=(('A',-.18,DZ+.18),('D',-.18,DZ+.18),('B',DZ-.18,2*DZ+.18),('C',DZ-.18,2*DZ+.18))
def mesh(name,v,f):
    m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.update();return m
def prism(name,xy,z0,z1):
    n=len(xy);v=[(x,y,z) for z in (z0,z1) for x,y in xy]
    f=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    f.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,v,f)
def make_link(name,l):
    xy=[(l+LINK_R*math.cos(-math.pi/2+i*math.pi/16),LINK_R*math.sin(-math.pi/2+i*math.pi/16)) for i in range(17)]
    xy.extend((LINK_R*math.cos(math.pi/2+i*math.pi/16),LINK_R*math.sin(math.pi/2+i*math.pi/16)) for i in range(17))
    m=prism(name,xy,-THICK/2,THICK/2);base=measure(m,'cube');stages=[]
    try:
        for x in (0.,l):
            n=drill(m,np.array([x,0.,0.]),basis((0,0,1)),.4,HOLE_R)
            bpy.data.meshes.remove(m);m=n;stages.append(measure(m,'cube'))
        a=stages[-1];q=a['metrics'];rays=Rays(m)
        bore=all(rays.cast((x+dx,dy,.5),(0,0,-1),1.) is None for x in (0.,l)
                 for dx,dy in ((0.,0.),(.08,0.),(-.08,0.),(0.,.08),(0.,-.08)))
        radii=[rays.cast((x,0.,0.),d,1.) for x in (0.,l) for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0))]
        expected=base['volume']-2*64*.5*HOLE_R**2*math.sin(2*math.pi/64)*THICK
        ok=base['clean'] and all(s['clean'] for s in stages) and q['boundary_edges']==0 and q['euler']==-2 and bore and all(r is not None and abs(r-HOLE_R)<EPS for r in radii) and abs(a['volume']-expected)<EPS
        return m,dict(passed=ok,faces=q['faces'],volume=a['volume'],expected_volume=expected,bore=bore,radii=radii)
    except:
        bpy.data.meshes.remove(m);raise
def make_pin(name,h,r=PIN_R):
    xy=[(r*math.cos(i*math.pi/32),r*math.sin(i*math.pi/32)) for i in range(64)]
    m=prism(name,xy,0.,h);a=measure(m,'cube')
    return m,dict(passed=a['clean'] and a['metrics']['boundary_edges']==0 and a['metrics']['euler']==2
                  and abs(a['volume']-32*r*r*math.sin(math.pi/32)*h)<EPS,faces=a['metrics']['faces'])
def pose(theta,lengths=LENGTHS):
    g,b,c,d=lengths;A=np.array([0.,0.]);D=np.array([g,0.]);B=b*np.array([math.cos(theta),math.sin(theta)])
    delta=D-B;s=float(np.linalg.norm(delta))
    if s<=1e-10 or s>c+d or s<abs(c-d):return None
    e=delta/s;u=(c*c-d*d+s*s)/(2*s);h=math.sqrt(max(0.,c*c-u*u))
    C=B+u*e+h*np.array([-e[1],e[0]])
    return dict(A=A,B=B,C=C,D=D)
def pdist(p,a,b):
    v=b-a;t=max(0.,min(1.,float(np.dot(p-a,v)/np.dot(v,v))))
    return float(np.linalg.norm(p-a-t*v))
def gap_z(a,b):return max(a[0]-b[1],b[0]-a[1])
def verify_pose(p,r=PIN_R,layer=DZ):
    links=[(n,a,b,z if n=='ground' else 2*layer if n=='coupler' else layer) for n,a,b,z in LINKS]
    pins=[(n,lo,hi) for n,lo,hi in PINS];errors=[];gaps=[]
    for (n,a,b,z),l in zip(links,LENGTHS):errors.append(abs(float(np.linalg.norm(p[b]-p[a]))-l))
    for i,(n,a,b,z) in enumerate(links):
        for _,c,d,w in links[i+1:]:
            zg=abs(z-w)-THICK
            if zg>0:gaps.append(zg);continue
            # Only crank/rocker share a layer, their disjoint segments are
            # guaranteed by the independent orientation intersection test.
            v=p[b]-p[a];q=p[d]-p[c]
            cross=lambda x,y:float(x[0]*y[1]-x[1]*y[0])
            det=cross(v,q);intersects=False
            if abs(det)>1e-12:
                s=cross(p[c]-p[a],q)/det;t=cross(p[c]-p[a],v)/det
                intersects=0<=s<=1 and 0<=t<=1
            dist=0. if intersects else min(pdist(p[x],p[y],p[z0]) for x,y,z0 in ((a,c,d),(b,c,d),(c,a,b),(d,a,b)))
            gaps.append(dist-2*LINK_R)
    for n,lo,hi in pins:
        for _,a,b,z in links:
            zg=gap_z((lo,hi),(z-THICK/2,z+THICK/2))
            if n in (a,b):
                gaps.append(HOLE_R-r)
                if lo>z-THICK/2 or hi<z+THICK/2:gaps.append(-1.)
            else:
                gaps.append(max(zg,pdist(p[n],p[a],p[b])-r-LINK_R))
    for i,(a,lo,hi) in enumerate(pins):
        for b,l,h in pins[i+1:]:gaps.append(max(gap_z((lo,hi),(l,h)),float(np.linalg.norm(p[a]-p[b]))-2*r))
    return dict(passed=max(errors)<1e-9 and min(gaps)>0.,closure_error=max(errors),min_gap=min(gaps))
def transforms(p):
    out={}
    for n,a,b,z in LINKS:
        d=p[b]-p[a];out[n]=(float(p[a][0]),float(p[a][1]),z,math.atan2(d[1],d[0]))
    for n,lo,hi in PINS:out['pin_'+n]=(float(p[n][0]),float(p[n][1]),lo,0.)
    return out
def tree(m,t):
    x,y,z,a=t;c=math.cos(a);s=math.sin(a)
    v=[Vector((x+c*w.co.x-s*w.co.y,y+s*w.co.x+c*w.co.y,z+w.co.z)) for w in m.vertices]
    m.calc_loop_triangles();f=[tuple(q.vertices) for q in m.loop_triangles]
    return BVHTree.FromPolygons(v,f,all_triangles=True,epsilon=0.)
def mesh_collisions(parts,p):
    tr=transforms(p);trees={n:tree(m,tr[n]) for n,m in parts.items()};names=list(trees);hits=[]
    for i,a in enumerate(names):
        for b in names[i+1:]:
            if trees[a].overlap(trees[b]):hits.append([a,b])
    return hits
def save_assembly(parts,poses,dest):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    obs={}
    colors=[(.2,.25,.3,1),(.12,.45,.8,1),(.2,.65,.35,1),(.9,.45,.12,1)]
    for i,(n,m) in enumerate(parts.items()):
        ob=bpy.data.objects.new(n,m);bpy.context.collection.objects.link(ob);obs[n]=ob
        mat=bpy.data.materials.new(n+'_material');mat.diffuse_color=colors[i] if i<4 else (.62,.65,.7,1)
        m.materials.append(mat);ob.color=mat.diffuse_color
    # 361 integer-frame poses; unwrap rotation to avoid artificial jumps.
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
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase204_four_bar.blend'))
    for n,m in parts.items():write_obj(m,dest/f'phase204_{n}.obj')
def main():
    assert bpy.app.version_string=='4.4.3';assert ray_controls()
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True);parts={};audits={}
    for (n,a,b,z),l in zip(LINKS,LENGTHS):parts[n],audits[n]=make_link(n,l)
    for n,lo,hi in PINS:parts['pin_'+n],audits['pin_'+n]=make_pin(n,hi-lo)
    poses=[pose(math.radians(i)) for i in range(361)];assert all(p is not None for p in poses)
    samples=[verify_pose(p) for p in poses]
    collisions=[dict(angle=i,pairs=mesh_collisions(parts,poses[i])) for i in range(0,361,5)]
    # Axial insertion: each pin swept only through its own two bores from the
    # outside of the assembly. Check nonincident XY clearance when traversing
    # every potentially intersected layer, choosing the nearer outside end.
    p=poses[0];insertion={}
    for n,lo,hi in PINS:
        gaps=[]
        from_bottom=n in ('A','D')
        for _,a,b,z in LINKS:
            if n in (a,b):gaps.append(HOLE_R-PIN_R);continue
            traversed=(z-THICK/2<=hi) if from_bottom else (z+THICK/2>=lo)
            if traversed:gaps.append(pdist(p[n],p[a],p[b])-PIN_R-LINK_R)
        insertion[n]=min(gaps)
    controls=dict(impossible_length=pose(0.,(3.,1.,.3,.3)) is None,
                  oversized_pin=not verify_pose(poses[0],r=.19)['passed'],
                  overlapping_layers=not verify_pose(poses[0],layer=.10)['passed'])
    gate=all(a['passed'] for a in audits.values()) and all(s['passed'] for s in samples) and not any(c['pairs'] for c in collisions) and all(g>0 for g in insertion.values()) and all(controls.values())
    if gate:save_assembly(parts,poses,dest)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,parts=audits,
             samples=samples,mesh_collisions=collisions,insertion_gaps=insertion,controls=controls,
             continuous_certified=False,retention_designed=False,elapsed=time.perf_counter()-start)
    (dest/'phase204_four_bar.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE204_SUMMARY',json.dumps(dict(gate=gate,parts=sum(a['passed'] for a in audits.values()),
        poses=len(samples),passed_poses=sum(s['passed'] for s in samples),mesh_poses=len(collisions),
        collision_poses=sum(bool(c['pairs']) for c in collisions),min_gap=min(s['min_gap'] for s in samples),
        max_closure_error=max(s['closure_error'] for s in samples),insertion_gaps=insertion,
        controls=controls,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
