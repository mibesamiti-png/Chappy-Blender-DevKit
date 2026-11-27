"""Outer conjugate wall of the radial roller channel, separate from the inner cam.
Ideal shaft coupling initially; no web or physical retaining backplate.
"""
import math
import numpy as np
from phase210_inverse_cam import pitch,ROLLER,N,CHECK
CLEARANCE=.006
def nearest(p,c):
    edge=np.roll(c,-1,axis=0)-c
    d=p-c
    t=np.clip(np.sum(d*edge,axis=1)/np.sum(edge*edge,axis=1),0.,1.)
    return float(np.linalg.norm(d-t[:,None]*edge,axis=1).min())
def wall(kind,base,duty):
    t=np.arange(N)*math.tau/N
    p,n,_,_,_=pitch(t,kind,base,duty)
    inner=p+(ROLLER+CLEARANCE)*n
    outer=inner*(1.+.35/np.linalg.norm(inner,axis=1)[:,None])
    theta=(np.arange(CHECK)+.37)*math.tau/CHECK
    test,*_=pitch(theta,kind,base,duty)
    gaps=np.array([nearest(v,inner)-ROLLER for v in test])
    step=np.arctan2(inner[:,0]*np.roll(inner[:,1],-1)-inner[:,1]*np.roll(inner[:,0],-1),
        np.sum(inner*np.roll(inner,-1,axis=0),axis=1))
    q=dict(min_gap=float(gaps.min()),max_gap=float(gaps.max()),min_polar_step=float(step.min()))
    q['passed']=q['min_gap']>=.004 and q['max_gap']<=.008 and q['min_polar_step']>0.
    return outer,inner,q
