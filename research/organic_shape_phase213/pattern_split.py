"""R12B: exact panel extraction and provenance-based reassembly.

No positional welding tolerance, shape edits, thickness or flat-pattern claim.
"""
from collections import Counter,defaultdict
from pattern_garment import mesh,partition

def split(p,q,groups,mode):
    labels=partition(groups,mode)
    parts={}
    for role in sorted(set(labels)):
        indices=[i for i,g in enumerate(labels) if g==role]
        ids=sorted({j for i in indices for j in q[i]})
        local={j:i for i,j in enumerate(ids)}
        parts[role]=dict(vertices=[p[j] for j in ids],
            faces=[tuple(local[j] for j in q[i]) for i in indices],
            source_vertices=ids,source_faces=indices)
    return parts

def assemble(parts,nv,nf):
    p=[None]*nv;q=[None]*nf
    for part in parts.values():
        ids=part["source_vertices"];face_ids=part["source_faces"]
        if len(ids)!=len(part["vertices"]) or len(set(ids))!=len(ids):raise ValueError("vertex provenance")
        if len(face_ids)!=len(part["faces"]):raise ValueError("face provenance")
        for i,v in zip(ids,part["vertices"]):
            if not 0<=i<nv:raise ValueError("source vertex range")
            v=tuple(v)
            if p[i] is not None and p[i]!=v:raise ValueError("seam coordinate conflict")
            p[i]=v
        for i,f in zip(face_ids,part["faces"]):
            if not 0<=i<nf or q[i] is not None:raise ValueError("duplicate or invalid source face")
            if len(f)!=4 or len(set(f))!=4 or any(not 0<=j<len(ids) for j in f):raise ValueError("invalid local quad")
            q[i]=tuple(ids[j] for j in f)
    if any(v is None for v in p) or any(f is None for f in q):raise ValueError("incomplete assembly")
    return p,q

def panel_audit(part):
    p,q=part["vertices"],part["faces"]
    edges=Counter();directions=Counter();adj=defaultdict(set)
    for f in q:
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b)));edges[e]+=1;directions[e]+=1 if a<b else -1
            adj[a].add(b);adj[b].add(a)
    seen={0};stack=[0]
    while stack:
        for j in adj[stack.pop()]-seen:seen.add(j);stack.append(j)
    border=[e for e,n in edges.items() if n==1]
    degrees=Counter(i for e in border for i in e)
    euler=len(p)-len(edges)+len(q)
    orientation_errors=sum(n==2 and directions[e]!=0 for e,n in edges.items())
    manifold_errors=sum(n>2 for n in edges.values())
    connected=len(seen)==len(p)
    return dict(vertices=len(p),quads=len(q),euler=euler,boundary_edges=len(border),
        boundary_degrees_ok=all(n==2 for n in degrees.values()),connected=connected,
        orientation_errors=orientation_errors,nonmanifold_edges=manifold_errors,
        passed=connected and euler==1 and all(n==2 for n in degrees.values()) and not orientation_errors and not manifold_errors)

def seam_audit(parts):
    inc=defaultdict(list)
    for role,part in parts.items():
        ids=part["source_vertices"]
        for f in part["faces"]:
            for a,b in zip(f,f[1:]+f[:1]):
                x,y=ids[a],ids[b]
                inc[tuple(sorted((x,y)))].append((role,x,y))
    counts=Counter();bad=0
    for records in inc.values():
        if len(records)==2 and records[0][0]!=records[1][0]:
            a,b=records
            counts["|".join(sorted((a[0],b[0])))]+=1
            bad+=int(a[1:]!=b[1:][::-1])
    return dict(counts=dict(counts),orientation_errors=bad)

def trial(case):
    p,q,l,g,a,b=mesh(case)
    modes={}
    for mode in ("integrated","separate"):
        parts=split(p,q,g,mode)
        recovered=assemble(parts,len(p),len(q))
        exact=recovered==(p,q)
        seams=seam_audit(parts)
        audits={k:panel_audit(v) for k,v in parts.items()}
        expected={"back|front":16,"back|crotch":32,"crotch|front":32} if mode=="separate" else {}
        passed=exact and seams["counts"]==expected and seams["orientation_errors"]==0
        if mode=="separate":passed=passed and all(v["passed"] for v in audits.values())
        modes[mode]=(dict(exact_reassembly=exact,parts=audits,seams=seams,passed=passed),parts)
    return p,q,modes
