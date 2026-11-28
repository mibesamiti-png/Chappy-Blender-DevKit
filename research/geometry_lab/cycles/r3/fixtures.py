import numpy as np
from cbdk_geometry import Mesh


def torus(n=16,m=8):
    v=[];f=[]
    for i in range(n):
        u=2*np.pi*i/n
        for j in range(m):
            t=2*np.pi*j/m;r=2+.6*np.cos(t)
            v.append([r*np.cos(u),r*np.sin(u),.6*np.sin(t)])
    for i in range(n):
        for j in range(m):
            a=i*m+j;b=((i+1)%n)*m+j;c=((i+1)%n)*m+(j+1)%m;d=i*m+(j+1)%m
            f.extend([[a,b,c],[a,c,d]])
    return Mesh(v,f)


def sheet(folded=False,n=12):
    v=[];f=[]
    for i in range(n):
        t=-1+2*i/(n-1)
        for j in range(n):
            s=-1+2*j/(n-1)
            v.append([t*t,s,t*(t*t-.5)] if folded else [t,s,.3*(t*t-s*s)])
    for i in range(n-1):
        for j in range(n-1):
            a=i*n+j;b=a+n;c=b+1;d=a+1
            f.extend([[a,b,c],[a,c,d]])
    return Mesh(v,f)
