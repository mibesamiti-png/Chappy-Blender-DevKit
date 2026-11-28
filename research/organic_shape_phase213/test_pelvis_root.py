import json,math,unittest
from pathlib import Path
from pelvis_field import CASES,field,edge_root,extract,audit
from visibility_diagnostic import raster,png
from intersection import audit as intersection_audit

class RootTests(unittest.TestCase):
    def test_bracket(self):
        case=CASES[0];a=(0.,0.,.8);b=(1.5,0.,.8)
        r=edge_root(a,b,field(a,case),field(b,case),case)
        self.assertLess(abs(field(r,case)),1e-7)
        self.assertEqual(r[1:],a[1:])
        with self.assertRaises(ValueError):edge_root(a,a,-1.,-1.,case)
    def test_same_connectivity_and_residual(self):
        for case in CASES:
            p,q=extract(case);v,f=extract(case,"bracketed")
            # Winding may change if nonlinear triangles turn over; report that
            # explicitly in the full audit rather than hiding it.
            self.assertEqual([sorted(t) for t in q],[sorted(t) for t in f])
            self.assertEqual(len(p),len(v))
            self.assertLess(max(abs(field(x,case)) for x in v),1e-7)

def evidence():
    dest=Path("results/pelvis_root");dest.mkdir(parents=True,exist_ok=True)
    results=[]
    for case in CASES:
        name=case[0];p,q=extract(case)
        v,f=extract(case,"bracketed")
        baseline=audit(p,q,case);m=audit(v,f,case)
        collision=intersection_audit(v,f)
        same_connectivity=[sorted(t) for t in q]==[sorted(t) for t in f]
        winding_changes=sum(a!=b for a,b in zip(q,f))
        movement=max(math.dist(a,b) for a,b in zip(p,v))
        passed=(m["passed"] and collision["passed"] and same_connectivity
                and winding_changes==0 and m["max_field_residual"]<=1e-7)
        results.append(dict(name=name,baseline=baseline,metrics=m,
            same_connectivity=same_connectivity,winding_changes=winding_changes,
            max_vertex_movement=movement,nonincident_intersection=collision,passed=passed))
        with (dest/(name+".obj")).open("w") as out:
            out.write("# R11B bracketed implicit envelope; triangle surface\n")
            for x in v:out.write("v "+" ".join(format(a,".12g") for a in x)+"\n")
            for t in f:out.write("f "+" ".join(str(i+1) for i in t)+"\n")
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(v,f,angle,width=430,height=340,scale=125)
            png(dest/(name+"_"+label+".png"),side,lights,False,width=430,height=340)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        synthetic_only=True,vertex_residual_only=True,anatomical_fit_verified=False,
        garment_fit_verified=False,quad_retopology_verified=False,global_intersection_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213ROOT_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
