import json,unittest,math
from pathlib import Path
from garment import base,trial,inspect,edge_groups,N
from junction import audit
from patch import cross,sub,dot
from boundary import norm

class GarmentTests(unittest.TestCase):
    def test_boundary_roles(self):
        p,q,l=base()
        self.assertTrue(audit(p,q,l,p)["topology_pass"])
        self.assertEqual([len(x) for x in l],[N]*3)
        self.assertTrue(all(p[i][0]<0 for i in l[1]))
        self.assertTrue(all(p[i][0]>0 for i in l[2]))
        for loop in l[1:]:
            z=[p[i][2] for i in loop]
            self.assertGreater(max(z)-min(z),.5)
    def test_bounded_trial(self):
        p,q,l,r=trial()
        self.assertEqual([c["smoothing"] for c in r["candidates"]],list((0,8,16)[:len(r["candidates"])]))
        self.assertEqual(r["fixture_gate"],any(c["metrics"]["garment_pilot_pass"] for c in r["candidates"]))
        self.assertEqual(len(q),6144)
        self.assertEqual(len(p),6287)
        self.assertEqual([len(x) for x in l],[96]*3)
    def test_negative_controls(self):
        p,q,l=base()
        self.assertFalse(inspect(p,q[1:],l,p)["garment_pilot_pass"])
        bad=p[:];i=l[0][0];x,y,z=p[i];bad[i]=(x*.7,y*.7,z)
        m=inspect(bad,q,l,p)
        self.assertFalse(m["garment_pilot_pass"])
        self.assertLess(m["upper_gap_min"],0)

def preview(path,p,q,groups):
    # Actual geometry, orthographic painter-sort preview, not a Blender render.
    text=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 930 350" width="930" height="350">','<rect width="930" height="350" fill="#f3f5f8"/>']
    for index,(label,angle) in enumerate((("Front",0),("Side",math.pi/2),("Back",math.pi))):
        c,s=math.cos(angle),math.sin(angle)
        right=(c,-s,0);view=(s,c,0)
        cx=155+index*310
        def xy(v):return (cx+112*dot(v,right),120-112*v[2])
        order=sorted(range(len(q)),key=lambda i:sum(dot(p[j],view) for j in q[i])/4)
        for i in order:
            f=q[i];a,b,c0=(p[j] for j in f[:3]);n=cross(sub(b,a),sub(c0,a))
            if norm(n)<1e-12:continue
            light=.45+.55*max(0,dot(n,view)/norm(n))
            basecolor=(80,106,135) if groups[i]=="fabric" else (45,62,83)
            color="#"+''.join(f"{round(25+k*light):02x}" for k in basecolor)
            points=" ".join(f"{x:.2f},{y:.2f}" for x,y in (xy(p[j]) for j in f))
            text.append(f'<polygon points="{points}" fill="{color}" stroke="{color}" stroke-width=".35"/>')
        text.append(f'<text x="{cx}" y="320" text-anchor="middle" font-size="16" fill="#26374a">{label}</text>')
    text.append("</svg>")
    path.write_text("\n".join(text))

def evidence():
    dest=Path("results/r7");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=trial()
    groups=edge_groups(q,l)
    with (dest/"static_shorts.obj").open("w") as out:
        out.write("# R7 static garment surface, optional Solidify in Blender\n")
        out.write("o Static_Shorts\n")
        for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
        last=None
        for face,role in zip(q,groups):
            if role!=last:out.write("g "+role+"\n");last=role
            out.write("f "+" ".join(str(i+1) for i in face)+"\n")
    preview(dest/"actual_geometry_preview.svg",p,q,groups)
    r.update(scope="synthetic static garment; upper torso fit only",thickness_required=False,global_intersection_verified=False,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(r,indent=2,allow_nan=False))
    print("PHASE213R7_SUMMARY",json.dumps(r,allow_nan=False))
if __name__=="__main__":evidence()
