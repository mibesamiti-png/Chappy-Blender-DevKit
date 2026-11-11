"""Review-only cyclic boundary stitching; no scene edits, no smoothness promise."""
from time import monotonic
import numpy as np
from .geometry import Mesh


def _loops(a,b):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    for loop in (a,b):
        if loop.ndim!=2 or loop.shape[1]!=3 or not 3<=len(loop)<=48:
            raise ValueError('each ordered loop must contain 3..48 XYZ points')
        if not np.isfinite(loop).all() or np.max(np.abs(loop))>1e8:
            raise ValueError('finite bounded coordinates required')
        if len(np.unique(loop,axis=0))!=len(loop):raise ValueError('duplicate loop vertex')
    scale=float(np.max(np.ptp(np.vstack((a,b)),axis=0)))
    if scale==0:raise ValueError('zero scale')
    return a.copy(),b.copy(),scale


def _costs(a,b):
    # Objective: sum of squared triangle edge lengths, scale-normalized by caller.
    # Degenerate triangles are forbidden rather than repaired silently.
    def cost(x,y,z):
        area=np.linalg.norm(np.cross(y-x,z-x),axis=-1)
        e=((x-y)**2).sum(-1)+((y-z)**2).sum(-1)+((z-x)**2).sum(-1)
        return np.where(area>1e-12*e,e,np.inf)
    return cost(a[:,None],np.roll(a,-1,axis=0)[:,None],b[None,:]),cost(a[:,None],np.roll(b,-1,axis=0)[None,:],b[None,:])


def _path(ca,cb,n,m,optimal):
    if not optimal:
        i=j=0;steps=[]
        while i<n or j<m:
            step=0 if i<n and (j==m or (i+1)/n<=(j+1)/m) else 1
            steps.append(step);i+=step==0;j+=step==1
        return steps
    dp=np.full((n+1,m+1),np.inf);dp[0,0]=0;prev={}
    for i in range(n+1):
        for j in range(m+1):
            if (i,j)==(0,0) or abs(i/n-j/m)>.45:continue
            if i and np.isfinite(dp[i-1,j]):
                dp[i,j]=dp[i-1,j]+ca[(i-1)%n,j%m];prev[i,j]=0
            if j and dp[i,j-1]+cb[i%n,(j-1)%m]<dp[i,j]:
                dp[i,j]=dp[i,j-1]+cb[i%n,(j-1)%m];prev[i,j]=1
    if not np.isfinite(dp[n,m]):return None
    i,j=n,m;steps=[]
    while i or j:
        s=prev[i,j];steps.append(s);i-=s==0;j-=s==1
    return steps[::-1]


def bridge_loops(a,b,method='dp',seconds=10):
    """Return detached annular strip, preserving every input vertex exactly.

    method=index: proportional zipper; phase: cyclic/reversal search;
    dp: cyclic/reversal search plus banded shortest monotone triangulation.
    The result is a proposal, never automatic geometry approval.
    """
    if method not in ('index','phase','dp'):raise ValueError('unknown method')
    if isinstance(seconds,bool) or not np.isfinite(seconds) or not 0<seconds<=60:raise ValueError('seconds in (0,60] required')
    deadline=monotonic()+seconds
    a,b,scale=_loops(a,b);n,m=len(a),len(b);best=None;trials=0
    # Recenter before normalization. Never change returned boundary coordinates.
    an=(a-a[0])/scale;bn=(b-a[0])/scale
    for reverse in ((False,) if method=='index' else (False,True)):
        for shift in (range(1) if method=='index' else range(m)):
            if monotonic()>deadline:raise TimeoutError('bridge candidate budget exhausted')
            order=np.roll(np.arange(m)[::-1] if reverse else np.arange(m),-shift)
            ca,cb=_costs(an,bn[order]);steps=_path(ca,cb,n,m,method=='dp');trials+=1
            if steps is None:continue
            i=j=0;faces=[];score=0.
            for s in steps:
                if s==0:
                    score+=ca[i%n,j%m];faces.append((i%n,(i+1)%n,n+int(order[j%m])));i+=1
                else:
                    score+=cb[i%n,j%m];faces.append((i%n,n+int(order[(j+1)%m]),n+int(order[j%m])));j+=1
            if np.isfinite(score) and (best is None or score<best[0]):best=(score,faces,shift,reverse)
    if best is None:raise ValueError('no nondegenerate strip found')
    mesh=Mesh(np.vstack((a,b)),best[1])
    return dict(mesh=mesh,objective=float(best[0]),shift=int(best[2]),reverse=best[3],trials=trials,approved=False)
