"""Phase 195: first bounded end-to-end part fabrication demonstration.
Synthetic regular faceted tapered spacer; semantic rim bevel THEN coaxial bore.
No arbitrary-mesh thickness guarantee, production adoption or attribute support.
Existing native bevel, exact Boolean, mesh audit and ray probes are reused.
"""
import json,sys,time,math
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase188_circular_frustum_recognition import build
from phase190_semantic_cap_selection import plan,robust_classify
from phase189_directional_end_roles import bind
from phase191_semantic_rim_bevel import attempt
from phase182_cylinder_recognition import basis
from phase163_hole_contracts import make,N
from phase160_operation_contracts import measure
from phase170_reindexed_state_planner import reindex
from phase171_planar_topology_variants import arrays
from phase167_protected_local_bevel import signature
from phase196_spacer_verification import Rays,ray_controls,merge_caps
ROOT=Path(__file__).resolve().parent
CASES=[
    ('upright',16,1.6,1.0,2.,(0,0,1),(0,0,0),'small_end'),
    ('tilted',24,.8,1.5,2.4,(1,2,3),(2,-1,1),'large_end'),
    ('horizontal',32,1.4,.9,1.2,(1,0,0),(-1,2,0),'small_end'),
]
def tree(m):
    m.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co.copy() for v in m.vertices],
        [tuple(t.vertices) for t in m.loop_triangles],all_triangles=True,epsilon=0.)
def ray(t,o,d,reach):
    hit=t.ray_cast(Vector(o),Vector(d),reach)
    return None if hit[0] is None else float(hit[3])
def drill(m,c,M,h,r):
    V=[tuple(c+M@np.array([r*math.cos(i*2*math.pi/N),r*math.sin(i*2*math.pi/N),z]))
       for z in (-h*.75,h*.75) for i in range(N)]
    F=[tuple(reversed(range(N))),tuple(range(N,2*N))]
    F.extend((i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N))
    co,cm=make('p195_cutter',V,F)
    ob=bpy.data.objects.new('p195_operand',m);bpy.context.scene.collection.objects.link(ob)
    try:
        mod=ob.modifiers.new('bore','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=co
        bpy.context.view_layer.update()
        dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg)
        out=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=False,depsgraph=dg)
        out.update();return out
    finally:
        bpy.data.objects.remove(ob,do_unlink=True);bpy.data.objects.remove(co,do_unlink=True);bpy.data.meshes.remove(cm)
def write_obj(m,path):
    V,F=arrays(m)
    path.write_text('# Phase 195 synthetic research candidate; not manufacturing certified\n'+
        ''.join('v %.9g %.9g %.9g\n'%tuple(v) for v in V)+
        ''.join('f '+' '.join(str(i+1) for i in f)+'\n' for f in F))
def fabricate(m,role,radius,width,minimum,output=None,probe='normal'):
    before=signature(*arrays(m));rounded=None;final=None;prepared=None
    def finish(reason,**kw):
        return dict(reason=reason,accepted=reason=='complete',source_unchanged=signature(*arrays(m))==before,
                    persistent_edit=False,**kw)
    p=plan(m,role)
    b=bind(m,classifier=robust_classify)['result']
    if p['reason']!='ready' or b['reason']!='small_to_large':return finish('unavailable')
    lo=np.asarray(b['small_end']['center']);hi=np.asarray(b['large_end']['center']);c=(lo+hi)*.5
    h=float(np.linalg.norm(hi-lo));a=(hi-lo)/h;M=basis(a)
    rmin=b['small_end']['radius'];rmax=b['large_end']['radius']
    if not all(math.isfinite(x) and x>0 for x in (radius,width,minimum)):return finish('invalid_dimensions')
    # Conservative preflight for the regular convex ring fixtures only.
    # The actual wall is checked at finite samples after both operations.
    n=len(p['rim_edges']);clearance=rmin*math.cos(math.pi/n)-2*width-radius
    if clearance<minimum:return finish('clearance_preflight',clearance=clearance)
    if probe=='skip_bevel':rounded=m.copy();bev=dict(qualified=False)
    else:
        capture=[]
        bev=attempt(m,role,p,width,observer=lambda z:capture.append(z.copy()))
        if len(capture)==1:rounded=capture[0]
        if not bev['qualified'] or rounded is None:return finish('bevel_rejected',bevel=bev)
    try:
        rb=measure(rounded,'cube');rh=signature(*arrays(rounded))
        final=rounded.copy() if probe=='skip_bore' else drill(rounded,c,M,h,radius*.8 if probe=='wrong_radius' else radius)
        raw_audit=measure(final,'cube');preparation=dict(reason='not_needed')
        # Only retry a failed Boolean mesh audit; do not waive its checks.
        if not raw_audit['clean'] and probe!='skip_bore':
            prepared,preparation=merge_caps(rounded,c,M[:,2],h)
            if prepared is not None:
                retry=drill(prepared,c,M,h,radius*.8 if probe=='wrong_radius' else radius)
                bpy.data.meshes.remove(final);final=retry
        out=measure(final,'cube');q=out['metrics'];tb=tree(rounded);tf=tree(final)
        db=Rays(rounded);df=Rays(final);disagreements=[]
        def checked(t,ind,o,d,reach):
            old=ray(t,o,d,reach);new=ind.cast(o,d,reach)
            if (old is None)!=(new is None) or (old is not None and new is not None and abs(old-new)>tol):
                disagreements.append(dict(origin=list(o),direction=list(d),legacy=old,independent=new))
            return new
        reach=4*(h+rmax);tol=2e-5*max(1.,h,rmax)
        zdir=M[:,2];inside=[]
        for i in range(9):
            d=np.zeros(3) if i==0 else M@np.array([.5*radius*math.cos(i*math.pi/4),.5*radius*math.sin(i*math.pi/4),0.])
            inside.extend(checked(tf,df,c+d+sign*zdir*h, -sign*zdir,reach) for sign in (-1,1))
        radius_ok=[];outer_ok=[];walls=[]
        for z in (-.45*h,0.,.45*h):
            center=c+z*zdir
            for i in range(16):
                d=M@np.array([math.cos(i*math.pi/8),math.sin(i*math.pi/8),0.])
                start=center+d*reach*.5
                inner=checked(tf,df,center,d,reach)
                outer0=checked(tb,db,start,-d,reach);outer1=checked(tf,df,start,-d,reach)
                radius_ok.append(inner is not None and abs(inner-radius)<=tol)
                outer_ok.append(outer0 is not None and outer1 is not None and abs(outer0-outer1)<=tol)
                if inner is not None and outer1 is not None:walls.append(reach*.5-outer1-inner)
        V,F=arrays(m);W,G=arrays(final);present=set(W)
        protected_rim={V[i] for f in p['protected_faces'] for i in F[f]
            if np.linalg.norm((np.asarray(V[i])-c)-zdir*np.dot(np.asarray(V[i])-c,zdir))>radius+minimum}
        area=N*.5*radius*radius*math.sin(2*math.pi/N)
        expected_volume=rb['volume']-area*h
        checks=dict(bevel_verified=bev['qualified'],clean=out['clean'],closed=q['boundary_edges']==0 and q['euler']==0,
            bore_clear=all(x is None for x in inside),radius=all(radius_ok),outer_surface_samples=all(outer_ok),
            wall_samples=len(walls)==48 and min(walls)>=minimum-tol,
            protected_rim=bool(protected_rim) and protected_rim<=present,
            volume=abs(out['volume']-expected_volume)<=max(1e-5,2e-5*rb['volume']),
            intermediate_unchanged=signature(*arrays(rounded))==rh)
        accepted=all(checks.values())
        if accepted and output is not None:write_obj(final,output)
        return finish('complete' if accepted else 'discarded',checks=checks,
            clearance=clearance,min_wall_sample=min(walls) if walls else None,wall_samples=len(walls),
            raw_audit=raw_audit,final_audit=out,preparation=preparation,ray_disagreements=disagreements,
            expected_volume=expected_volume,volume=out['volume'],faces=q['faces'],vertices=q['vertices'],
            euler=q['euler'],bore_radius=radius,bevel_width=width,minimum_wall=minimum)
    finally:
        if final is not None:bpy.data.meshes.remove(final)
        if prepared is not None:bpy.data.meshes.remove(prepared)
        if rounded is not None:bpy.data.meshes.remove(rounded)
def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter();rows=[]
    assert ray_controls()
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    for name,n,r0,r1,h,axis,c,role in CASES:
        for mode in ('quad','mixed'):
            m=build(n,r0,r1,h,axis,c,None,mode);q=None
            try:
                q=reindex(m,1951);r=.35*min(r0,r1);w=.01*min(h,r0,r1);wall=.25*min(r0,r1)
                trials=[('normal',r,'complete'),('oversize',.95*min(r0,r1),'clearance_preflight'),
                        ('skip_bevel',r,'discarded'),('skip_bore',r,'discarded'),('wrong_radius',r,'discarded')]
                for kind,rad,expected in trials:
                    path=dest/f'phase195_{name}_{mode}.obj' if kind=='normal' else None
                    result=fabricate(q,role,rad,w,wall,path,kind)
                    row=dict(name=name,mode=mode,kind=kind,expected=expected,
                        matched=result['reason']==expected,**result)
                    rows.append(row);print('PHASE195_ROW',json.dumps(row,allow_nan=False),flush=True)
            finally:
                if q is not None:bpy.data.meshes.remove(q)
                bpy.data.meshes.remove(m)
    gate=len(rows)==30 and all(r['matched'] and r['source_unchanged'] and not r['persistent_edit'] for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,elapsed=time.perf_counter()-start)
    (dest/'phase195_tapered_spacer.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE195_SUMMARY',json.dumps(dict(cases=len(rows),parts=sum(r['accepted'] for r in rows),
        matched=sum(r['matched'] for r in rows),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
