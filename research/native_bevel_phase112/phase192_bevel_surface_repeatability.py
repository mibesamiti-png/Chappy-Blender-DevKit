"""Phase 192: measured surface repeatability of native semantic bevel.
Compare reindexing and tessellation separately. Sampled nearest surface distances,
not exact Hausdorff distance or an independent exact intersection oracle.
Fixed screen: maximum sampled symmetric distance <= 5% of requested offset.
Research negative results are retained; CI gate requires complete safe measurements.
"""
import json,sys,time,itertools
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase191_semantic_rim_bevel import attempt
from phase190_semantic_cap_selection import plan,CASES,FRESH
from phase188_circular_frustum_recognition import build
from phase170_reindexed_state_planner import reindex
from phase171_planar_topology_variants import arrays
from phase167_protected_local_bevel import signature

ROOT=Path(__file__).resolve().parent
MODES=('quad','diag_a','mixed')
SEEDS=(1901,1922)
def snapshot(m):
    m.calc_loop_triangles()
    return (np.asarray([tuple(v.co) for v in m.vertices],dtype=float),
            np.asarray([tuple(t.vertices) for t in m.loop_triangles],dtype=int))
def samples(s):
    V,T=s;A=V[T];a,b,c=A[:,0],A[:,1],A[:,2]
    return np.concatenate((a,b,c,(a+b)*.5,(b+c)*.5,(c+a)*.5,(a+b+c)/3),axis=0)
def distances(source,target):
    V,T=target
    tree=BVHTree.FromPolygons([Vector(v) for v in V],T.tolist(),all_triangles=True,epsilon=0.)
    values=[]
    for p in samples(source):
        loc,normal,index,d=tree.find_nearest(Vector(p))
        if loc is None or d is None or not np.isfinite(d):raise ValueError('nearest query failed')
        values.append(float(d))
    return np.asarray(values)
def compare(a,b,width):
    x=distances(a,b);y=distances(b,a);d=np.concatenate((x,y))
    maximum=float(d.max());ratio=maximum/width
    return dict(samples=len(d),max_distance=maximum,p95=float(np.percentile(d,95)),
        rms=float(np.sqrt(np.mean(d*d))),max_over_offset=ratio,screen_pass=bool(ratio<=.05))
def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter();rows=[];pairs=[]
    t=(np.asarray([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]),np.asarray([[0,1,2]]))
    same=compare(t,t,.1);shift=compare(t,(t[0]+[0.,0.,.01],t[1]),.1)
    assert same['max_distance']<1e-7 and same['screen_pass']
    assert abs(shift['max_distance']-.01)<1e-7 and not shift['screen_pass']
    for name,n,r0,r1,h,axis,c,defect,expected in CASES+FRESH:
        if expected!='frustum':continue
        width=.01*min(h,r0,r1)
        for role in ('small_end','large_end'):
            outputs={}
            for mode in MODES:
                m=build(n,r0,r1,h,axis,c,defect,mode)
                try:
                    for seed in SEEDS:
                        q=reindex(m,seed)
                        try:
                            before=signature(*arrays(q));capture=[]
                            out=attempt(q,role,plan(q,role),width,observer=lambda z:capture.append(snapshot(z)))
                            row=dict(name=name,mode=mode,seed=seed,role=role,
                                qualified=out['qualified'],reason=out['reason'],
                                input_unchanged=out['input_unchanged'] and signature(*arrays(q))==before,
                                persistent_edit=out['persistent_edit'],captured=len(capture)==1)
                            rows.append(row)
                            if len(capture)==1:outputs[(mode,seed)]=capture[0]
                            print('PHASE192_ROW',json.dumps(row,allow_nan=False),flush=True)
                        finally:bpy.data.meshes.remove(q)
                finally:bpy.data.meshes.remove(m)
            requests=[('reindex',(mode,SEEDS[0]),(mode,SEEDS[1])) for mode in MODES]
            requests.extend(('tessellation',('quad',seed),(mode,seed)) for seed in SEEDS for mode in MODES[1:])
            for kind,a,b in requests:
                pair=dict(name=name,role=role,kind=kind,a=list(a),b=list(b),width=width,
                          measured=a in outputs and b in outputs)
                if pair['measured']:pair.update(compare(outputs[a],outputs[b],width))
                pairs.append(pair);print('PHASE192_PAIR',json.dumps(pair,allow_nan=False),flush=True)
    gate=(len(rows)==72 and len(pairs)==84 and all(r['qualified'] and r['captured'] and r['input_unchanged'] and not r['persistent_edit'] for r in rows)
          and all(p['measured'] for p in pairs))
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,pairs=pairs,
        controls=dict(identical=same,translated=shift),screen_fraction=.05,elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True)
    (p/'phase192_bevel_surface_repeatability.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE192_SUMMARY',json.dumps(dict(cases=len(rows),pairs=len(pairs),gate=gate,
        reindex_pass=sum(p.get('screen_pass',False) for p in pairs if p['kind']=='reindex'),
        tessellation_pass=sum(p.get('screen_pass',False) for p in pairs if p['kind']=='tessellation'),
        elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
