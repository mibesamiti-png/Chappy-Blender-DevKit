"""R12K: exact independent panel file roundtrip of actual R12J exports."""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from pattern_coverage import PLAN
from test_pattern_bridge import candidate
from pattern_split import split
from pattern_reimport import verify
from visibility_diagnostic import read_obj
from test_pattern_garment import export_obj

SOURCE = Path("results/pattern_bridge")
DEST = Path("results/pattern_bridge_roundtrip")

def roundtrip(spec, source_path, dest):
    _, _, expected, q, _, groups, _, _, _, _ = candidate(spec)
    p, faces = read_obj(source_path)
    if len(p) != len(expected) or faces != q:
        raise ValueError("R12J exported topology mismatch")
    if not all(math.isfinite(x) for v in p for x in v):
        raise ValueError("nonfinite source coordinates")
    error = max(math.dist(x,y) for x,y in zip(p,expected))
    if error >= 1e-10:
        raise ValueError("R12J coordinate discrepancy")
    # Check the actual exported panel groups, not just regenerated labels.
    labels = []
    role = None
    for line in source_path.read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == "g":
            if len(a) != 2:
                raise ValueError("invalid source group")
            role = a[1]
        elif a[0] == "f":
            labels.append(role)
    if labels != groups:
        raise ValueError("R12J source groups mismatch")
    modes = {}
    for mode in ("integrated","separate"):
        parts = split(p,faces,groups,mode)
        folder = dest / mode
        folder.mkdir(parents=True,exist_ok=True)
        (folder/"provenance.json").write_text(json.dumps(parts,indent=2,allow_nan=False))
        for role,part in parts.items():
            with (folder/(role+".obj")).open("w") as out:
                out.write("o "+role+"\n")
                for v in part["vertices"]:
                    out.write("v "+" ".join(format(x,".17g") for x in v)+"\n")
                for f in part["faces"]:
                    out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        modes[mode] = verify(folder,mode,p,faces)
    return dict(name=spec[0],source_obj_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                source_coordinate_error=error,modes=modes,passed=all(m["passed"] for m in modes.values()))

class BridgeRoundtripTests(unittest.TestCase):
    def test_actual_files(self):
        spec=PLAN[0]
        _,_,p,q,_,g,_,_,_,_=candidate(spec)
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            src=d/"source.obj"
            export_obj(src,p,q,g)
            result=roundtrip(spec,src,d/"parts")
            self.assertTrue(result["passed"])
            self.assertEqual(len(list((d/"parts").rglob("*.obj"))),4)
    def test_wrong_groups_rejected(self):
        spec=PLAN[0]
        _,_,p,q,_,g,_,_,_,_=candidate(spec)
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            src=d/"source.obj"
            export_obj(src,p,q,["wrong"]*len(g))
            with self.assertRaisesRegex(ValueError,"source groups mismatch"):
                roundtrip(spec,src,d/"parts")

def evidence():
    raw=(SOURCE/"report.json").read_bytes()
    source=json.loads(raw)
    if (not source["complete"] or not source["fixture_gate"]
            or len(source["cases"])!=len(PLAN)
            or {c["name"] for c in source["cases"] if c["passed"]}!={s[0] for s in PLAN}):
        raise ValueError("R12J source gate not satisfied")
    DEST.mkdir(parents=True,exist_ok=True)
    cases=[]
    for spec in PLAN:
        name=spec[0]
        try:
            cases.append(roundtrip(spec,SOURCE/(name+"_candidate.obj"),DEST/name))
        except Exception as exc:
            cases.append(dict(name=name,error=repr(exc),passed=False))
    report=dict(complete=True,source_stage="R12J",source_report_sha256=hashlib.sha256(raw).hexdigest(),
        cases=cases,fixture_gate=all(c["passed"] for c in cases),
        actual_file_readback=True,anatomical_fit_verified=False,physical_sewing_verified=False)
    (DEST/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213BRIDGEROUNDTRIP_SUMMARY",json.dumps(report,allow_nan=False))
    if not report["fixture_gate"]:
        raise RuntimeError("R12K panel roundtrip gate failed")

if __name__=="__main__":
    evidence()
