"""R7B: compare a single rounded garment variant with original R7A.
Shape proxies are not a guarantee of aesthetics or real lower-body fit.
"""
import json,unittest,math
from pathlib import Path
from garment import trial,base,edge_groups
from test_garment import preview

def shape_metrics(p,q,l):
    # Central-plane edge intersections, independent of the prescribed bridge.
    center=[]
    for f in q:
        for a,b in zip(f,f[1:]+f[:1]):
            A,B=p[a],p[b]
            if abs(A[0])<1e-12:center.append(A[2])
            if A[0]*B[0]<0:
                t=-A[0]/(B[0]-A[0])
                center.append(A[2]+t*(B[2]-A[2]))
    low=min(z for x,y,z in p)
    if not center:raise ValueError("missing center-plane intersection")
    # Rear vs front leg hem heights, sampled at corresponding y extrema.
    rear_drop=[]
    for loop in l[1:]:
        front=max(loop,key=lambda i:p[i][1]);back=min(loop,key=lambda i:p[i][1])
        rear_drop.append(p[front][2]-p[back][2])
    return dict(center_min_z=min(center),lowest_z=low,notch_depth=min(center)-low,rear_hem_drop=rear_drop)

def compare():
    results={}
    models={}
    for style in ("original","rounded"):
        p,q,l,r=trial(style)
        m=shape_metrics(p,q,l)
        results[style]=dict(trial=r,shape=m)
        models[style]=(p,q,l)
    a,b=(results[s]["shape"] for s in ("original","rounded"))
    gate=results["rounded"]["trial"]["fixture_gate"] and b["notch_depth"]<=.7*a["notch_depth"] and min(b["rear_hem_drop"])>=.15
    return dict(complete=True,results=results,shape_proxy_gate=gate,visual_review_required=True,
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False),models

class RoundedTests(unittest.TestCase):
    def test_baseline_and_topology(self):
        a,b,c=base();p,q,l=base("rounded")
        self.assertEqual((b,c),(q,l))
        self.assertNotEqual(a,p)
        with self.assertRaises(ValueError):base("unknown")
    def test_comparison(self):
        r,models=compare()
        self.assertTrue(r["results"]["original"]["trial"]["fixture_gate"])
        for style,(p,q,l) in models.items():
            self.assertEqual((len(p),len(q)),(6287,6144))
            self.assertGreaterEqual(r["results"][style]["shape"]["notch_depth"],0)
        self.assertTrue(r["visual_review_required"])

def evidence():
    dest=Path("results/r7b");dest.mkdir(parents=True,exist_ok=True)
    report,models=compare()
    for style,(p,q,l) in models.items():
        groups=edge_groups(q,l)
        with (dest/(style+".obj")).open("w") as out:
            out.write("# R7B static garment comparison\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(q,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(style+"_preview.svg"),p,q,groups)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R7B_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
