"""R28 synthetic controls only: no Blender or candidate execution."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from cbdk.parameter_candidate_evidence_r28 import (
    CASE, TRIALS, VALUES, REFERENCES, REFERENCE_PAIRS, PHASES, PROPERTIES,
    SOURCE_SHA256, STAGES, SPHERE, CUBE, RUN_FLAGS, EXPECTED_DECISIONS,
    _fixed_candidate, _replay, reduce_candidate_evidence,
)
from test_parameter_source_evidence_r27 import mesh

ROOT = Path(__file__).resolve().parents[1]
RUN, REF_RUN = "1"*32, "2"*32
PRIVATE = "private/path/never-copy"


def fixed_source():
    raw = (ROOT / "fixtures/cbdk_parameter_experiment.py").read_bytes()
    if hashlib.sha256(raw).hexdigest() == "eec6968b7cb5208e0af92279b7b32dc0c8d617ebad6d1cdbb5ca39cc64d1918f":
        canonical = raw.replace(b"\r\n", b"\n")
        assert canonical.replace(b"\n", b"\r\n") == raw
        return canonical
    return raw


def observations(version="4.4.3", budget=4):
    source = fixed_source()
    identity = dict(case_id=CASE, run_id=RUN, blender_version=version,
                    source_sha256=SOURCE_SHA256, reference_run_id=REF_RUN)
    variants = {}
    for name, radius, bevel, digest in (
        ("baseline", .75, .08, "1"), ("sphere_radius_changed",1.15,.08,"2"),
        ("bevel_width_changed",.75,.35,"3"), ("sphere_probe_up",.95,.08,"4"),
        ("sphere_probe_down",.55,.08,"5"), ("bevel_probe_up",.75,.20,"6"),
        ("bevel_probe_down",.75,.03,"7"),
    ):
        row = {"glb_sha256":digest*64}
        sphere_code = {.75:"a",1.15:"b",.95:"c",.55:"d"}[radius]
        cube_code = {.08:"e",.35:"f",.20:"8",.03:"9"}[bevel]
        for phase in PHASES:
            row[phase] = {SPHERE:mesh(sphere_code,2*radius),CUBE:mesh(cube_code,2.0)}
        variants[name] = row
    references = dict(case_id="parameter_fixture_r26", run_id=REF_RUN,
                      blender_version=version, source_sha256=SOURCE_SHA256, variants=variants)
    records, candidates = [], {}
    hashes = {k:v["glb_sha256"] for k,v in variants.items()}
    for index, trial in enumerate(TRIALS[:budget]):
        # Independent control construction: simple unique token substitutions,
        # never the reducer's candidate builder or replay to construct claims.
        radius, bevel = VALUES[index]
        candidate = source.replace(b"default=0.75", f"default={radius:.2f}".encode())
        candidate = candidate.replace(b"default=0.08", f"default={bevel:.2f}".encode())
        candidates[trial] = candidate
        ident = dict(**identity, trial_id=trial, candidate_sha256=hashlib.sha256(candidate).hexdigest())
        tokens = []
        for prop, old, new in zip(PROPERTIES, ("0.75","0.08"), (f"{radius:.2f}",f"{bevel:.2f}")):
            if old != new:
                tokens.append(dict(property=prop, byte_offset=source.index(b"default="+old.encode())+8,
                                   old_token=old, new_token=new))
        stages = []
        for j,stage in enumerate(STAGES):
            values = (radius,bevel) if stage=="candidate" else (.75,.08)
            readback = dict(zip(PROPERTIES,values))
            pair = REFERENCE_PAIRS[index] if stage=="candidate" else ("baseline","baseline")
            stage_row = dict(**ident, stage=stage,
                             actual_source_sha256=ident["candidate_sha256"] if stage=="candidate" else SOURCE_SHA256,
                             rna_defaults=readback, rna_after_build=dict(readback),
                             registered=True, cleanup_verified=True,
                             glb_sha256=hashlib.sha256((trial+stage).encode()).hexdigest())
            for phase in PHASES:
                stage_row[phase] = {part:copy.deepcopy(variants[ref][phase][part])
                                    for part,ref in zip((SPHERE,CUBE),pair)}
            stages.append(stage_row)
        records.append(dict(**ident, **dict.fromkeys(RUN_FLAGS,True), stages=stages,
                            diff=dict(tokens=tokens, ast_diff_verified=True,
                                      exact_diff_verified=True,restored_sha256=SOURCE_SHA256),
                            restored_copy_sha256=SOURCE_SHA256,reference_glb_sha256=dict(hashes)))
    before = ("baseline","baseline","baseline","intermediate")
    after = ("baseline","baseline","intermediate","target")
    scores = (1.2,0.0,.4,0.0)
    history = dict(budget=budget, rows=[
        dict(trial_id=trial,generated_score=scores[i],imported_score=scores[i],
             decision=EXPECTED_DECISIONS[i],best_before=before[i],best_after=after[i])
        for i,trial in enumerate(TRIALS[:budget])],
        best_id=after[budget-1],stop_reason="target_reached" if budget==4 else "budget_exhausted",
        target_reached=budget==4)
    return records, history, dict(run_id=RUN,blender_version=version,reference_run_id=REF_RUN,
                                   source_bytes=source,allowed_candidates=candidates,
                                   measured={x["trial_id"]:copy.deepcopy(x) for x in records},
                                   references=references,budget=budget)


def evaluate(args):
    return reduce_candidate_evidence(args[0],args[1],**args[2])


class CandidateEvidenceTests(unittest.TestCase):
    def blocked(self,args,reason=None,status="rejected"):
        out=evaluate(args)
        self.assertEqual(out["status"],status)
        self.assertFalse(out["same_fixture_selection_verified"])
        self.assertFalse(any(out["safety"].values()))
        self.assertNotIn(PRIVATE,json.dumps(out))
        if reason:
            self.assertIn(reason,out["reason_codes"])

    def test_all_versions_and_prefix_budgets(self):
        for version in ("4.4.3","4.5.15","5.2.1"):
            for budget in (1,2,3,4):
                args=observations(version,budget)
                before=copy.deepcopy(args)
                out=evaluate(args)
                self.assertEqual(out["status"],"verified_fixed_history" if budget==4 else "verified_budget_exhausted")
                self.assertEqual(out["same_fixture_selection_verified"],budget==4)
                self.assertEqual(out["history"]["target_reached"],budget==4)
                self.assertEqual(out["history"]["best_id"],("baseline","baseline","intermediate","target")[budget-1])
                self.assertFalse(any(out["safety"].values()))
                self.assertEqual(args,before)

    def test_fixed_bytes_and_two_token_exception(self):
        args=observations()
        source=args[2]["source_bytes"]
        self.assertEqual(hashlib.sha256(source).hexdigest(),SOURCE_SHA256)
        for i,trial in enumerate(TRIALS):
            candidate,tokens=_fixed_candidate(source,i)
            self.assertEqual(candidate,args[2]["allowed_candidates"][trial])
            self.assertEqual(len(tokens),2 if trial=="cross_part" else 1)
            restored=candidate
            for t in reversed(tokens):
                offset=t["byte_offset"]
                restored=restored[:offset]+t["old_token"].encode()+restored[offset+4:]
            self.assertEqual(restored,source)
        args[2]["source_bytes"]=source.replace(b"\n",b"\r\n")
        self.blocked(args,"source_digest_mismatch")
        args=observations(); args[2]["allowed_candidates"]["target"]+=b"\n"
        self.blocked(args,"fixed_candidate_mismatch")

    def test_wrong_order_duplicate_unknown_and_budget(self):
        for change in (lambda x:x.reverse(),lambda x:x.__setitem__(1,x[0]),
                       lambda x:x[0].update(trial_id=PRIVATE)):
            args=observations();change(args[0]);self.blocked(args,"trial_order_mismatch")
        for budget in (True,0,5,1.0):
            args=observations();args[2]["budget"]=budget;self.blocked(args,"budget_invalid")

    def test_identity_is_independent_of_reports(self):
        for key,value in (("run_id","3"*32),("reference_run_id","3"*32),("blender_version","5.2.1"),
                          ("source_sha256","a"*64),("candidate_sha256","b"*64)):
            for stage in (False,True):
                args=observations();row=args[0][0]["stages"][1] if stage else args[0][0]
                row[key]=value;self.blocked(args,"identity_mismatch")
        args=observations();args[2]["reference_run_id"]=RUN;self.blocked(args,"identity_mismatch")
        args=observations();args[2]["references"]["run_id"]="3"*32;self.blocked(args,"identity_mismatch")

    def test_bad_diff_stage_and_restoration(self):
        changes=(
            (lambda a:a["diff"]["tokens"].append(a["diff"]["tokens"][0]),"fixed_diff_mismatch"),
            (lambda a:a["diff"]["tokens"][0].update(byte_offset=True),"fixed_diff_mismatch"),
            (lambda a:a["diff"]["tokens"][0].update(new_token=PRIVATE),"fixed_diff_mismatch"),
            (lambda a:a["diff"].update(ast_diff_verified=False),"fixed_diff_mismatch"),
            (lambda a:a.update(restored_copy_sha256="3"*64),"restoration_mismatch"),
            (lambda a:a.update(restoration_verified=False),"copy_integrity_unverified"),
            (lambda a:a.update(reference_sha_unchanged=False),"copy_integrity_unverified"),
            (lambda a:a.update(original_source_unchanged=False),"copy_integrity_unverified"),
            (lambda a:a["stages"].reverse(),"stage_order_mismatch"),
            (lambda a:a["stages"][2].update(actual_source_sha256=a["candidate_sha256"]),"stage_source_mismatch"),
            (lambda a:a["stages"][1].update(cleanup_verified=False),"stage_lifecycle_unverified"),
            (lambda a:a["stages"][1]["rna_defaults"].update(sphere_radius=True),"rna_default_mismatch"),
            (lambda a:a["stages"][1]["rna_defaults"].update(sphere_radius=float("nan")),"rna_default_mismatch"),
            (lambda a:a["stages"][1]["rna_after_build"].update(bevel_width=.35),"rna_default_mismatch"),
        )
        for change,reason in changes:
            args=observations();change(args[0][0]);self.blocked(args,reason)

    def test_independent_measurements_and_reference_sha(self):
        args=observations();args[0][0]["stages"][1]["glb_sha256"]="9"*64
        self.blocked(args,"parent_measurement_mismatch")
        args=observations();args[0][0]["reference_glb_sha256"]["baseline"]="9"*64
        self.blocked(args,"reference_digest_mismatch")
        for phase in PHASES:
            args=observations();args[0][1]["stages"][1][phase][CUBE]=copy.deepcopy(args[2]["references"]["variants"]["baseline"][phase][CUBE])
            self.blocked(args,"fixed_reference_geometry_mismatch")
            args=observations();args[0][0]["stages"][2][phase][SPHERE]["mesh_coordinate_sha256"]="9"*64
            self.blocked(args,"fixed_reference_geometry_mismatch")
        args=observations();args[0][0]["stages"][1][PHASES[0]][SPHERE]["world_dimensions"]=[1,2,float("inf")]
        self.blocked(args,"measurement_invalid")

    def test_missing_data_and_premature_target(self):
        for key in ("allowed_candidates","measured","references"):
            args=observations();args[2][key]=None;self.blocked(args,"premature_target")
            args[1].update(target_reached=False,stop_reason="incomplete")
            self.blocked(args,status="incomplete")
        args=observations(budget=2);args[0][0]["stages"].pop()
        args[2]["measured"]["wrong_direction"]["stages"].pop()
        self.blocked(args,"stage_missing","incomplete")
        args=observations(budget=2);args[1]["target_reached"]=True
        self.blocked(args,"history_mismatch")

    def test_forged_history_best_scores_and_claims(self):
        for change in (
            lambda h:h["rows"][1].update(decision="observed_target_reached",best_after="cross_part"),
            lambda h:h["rows"][0].update(best_after="wrong_direction"),
            lambda h:h["rows"][2].update(generated_score=True),
            lambda h:h["rows"][2].update(imported_score=float("inf")),
            lambda h:h.update(best_id="cross_part"),
            lambda h:h.update(target_reached=1),
            lambda h:h.update(auto_adopt=True),
        ):
            args=observations();change(args[1]);self.blocked(args)
        args=observations();args[0][0].update(auto_apply=True);self.blocked(args)

    def test_replay_veto_margin_and_uncertain_controls(self):
        args=observations();refs=args[2]["references"]["variants"]
        baseline,target=refs["baseline"],refs["sphere_radius_changed"]
        candidates=[r["stages"][1] for r in args[0]]
        replay=_replay(baseline,target,candidates,4)
        self.assertEqual([x["decision"] for x in replay["rows"]],list(EXPECTED_DECISIONS))
        self.assertEqual(replay["rows"][1]["best_after"],"baseline")
        for mode in ("tie","one_side","zero_score_wrong_mesh"):
            trial=copy.deepcopy(baseline)
            if mode=="one_side":
                trial[PHASES[0]][SPHERE]=copy.deepcopy(target[PHASES[0]][SPHERE])
            elif mode=="zero_score_wrong_mesh":
                for phase in PHASES:
                    trial[phase][SPHERE]["world_dimensions"]=list(target[phase][SPHERE]["world_dimensions"])
            result=_replay(baseline,target,[trial],1)
            self.assertEqual(result["rows"][0]["decision"],"uncertain_no_strict_improvement")
            self.assertEqual(result["best_id"],"baseline")
            self.assertFalse(result["target_reached"])
        trial=copy.deepcopy(baseline)
        for phase in PHASES:
            trial[phase][SPHERE]["world_dimensions"]=[1.500001]*3
        self.assertEqual(_replay(baseline,target,[trial],1)["rows"][0]["decision"],"uncertain_no_strict_improvement")

    def test_incomplete_prefix_without_target(self):
        args=observations(budget=2);args[0].pop();del args[2]["measured"]["cross_part"]
        args[1]["rows"].pop();args[1]["stop_reason"]="incomplete"
        self.blocked(args,"trial_prefix_incomplete","incomplete")


if __name__=="__main__":
    unittest.main()
