import json,math,unittest
from pathlib import Path
from rim_local import PLAN,turns,fair,loops_from_mesh,trial
from visibility_diagnostic import read_obj,raster,png
from garment import edge_groups

class RimLocalTests(unittest.TestCase):
    def test_turn_detects_corner(self):
        p=[(0.,0.,0.),(1.,0.,0.),(1.,1.,0.),(0.,1.,0.)]
        self.assertEqual(turns(p,[0,1,2,3]),[90.]*4)
    def test_fixed_waist_and_smooth_loop_identity(self):
        p=[(math.cos(2*math.pi*i/16),math.sin(2*math.pi*i/16),z) for z in (.4,-.4) for i in range(16)]
        q=[(i,(i+1)%16,(i+1)%16+16,i+16) for i in range(16)]
        l=(list(range(16)),list(range(16,32)))
        for steps in PLAN:self.assertEqual(fair(p,q,l,steps),p)
        with self.assertRaises(ValueError):fair(p,q,l,99)

def evidence():
    src=Path("results/cap_fairing")
    dest=Path("results/rim_local");dest.mkdir(parents=True,exist_ok=True)
    source=json.loads((src/"report.json").read_text())
    if not source["fixture_gate"]:raise ValueError("unqualified source")
    cases=[]
    for name in ("standard","front_wrap","rear_wrap","both_wrap"):
        p,q=read_obj(src/(name+".obj"))
        l=loops_from_mesh(p,q)
        r,a=trial(p,q,l)
        r["name"]=name
        cases.append(r)
        groups=edge_groups(q,l)
        with (dest/(name+".obj")).open("w") as out:
            out.write("# R10D accepted candidate or unchanged source fallback\n")
            for v in a:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(q,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(a,tris,angle)
            png(dest/(name+"_"+label+".png"),side,lights,False)
    report=dict(complete=True,cases=cases,fixture_gate=all(r["passed"] for r in cases),
        visual_review_required=True,global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213RIMLOCAL_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
