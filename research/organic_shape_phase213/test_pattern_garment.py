import json,math,unittest
from pathlib import Path
from pattern_garment import CASES,N,UP,mesh,partition,inspect
from visibility_diagnostic import raster,png

class PatternTests(unittest.TestCase):
    def test_dimensions_and_topology(self):
        for case in CASES:
            p,q,l,g,a,b=mesh(case)
            self.assertEqual(len(l),3)
            self.assertEqual(len(g),len(q))
            self.assertAlmostEqual(math.dist(p[a[0]],p[a[-1]]),case[5])
            self.assertAlmostEqual(math.dist(p[a[N//2]],p[b[N//2]]),case[6])
            self.assertTrue(all(len(set(f))==4 for f in q))
    def test_panel_modes_do_not_modify_geometry(self):
        p,q,l,g,a,b=mesh(CASES[0])
        self.assertEqual(set(partition(g,"integrated")),{"fabric"})
        self.assertEqual(set(partition(g,"separate")),{"front","back","crotch"})
        self.assertEqual(len(partition(g,"integrated")),len(q))
        self.assertEqual(mesh(CASES[0]),(p,q,l,g,a,b))
        with self.assertRaises(ValueError):partition(g,"invalid")
    def test_negative_fixture(self):
        with self.assertRaises(ValueError):mesh(("unknown",))

def export_obj(path,p,q,groups):
    with path.open("w") as out:
        out.write("# R12A welded analytic synthetic surface, groups indicate optional segmentation only\n")
        for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
        prev=None
        for f,g in zip(q,groups):
            if g!=prev:out.write("g "+g+"\n");prev=g
            out.write("f "+" ".join(str(i+1) for i in f)+"\n")

def evidence():
    dest=Path("results/pattern_garment");dest.mkdir(parents=True,exist_ok=True)
    results=[]
    for case in CASES:
        name=case[0];p,q,l,g,a,b=mesh(case)
        r=inspect(case,p,q,l,g,a,b)
        r.update(name=name,configuration=case[1:],panel_modes=["integrated","separate"],same_welded_geometry=True)
        results.append(r)
        for mode in ("integrated","separate"):
            export_obj(dest/(name+"_"+mode+".obj"),p,q,partition(g,mode))
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(p,tris,angle)
            png(dest/(name+"_"+label+".png"),side,lights,False)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        synthetic_only=True,visual_review_required=True,physical_panel_split_verified=False,
        pattern_flattening_verified=False,anatomical_fit_verified=False,
        global_intersection_verified=False,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213PATTERN_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
