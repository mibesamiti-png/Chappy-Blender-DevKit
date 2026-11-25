"""Region-aware synthetic temple revision; use frozen original for all other parts."""
import sys,math,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
from applied02 import blender_run as old

# y, inward x, z, half-width, half-height; metres. First interval exactly linear.
PROFILE=[(0,0,0,.0014,.00165),(.085,0,0,.0014,.00165),
         (.091,-.0005,-.0004,.0016,.00185),(.098,-.002,-.002,.0021,.00225),
         (.110,-.0045,-.007,.0022,.0023),(.124,-.007,-.016,.0021,.0022),
         (.132,-.009,-.022,.0017,.0018)]
def temple(s,label):
    points=[Vector((s*x,y,z)) for y,x,z,_,_ in PROFILE]
    v=[];f=[]
    for i,(p,row) in enumerate(zip(points,PROFILE)):
        if i==0:t=(points[1]-p).normalized()
        elif i==len(points)-1:t=(p-points[i-1]).normalized()
        elif i==1:t=(points[i]-points[i-1]).normalized() # shared end of exact straight interval
        else:t=((p-points[i-1]).normalized()+(points[i+1]-p).normalized()).normalized()
        u=Vector((1,0,0));u=(u-t*u.dot(t)).normalized();n=t.cross(u).normalized()
        for a,b in ((-1,-1),(1,-1),(1,1),(-1,1)):v.append(tuple(p+a*row[3]*u+b*row[4]*n))
    for i in range(len(points)-1):
        for j in range(4):f.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    f.extend([(3,2,1,0),tuple(range(len(v)-4,len(v)))])
    ob=old.mesh("Temple_"+label,v,f,bpy.data.materials["Brushed champagne alloy"])
    ob.data.materials.append(bpy.data.materials["Deep petrol acetate"])
    for q in ob.data.polygons:
        q.use_smooth=False
        q.material_index=1 if 8<=q.index<24 or q.index==25 else 0
    ob.parent=bpy.data.objects["Hinge_"+label]
    bevel=ob.modifiers.new("Local edge rounding","BEVEL");bevel.width=.00035;bevel.segments=3;bevel.limit_method="ANGLE";bevel.material=-1
    ob["straight_interval_m"]=.085;ob["construction"]="continuous exterior; material regions, no physical core"
def build():
    old.build()
    for label,s in (("R",1),("L",-1)):
        for name in ("Temple_"+label,"Tip_"+label):bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
        temple(s,label)
def info():
    out={}
    for l in ("R","L"):
        o=bpy.data.objects["Temple_"+l]
        out[l]=dict(vertices=[list(v.co) for v in o.data.vertices],faces=[list(p.vertices) for p in o.data.polygons],materials=[p.material_index for p in o.data.polygons],modifier_types=[m.type for m in o.modifiers])
    return out
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args(sys.argv[sys.argv.index("--")+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    build();old.pose();before=old.snapshot();ib=info()
    f=out/"INK_02B_editable.blend";bpy.ops.wm.save_as_mainfile(filepath=str(f.resolve()));bpy.ops.wm.open_mainfile(filepath=str(f.resolve()))
    after=old.snapshot();ia=info()
    raw={"open":after,"roundtrip_exact":before==after and ib==ia,"temple_base":ia}
    for l in ("R","L"):old.pose(l);raw["fold_"+l]=old.snapshot()
    old.pose();(out/"raw.json").write_text(json.dumps(raw));old.render(out)
