"""R17 bounded, detached conformal distortion refinement; no XYZ mutation."""
import numpy as np
from collections import defaultdict
from cycles.r14.audit import incidence,uv_audit

def seam_set(f,uv,tol=1e-5):
    result=set()
    for e,refs in incidence(f).items():
        if len(refs)!=2: continue
        a,b=refs; p=dict(zip(f[a],uv[a])); q=dict(zip(f[b],uv[b]))
        if max(np.max(np.abs(p[k]-q[k])) for k in e)>tol: result.add(e)
    return result

def refine(vertices,faces,initial,path):
    v=np.asarray(vertices,float); f=np.asarray(faces,int); u=np.asarray(initial,float)
    if f.ndim!=2 or f.shape[1]!=3 or not 3<=len(f)<=600 or u.shape!=(len(f),3,2) or not np.isfinite(u).all(): raise ValueError("bad chart")
    edges=incidence(f); seam={tuple(sorted(e)) for e in zip(path,path[1:])}
    if seam_set(f,u)!=seam: raise ValueError("initial seam mismatch")
    boundary={e for e,refs in edges.items() if len(refs)==1}
    pins={k for e in boundary|seam for k in e}
    # R16 emits bit-identical shared corners. Separate the two seam copies.
    keys={}; nodes=[]; cf=np.empty_like(f); fixed=[]
    for i,t in enumerate(f):
        for j,vi in enumerate(t):
            key=(int(vi),*map(float,u[i,j]))
            if key not in keys:
                keys[key]=len(nodes); nodes.append(u[i,j].copy()); fixed.append(int(vi) in pins)
            cf[i,j]=keys[key]
    init=np.asarray(nodes); fixed=np.asarray(fixed,bool); free=~fixed
    if not free.any(): return u.copy(),{"method":"baseline","steps":0}
    x=v[f[:,1]]-v[f[:,0]]; y=v[f[:,2]]-v[f[:,0]]
    l=np.linalg.norm(x,axis=1); cross=np.linalg.norm(np.cross(x,y),axis=1)
    if np.any(l<=1e-10) or np.any(cross<=1e-10): raise ValueError("degenerate XYZ")
    B=np.zeros((len(f),2,2)); B[:,0,0]=l; B[:,0,1]=np.sum(x*y,axis=1)/l; B[:,1,1]=cross/l
    inv=np.linalg.inv(B)
    def jac(z):
        t=z[cf]; D=np.stack((t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=2)
        return D@inv
    J=jac(init); det=np.linalg.det(J); sign=np.sign(det)
    if np.any(np.abs(det)<=1e-10) or np.any(sign!=sign[0]): raise ValueError("initial winding")
    def obj(z,p,grad=False):
        J=jac(z); d=np.linalg.det(J); ad=d*sign
        if np.any(ad<=1e-10) or np.any(z<0) or np.any(z>1): return (float("inf"),None)
        q=np.sum(J*J,axis=(1,2))/(2*ad)
        power=q**p; mean=float(np.mean(power))
        if not grad: return np.log(mean)/p,None
        co=np.empty_like(J); co[:,0,0]=J[:,1,1]; co[:,1,1]=J[:,0,0]; co[:,0,1]=-J[:,1,0]; co[:,1,0]=-J[:,0,1]
        G=(J/ad[:,None,None]-q[:,None,None]*co/d[:,None,None])*(q**(p-1)/(len(f)*mean))[:,None,None]
        D=G@np.swapaxes(inv,1,2)
        result=np.zeros_like(z)
        np.add.at(result,cf[:,1],D[:,:,0]); np.add.at(result,cf[:,2],D[:,:,1]); np.add.at(result,cf[:,0],-D.sum(axis=2))
        result[fixed]=0.
        return np.log(mean)/p,result
    def score(z):
        s=np.linalg.svd(jac(z),compute_uv=False); r=s[:,0]/s[:,1]
        return float(np.percentile(r,95)),float(np.max(r))
    base=score(init); candidates=[(base,"baseline",init.copy(),0)]
    for p in (2,6,12):
        z=init.copy(); steps=0; step=.02
        for it in range(180):
            value,g=obj(z,p,True)
            if g is None: break
            scale=float(np.max(np.abs(g)))
            if scale<1e-10: break
            direction=-g/scale
            accepted=False
            for _ in range(24):
                trial=z+step*direction
                trial[fixed]=init[fixed]
                nv,_=obj(trial,p)
                if nv<value-1e-12:
                    z=trial; steps+=1; step=min(step*1.2,.04); accepted=True; break
                step*=.5
            if not accepted: break
            if steps in (20,60,120,180): candidates.append((score(z),f"p{p}_{steps}",z.copy(),steps))
        candidates.append((score(z),f"p{p}_final",z.copy(),steps))
    for sc,method,z,steps in sorted(candidates,key=lambda r:(r[0][0],r[0][1],r[1])):
        if sc[0]>base[0]+1e-8 or sc[1]>base[1]+1e-8: continue
        out=z[cf]
        if not np.array_equal(out[np.isin(f,list(pins))],u[np.isin(f,list(pins))]): continue
        if seam_set(f,out)!=seam: continue
        q=uv_audit(v,f,out)
        if q["overlap_pairs"] or q["mixed_winding_islands"] or q["degenerate_uv"] or q["islands"]!=1: continue
        return out,dict(method=method,steps=steps,baseline_p95=base[0],baseline_max=base[1])
    raise RuntimeError("no verified candidate, including baseline")
