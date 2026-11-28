"""R12C strict readback of actual independent panel OBJ and provenance files."""
import json,math,hashlib
from pathlib import Path
from pattern_split import assemble,panel_audit,seam_audit

def read_panel(path,role):
    p=[];q=[];objects=[]
    for line in path.read_text().splitlines():
        a=line.split()
        if not a or a[0].startswith("#"):continue
        if a[0]=="o" and len(a)==2:objects.append(a[1])
        elif a[0]=="v" and len(a)==4:
            v=tuple(map(float,a[1:]))
            if not all(map(math.isfinite,v)):raise ValueError("nonfinite OBJ vertex")
            p.append(v)
        elif a[0]=="f" and len(a)==5:
            f=tuple(int(x)-1 for x in a[1:])
            if min(f)<0 or max(f)>=len(p) or len(set(f))!=4:raise ValueError("invalid OBJ face")
            q.append(f)
        else:raise ValueError("unexpected OBJ record")
    if objects!=[role] or not p or not q:raise ValueError("invalid OBJ panel")
    return p,q

def read_parts(folder,mode):
    folder=Path(folder)
    if mode not in ("integrated","separate"):raise ValueError("unknown mode")
    roles={"fabric"} if mode=="integrated" else {"front","back","crotch"}
    provenance=json.loads((folder/"provenance.json").read_text())
    if set(provenance)!=roles or {p.stem for p in folder.glob("*.obj")}!=roles:
        raise ValueError("panel file set mismatch")
    result={};hashes={}
    for role in sorted(roles):
        path=folder/(role+".obj");p,q=read_panel(path,role);m=provenance[role]
        if p!=[tuple(v) for v in m["vertices"]] or q!=[tuple(f) for f in m["faces"]]:
            raise ValueError("OBJ/provenance geometry mismatch")
        result[role]=dict(vertices=p,faces=q,source_vertices=m["source_vertices"],source_faces=m["source_faces"])
        hashes[role]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result,hashes

def verify(folder,mode,p,q):
    parts,hashes=read_parts(folder,mode)
    recovered=assemble(parts,len(p),len(q))
    audits={k:panel_audit(v,3 if mode=="integrated" else 1) for k,v in parts.items()}
    seams=seam_audit(parts)
    expected={} if mode=="integrated" else {"back|front":16,"back|crotch":32,"crotch|front":32}
    exact=recovered==(p,q)
    return dict(exact_file_reassembly=exact,parts=audits,seams=seams,
        obj_sha256=hashes,provenance_sha256=hashlib.sha256((Path(folder)/"provenance.json").read_bytes()).hexdigest(),
        passed=exact and all(a["passed"] for a in audits.values()) and seams["counts"]==expected and seams["orientation_errors"]==0)
