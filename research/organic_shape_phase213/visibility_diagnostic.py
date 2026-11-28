"""R10C visibility diagnostic: actual OBJ triangles, depth buffer, smooth shading.
Pure Python PNG output; front/back-facing triangle classes are diagnostic only.
No geometry edits and no claim of a native Blender render.
"""
import math,struct,zlib,json
from pathlib import Path
from collections import Counter,defaultdict
from patch import sub,cross,dot
from boundary import norm

W,H,SCALE=430,340,165
def read_obj(path):
    p=[];q=[]
    for line in path.read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[0]=="v":p.append(tuple(map(float,a[1:])))
        if a[0]=="f":q.append(tuple(int(x.split("/")[0])-1 for x in a[1:]))
    if not p or not q or any(len(f)!=4 or min(f)<0 or max(f)>=len(p) for f in q):raise ValueError("invalid quad OBJ")
    return p,q

def unit(v):
    n=norm(v)
    return tuple(x/n for x in v) if n>1e-12 else (0.,0.,0.)

def raster(p,triangles,angle,width=W,height=H,scale=SCALE):
    c,s=math.cos(angle),math.sin(angle)
    right,view=(c,-s,0.),(s,c,0.)
    uv=[(width/2+scale*dot(v,right),100-scale*v[2]) for v in p]
    ds=[dot(v,view) for v in p]
    normals=[cross(sub(p[t[1]],p[t[0]]),sub(p[t[2]],p[t[0]])) for t in triangles]
    vn=[[0.,0.,0.] for v in p]
    for t,n in zip(triangles,normals):
        for i in t:
            for k in range(3):vn[i][k]+=n[k]
    vn=[unit(v) for v in vn]
    depths=[-math.inf]*(width*height)
    side=[0]*(width*height)
    lights=[0.]*(width*height)
    for t,n in zip(triangles,normals):
        a,b,c0=[uv[i] for i in t]
        v,w=sub(b,a),sub(c0,a)
        den=v[0]*w[1]-v[1]*w[0]
        if abs(den)<1e-12:continue
        x0=max(0,math.floor(min(a[0],b[0],c0[0])))
        x1=min(width-1,math.ceil(max(a[0],b[0],c0[0])))
        y0=max(0,math.floor(min(a[1],b[1],c0[1])))
        y1=min(height-1,math.ceil(max(a[1],b[1],c0[1])))
        front=1 if dot(n,view)>0 else 2
        for y in range(y0,y1+1):
            for x in range(x0,x1+1):
                X,Y=x+.5-a[0],y+.5-a[1]
                u=(X*w[1]-Y*w[0])/den;v0=(v[0]*Y-v[1]*X)/den;w0=1-u-v0
                if min(u,v0,w0)<-1e-8:continue
                z=w0*ds[t[0]]+u*ds[t[1]]+v0*ds[t[2]]
                j=y*width+x
                if z<=depths[j]:continue
                depths[j]=z;side[j]=front
                nn=unit(tuple(w0*vn[t[0]][k]+u*vn[t[1]][k]+v0*vn[t[2]][k] for k in range(3)))
                lights[j]=.55+.45*abs(dot(nn,view))
    return side,lights

def png(path,side,lights,show_faces,width=W,height=H):
    raw=bytearray()
    for y in range(height):
        raw.append(0)
        for j in range(y*width,(y+1)*width):
            if not side[j]:raw.extend((243,245,248));continue
            base=(220,151,93) if show_faces and side[j]==2 else (115,150,182)
            raw.extend(int(c*lights[j]) for c in base)
    def chunk(tag,data):
        return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b""))

def rim_stats(p,q):
    edges=Counter(tuple(sorted((a,b))) for f in q for a,b in zip(f,f[1:]+f[:1]))
    adj=defaultdict(set)
    for (a,b),n in edges.items():
        if n==1:adj[a].add(b);adj[b].add(a)
    if any(len(v)!=2 for v in adj.values()):raise ValueError("invalid rim")
    result=[]
    while adj:
        start=min(adj);loop=[start];prev=-1;cur=start
        while True:
            nxt=min(adj[cur]-{prev})
            prev,cur=cur,nxt
            if cur==start:break
            loop.append(cur)
        for i in loop:del adj[i]
        turns=[]
        for j,i in enumerate(loop):
            a=unit(sub(p[i],p[loop[j-1]]));b=unit(sub(p[loop[(j+1)%len(loop)]],p[i]))
            turns.append(math.degrees(math.acos(max(-1.,min(1.,dot(a,b))))))
        idx=max(range(len(loop)),key=lambda i:turns[i])
        result.append(dict(role="waist" if min(p[i][2] for i in loop)>.3 else ("left_leg" if sum(p[i][0] for i in loop)<0 else "right_leg"),
            count=len(loop),max_3d_turn=turns[idx],location=p[loop[idx]]))
    return sorted(result,key=lambda r:r["role"])

def main():
    src=Path("results/cap_fairing");dest=Path("results/visibility");dest.mkdir(parents=True,exist_ok=True)
    source=json.loads((src/"report.json").read_text())
    if not source["fixture_gate"]:raise ValueError("R9F input gate failed")
    results=[]
    for name in ("standard","front_wrap","rear_wrap","both_wrap"):
        p,q=read_obj(src/(name+".obj"))
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        views=[]
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(p,tris,angle)
            png(dest/(name+"_"+label+".png"),side,lights,False)
            png(dest/(name+"_"+label+"_faces.png"),side,lights,True)
            views.append(dict(view=label,front_pixels=side.count(1),back_pixels=side.count(2),background_pixels=side.count(0)))
        results.append(dict(name=name,rims=rim_stats(p,q),views=views))
    report=dict(complete=True,cases=results,geometry_changed=False,visual_review_required=True,renderer="orthographic per-pixel depth test",native_blender_render=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213VISIBILITY_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":main()
