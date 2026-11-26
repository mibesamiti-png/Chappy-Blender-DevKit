"""Research only. Section polyline between preserved host and child seam anchors.
Triangulated finite-precision intersection; coplanar triangles and ambiguous paths rejected.
No native mesh input yet; not a safety oracle or an adoption criterion.
"""
import json, math, heapq, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent

def angle(a,b):
    return float(np.degrees(np.arccos(np.clip(a@b/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1))))

def section(V,F,A,B,N,tol):
    V=np.asarray(V,float);A=np.asarray(A,float);B=np.asarray(B,float);N=np.asarray(N,float);N/=np.linalg.norm(N)
    d=(V-A)@N;d[np.abs(d)<tol]=0
    pts=[];lookup={};adj={}
    def node(p):
        k=tuple(np.rint((p-A)/tol).astype(np.int64))
        # Search neighboring bins to avoid false disconnection on rounding borders.
        for i in (-1,0,1):
            for j in (-1,0,1):
                for l in (-1,0,1):
                    for idx in lookup.get((k[0]+i,k[1]+j,k[2]+l),[]):
                        if np.linalg.norm(pts[idx]-p)<=tol:return idx
        idx=len(pts);pts.append(p);lookup.setdefault(k,[]).append(idx);adj[idx]=set();return idx
    for f in F:
        for k in range(1,len(f)-1):
            ids=[f[0],f[k],f[k+1]];q=V[ids];s=d[ids]
            if np.all(s==0):raise ValueError('coplanar_triangle')
            if np.all(s>0) or np.all(s<0):continue
            hit=[]
            for i,j in ((0,1),(1,2),(2,0)):
                if s[i]==0:hit.append(q[i])
                if s[i]*s[j]<0:hit.append(q[i]+(q[j]-q[i])*s[i]/(s[i]-s[j]))
            idx=list(set(node(p) for p in hit))
            if len(idx)==2:adj[idx[0]].add(idx[1]);adj[idx[1]].add(idx[0])
            elif len(idx)>2:raise ValueError('ambiguous_triangle')
    def anchor(p):
        # Anchors can lie in the interior of a section segment.
        candidates=[]
        for i,ns in adj.items():
            for j in ns:
                if j<i:continue
                a,b=pts[i],pts[j];e=b-a;t=np.clip((p-a)@e/(e@e),0,1);dist=np.linalg.norm(p-(a+t*e))
                if dist<=4*tol:candidates.append((dist,i,j))
        if not candidates:raise ValueError('anchor_missing')
        _,i,j=min(candidates);idx=node(p)
        if idx not in (i,j):adj[i].remove(j);adj[j].remove(i);adj[i].add(idx);adj[j].add(idx);adj[idx].update((i,j))
        return idx
    a,b=anchor(A),anchor(B)
    if a==b:raise ValueError('same_anchor')
    component={a};pending=[a]
    while pending:
        for j in adj[pending.pop()]:
            if j not in component:component.add(j);pending.append(j)
    if b not in component:raise ValueError('disconnected')
    if any(len(adj[i])>2 for i in component) or sum(len(adj[i])==1 for i in component)!=2:
        raise ValueError('ambiguous_component')
    # Require an unambiguous chain in the connected component between anchors.
    dist={a:0.};prev={};heap=[(0.,a)]
    while heap:
        z,i=heapq.heappop(heap)
        if z!=dist[i]:continue
        if i==b:break
        for j in adj[i]:
            w=z+np.linalg.norm(pts[j]-pts[i])
            if w<dist.get(j,float('inf')):dist[j]=w;prev[j]=i;heapq.heappush(heap,(w,j))
    if b not in dist:raise ValueError('disconnected')
    path=[b]
    while path[-1]!=a:path.append(prev[path[-1]])
    path=path[::-1]
    if any(len(adj[i])!=2 for i in path):raise ValueError('branch_or_missing_tangent')
    left=next(iter(adj[a]-{path[1]}));right=next(iter(adj[b]-{path[-2]}))
    if left in path or right in path:raise ValueError('loop_shortcut')
    X=np.asarray([pts[i] for i in [left]+path+[right]])
    # Triangulation can insert collinear points; ignore them as curvature events.
    dirs=np.diff(X,axis=0);turn=[angle(u,v) for u,v in zip(dirs,dirs[1:])];turn=[0. if t<1e-5 else t for t in turn]
    return dict(max_turn=max(turn),sum_turn=sum(turn),seam_turn=[turn[0],turn[-1]],events=sum(t>1e-5 for t in turn),profile_length=float(np.linalg.norm(np.diff(X[1:-1],axis=0),axis=1).sum()),points=X[1:-1].tolist())

def controls():
    out=[]
    for n in (1,2,3,6,12,24):
        t=np.linspace(0,np.pi/2,n+1);p=np.c_[1-np.sin(t),1-np.cos(t)];p=np.vstack([[2,0],p,[0,2]])
        V=np.array([[x,y,z] for x,z in p for y in (-1,1)]);F=[[2*i,2*i+1,2*i+3,2*i+2] for i in range(len(p)-1)]
        r=section(V,F,[1,0,0],[0,0,1],[0,1,0],1e-8);expected=45 if n==1 else 90/n
        assert abs(r['max_turn']-expected)<1e-5 and abs(r['sum_turn']-90)<1e-5,(n,r)
        out.append(dict(segments=n,expected=expected,**r))
    # Add deliberate backtracking kink: geometry still has same anchors.
    p=np.array([[2,0],[1,0],[.3,.15],[.65,.5],[0,1],[0,2]])
    V=np.array([[x,y,z] for x,z in p for y in (-1,1)]);F=[[2*i,2*i+1,2*i+3,2*i+2] for i in range(len(p)-1)]
    r=section(V,F,[1,0,0],[0,0,1],[0,1,0],1e-8);assert r['sum_turn']>180
    out.append(dict(segments='kink',**r))
    # Ambiguous/coplanar sections must not produce a quality score.
    controls=[('coplanar',[[0,0,0],[1,0,0],[0,0,1]],[[0,1,2]],[0,0,0],[1,0,0],[0,1,0],'coplanar_triangle'),
      ('missing_anchor',V,F,[20,0,0],[0,0,1],[0,1,0],'anchor_missing')]
    for name,v,f,a,b,n,expected in controls:
        try:section(v,f,a,b,n,1e-8)
        except ValueError as e:assert str(e)==expected,(name,e);out.append(dict(test=name,rejected=str(e)))
        else:raise AssertionError(name)
    return out

def main():
    t=time.perf_counter();cc=controls();rows=[]
    for c in json.loads((ROOT/'phase111_fixtures.json').read_text())['cases']:
        sharp=c['sharp'];V=np.array(sharp['vertices']);F=sharp['faces'];n=len(sharp['edges']);nf=len(c['source_faces']);axis=V[F[nf+n][3]]-V[F[nf+n][0]]
        # For each corresponding root edge use a radial plane through source and child seam midpoints.
        for j in range(n):
            f=F[nf+j];g=F[nf+n+j];A=V[f[:2]].mean(0);B=V[g[2:]].mean(0);C=V[f[2:]].mean(0);N=np.cross(C-A,B-C);scale=max(np.ptp(V,axis=0));tol=scale*1e-7
            entry=dict(case=c['name'],section=j)
            if np.linalg.norm(N)<tol:entry['error']='degenerate_plane';rows.append(entry);continue
            for mode in ('sharp','custom'):
                try:entry[mode]=section(c[mode]['vertices'],c[mode]['faces'],A,B,N,tol)
                except ValueError as e:entry[mode]={'error':str(e)}
            rows.append(entry)
    good=[r for r in rows if all('error' not in r.get(m,{'error':1}) for m in ('sharp','custom'))];summary=[]
    for c in sorted({r['case'] for r in rows}):
        allr=[r for r in rows if r['case']==c];g=[r for r in good if r['case']==c];summary.append(dict(case=c,valid=len(g),total=len(allr),sharp_max=max((r['sharp']['max_turn'] for r in g),default=None),custom_max=max((r['custom']['max_turn'] for r in g),default=None),sharp_p95=float(np.percentile([r['sharp']['max_turn'] for r in g],95)) if g else None,custom_p95=float(np.percentile([r['custom']['max_turn'] for r in g],95)) if g else None))
    result=dict(scope=__doc__,approved=False,controls=cc,rows=rows,summary=summary,elapsed=time.perf_counter()-t);(ROOT/'phase119_section_quality.json').write_text(json.dumps(result,indent=2));print(json.dumps(summary,indent=2));print('controls',len(cc),'matched sections',len(good),'/',len(rows),'elapsed',result['elapsed'])
if __name__=='__main__':main()
