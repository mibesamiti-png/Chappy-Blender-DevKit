import json,math,unittest
from pathlib import Path
from pelvis_field import CASES,field,smooth_min,extract,audit
from visibility_diagnostic import raster,png
from intersection import audit as intersection_audit

class PelvisTests(unittest.TestCase):
    def test_field_sections(self):
        for case in CASES:
            sep=case[4]
            self.assertLess(field((0.,0.,.8),case),0)
            self.assertGreater(field((0.,0.,-1.25),case),0)
            for sign in (-1,1):
                self.assertLess(field((sign*sep,-.035,-1.25),case),0)
            self.assertGreater(field((1.5,0.,-.1),case),0)
    def test_smooth_union(self):
        self.assertAlmostEqual(smooth_min(.2,.2),.175)
        self.assertEqual(smooth_min(.2,.4),.2)
        self.assertEqual(smooth_min(.4,.2),.2)
    def test_extraction_topology_and_negative(self):
        p,q=extract(CASES[0])
        m=audit(p,q,CASES[0])
        self.assertEqual(m["boundary_roles"],["left","right","waist"])
        self.assertEqual(m["components"],1)
        self.assertEqual(m["orientation_errors"],0)
        self.assertFalse(audit(p,q[1:],CASES[0])["passed"])
        with self.assertRaises(ValueError):extract(("invalid",))

def evidence():
    dest=Path("results/pelvis_field");dest.mkdir(parents=True,exist_ok=True)
    results=[]
    for case in CASES:
        name=case[0];p,q=extract(case);m=audit(p,q,case)
        collision=intersection_audit(p,q)
        results.append(dict(name=name,configuration=case[1:],metrics=m,
            nonincident_intersection=collision,passed=m["passed"] and collision["passed"]))
        with (dest/(name+".obj")).open("w") as out:
            out.write("# R11A synthetic implicit envelope; triangle surface\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            for f in q:out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(p,q,angle,width=430,height=340,scale=125)
            png(dest/(name+"_"+label+".png"),side,lights,False,width=430,height=340)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        synthetic_only=True,anatomical_fit_verified=False,garment_fit_verified=False,
        quad_retopology_verified=False,global_intersection_verified=False,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213PELVIS_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
