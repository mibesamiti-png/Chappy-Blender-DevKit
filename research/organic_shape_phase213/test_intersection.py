import json,unittest
from pathlib import Path
from intersection import triangle_hit,audit
from fair_garment import trial
from cut_garment import trial as cut_trial

class IntersectionTests(unittest.TestCase):
    def test_known_crossing_and_separation(self):
        a=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        crossing=[(.2,.2,-.5),(.2,.2,.5),(.6,.2,0.)]
        separated=[(.2,.2,.1),(.4,.2,.1),(.2,.4,.1)]
        self.assertTrue(triangle_hit(a,crossing))
        self.assertTrue(triangle_hit(crossing,a))
        self.assertFalse(triangle_hit(a,separated))
        self.assertEqual(audit(a+crossing,[(0,1,2),(3,4,5)])["intersections"],1)
        self.assertEqual(audit(a+separated,[(0,1,2),(3,4,5)])["intersections"],0)
    def test_coplanar_and_touch(self):
        a=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        inside=[(.1,.1,0.),(.3,.1,0.),(.1,.3,0.)]
        outside=[(.6,.6,0.),(.8,.6,0.),(.6,.8,0.)]
        touch=[(1.,0.,0.),(2.,0.,0.),(1.,1.,0.)]
        self.assertTrue(triangle_hit(a,inside))
        self.assertFalse(triangle_hit(a,outside))
        self.assertTrue(triangle_hit(a,touch))
        for b,expected in ((inside,1),(outside,0),(touch,1)):
            self.assertEqual(audit(a+b,[(0,1,2),(3,4,5)])["intersections"],expected)
    def test_incident_exclusion_and_degenerate_reject(self):
        p=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(1.,1.,0.)]
        r=audit(p,[(0,1,2),(1,3,2)])
        self.assertEqual(r["incident_pairs_excluded"],1)
        self.assertEqual(r["nonincident_pairs_tested"],0)
        self.assertFalse(r["incident_overlap_verified"])
        with self.assertRaises(ValueError):audit([(0.,0.,0.),(.1,0.,0.),(.2,0.,0.)],[(0,1,2)])
    def test_broadphase_against_all_pairs(self):
        # Fixed deterministic triangles: compare the grid to exhaustive SAT.
        import random
        rng=random.Random(213)
        p=[];f=[]
        for j in range(36):
            center=[rng.uniform(-.5,.5) for _ in range(3)]
            f.append(tuple(range(len(p),len(p)+3)))
            p.extend(tuple(x+rng.uniform(-.16,.16) for x in center) for _ in range(3))
        expected=sum(triangle_hit([p[k] for k in a],[p[k] for k in b]) for i,a in enumerate(f) for b in f[i+1:])
        self.assertGreater(expected,0)
        self.assertEqual(audit(p,f)["intersections"],expected)

def evidence():
    dest=Path("results/r7e");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for name,generate in (("R7C",cut_trial),("R7D",trial)):
        p,q,l,r=generate()
        assert r["fixture_gate"]
        cases.append(dict(name=name,metrics=audit(p,q)))
    report=dict(complete=True,cases=cases,nonincident_gate=all(c["metrics"]["passed"] for c in cases),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R7E_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
