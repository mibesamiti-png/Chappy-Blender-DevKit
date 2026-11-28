import json,math,unittest
from pathlib import Path
from pattern_garment import CASES,mesh,inspect,WAIST
from rim_local import turns
from visibility_diagnostic import raster,png
from test_pattern_garment import export_obj

def side_angles(p,l,case):
    out=[]
    for loop in l[1:]:
        idx=min(range(len(loop)),key=lambda j:math.dist(p[loop[j]],(math.copysign(case[1],p[loop[j]][0]),0.,WAIST-case[4])))
        if abs(p[loop[idx]][1])>1e-10 or abs(p[loop[idx]][2]-(WAIST-case[4]))>1e-10:
            raise ValueError("missing side junction")
        out.append(turns(p,loop)[idx])
    return out

def compare(case):
    p,q,l,g,a,b=mesh(case)
    v,f,r,h,c,d=mesh(case,"round_rim")
    m=inspect(case,v,f,r,h,c,d)
    before=side_angles(p,l,case);after=side_angles(v,r,case)
    old_max=max(max(turns(p,loop)) for loop in l[1:])
    new_max=max(max(turns(v,loop)) for loop in r[1:])
    fixed=set(l[0])|set(a)|set(b)
    unchanged=all(p[i]==v[i] for i in fixed)
    topology_same=(q,l,g,a,b)==(f,r,h,c,d)
    passed=(m["passed"] and topology_same and unchanged and max(after)<=35
            and all(y<=.5*x for x,y in zip(before,after)) and new_max<=old_max)
    return dict(name=case[0],baseline_side_turn=before,candidate_side_turn=after,
        baseline_max_rim_turn=old_max,candidate_max_rim_turn=new_max,
        fixed_endpoints=unchanged,same_connectivity=topology_same,metrics=m,passed=passed), (v,f,h)

class PatternRimTests(unittest.TestCase):
    def test_fixed_endpoints(self):
        for case in CASES:
            p,q,l,g,a,b=mesh(case)
            v,f,r,h,c,d=mesh(case,"round_rim")
            self.assertEqual((q,l,g,a,b),(f,r,h,c,d))
            self.assertTrue(all(p[i]==v[i] for i in set(l[0])|set(a)|set(b)))
    def test_side_angle_reduction(self):
        case=CASES[0]
        p,q,l,*_=mesh(case)
        v,f,r,*_=mesh(case,"round_rim")
        self.assertLess(max(side_angles(v,r,case)),max(side_angles(p,l,case)))

def evidence():
    dest=Path("results/pattern_rim");dest.mkdir(parents=True,exist_ok=True)
    source=json.loads(Path("results/pattern_reimport/report.json").read_text())
    if not source["fixture_gate"]:raise ValueError("R12C gate failed")
    cases=[]
    for case in CASES:
        result,(p,q,g)=compare(case);cases.append(result)
        name=case[0]
        export_obj(dest/(name+"_candidate.obj"),p,q,g)
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(p,tris,angle)
            png(dest/(name+"_"+label+".png"),side,lights,False)
    report=dict(complete=True,cases=cases,fixture_gate=all(c["passed"] for c in cases),
        original_preserved=True,visual_review_required=True,blender_verified=False,anatomical_fit_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213PATTERNRIM_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
