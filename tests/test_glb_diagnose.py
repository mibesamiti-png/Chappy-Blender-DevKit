from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from cbdk.glb_diagnose import DiagnosticError, diagnose_comparison, write_diagnosis

def report(differences,errors=1,passed=False):
    return {"kind":"cbdk_glb_scene_comparison","passed":passed,"summary":{"errors":errors},"differences":differences}

class GLBDiagnoseTests(unittest.TestCase):
    def test_silhouette_points_to_profile_boolean(self):
        out=diagnose_comparison(report([{"code":"object_silhouette","severity":"error","metrics":{"reference_object":"Socket_L","view":"front","iou":0.6}}]))
        self.assertEqual(out["hypotheses"][0]["category"],"part_profile_boolean_or_cutout")
        self.assertIn("boolean cutters",out["hypotheses"][0]["inspect"])
    def test_missing_part_is_high_priority(self):
        out=diagnose_comparison(report([
            {"code":"object_center","severity":"error","metrics":{"reference_object":"Ball"}},
            {"code":"missing_reference_object","severity":"error","metrics":{"object":"Socket_R"}}
        ],errors=2))
        self.assertEqual(out["hypotheses"][0]["target"],"Socket_R")
    def test_repeated_views_are_grouped(self):
        rows=[{"code":"object_silhouette","severity":"error","metrics":{"reference_object":"Body","view":v}} for v in ("front","right","top")]
        out=diagnose_comparison(report(rows,errors=3))
        self.assertEqual(out["hypothesis_count"],1); self.assertEqual(len(out["hypotheses"][0]["evidence_items"]),3)
    def test_passed_needs_no_fix(self):
        out=diagnose_comparison(report([],errors=0,passed=True))
        self.assertFalse(out["needs_review"])
    def test_unknown_code_preserved(self):
        out=diagnose_comparison(report([{"code":"future_metric","severity":"warning","metrics":{}}],errors=0,passed=True))
        self.assertEqual(out["unsupported_difference_codes"],["future_metric"])
    def test_write(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t)/"c.json"; o=Path(t)/"d.json"; r.write_text(json.dumps(report([],errors=0,passed=True)))
            out=write_diagnosis(r,o); self.assertTrue(o.is_file()); self.assertFalse(out["safety"]["edits_code"])
    def test_wrong_kind_rejected(self):
        with self.assertRaises(DiagnosticError): diagnose_comparison({"kind":"wrong","summary":{"errors":0},"differences":[]})
