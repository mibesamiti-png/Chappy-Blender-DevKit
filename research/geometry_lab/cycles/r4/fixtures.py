"""R4 corpus; held-out names/parameters frozen before first bridge evaluation.

New to R1-R3. Holdout is development-separated synthetic coverage, not a claim
of an independent human-designed or real-world dataset.
"""
import numpy as np

def ring(n,z,kind='circle',radius=1.,offset=(0,0),phase=0):
    t=np.arange(n)*2*np.pi/n+phase
    r=radius*(1+.18*np.cos(3*t)) if kind=='lobed' else np.full(n,radius)
    x=r*np.cos(t);y=r*np.sin(t)
    if kind=='ellipse':x*=1.6;y*=.65
    if kind=='superellipse':
        x=radius*np.sign(np.cos(t))*np.sqrt(np.abs(np.cos(t)))
        y=radius*.7*np.sign(np.sin(t))*np.sqrt(np.abs(np.sin(t)))
    return np.column_stack((x+offset[0],y+offset[1],np.full(n,z)))

def cases(split='development'):
    specs=[('cylinder',12,12,'circle',1.,(0,0),4,False),
           ('unequal_ellipse',12,20,'ellipse',.8,(.1,0),7,False),
           ('reversed',16,16,'circle',1.,(0,0),3,True),
           ('taper',16,24,'circle',.55,(.3,0),9,False)] if split=='development' else [
           ('holdout_lobed',15,21,'lobed',.8,(.1,.1),8,True),
           ('holdout_superellipse',20,28,'superellipse',.9,(.2,-.1),11,False),
           ('holdout_offset',18,30,'ellipse',.65,(.9,.3),13,True),
           ('holdout_lowpoly',5,9,'circle',.7,(.1,0),4,False),
           ('holdout_slender',32,12,'ellipse',.25,(.4,.2),5,True),
           ('holdout_far_offset',16,24,'lobed',.9,(2.3,0),10,False)]
    for name,n,m,kind,r,offset,shift,reverse in specs:
        a=ring(n,0,kind);b=ring(m,1,kind,r,offset,.07)
        if reverse:b=b[::-1]
        b=np.roll(b,shift,axis=0)
        yield dict(name=name,split=split,a=a,b=b,kind=kind,radius=r,offset=offset)
