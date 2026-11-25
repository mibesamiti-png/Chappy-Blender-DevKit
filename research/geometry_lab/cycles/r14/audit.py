"""R14 diagnostic only: audit actual saved triangle UVs and joined geometry."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree

EPS=1e-10
OVERLAP_AREA=1e-9
UV_MATCH=1e-5


def incidence(faces):
    edges=defaultdict(list)
    for i,tri in enumerate(faces):
        for a,b in zip(tri,np.roll(tri,-1)):
            edges[tuple(sorted((int(a),int(b))))].append(i)
    return edges


def uv_audit(vertices,faces,corners):
    v=np.asarray(vertices,float); f=np.asarray(faces,int); u=np.asarray(corners,float)
    if v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3 or u.shape!=(len(f),3,2) or not len(f):
        raise ValueError('bad geometry/UV dimensions')
    if not np.isfinite(v).all() or not np.isfinite(u).all() or np.any(f<0) or np.any(f>=len(v)):
        raise ValueError('nonfinite or invalid index')
    if len(f)>600: raise ValueError('R14 face budget exceeded')
    tri=v[f]; x=tri[:,1]-tri[:,0]; y=tri[:,2]-tri[:,0]
    l=np.linalg.norm(x,axis=1); cross=np.linalg.norm(np.cross(x,y),axis=1)
    if np.any(l<=EPS) or np.any(cross<=EPS): raise ValueError('degenerate XYZ triangle')
    b=np.zeros((len(f),2,2)); b[:,0,0]=l; b[:,0,1]=np.sum(x*y,axis=1)/l; b[:,1,1]=cross/l
    d=np.stack((u[:,1]-u[:,0],u[:,2]-u[:,0]),axis=2)
    jac=d@np.linalg.inv(b); sv=np.linalg.svd(jac,compute_uv=False)
    areas=np.linalg.det(d)*.5
    valid=np.abs(areas)>EPS
    ratios=sv[valid,0]/sv[valid,1] if np.any(valid) else np.array([])
    density=np.sqrt(np.abs(np.linalg.det(jac[valid]))) if np.any(valid) else np.array([])
    parent=list(range(len(f)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    for (a,c),refs in incidence(f).items():
        if len(refs)!=2: continue
        p,q=refs
        pmap=dict(zip(f[p],u[p])); qmap=dict(zip(f[q],u[q]))
        if max(np.max(np.abs(pmap[k]-qmap[k])) for k in (a,c))<=UV_MATCH:
            parent[root(q)]=root(p)
    islands=np.array([root(i) for i in range(len(f))])
    mixed=0; minority=0
    for i in set(islands):
        subset=areas[islands==i]; pos=int(np.sum(subset>EPS)); neg=int(np.sum(subset<-EPS))
        mixed+=int(pos>0 and neg>0); minority+=min(pos,neg)
    ids=np.flatnonzero(valid); polys=[Polygon(u[i]) for i in ids]
    count=within=0; total=within_area=0.; affected=set(); robust_count=robust_within=0
    if polys:
        tree=STRtree(polys)
        for i,p in enumerate(polys):
            for j in tree.query(p):
                if j<=i: continue
                area=p.intersection(polys[j]).area
                if area<=OVERLAP_AREA: continue
                a,c=int(ids[i]),int(ids[j]); count+=1; total+=area; affected.update((a,c))
                if islands[a]==islands[c]: within+=1; within_area+=area
                if area>1e-6:
                    robust_count+=1; robust_within+=int(islands[a]==islands[c])
    return dict(faces=len(f),degenerate_uv=int(np.sum(~valid)),positive_uv=int(np.sum(areas>EPS)),negative_uv=int(np.sum(areas<-EPS)),islands=len(set(islands)),mixed_winding_islands=mixed,minority_winding_faces=minority,anisotropy_p95=float(np.percentile(ratios,95)) if len(ratios) else None,anisotropy_max=float(max(ratios)) if len(ratios) else None,density_p95_p05=float(np.percentile(density,95)/np.percentile(density,5)) if len(density) else None,overlap_pairs=count,within_island_overlap_pairs=within,cross_island_overlap_pairs=count-within,overlap_pair_area=total,within_island_overlap_pair_area=within_area,overlap_affected_faces=len(affected),overlap_pairs_area_gt_1e_minus6=robust_count,within_island_overlap_pairs_area_gt_1e_minus6=robust_within,wide_u_faces=int(np.sum(np.ptp(u[:,:,0],axis=1)>.5)),signed_areas=areas.tolist())


def boundary_normals(strip_v,strip_f,joined_v,joined_f):
    # Blender writes float32 XYZ. Identify actual assembled triangles, not inferred collars.
    sv=np.asarray(strip_v,dtype=np.float32); sf=np.asarray(strip_f,int)
    jv=np.asarray(joined_v,dtype=np.float32); jf=np.asarray(joined_f,int)
    lookup={tuple(p):i for i,p in enumerate(jv)}
    if len(lookup)!=len(jv): raise ValueError('ambiguous joined XYZ')
    mapping=np.array([lookup[tuple(p)] for p in sv]); mapped=mapping[sf]
    keys={tuple(sorted(t)) for t in mapped}
    joined_keys=[tuple(sorted(t)) for t in jf]
    if len(set(joined_keys))!=len(jf) or not keys.issubset(set(joined_keys)): raise ValueError('strip triangle correspondence failed')
    strip_mask=np.array([k in keys for k in joined_keys]); tri=jv[jf].astype(float)
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); l=np.linalg.norm(n,axis=1)
    if np.any(l<=EPS): raise ValueError('degenerate joined XYZ')
    n/=l[:,None]; edges=incidence(jf); angles=[]
    incidence_sf=incidence(sf)
    for a,b in incidence_sf:
        if len(incidence_sf[(a,b)])!=1: continue
        refs=edges[tuple(sorted((int(mapping[a]),int(mapping[b]))))]
        if len(refs)!=2 or strip_mask[refs[0]]==strip_mask[refs[1]]: raise ValueError('missing source/bridge edge')
        angles.append(float(np.degrees(np.arccos(np.clip(n[refs[0]]@n[refs[1]],-1,1)))))
    if not angles: raise ValueError('no boundary normal samples')
    return dict(edges=len(angles),mean_deg=float(np.mean(angles)),p95_deg=float(np.percentile(angles,95)),max_deg=max(angles))


def controls():
    v=[[0,0,0],[1,0,0],[0,1,0],[1,1,0]]; f=[[0,1,2],[1,3,2]]
    clean=np.asarray([[[0,0],[1,0],[0,1]],[[1,0],[1,1],[0,1]]],float)
    c=uv_audit(v,f,clean); assert c['overlap_pairs']==0 and c['anisotropy_max']==1 and c['mixed_winding_islands']==0
    stretch=clean*np.array([4,1]); assert abs(uv_audit(v,f,stretch)['anisotropy_max']-4)<1e-10
    folded=clean.copy(); folded[1,1]=[0,0]; q=uv_audit(v,f,folded); assert q['within_island_overlap_pairs']==1 and q['mixed_winding_islands']==1 and abs(q['overlap_pair_area']-.5)<1e-10
    collapsed=clean.copy(); collapsed[1]=0; assert uv_audit(v,f,collapsed)['degenerate_uv']==1
    stack=clean.copy(); stack[1]=clean[0]; q=uv_audit(v,f,stack); assert q['cross_island_overlap_pairs']==1 and abs(q['overlap_pair_area']-.5)<1e-10
    assert uv_audit(v,f,clean+5)['overlap_pairs']==0
    mirrored=clean*np.array([-1,1]); q=uv_audit(v,f,mirrored); assert q['negative_uv']==2 and q['mixed_winding_islands']==0
    # Use a full three-edge collar for exact flat and perpendicular controls.
    xyz=[[0,0,0],[1,0,0],[0,1,0],[0,-1,0],[1,1,0],[-1,0,0]]
    assert abs(boundary_normals(xyz[:3],[[0,1,2]],xyz,[[0,1,2],[1,0,3],[2,1,4],[0,2,5]])['max_deg'])<1e-8
    xyz[3]=[0,0,1]
    assert abs(boundary_normals(xyz[:3],[[0,1,2]],xyz,[[0,1,2],[1,0,3],[2,1,4],[0,2,5]])['max_deg']-90)<1e-8
    return ['clean_square','4x_stretch','folded_overlap','collapsed_uv','stacked_islands','translation_invariance','whole_island_mirror','flat_boundary','right_angle_boundary']


def audit(raw):
    if not raw.get('synthetic_only') or raw.get('approved') or raw.get('cycle') not in ('R11','R12','R13'): raise ValueError('unexpected research input')
    rows=[]; seen=set()
    for r in raw['cases']:
        key=(r['case'],r['uv_mode'],r['arm'])
        if key in seen or r['status']!='generated': raise ValueError('missing or duplicate generated mesh')
        seen.add(key)
        legacy=raw['cycle']=='R11'
        uv=None if legacy else uv_audit(r['strip_vertices'],r['strip_faces'],r['bridge_corner_uvs'])
        normal=boundary_normals(r['strip_vertices'],r['strip_faces'],r['complete_vertices' if legacy else 'joined_vertices'],r['complete_triangles' if legacy else 'joined_triangles'])
        if normal['edges']!=r['expected_shared_edges']: raise ValueError('normal correspondence count mismatch')
        delta=None if not legacy else abs(normal['max_deg']-r['max_normal_discontinuity_deg'])
        if legacy and delta>1e-3: raise ValueError('R11 normal crosscheck mismatch')
        rows.append(dict(case=r['case'],arm=r['arm'],original_split=r['split'],uv_mode=r['uv_mode'],uv=uv,normal=normal,legacy_normal_max_abs_delta_deg=delta))
    if len(rows)!=(28 if raw['cycle']=='R11' else 24): raise ValueError('historical output count mismatch')
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    inp=Path(a.input); raw=json.loads(inp.read_text()); c=controls(); rows=audit(raw)
    result=dict(cycle='R14',approved=False,diagnostic_only=True,source_cycle=raw['cycle'],source_blender=raw['blender'],input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),shapely=shapely.__version__,controls_passed=c,thresholds=dict(area_degenerate=EPS,overlap_area=OVERLAP_AREA,robust_overlap_area=1e-6,uv_match=UV_MATCH),rows=rows)
    with Path(a.output).open('x') as out: json.dump(result,out,indent=2,allow_nan=False)
    print('R14_AUDIT',len(rows),len(c),raw['cycle'])
