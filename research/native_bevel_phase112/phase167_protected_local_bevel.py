"""Research only: explicit region-scoped native bevel, protected faces and rollback.
New synthetic three-ring rectangular prism. No arbitrary user mesh or inferred intent.
"""
import hashlib,json,math,sys,time
from pathlib import Path
import bpy,bmesh
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase160_operation_contracts import measure,close
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
EPS=1e-5
def fixture():
    V=[(x,y,z) for x in (-1.,0.,1.) for y,z in ((-1.,-1.),(1.,-1.),(1.,1.),(-1.,1.))]
    F=[(3,2,1,0),(8,9,10,11)]
    F.extend((4*k+j,4*k+(j+1)%4,4*(k+1)+(j+1)%4,4*(k+1)+j) for k in range(2) for j in range(4))
    # The ring traverses +X-normal; side winding must face outwards.
    return V,F
def signature(V,F):
    return hashlib.sha256(np.asarray(V,dtype='<f8').tobytes()+json.dumps([list(f) for f in F]).encode()).hexdigest()
def face_key(V,f):
    q=tuple(tuple(round(float(x),6) for x in V[i]) for i in f)
    # Preserve orientation as well as cyclic adjacency.
    return min(q[i:]+q[:i] for i in range(len(q)))
def audit(m,source):
    V=[tuple(v.co) for v in m.vertices];F=[tuple(f.vertices) for f in m.polygons]
    a=measure(m,'cube');sv,sf=source
    protected=[f for f in sf if all(sv[i][0]<=0 for i in f)]
    wanted={face_key(sv,f) for f in protected}
    # Protect all source faces on the left half, and forbid added faces there.
    found={face_key(V,f) for f in F if all(V[i][0]<=EPS for i in f)}
    pv=np.asarray([v for v in sv if v[0]<=0]);av=np.asarray(V)
    fixed_error=max(float(np.min(np.linalg.norm(av-v,axis=1))) for v in pv)
    oblique=[f for f,p in zip(F,m.polygons) if max(abs(float(n)) for n in p.normal)<.999]
    a.update(protected_faces=len(wanted),protected_faces_preserved=len(wanted&found),
        protected_exact=wanted==found,fixed_error=fixed_error,
        oblique_faces_local=bool(oblique) and all(V[i][0]>0 for f in oblique for i in f),
        sha256=signature(V,F))
    return a
def apply(m,region,width):
    if region=='keep':return 0
    bm=bmesh.new()
    try:
        bm.from_mesh(m);bm.verts.ensure_lookup_table();bm.normal_update()
        if region=='right':geom=[e for e in bm.edges if all(v.co.x>.99 for v in e.verts)]
        elif region=='left':geom=[e for e in bm.edges if all(v.co.x<-.99 for v in e.verts)]
        elif region=='all':geom=[e for e in bm.edges if e.is_manifold and e.calc_face_angle()>math.radians(30)]
        else:raise ValueError(region)
        count=len(geom);assert count>0 and all(e.is_manifold for e in geom)
        bmesh.ops.bevel(bm,geom=geom,offset=width,offset_type='OFFSET',segments=3,profile=.5,
            affect='EDGES',clamp_overlap=True,loop_slide=True)
        bm.normal_update();bm.to_mesh(m);m.update()
        return count
    finally:bm.free()
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source
    m=bpy.data.meshes.new('p167_source');m.from_pydata(V,[],F);m.update()
    try:
        base=audit(m,source);assert base['clean'] and base['protected_exact'] and abs(base['volume']-8)<EPS
        rows=[]
        for label,region,width in [('keep','keep',0.),('local_small','right',.10),
                                  ('local_large','right',.20),('wrong_end','left',.10),('global','all',.10)]:
            c=m.copy()
            try:
                n=apply(c,region,width);a=audit(c,source);q=a['metrics']
                checks=dict(clean=a['clean'],closed=q['boundary_edges']==0 and q['euler']==2,
                    bounds=close(a['bounds'],base['bounds']),volume=.95*base['volume']<=a['volume']<base['volume']-EPS,
                    protected=a['protected_exact'] and a['fixed_error']<=EPS,
                    localized_rounding=a['oblique_faces_local'],changed=a['sha256']!=base['sha256'])
                row=dict(name=label,region=region,width=width,selected_edges=n,checks=checks,passed=all(checks.values()),
                    faces=q['faces'],volume=a['volume'],oblique_faces=a['oblique_faces'],
                    protected_faces=a['protected_faces'],protected_preserved=a['protected_faces_preserved'],
                    fixed_error=a['fixed_error'],native_audit=a)
            finally:bpy.data.meshes.remove(c)
            row['source_unchanged']=audit(m,source)['sha256']==base['sha256'];assert row['source_unchanged']
            rows.append(row);print('PHASE167_ROW',json.dumps(row,allow_nan=False),flush=True)
        assert all(not r['passed'] for r in rows if r['name'] in ('keep','wrong_end','global'))
        selected=next((r['name'] for r in rows if r['passed']),None)
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,selected=selected,
            source_faces=base['metrics']['faces'],elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase167_protected_local_bevel.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        print('PHASE167_SUMMARY',json.dumps(dict(candidates=len(rows),qualified=sum(r['passed'] for r in rows),
            selected=selected,source_preserved=sum(r['source_unchanged'] for r in rows),elapsed=out['elapsed'])),flush=True)
    finally:bpy.data.meshes.remove(m)
if __name__=='__main__':main()
