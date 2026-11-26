"""Independent float64 sampled point-to-triangle distance.
No Blender BVH queries. Not an exact Hausdorff or intersection certificate.
For nondegenerate triangles compare plane projection (if inside) and all
three finite edges. Degenerate triangles reduce to their segments.
"""
import numpy as np
from phase192_bevel_surface_repeatability import samples

def nearest(source,target,chunk=64):
    V,T=target
    tri=np.asarray(V,dtype=np.float64)[np.asarray(T,dtype=int)]
    if not len(tri) or not np.isfinite(tri).all():raise ValueError('invalid triangles')
    A,B,C=tri[:,0],tri[:,1],tri[:,2]
    e=B-A;f=C-A;n=np.cross(e,f);nn=np.einsum('ij,ij->i',n,n)
    valid=nn>0
    if not np.isfinite(nn).all():raise ValueError('invalid normal')
    safe=np.where(valid,nn,1.)
    def dot(x,y):return np.sum(x*y,axis=-1)
    def segment(P,U,W):
        d=W-U;dd=dot(d,d)
        t=np.clip(dot(P-U,d)/np.where(dd>0,dd,1.),0.,1.)
        D=P-U-t[...,None]*d
        return dot(D,D)
    P=samples(source)
    if not np.isfinite(P).all():raise ValueError('invalid samples')
    out=[]
    for i in range(0,len(P),chunk):
        X=P[i:i+chunk,None,:];AP=X-A
        # Signed oriented barycentric numerators; no cancellation-prone Gram determinant.
        u=dot(np.cross(AP,f),n)/safe
        v=dot(np.cross(e,AP),n)/safe
        inside=valid&(u>=0)&(v>=0)&(u+v<=1)
        plane=dot(AP,n)**2/safe
        d=np.minimum(np.minimum(segment(X,A,B),segment(X,B,C)),segment(X,C,A))
        d=np.minimum(d,np.where(inside,plane,np.inf))
        out.extend(np.sqrt(np.min(d,axis=1)))
    return np.asarray(out)

def triangle_key(s):
    V,T=s
    return sorted(tuple(sorted(tuple(float(x) for x in V[i]) for i in t)) for t in T)

def compare(a,b,width):
    x=nearest(a,b);y=nearest(b,a);d=np.concatenate((x,y))
    maximum=float(d.max());ratio=maximum/width
    return dict(samples=len(d),max_distance=maximum,p95=float(np.percentile(d,95)),
        rms=float(np.sqrt(np.mean(d*d))),max_over_offset=ratio,screen_pass=bool(ratio<=.05),
        triangle_geometry_equal=triangle_key(a)==triangle_key(b))

def controls():
    T=np.array([[0,1,2]]);V=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    base=(V,T);shift=(V+[0,0,.01],T)
    identical=compare(base,base,.1);translated=compare(base,shift,.1)
    # Sliver triangle, far from origin and tilted, known normal offset.
    A=np.array([100.,-200.,300.]);e=np.array([1.,2.,3.]);f=np.array([-.001,.002,-.001])
    W=np.array([A,A+e,A+e+f]);n=np.cross(e,f);n/=np.linalg.norm(n)
    sliver=(W,T);offset=(W+.007*n,T)
    thin_same=compare(sliver,sliver,.1);thin_shift=compare(sliver,offset,.1)
    # Point samples from collapsed triangle: analytic nearest point on finite edge.
    point=(np.array([[2.,0.,0.]]),np.array([[0,0,0]]))
    edge=nearest(point,base)
    checks=dict(identical=identical['max_distance']<1e-12,
        translated=abs(translated['max_distance']-.01)<1e-12 and not translated['screen_pass'],
        sliver_same=thin_same['max_distance']<1e-10,
        sliver_shift=abs(thin_shift['max_distance']-.007)<1e-10 and not thin_shift['screen_pass'],
        finite_edge=bool(np.max(np.abs(edge-1.))<1e-12))
    assert all(checks.values()),checks
    return checks
