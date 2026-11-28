"""R12J: fixed localized crotch-strip taper; no change to R12H."""
import json, math, unittest
from pathlib import Path
from pattern_coverage import PLAN, generate
from pattern_garment import N, BRIDGE, inspect
from test_pattern_rim import side_angles
from rim_local import turns
from test_pattern_garment import export_obj
from visibility_diagnostic import raster, png

FRACTION = .15

def candidate(spec):
    case, _, baseline, q, loops, groups, a, b, _ = generate(spec)
    # Only vertices belonging to the crotch panel, with seams excluded.
    ids = {i for f, role in zip(q, groups) if role == "crotch" for i in f}
    seams = set(a) | set(b)
    interior = ids - seams
    out = list(baseline)
    length = case[6]
    rows = [[] for _ in range(BRIDGE+1)]
    for i in ids:
        x,y,z = baseline[i]
        t = .5-y/length
        j = round(t*BRIDGE)
        if not 0 <= j <= BRIDGE or abs(t-j/BRIDGE)>1e-10:
            raise ValueError("unexpected bridge row")
        rows[j].append(i)
        if i in interior:
            out[i] = (x*(1-FRACTION*math.sin(math.pi*t)**2),y,z)
    if any(len(r)!=N+1 for r in rows) or len(interior)!=(BRIDGE-1)*(N+1):
        raise ValueError("unexpected bridge layout")
    return case,baseline,out,q,loops,groups,a,b,rows,interior

def widths(p, rows):
    return [max(p[i][0] for i in r)-min(p[i][0] for i in r) for r in rows]

def evaluate(spec):
    case,p,v,q,l,g,a,b,rows,interior = candidate(spec)
    old,new = widths(p,rows), widths(v,rows)
    mid = BRIDGE//2
    fractions = [1-y/x for x,y in zip(old,new)]
    width_error = max(abs(x-FRACTION*math.sin(math.pi*j/BRIDGE)**2)
                      for j,x in enumerate(fractions))
    fixed = all(x==y for i,(x,y) in enumerate(zip(p,v)) if i not in interior)
    yz_fixed = all(x[1:]==y[1:] for x,y in zip(p,v))
    side0, side1 = side_angles(p,l,case), side_angles(v,l,case)
    rim0 = max(max(turns(p,r)) for r in l[1:])
    rim1 = max(max(turns(v,r)) for r in l[1:])
    m = inspect(case,v,q,l,g,a,b)
    gate = (m["passed"] and fixed and yz_fixed and width_error<1e-10
            and all(y<=x+1e-12 for x,y in zip(old,new))
            and max(abs(x-y) for x,y in zip(side0,side1))<1e-10
            and rim1<=rim0+5)
    return dict(name=spec[0],baseline_widths=old,candidate_widths=new,
        middle_width_reduction=fractions[mid],profile_error=width_error,
        unchanged_outside_bridge=fixed,yz_fixed=yz_fixed,
        baseline_side_turn=side0,candidate_side_turn=side1,
        baseline_max_rim_turn=rim0,candidate_max_rim_turn=rim1,
        metrics=m,passed=gate),(p,v,q,g)

class BridgeTests(unittest.TestCase):
    def test_locality_and_width(self):
        for spec in PLAN:
            _,p,v,_,_,_,a,b,rows,interior=candidate(spec)
            self.assertTrue(all(x==y for i,(x,y) in enumerate(zip(p,v)) if i not in interior))
            self.assertTrue(all(x[1:]==y[1:] for x,y in zip(p,v)))
            self.assertTrue(all(p[i]==v[i] for i in set(a)|set(b)))
            old,new=widths(p,rows),widths(v,rows)
            self.assertAlmostEqual(new[BRIDGE//2]/old[BRIDGE//2],1-FRACTION)
            self.assertEqual((old[0],old[-1]),(new[0],new[-1]))
    def test_invalid_spec(self):
        with self.assertRaises(ValueError):
            candidate(("unknown",0,0.,0.))

def evidence():
    source=json.loads(Path("results/pattern_coverage/report.json").read_text())
    if not source["fixture_gate"]:raise ValueError("R12H source gate failed")
    dest=Path("results/pattern_bridge");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for spec in PLAN:
        result,(p,v,q,g)=evaluate(spec);cases.append(result)
        name=spec[0]
        export_obj(dest/(name+"_candidate.obj"),v,q,g)
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        # Rotate coordinates for a view from below (original negative Z).
        # This is a rigid rotation and screen-centering translation.
        for label,points in (("baseline_bottom",[(x,-z,y-.35) for x,y,z in p]),
                             ("candidate_bottom",[(x,-z,y-.35) for x,y,z in v]),
                             ("baseline_front",p),("candidate_front",v)):
            side,lights=raster(points,tris,0.,height=400,scale=125)
            png(dest/(name+"_"+label+".png"),side,lights,False,height=400)
    report=dict(complete=True,cases=cases,fixture_gate=all(c["passed"] for c in cases),
        original_preserved=True,visual_review_required=True,blender_verified=False,
        anatomical_fit_verified=False,metric="local crotch planform width; not overall silhouette")
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213PATTERNBRIDGE_SUMMARY",json.dumps(report,allow_nan=False))

if __name__=="__main__":evidence()
