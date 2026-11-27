"""Native fixed four-slot Geneva geometry trial; no physical drive claim."""
import math,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from phase212_geneva import Geneva
from phase212_geneva_geometry import profiles,rotate
from phase212_radial_cam import _edges,_nearest_and_inside
from phase212_design_evaluation import Limit,evaluate
from phase204_four_bar import prism,tree
from phase206_hybrid_machine import closed,polygon_area,ring
from phase195_tapered_spacer import drill,basis,N
from phase196_spacer_verification import Rays

def part(name,xy,h,bore,radial=False):
    if radial:
        # Star-shaped driver: direct annulus avoids Boolean cap triangulation.
        inner=[tuple(v*bore/math.hypot(*p) for v in p) for p in xy]
        m,r=ring(name,list(xy),inner,h=h)
    else:
        raw=prism(name,list(xy),-h/2,h/2)
        m=drill(raw,np.zeros(3),basis((0,0,1)),h,bore)
        bpy.data.meshes.remove(raw)
        area=N*bore*bore*math.sin(math.tau/N)/2
        r=closed(m,1,(polygon_area(xy)-area)*h)
    ray=Rays(m)
    r['bore_open']=ray.cast((0,0,h),(0,0,-1),2*h) is None
    r['passed']=bool(r['passed'] and r['bore_open'])
    return m,r

def main():
    assert bpy.app.version_string=='4.4.3'
    dest=ROOT/'results'/'phase212_geneva_geometry';dest.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    g=Geneva(4,10,.3,.05);wheel,driver,dims=profiles(g)
    h=.6
    wm,wa=part('four slot wheel',wheel,h,.7)
    dm,da=part('relieved locking disk',driver,h,.5,radial=True)
    pinxy=[(.3*math.cos(i*math.tau/96),.3*math.sin(i*math.tau/96)) for i in range(96)]
    pm=prism('drive pin',pinxy,-h/2,h/2)
    pa=closed(pm,0,polygon_area(pinxy)*h)
    meshes=dict(wheel=wm,driver=dm,pin=pm)
    objects={}
    for name,m in meshes.items():
        o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o)
        o.color=(.25,.55,.85,1) if name=='wheel' else (.9,.55,.15,1);objects[name]=o
    edges=_edges(wheel);rows=[];locks=[]
    samples=721
    def transforms(u,delta=0.):
        a=g.sample(u)[0]+delta;theta=math.tau*(u-.5);x,y=g.pin(u)
        return dict(wheel=(0,0,0,a),driver=(10,0,0,-theta),pin=(x,y,0,0))
    for i in range(samples):
        u=i/(samples-1);tr=transforms(u)
        wt=tree(wm,tr['wheel']);dt=tree(dm,tr['driver']);pt=tree(pm,tr['pin'])
        x,y=rotate(g.pin(u),-tr['wheel'][3]);d,inside=_nearest_and_inside((x,y),edges)
        gap=(-d if inside else d)-g.pin_radius
        r=dict(frame=i+1,phase=u,pin_gap=gap,pin_overlap=int(bool(wt.overlap(pt))),disk_overlap=int(bool(wt.overlap(dt))))
        rows.append(r)
        if u<g.start or u>g.end:
            # At each dwell sample, test blocking under both signed 2 degree perturbations.
            hits=[bool(tree(wm,transforms(u,sign*math.radians(2))['wheel']).overlap(dt)) for sign in (-1,1)]
            locks.append(dict(frame=i+1,phase=u,blocks_both=all(hits),signed_hits=hits))
        for name,o in objects.items():
            x,y,z,a=tr[name];o.location=(x,y,z);o.rotation_euler.z=a
            o.keyframe_insert(data_path='location',frame=i+1);o.keyframe_insert(data_path='rotation_euler',frame=i+1)
    obs={k:[(r['frame'],'wheel',r[k]) for r in rows] for k in ('pin_gap','pin_overlap','disk_overlap')}
    evaluation=evaluate((Limit('pin_gap',lower=-1e-6),Limit('pin_overlap',upper=0),Limit('disk_overlap',upper=0)),obs)
    # A deliberate 2 degree wheel error at central dwell must hit the locking disk.
    controls=dict(mid_dwell_lock=locks[0]['blocks_both'],
        pin_intrusion=bool(tree(wm,(0,0,0,0)).overlap(tree(pm,(1.5,0,0,0)))))
    lock_fraction=sum(r['blocks_both'] for r in locks)/len(locks)
    gate=all(r['passed'] for r in (wa,da,pa)) and evaluation['status']=='pass' and all(controls.values())
    lock_gate=lock_fraction>=.98
    out=dict(complete=True,native_executed=True,geometry_gate=gate,parts=dict(wheel=wa,driver=da,pin=pa),
        dimensions=dims,evaluation=evaluation,rows=rows,lock_samples=locks,lock_fraction=lock_fraction,
        controls=controls,sampled_lock_gate=lock_gate,lock_target=.98,continuous_lock_proven=False,physical_contact_certified=False,manufacturing_certified=False)
    (dest/'report.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    sc=bpy.context.scene;sc.frame_start=1;sc.frame_end=samples;sc.render.fps=60;sc.frame_set(1)
    if gate and lock_gate:bpy.ops.wm.save_as_mainfile(filepath=str(dest/'geneva_geometry_preview.blend'))
    print('PHASE212J_SUMMARY',json.dumps(dict(gate=gate,part_pass={k:v['passed'] for k,v in out['parts'].items()},
        evaluation=evaluation,lock_fraction=lock_fraction,sampled_lock_gate=lock_gate,controls=controls),allow_nan=False),flush=True)
if __name__=='__main__':main()
