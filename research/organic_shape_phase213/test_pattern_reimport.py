import json,unittest,tempfile
from pathlib import Path
from pattern_garment import CASES,mesh
from pattern_split import panel_audit,split
from pattern_reimport import read_panel,verify

class ReimportTests(unittest.TestCase):
    def test_correct_topology_by_mode(self):
        p,q,l,g,_,_=mesh(CASES[0])
        one=split(p,q,g,"integrated")["fabric"]
        self.assertTrue(panel_audit(one,3)["passed"])
        self.assertFalse(panel_audit(one,1)["passed"])
        for part in split(p,q,g,"separate").values():
            self.assertTrue(panel_audit(part,1)["passed"])
            self.assertFalse(panel_audit(part,3)["passed"])
    def test_reject_invalid_obj(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"front.obj"
            f.write_text("o front\nv nan 0 0\n")
            with self.assertRaisesRegex(ValueError,"nonfinite"):read_panel(f,"front")
            f.write_text("o wrong\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n")
            with self.assertRaisesRegex(ValueError,"invalid OBJ panel"):read_panel(f,"front")

def evidence():
    src=Path("results/pattern_split")
    if not json.loads((src/"report.json").read_text())["fixture_gate"]:raise ValueError("R12B gate failed")
    dest=Path("results/pattern_reimport");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for case in CASES:
        name=case[0];p,q,*_=mesh(case)
        modes={mode:verify(src/name/mode,mode,p,q) for mode in ("integrated","separate")}
        cases.append(dict(name=name,modes=modes,passed=all(r["passed"] for r in modes.values())))
    report=dict(complete=True,cases=cases,fixture_gate=all(r["passed"] for r in cases),
        actual_file_readback=True,synthetic_only=True,blender_verified=False,anatomical_fit_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213REIMPORT_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
