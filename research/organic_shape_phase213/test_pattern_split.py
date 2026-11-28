import json,unittest,copy
from pathlib import Path
from pattern_garment import CASES,mesh
from pattern_split import split,assemble,trial

class PanelSplitTests(unittest.TestCase):
    def test_exact_roundtrip(self):
        for case in CASES:
            p,q,modes=trial(case)
            self.assertTrue(all(r["passed"] for r,_ in modes.values()),modes)
            self.assertEqual(len(modes["integrated"][1]),1)
            self.assertEqual(len(modes["separate"][1]),3)
    def test_reject_modified_seam(self):
        p,q,l,g,a,b=mesh(CASES[0])
        parts=split(p,q,g,"separate")
        bad=copy.deepcopy(parts)
        i=next(i for i,v in enumerate(bad["crotch"]["source_vertices"]) if v in bad["front"]["source_vertices"])
        x,y,z=bad["crotch"]["vertices"][i]
        bad["crotch"]["vertices"][i]=(x+.001,y,z)
        with self.assertRaisesRegex(ValueError,"seam coordinate conflict"):assemble(bad,len(p),len(q))
    def test_missing_panel(self):
        p,q,l,g,a,b=mesh(CASES[0])
        parts=split(p,q,g,"separate")
        del parts["back"]
        with self.assertRaisesRegex(ValueError,"incomplete assembly"):assemble(parts,len(p),len(q))

def evidence():
    src=json.loads(Path("results/pattern_garment/report.json").read_text())
    if not src["fixture_gate"]:raise ValueError("R12A source unqualified")
    dest=Path("results/pattern_split");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for case in CASES:
        name=case[0];p,q,modes=trial(case)
        r={"name":name,"modes":{}}
        for mode,(report,parts) in modes.items():
            r["modes"][mode]=report
            folder=dest/name/mode;folder.mkdir(parents=True,exist_ok=True)
            (folder/"provenance.json").write_text(json.dumps(parts,indent=2,allow_nan=False))
            for role,part in parts.items():
                with (folder/(role+".obj")).open("w") as out:
                    out.write("# R12B independent surface panel, no thickness\n")
                    out.write("o "+role+"\n")
                    for v in part["vertices"]:out.write("v "+" ".join(format(x,".17g") for x in v)+"\n")
                    for f in part["faces"]:out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        r["passed"]=all(m["passed"] for m in r["modes"].values())
        cases.append(r)
    report=dict(complete=True,cases=cases,fixture_gate=all(r["passed"] for r in cases),
        exact_index_reassembly=True,physical_panel_split=True,synthetic_only=True,
        cloth_simulation=False,pattern_flattening_verified=False,anatomical_fit_verified=False,
        blender_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213SPLIT_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
