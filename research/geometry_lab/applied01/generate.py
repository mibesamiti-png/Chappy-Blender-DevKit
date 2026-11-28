"""Synthetic garment design; no private inputs. Metres, -Y front."""
import math
from math import sin,cos,pi
import numpy as np

N=16; M=8; GAP=.12
def ring(t,z):return np.array([.16*sin(t),-.115*cos(t),z])
def cup(side,u,v,depth):
    t=side*(.05+.95*u); p=ring(t,.11+v*(.06+.095*sin(pi*u)+.02*u))
    p[1]+=.022*v-depth*sin(pi*u)*(.8*sin(pi*v)+.2*v)
    return p
def grid(name,nu,nv,fn,reverse=False):
    points=[fn(i/nu,j/nv).tolist() for j in range(nv+1) for i in range(nu+1)]
    uv=[[i/nu,j/nv] for j in range(nv+1) for i in range(nu+1)]
    faces=[]
    for j in range(nv):
        for i in range(nu):
            k=j*(nu+1)+i; f=[k,k+1,k+nu+2,k+nu+1];faces.append(f[::-1] if reverse else f)
    return dict(name=name,vertices=points,faces=faces,uv=uv,nu=nu,nv=nv)
def bezier(a,b,c,d,t):
    return (1-t)**3*a+3*t*(1-t)**2*b+3*t*t*(1-t)*c+t**3*d
def generate(depth_right=.055):
    parts=[]
    ts=sorted(set([round(k*.05/2,12) for k in range(-2,3)]+[round(s*(.05+.95*i/N),12) for s in (-1,1) for i in range(N+1)]+[round(s*t,12) for s in (-1,1) for t in (1.1,1.25,1.4,1.55,1.7,1.85,2.,2.15,2.3,2.4,2.46,2.6,2.75,2.9,pi-GAP)]))
    parts.append(grid("band",len(ts)-1,3,lambda u,v:ring(ts[round(u*(len(ts)-1))],.055+.055*v)))
    parts.append(grid("bridge",4,M,lambda u,v:ring(-.05+.1*u,.11+.06*v)+np.array([0,.022*v,0])))
    for side,label,depth in ((1,"R",depth_right),(-1,"L",.055)):
        parts.append(grid("cup_"+label,N,M,lambda u,v:cup(side,u,v,depth),side<0))
        a=[cup(side,i/N,1,depth) for i in (12,13)]
        d=[ring(side*t,.11) for t in (2.4,2.46)]
        def ribbon(u,v):
            start=(1-u)*a[0]+u*a[1]; end=(1-u)*d[0]+u*d[1]
            return bezier(start,start+np.array([0,-.008,.18]),end+np.array([0,.008,.25]),end,v)
        parts.append(grid("strap_"+label,1,24,ribbon,side<0))
    # A separate flexible closure tab, not a modeled functional hook.
    parts.append(grid("closure",4,3,lambda u,v:(1-u)*ring(pi-GAP,.055+.055*v)+u*ring(-pi+GAP,.055+.055*v)))
    return parts

if __name__=="__main__":
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps({"baseline":generate(),"changed":generate(.075)},indent=2))
