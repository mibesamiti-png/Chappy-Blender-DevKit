"""R13B: frozen analytic Y-tube form-first pilot; generic mechanical geometry."""
import math, json
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from patch import sub, cross, dot
from boundary import norm
from pelvis_field import components, TETS, CORNERS
from intersection import audit as contact_audit
from visibility_diagnostic import raster, png

BOUNDS=((-1.25,1.25),(-.75,.75),(-1.,1.))
RES=(20,14,24)
LEVEL=.035
RADIUS=.317
K=.18
SLOPE=.63
VIEWS=(("front",0.),("quarter",math.pi/4),("side",math.pi/2),("back",math.pi))
W,H,SCALE=320,340,120

def unit(v):
    n=norm(v)
    if n<1e-12:raise ValueError("zero direction")
    return tuple(x/n for x in v)

RAYS=((0.,0.,1.),unit((SLOPE,0.,-1.)),unit((-SLOPE,0.,-1.)))

def field(p):
    # Ray-distance smooth union; a scalar design field, not a signed distance.
    vals=[]
    for d in RAYS:
        s=max(0.,dot(p,d))
        vals.append(math.sqrt(sum((x-s*y)**2 for x,y in zip(p,d)))-RADIUS)
    # Symmetric combination: branch pair first, then stem.
    def sm(a,b):
        h=max(K-abs(a-b),0.)/K
        return min(a,b)-K*h*h/4
    return sm(vals[0],sm(vals[1],vals[2]))

def extract(level,res):
    nx,ny,nz=res
    grid={k:tuple(lo+(hi-lo)*i/n for i,n,(lo,hi) in zip(k,res,BOUNDS))
          for k in product(range(nx+1),range(ny+1),range(nz+1))}
    values={k:field(v)-level for k,v in grid.items()}
    p=[];q=[];cache={}
    def edge(a,b):
        key=tuple(sorted((a,b)))
        if key not in cache:
            a,b=key;fa,fb=values[a],values[b]
            t=fa/(fa-fb)
            cache[key]=len(p)
            p.append(tuple(x+t*(y-x) for x,y in zip(grid[a],grid[b])))
        return cache[key]
    def emit(t,normal):
        a,b,c=(p[i] for i in t)
        if dot(cross(sub(b,a),sub(c,a)),normal)<0:t=(t[0],t[2],t[1])
        q.append(t)
    for i,j,k in product(range(nx),range(ny),range(nz)):
        cube=[(i+x,j+y,k+z) for x,y,z in CORNERS]
        for tet in TETS:
            ins=[cube[t] for t in tet if values[cube[t]]<0]
            outs=[cube[t] for t in tet if values[cube[t]]>=0]
            if not ins or not outs:continue
            normal=tuple(sum(grid[a][n] for a in outs)/len(outs)-sum(grid[a][n] for a in ins)/len(ins) for n in range(3))
            if len(ins)==1:emit(tuple(edge(ins[0],b) for b in outs),normal)
            elif len(outs)==1:emit(tuple(edge(a,outs[0]) for a in ins),normal)
            else:
                a,b=ins;c,d=outs
                ring=(edge(a,c),edge(a,d),edge(b,d),edge(b,c))
                emit((ring[0],ring[1],ring[2]),normal);emit((ring[0],ring[2],ring[3]),normal)
    return p,q

def gradient(p,boundary=False):
    eps=1e-5
    out=[]
    for k in range(3):
        if boundary and k==2:out.append(0.);continue
        a=list(p);b=list(p);a[k]+=eps;b[k]-=eps
        out.append((field(a)-field(b))/(2*eps))
    return tuple(out)

def adjacency(q):
    adj=defaultdict(set);edges=Counter()
    for f in q:
        for a,b in zip(f,f[1:]+f[:1]):
            adj[a].add(b);adj[b].add(a);edges[tuple(sorted((a,b)))]+=1
    border=defaultdict(set)
    for (a,b),n in edges.items():
        if n==1:border[a].add(b);border[b].add(a)
    return adj,border,edges

def constrain(p,z):
    return (p[0],p[1],z if z is not None else max(-1.+1e-8,min(1.-1e-8,p[2])))

def offset(p,q):
    _,border,_=adjacency(q)
    out=[]
    for i,v in enumerate(p):
        z=v[2] if i in border else None
        n=unit(gradient(v,z is not None))
        out.append(constrain(tuple(x+LEVEL*y for x,y in zip(v,n)),z))
    return out

def project(v,z):
    for _ in range(6):
        r=field(v)-LEVEL
        if abs(r)<1e-9:break
        g=gradient(v,z is not None);gg=dot(g,g)
        if gg<1e-10:break
        step=max(-.06,min(.06,r/gg))
        v=constrain(tuple(x-step*y for x,y in zip(v,g)),z)
    return v

def fair(p,q):
    adj,border,_=adjacency(q)
    out=list(p)
    for _ in range(4):
        nxt=[]
        for i,v in enumerate(out):
            ids=sorted(border[i] if i in border else adj[i])
            avg=tuple(sum(out[j][k] for j in ids)/len(ids) for k in range(3))
            z=p[i][2] if i in border else None
            moved=constrain(tuple(.65*x+.35*y for x,y in zip(v,avg)),z)
            nxt.append(project(moved,z))
        out=nxt
    return out

def percentile(a,f):
    s=sorted(a)
    return s[min(len(s)-1,math.ceil(f*len(s))-1)]

def measure(p,q):
    adj,border,edges=adjacency(q)
    loops=components(border)
    roles=[]
    for r in loops:
        if all(abs(p[i][2]-1.)<1e-8 for i in r):roles.append("stem")
        elif all(abs(p[i][2]+1.)<1e-8 for i in r):
            roles.append("left" if max(p[i][0] for i in r)<0 else "right" if min(p[i][0] for i in r)>0 else "mixed")
        else:roles.append("invalid")
    directions=Counter();normals=defaultdict(list);links=defaultdict(lambda:defaultdict(set))
    areas=[];quality=[];res=[];vertex_res=[abs(field(v)-LEVEL) for v in p]
    for f in q:
        a,b,c=(p[i] for i in f)
        n=cross(sub(b,a),sub(c,a));area=norm(n)/2;areas.append(area)
        denom=sum(math.dist(p[i],p[j])**2 for i,j in zip(f,f[1:]+f[:1]))
        quality.append(4*math.sqrt(3)*area/denom if denom else 0.)
        for w in ((1/3,1/3,1/3),(.5,.5,0),(.5,0,.5),(0,.5,.5)):
            v=tuple(sum(w[j]*p[f[j]][k] for j in range(3)) for k in range(3))
            res.append(abs(field(v)-LEVEL))
        for j,i in enumerate(f):
            k=f[(j+1)%3];prev=f[(j-1)%3];e=tuple(sorted((i,k)))
            directions[e]+=1 if i<k else -1;normals[e].append(n)
            links[i][k].add(prev);links[i][prev].add(k)
    bad_links=0
    for i,g in links.items():
        d=[len(s) for s in g.values()]
        ok=(d.count(1)==2 and all(x in (1,2) for x in d)) if i in border else all(x==2 for x in d)
        bad_links+=int(not ok or len(components(g))!=1)
    jumps=[math.degrees(math.acos(max(-1.,min(1.,dot(*ns)/(norm(ns[0])*norm(ns[1]))))))
           for ns in normals.values() if len(ns)==2 and min(map(norm,ns))>0]
    euler=len(p)-len(edges)+len(q)
    bad_edges=sum(n>2 for n in edges.values())
    bad_winding=sum(n==2 and directions[e]!=0 for e,n in edges.items())
    topology=(euler==-1 and len(components(adj))==1 and len(adj)==len(p)
        and sorted(roles)==["left","right","stem"] and all(len(v)==2 for v in border.values())
        and bad_edges==bad_winding==bad_links==0)
    try:contacts=contact_audit(p,q)
    except ValueError as exc:contacts=dict(passed=False,error=str(exc))
    return dict(vertices=len(p),triangles=len(q),euler=euler,port_roles=sorted(roles),
        topology_pass=topology,nonmanifold_edges=bad_edges,orientation_errors=bad_winding,
        vertex_link_errors=bad_links,min_area=min(areas),quality_p05=percentile(quality,.05),
        normal_jump_p95=percentile(jumps,.95),normal_jump_max=max(jumps),
        vertex_field_residual_p95=percentile(vertex_res,.95),
        sampled_field_residual_p95=percentile(res,.95),sampled_field_residual_max=max(res),
        nonincident_contacts=contacts,geometry_pass=topology and min(areas)>1e-10 and contacts["passed"])

def render(p,q,angle):
    return raster([(x,y,z-.5) for x,y,z in p],q,angle,width=W,height=H,scale=SCALE)

def mask(side):
    return {i for i,s in enumerate(side) if s}

def contour(m):
    return {i for i in m if i%W in (0,W-1) or i//W in (0,H-1)
            or any(i+j not in m for j in (-1,1,-W,W))}

def compare_masks(a,b):
    if not a or not b:raise ValueError("empty silhouette")
    aa,bb=contour(a),contour(b)
    def dist(a,b):
        xy=[(i%W,i//W) for i in b]
        return [math.sqrt(min((i%W-x)**2+(i//W-y)**2 for x,y in xy)) for i in a]
    return dict(iou=len(a&b)/len(a|b),symmetric_contour_p95_px=percentile(dist(aa,bb)+dist(bb,aa),.95))

def export(path,p,q):
    with path.open("w") as out:
        out.write("# Synthetic generic three-port cover\n")
        for v in p:out.write("v "+" ".join(format(x,".17g") for x in v)+"\n")
        for f in q:out.write("f "+" ".join(str(i+1) for i in f)+"\n")

def main():
    dest=Path("results/form_first");dest.mkdir(parents=True,exist_ok=True)
    ref,q=extract(0.,RES)
    target,tq=extract(LEVEL,tuple(2*x for x in RES))
    base,bq=extract(LEVEL,RES)
    raw=offset(ref,q);smooth=fair(raw,q)
    target_masks={}
    for name,p,f in (("reference",ref,q),("target",target,tq)):
        export(dest/(name+".obj"),p,f)
        for view,angle in VIEWS:
            side,light=render(p,f,angle)
            png(dest/(name+"_"+view+".png"),side,light,False,width=W,height=H)
            if name=="target":target_masks[view]=mask(side)
    # Controls: exact and intentionally horizontally shifted small mask.
    control={y*W+x for y in range(100,130) for x in range(100,130)}
    exact=compare_masks(control,control);shift=compare_masks(control,{i+8 for i in control})
    controls=dict(exact=exact,shifted=shift,reference_vertex_field_p95=percentile([abs(field(v)) for v in ref],.95))
    control_pass=exact["iou"]==1 and exact["symmetric_contour_p95_px"]==0 and shift["iou"]<.7 and shift["symmetric_contour_p95_px"]>0
    results=[]
    for name,p,f in (("direct",base,bq),("offset",raw,q),("fair_project",smooth,q)):
        export(dest/(name+".obj"),p,f)
        r=measure(p,f);views={}
        for view,angle in VIEWS:
            side,light=render(p,f,angle)
            png(dest/(name+"_"+view+".png"),side,light,False,width=W,height=H)
            views[view]=compare_masks(mask(side),target_masks[view])
        r.update(name=name,views=views,passes_numeric_gate=control_pass and r["geometry_pass"] and all(v["iou"]>=.9 for v in views.values()))
        results.append(r)
    report=dict(complete=True,field_level=LEVEL,coarse_grid=RES,target_grid=tuple(2*x for x in RES),
        controls=controls,control_pass=control_pass,cases=results,
        target_is_numerical_same_field=True,visual_review_required=True,
        anatomical_fit_verified=False,physical_clearance_verified=False,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213FORMFIRST_SUMMARY",json.dumps(report,allow_nan=False))
    if not control_pass:raise RuntimeError("silhouette control failed")
if __name__=="__main__":main()
