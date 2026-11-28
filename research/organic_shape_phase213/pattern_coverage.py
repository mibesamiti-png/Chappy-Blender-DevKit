"""R12H: independent front/back outline width over accepted R12G geometry.

Static analytic pilot. Changes projected panel halfwidth, not measured body coverage.
No change to waist, side junction, bridge or opposite unrequested panel.
"""
import math
from pattern_garment import CASES,N,UP,DOWN,mesh,inspect
from test_pattern_rim import side_angles
from rim_local import turns

# Fixed signed fractional change at the middle of each lower panel.
PLAN=(("standard",0,0.,0.),
      ("front_narrow",0,-.12,0.),
      ("rear_full",0,0.,.12),
      ("combined",0,-.12,.12),
      ("narrow_side_holdout",1,-.12,.12))

def generate(spec):
    if spec not in PLAN:raise ValueError("fixed coverage fixtures")
    name,index,front,rear=spec
    case=CASES[index]
    p,q,l,g,a,b=mesh(case,"ellipse_rim")
    # Faces are generated in structured row order. Recover lower row IDs from
    # their face indices, avoiding positional classification of the rear panel.
    rows={}
    for role,offset in (("front",0),("back",(UP+DOWN)*N)):
        panel=[]
        for j in range(UP,UP+DOWN):
            fs=q[offset+j*N:offset+(j+1)*N]
            row=sorted({i for face in fs for i in face},key=lambda i:(-p[i][2],p[i][0]))
            if len(row)!=2*(N+1):raise ValueError("unexpected structured row")
            if j==UP:panel.append(row[:N+1])
            panel.append(row[N+1:])
        rows[role]=panel
    out=list(p)
    for role,value in (("front",front),("back",rear)):
        if not value:continue
        for j,row in enumerate(rows[role][1:-1],1):
            weight=math.sin(math.pi*j/DOWN)**2
            for i in row:
                x,y,z=p[i];out[i]=(x*(1+value*weight),y,z)
    return case,p,out,q,l,g,a,b,rows

def evaluate(spec):
    name,_,front,rear=spec
    case,p,v,q,l,g,a,b,rows=generate(spec)
    m=inspect(case,v,q,l,g,a,b)
    fixed=set(l[0])|set(a)|set(b)|set(rows["front"][0])|set(rows["back"][0])
    requested={"front":front,"back":rear}
    measured={}
    errors=[]
    unchanged={}
    for role,rowset in rows.items():
        row=rowset[DOWN//2]
        before=max(abs(p[i][0]) for i in row)
        after=max(abs(v[i][0]) for i in row)
        actual=after/before-1
        measured[role]=dict(baseline_halfwidth=before,actual_halfwidth=after,
                            requested_fraction=requested[role],actual_fraction=actual)
        errors.append(abs(actual-requested[role]))
        unchanged[role]=all(p[i]==v[i] for row in rowset for i in row)
    changed_ids={i for role,rows0 in rows.items() if requested[role] for row in rows0[1:-1] for i in row}
    outside_fixed=all(x==y for i,(x,y) in enumerate(zip(p,v)) if i not in changed_ids)
    side=side_angles(v,l,case)
    max_rim=max(max(turns(v,loop)) for loop in l[1:])
    original_rim=max(max(turns(p,loop)) for loop in l[1:])
    fixed_ok=all(p[i]==v[i] for i in fixed)
    gate=(m["passed"] and max(errors)<1e-10 and fixed_ok and outside_fixed
          and all(unchanged[r] for r in rows if not requested[r])
          and max(side)<=35 and max_rim<=original_rim+5.)
    return dict(name=name,measured=measured,dimension_error=max(errors),
        unchanged_panels=unchanged,outside_requested_rows_fixed=outside_fixed,
        fixed_endpoints=fixed_ok,side_turn=side,baseline_max_rim_turn=original_rim,
        max_rim_turn=max_rim,metrics=m,passed=gate), (v,q,g)
