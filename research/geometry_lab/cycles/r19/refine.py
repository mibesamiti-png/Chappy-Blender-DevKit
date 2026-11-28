"""R19 detached refinement of the actual R18 joined triangle arrays.
Source vertices, source faces, bridge connectivity and all UV corners are fixed.
No Blender shading or custom-normal claim.
"""
import numpy as np
from cycles.r14.audit import incidence,uv_audit,boundary_normals
from cbdk_geometry import Mesh,quality
from cycles.r2.oracle import mesh_hits
from cycles.r7.evaluate import assess

def normals(v,f):
    t=v[f]; n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); length=np.linalg.norm(n,axis=1)
    if np.any(length<=1e-10): raise ValueError("degenerate triangle")
    return n/length[:,None]

def angles(n,pairs):
    p=np.asarray(pairs,int)
    a=np.degrees(np.arccos(np.clip(np.sum(n[p[:,0]]*n[p[:,1]],axis=1),-1,1)))
    return dict(mean_deg=float(a.mean()),p95_deg=float(np.percentile(a,95)),max_deg=float(a.max()))

def distortion(v,f,uv):
    t=v[f]; x=t[:,1]-t[:,0]; y=t[:,2]-t[:,0]
    l=np.linalg.norm(x,axis=1); cross=np.linalg.norm(np.cross(x,y),axis=1)
    if np.any(l<=1e-10) or np.any(cross<=1e-10): raise ValueError("degenerate XYZ")
    b=np.zeros((len(f),2,2)); b[:,0,0]=l; b[:,0,1]=np.sum(x*y,axis=1)/l; b[:,1,1]=cross/l
    d=np.stack((uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]),axis=2)
    s=np.linalg.svd(d@np.linalg.inv(b),compute_uv=False); r=s[:,0]/s[:,1]
    return float(np.percentile(r,95)),float(r.max())

def refine(row,case):
    v=np.asarray(row["vertices"],float); f=np.asarray(row["triangles"],int); uv=np.asarray(row["corner_uv"],float)
    ids=np.asarray(row["face_ids"],int); bridge=ids<0
    if not row["source_preserved"] or not row["scene_restored"] or not np.any(bridge) or len(f)>600: raise ValueError("invalid source")
    edges=incidence(f); n=normals(v,f)
    pinned=set(f[~bridge].ravel()); free=sorted(set(f[bridge].ravel())-pinned)
    if not free: raise ValueError("no interior vertices")
    boundary_pairs=[]; internal_pairs=[]; targets={i:[] for i in free}
    neighbors={i:set() for i in range(len(v))}
    for e,refs in edges.items():
        a,b=e; neighbors[a].add(b); neighbors[b].add(a)
        if len(refs)>2: raise ValueError("nonmanifold")
        if len(refs)!=2: continue
        i,j=refs
        if bridge[i] and bridge[j]: internal_pairs.append((i,j))
        if bridge[i]==bridge[j]: continue
        bi,si=(i,j) if bridge[i] else (j,i)
        boundary_pairs.append((bi,si))
        k=next(int(x) for x in f[bi] if x not in e)
        if k in targets:
            edge=v[b]-v[a]; length=np.linalg.norm(edge)
            altitude=np.linalg.norm(np.cross(edge,v[k]-v[a]))/length
            if altitude<=1e-10: raise ValueError("zero altitude")
            # normalized plane distance is a local tangency proxy, not a shading normal.
            targets[k].append((n[si]/altitude,-float(n[si]@(v[k]-v[a]))/altitude))
    if not boundary_pairs or not internal_pairs: raise ValueError("missing edge sets")
    strip_ids=sorted(set(f[bridge].ravel())); index={k:i for i,k in enumerate(strip_ids)}
    sf=np.array([[index[int(k)] for k in t] for t in f[bridge]])
    sv=v[strip_ids]; su=uv[bridge]
    old_geo=assess(Mesh(sv,sf),case)
    if old_geo["status"]!="passed" or mesh_hits(Mesh(v,f)): raise ValueError("invalid baseline")
    old=angles(n,boundary_pairs); old_internal=angles(n,internal_pairs)
    old_uv=distortion(v,f,uv); old_strip=distortion(sv,sf,su)
    old_q=old_geo["quality"]["min_triangle_quality"]
    idx={k:i for i,k in enumerate(free)}; m=len(free); basis=np.eye(3)
    caps=np.array([.4*min(np.linalg.norm(v[k]-v[j]) for j in neighbors[k]) for k in free])
    possible=[]; rejected={"normal":0,"uv":0,"geometry":0,"oracle":0}; attempted=0
    for smooth in (.05,.25,1.):
        # Least-squares normal plane residual + displacement and graph regularization.
        A=np.zeros((3*m,3*m)); B=np.zeros(3*m)
        for k,i in idx.items():
            sl=slice(3*i,3*i+3); local=max(caps[i]/.4,1e-8)
            A[sl,sl]+=(.10/(local*local))*basis
            for a,b in targets[k]:
                A[sl,sl]+=np.outer(a,a); B[sl]+=a*b
            for j in neighbors[k]:
                weight=smooth/max(float(np.linalg.norm(v[k]-v[j]))**2,1e-10)
                A[sl,sl]+=weight*basis
                if j in idx:
                    q=idx[j]; A[sl,3*q:3*q+3]-=weight*basis
        d=np.linalg.solve(A,B).reshape(m,3)
        lengths=np.linalg.norm(d,axis=1)
        d*=np.minimum(1.,caps/np.maximum(lengths,1e-15))[:,None]
        for fraction in (.125,.25,.5,.75,1.):
            attempted+=1
            z=v.copy(); z[free]=(v[free]+fraction*d).astype(np.float32).astype(float)
            try: nn=normals(z,f)
            except ValueError: rejected["geometry"]+=1; continue
            if np.any(np.sum(nn*n,axis=1)<.5): rejected["geometry"]+=1; continue
            a=angles(nn,boundary_pairs); internal=angles(nn,internal_pairs)
            if (a["p95_deg"]>=old["p95_deg"]-1e-8 or a["max_deg"]>old["max_deg"]+1e-8
                or a["mean_deg"]>old["mean_deg"]+1e-8 or internal["p95_deg"]>1.05*old_internal["p95_deg"]+1e-8
                or internal["max_deg"]>old_internal["max_deg"]+5): rejected["normal"]+=1; continue
            q=quality(Mesh(z[strip_ids],sf))["min_triangle_quality"]
            if q<max(.1,.9*old_q): rejected["geometry"]+=1; continue
            du=distortion(z,f,uv); ds=distortion(z[strip_ids],sf,su)
            if any(x>y+1e-6 for x,y in zip(du+ds,old_uv+old_strip)):
                rejected["uv"]+=1; continue
            possible.append((a["p95_deg"],a["max_deg"],smooth,fraction,z))
    selected=v.copy(); method="baseline"; final_geo=old_geo
    for _,_,smooth,fraction,z in sorted(possible,key=lambda x:x[:4]):
        g=assess(Mesh(z[strip_ids],sf),case)
        if g["status"]!="passed" or mesh_hits(Mesh(z,f)):
            rejected["oracle"]+=1; continue
        selected=z; method=f"smooth{smooth}_step{fraction}"; final_geo=g; break
    # Re-measure final output using frozen R14 and independent CGAL, not proxy.
    after=boundary_normals(selected[strip_ids],sf,selected,f)
    before=boundary_normals(sv,sf,v,f)
    if max(abs(before[k]-old[k]) for k in old)>1e-8: raise ValueError("normal measurement disagreement")
    internal=angles(normals(selected,f),internal_pairs)
    qa=uv_audit(selected,f,uv); qs=uv_audit(selected[strip_ids],sf,su)
    qb=uv_audit(v,f,uv); qbs=uv_audit(sv,sf,su)
    for q in (qa,qs,qb,qbs): q.pop("signed_areas")
    hits=len(mesh_hits(Mesh(selected,f)))
    fixed=bool(np.array_equal(selected[sorted(pinned)],v[sorted(pinned)]))
    def clean(q): return q["overlap_pairs"]==q["mixed_winding_islands"]==q["degenerate_uv"]==0 and q["islands"]==1
    passed=bool(fixed and hits==0 and final_geo["status"]=="passed" and
        final_geo["quality"]["min_triangle_quality"]>=max(.1,.9*old_q) and
        all(clean(q) for q in (qa,qs)) and
        all(after[k]<=before[k]+1e-8 for k in old) and
        internal["p95_deg"]<=1.05*old_internal["p95_deg"]+1e-8 and internal["max_deg"]<=old_internal["max_deg"]+5 and
        all(a[k]<=b[k]+1e-6 for a,b in ((qa,qb),(qs,qbs)) for k in ("anisotropy_p95","anisotropy_max")))
    return dict(passed=passed,method=method,attempted=attempted,screened_candidates=len(possible),rejected=rejected,
      before=before,after=after,p95_gain=1-after["p95_deg"]/before["p95_deg"],
      internal_before=old_internal,internal_after=internal,uv_before=qb,uv_after=qa,strip_uv_before=qbs,strip_uv_after=qs,
      geometry_before=old_geo,geometry_after=final_geo,source_xyz_exact=fixed,joined_cgal_pairs=hits,
      max_displacement=float(np.linalg.norm(selected-v,axis=1).max()),vertices=selected.tolist(),
      triangles=f.tolist(),corner_uv=uv.tolist(),face_ids=ids.tolist(),materials=row["materials"],seam_flags=row["seam_flags"])
