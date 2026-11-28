"""R29A: garment-only local rear shape adjustment. Local coordinates +Y = rear.
Run in Blender Text Editor with the garment mesh active, in Object Mode.
Creates two editable copies, leaving the original untouched.
"""
import math
from collections import Counter

PRESETS = (("soft", .045, .51), ("lower_full", .085, .34))

def smoothstep(t):
    t=max(0.,min(1.,t)); return t*t*(3.-2.*t)

def deform(points, faces, amplitude, center):
    edges=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]))
    if not edges or max(edges.values())>2:
        raise ValueError('Expected manifold open surface')
    boundary={i for edge,count in edges.items() if count==1 for i in edge}
    if not boundary: raise ValueError('Expected open garment surface')
    xmin,xmax=min(v[0] for v in points),max(v[0] for v in points)
    zmin,zmax=min(v[2] for v in points),max(v[2] for v in points)
    ymax=max(v[1] for v in points)
    if xmax<=xmin or zmax<=zmin or ymax<=0: raise ValueError('Invalid local axes')
    half=(xmax-xmin)/2; mid=(xmax+xmin)/2
    out=[]
    for i,(x,y,z) in enumerate(points):
        if i in boundary or y<=0:
            out.append((x,y,z));continue
        t=(z-zmin)/(zmax-zmin)
        w=smoothstep((y/ymax-.15)/.45)*math.exp(-((x-mid)/(.78*half))**4)*math.exp(-((t-center)/.27)**2)
        out.append((x,y+amplitude*half*w,z))
    return out,boundary

def main():
    import bpy
    obj=bpy.context.active_object
    if obj is None or obj.type!='MESH' or obj.mode!='OBJECT':
        raise RuntimeError('Select garment mesh in Object Mode')
    p=[tuple(v.co) for v in obj.data.vertices]
    f=[tuple(poly.vertices) for poly in obj.data.polygons]
    for name,amplitude,center in PRESETS:
        new,boundary=deform(p,f,amplitude,center)
        copy=obj.copy();copy.data=obj.data.copy();copy.name='R29A_'+name
        bpy.context.collection.objects.link(copy)
        for v,co in zip(copy.data.vertices,new):v.co=co
        copy.data.update()
        copy.hide_set(True);copy.hide_render=True
    print('R29A: two hidden editable copies created; unhide one at a time in Outliner.')

if __name__=='__main__':main()
