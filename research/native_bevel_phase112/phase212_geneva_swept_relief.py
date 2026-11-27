"""Phase212-L: fixed bounded radial clipping of the original locking disk.
This is a sampled, planar sweep in the driver frame, not continuous CSG.
Only the 35-degree disk changes; wheel, pin, supports and motor are fixed.
"""
import math
from phase212_geneva_geometry import profiles,rotate

MARGIN=.02
ERROR_DEGREES=.96
SAMPLES=721

def swept_profiles(g,relief_degrees=35):
    if relief_degrees!=35:
        raise ValueError("only the original 35 degree disk is supported")
    wheel,base,dims=profiles(g,relief_degrees)
    radii=[math.hypot(*q) for q in base]
    rays=[(x/r,y/r) for (x,y),r in zip(base,radii)]
    caps=radii[:]
    poses=0
    for i in range(SAMPLES):
        u=i/(SAMPLES-1)
        if not g.start<=u<=g.end:
            continue
        theta=math.tau*(u-.5)
        for sign in (-1,0,1):
            a=g.sample(u)[0]+sign*math.radians(ERROR_DEGREES)
            pts=[]
            for p in wheel:
                x,y=rotate(p,a)
                pts.append(rotate((x-g.center_distance,y),theta))
            edges=[]
            limit=dims["locking_radius"]+MARGIN
            for (x,y),(X,Y) in zip(pts,pts[1:]+pts[:1]):
                if min(x,X)>limit or max(x,X)<-limit or min(y,Y)>limit or max(y,Y)<-limit:
                    continue
                edges.append((x,y,X-x,Y-y))
            poses+=1
            for j,(dx,dy) in enumerate(rays):
                for x,y,ex,ey in edges:
                    den=dx*ey-dy*ex
                    if abs(den)<1e-12:
                        continue
                    t=(x*ey-y*ex)/den
                    s=(x*dy-y*dx)/den
                    if t>0 and 0<=s<=1:
                        caps[j]=min(caps[j],t-MARGIN)
    assert poses==543
    assert all(math.isfinite(v) and 1.0<=v<=r+1e-12 for v,r in zip(caps,radii))
    disk=tuple((x*v,y*v) for (x,y),v in zip(rays,caps))
    cuts=[r-v for r,v in zip(radii,caps)]
    dims.update(profile_kind="sampled_radial_sweep",sweep_margin=MARGIN,
        error_degrees=ERROR_DEGREES,sweep_poses=poses,changed_vertices=sum(c>1e-8 for c in cuts),
        max_cut=max(cuts),min_radius=min(caps),radial_vertices=len(caps),
        radius_before=radii,radius_after=caps,continuous_sweep_proven=False)
    assert dims["changed_vertices"]>0 and dims["max_cut"]<.1
    return wheel,disk,dims
