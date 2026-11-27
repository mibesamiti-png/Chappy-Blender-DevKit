"""Synthetic R29 controls; no native or GUI proof is produced by these tests."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from cbdk.joint_panel_evidence_r29 import (
    FIXTURE, PARTS, RECIPE, CASES, OPERATORS, reduce_panel_evidence,
)
from scripts import package_windows_kit

RUN = "1"*32
SCENE = "a"*64
PRIVATE = "private/path/never-copy"
ROWS = [
    dict(candidate_id="negative_control", diameter=5.5, decision="regression", score=1.5, accepted_for_review=False),
    dict(candidate_id="midpoint", diameter=4.5, decision="observed_improvement", score=.5, accepted_for_review=True),
    dict(candidate_id="declared_target", diameter=4., decision="target_reached", score=0., accepted_for_review=True),
]


def snapshot(status, *, fresh=False, selected=None, diameter=5., reason="", cancel=False, rows=None):
    return dict(status=status, reason=reason, diameter=diameter, target=4., policy="FREE",
                fresh=fresh, selected=selected, candidates=copy.deepcopy(rows or []),
                scene_sha=SCENE, cancel_requested=cancel)


def ready(selected=2, fresh=True):
    return snapshot("READY", fresh=fresh, selected=selected, rows=ROWS)


def view(s):
    # Independent synthetic projection; deliberately not the reducer's helper.
    status = s["status"]
    available = status != "READY" or s["fresh"]
    actions = {
        "IDLE":["START"], "RUNNING":["CANCEL"], "BLOCKED":[],
        "READY":["REJECT"], "FAILED":["RETRY"], "CANCELLED":["RETRY"],
        "REJECTED":["RETRY"], "ADOPTED_DIMENSION_ONLY":["RESTORE"], "RESTORED":["START"],
    }[status][:]
    if status=="READY" and s["fresh"] and s["selected"] in (1,2):
        actions.append("ADOPT")
    return dict(fixture_id=FIXTURE, part_ids=list(PARTS), recipe_id=RECIPE,
                status=status,reason=s["reason"], available=available,
                candidates=copy.deepcopy(s["candidates"]) if available else [],
                selected=s["selected"] if available else None, enabled_actions=actions)


def observations(version="4.4.3", mode="native"):
    identity=dict(run_id=RUN,blender_version=version,fixture_id=FIXTURE,mode=mode)
    idle=snapshot("IDLE"); running=snapshot("RUNNING")
    cancelled_request=snapshot("RUNNING",reason="cancellation_requested",cancel=True)
    cancelled=snapshot("CANCELLED",reason="cancelled_between_trials",cancel=True)
    failed=snapshot("FAILED",reason="provider_configuration_failed")
    adopted=snapshot("ADOPTED_DIMENSION_ONLY",diameter=4.,rows=ROWS,selected=2)
    restored=snapshot("RESTORED"); blocked=snapshot("BLOCKED",reason="restoration_blocked")
    specs={
        "adopt_restore":[(idle,running,"RUNNING_MODAL"),(running,ready(),"FINISHED"),
                         (ready(),adopted,"FINISHED"),(adopted,restored,"FINISHED")],
        "rejected_candidate":[(ready(0),snapshot("FAILED",reason="rejected_candidate"),"CANCELLED")],
        "stale_candidate":[(ready(fresh=False),snapshot("FAILED",reason="stale_inputs"),"CANCELLED")],
        "cancel_retry":[(idle,running,"RUNNING_MODAL"),(running,running,"CANCELLED"),
                        (running,running,"CANCELLED"),(running,cancelled_request,"FINISHED"),
                        (cancelled_request,cancelled,"CANCELLED"),(cancelled,ready(),"FINISHED")],
        "failed_retry":[(idle,running,"RUNNING_MODAL"),(running,failed,"CANCELLED"),
                        (failed,ready(),"FINISHED")],
        "blocked":[(blocked,blocked,"CANCELLED") for _ in CASES["blocked"]],
        "explicit_reject":[(ready(),snapshot("REJECTED",cancel=True),"FINISHED")],
    }
    records=[]
    for case, transitions in specs.items():
        steps=[]
        for index,(action,(before,after,result)) in enumerate(zip(CASES[case],transitions)):
            method = ("stub" if mode=="stub" else "native_operator" if action in OPERATORS
                      else "native_iterator" if action=="COMPLETE" else "callback_simulation")
            steps.append(dict(index=index,action=action,operator=OPERATORS.get(action),
                              method=method,explicit=action in OPERATORS,result=result,
                              before=copy.deepcopy(before),after=copy.deepcopy(after),
                              view_before=view(before),view_after=view(after)))
        records.append(dict(**identity,case=case,steps=steps))
    lifecycle=dict(**identity,registered=True,duplicate_rejected=True,unregistered=True,
                   existing_registration_unchanged=True,scene_before=SCENE,scene_after=SCENE,
                   fixture_settings=dict(axis="Z",origin=[0.,0.,0.],unit_scale=1.,
                                         axle_diameter=2.,clearance=.4,mode="OBJECT"),
                   draw_method="native_panel_draw_recording_layout" if mode=="native" else "stub",
                   projection_source="real_projection" if mode=="native" else "stub")
    return records,dict(run_id=RUN,blender_version=version,mode=mode,scene_sha=SCENE,
                        measured={r["case"]:copy.deepcopy(r) for r in records},
                        lifecycle=lifecycle,measured_lifecycle=copy.deepcopy(lifecycle))


def evaluate(args):
    return reduce_panel_evidence(args[0],**args[1])


class PanelEvidenceTests(unittest.TestCase):
    def blocked(self,args,reason=None,status="rejected"):
        out=evaluate(args)
        self.assertEqual(out["status"],status)
        self.assertFalse(out["native_fixed_panel_evidence_verified"])
        self.assertFalse(out["stub_contract_verified"])
        self.assertFalse(any(out["safety"].values()))
        self.assertNotIn(PRIVATE,json.dumps(out))
        if reason:
            self.assertIn(reason,out["reason_codes"])

    def test_all_versions_and_stub_native_separation(self):
        for version in ("4.4.3","4.5.15","5.2.1"):
            for mode in ("native","stub"):
                args=observations(version,mode); before=copy.deepcopy(args)
                out=evaluate(args)
                self.assertEqual(out["status"],"verified_native_observations" if mode=="native" else "verified_stub_contract")
                self.assertEqual(out["native_fixed_panel_evidence_verified"],mode=="native")
                self.assertEqual(out["verified_cases"],list(CASES))
                self.assertFalse(any(out["safety"].values()))
                self.assertEqual(args,before)

    def test_missing_and_wrong_identity(self):
        for key in ("measured","lifecycle","measured_lifecycle"):
            args=observations();args[1][key]=None;self.blocked(args,status="incomplete")
        args=observations();row=args[0].pop();del args[1]["measured"][row["case"]]
        self.blocked(args,"case_missing","incomplete")
        args=observations();args[0][0]["steps"].pop();args[1]["measured"]["adopt_restore"]["steps"].pop()
        self.blocked(args,"step_missing","incomplete")
        for key,value in (("run_id","2"*32),("blender_version","5.2.1"),("fixture_id",PRIVATE),("mode","stub")):
            args=observations();args[0][0][key]=value;self.blocked(args,"identity_mismatch")
        args=observations();args[0][0]=None;self.blocked(args,"case_inventory_invalid")
        args=observations();args[0].reverse();self.blocked(args,"case_order_mismatch")
        args=observations();args[0][1]=copy.deepcopy(args[0][0]);self.blocked(args,"case_order_mismatch")

    def test_running_blocked_and_stale_never_offer_adoption(self):
        for index,step,side,action,reason in (
            (0,0,"after","ADOPT","busy_operation"),
            (5,0,"before","RESTORE","blocked_operation"),
            (2,0,"before","ADOPT","operation_invalid"),
            (1,0,"before","ADOPT","operation_invalid"),
        ):
            args=observations();args[0][index]["steps"][step]["view_"+side]["enabled_actions"].append(action)
            self.blocked(args,reason)
        args=observations();args[0][2]["steps"][0]["view_before"]["available"]=True
        self.blocked(args,"projection_mismatch")
        args=observations();args[0][0]["steps"][2]["view_before"].update(available=False,candidates=[],selected=None)
        self.blocked(args,"projection_mismatch")

    def test_read_only_rows_finite_and_fixed(self):
        for updates in (dict(score=float("nan")),dict(score=True),dict(score=float("inf")),
                        dict(diameter=True),dict(decision=PRIVATE),dict(accepted_for_review=1),
                        dict(accepted_for_review=True),dict(candidate_id="midpoint")):
            args=observations();args[0][0]["steps"][1]["after"]["candidates"][0].update(updates)
            self.blocked(args)
        args=observations();args[0][0]["steps"][1]["after"]["candidates"].append(ROWS[0])
        self.blocked(args,"candidate_inventory_invalid")
        args=observations();args[0][0]["steps"][2]["before"]["selected"]=True
        self.blocked(args,"selection_invalid")
        args=observations();args[0][0]["steps"][2]["view_before"]["candidates"][2]["score"]=.000001
        self.blocked(args,"projection_mismatch")

    def test_explicit_dimension_only_and_scene_preservation(self):
        for index,step,change,reason in (
            (0,2,lambda s:s.update(explicit=False),"explicit_operation_required"),
            (0,2,lambda s:s.update(operator="cbdk_a.joint_action"),"delegation_mismatch"),
            (0,2,lambda s:s["after"].update(diameter=4.5),"dimension_transition_invalid"),
            (0,3,lambda s:s["after"].update(diameter=4.5),"restoration_invalid"),
            (1,0,lambda s:s["after"].update(diameter=4.),"unexpected_dimension_change"),
            (3,3,lambda s:s["after"].update(scene_sha="b"*64),"scene_changed"),
            (4,1,lambda s:s["after"].update(diameter=4.),"unexpected_dimension_change"),
            (5,0,lambda s:s.update(result="FINISHED"),"blocked_operation"),
        ):
            args=observations();change(args[0][index]["steps"][step]);self.blocked(args,reason)

    def test_callback_stub_and_gui_overclaim_rejected(self):
        for index,step,method in ((0,1,"callback_simulation"),(0,2,"stub"),(0,2,"gui_input")):
            args=observations();args[0][index]["steps"][step]["method"]=method
            self.blocked(args,"method_invalid")
        args=observations();args[1]["lifecycle"]["projection_source"]="stub"
        self.blocked(args,"method_invalid")
        args=observations();args[1]["lifecycle"]["windows_gui_verified"]=True
        self.blocked(args,"evidence_mismatch")
        args=observations();args[0][0]["steps"][2]["auto_adopt"]=True
        self.blocked(args,"evidence_mismatch")

    def test_cancellation_retry_failure_and_registration(self):
        args=observations();args[0][3]["steps"][3]["after"]["cancel_requested"]=False
        self.blocked(args,"state_transition_invalid")
        args=observations();args[0][4]["steps"][2]["result"]="CANCELLED"
        self.blocked(args,"state_transition_invalid")
        for key in ("registered","duplicate_rejected","unregistered","existing_registration_unchanged"):
            args=observations();args[1]["lifecycle"][key]=False
            self.blocked(args,"lifecycle_unverified")
        args=observations();args[1]["lifecycle"]["fixture_settings"]["axle_diameter"]=True
        self.blocked(args,"fixture_settings_mismatch")
        args=observations();args[1]["lifecycle"]["scene_after"]="b"*64
        self.blocked(args,"scene_changed")

    def test_parent_observation_not_self_attested(self):
        args=observations();args[1]["measured"]["adopt_restore"]["steps"][0]["view_before"]["enabled_actions"].append("RESTORE")
        self.blocked(args,"parent_measurement_mismatch")
        args=observations();step=args[0][0]["steps"][1]
        step["before"]["reason"]="cancellation_requested";step["view_before"]["reason"]="cancellation_requested"
        self.blocked(args,"transition_discontinuity")

    @unittest.skipUnless(os.name == "posix", "existing Windows kit builder runs in Linux CI")
    def test_existing_kit_builder_excludes_research_provider(self):
        # Exercise the existing packaging implementation, not a copied filter.
        required=["run_blender_tests_windows.bat","scripts/windows_run_blender_tests.ps1",
                  "cbdk/evidence.py","docs/TEST_ENVIRONMENT.md"]
        provider="experiments/team_a_staged/providers/chappy_joint_maker_v042_debug_fix.zip"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in required+[provider]:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"synthetic")
            tracked=b"\0".join(x.encode() for x in required+[provider])+b"\0"
            out=root/"kit.zip"
            with patch.object(package_windows_kit,"ROOT",root), patch.object(package_windows_kit.subprocess,"check_output",return_value=tracked):
                self.assertEqual(package_windows_kit.build(out),len(required))
            with ZipFile(out) as archive:
                self.assertEqual(set(archive.namelist()),{package_windows_kit.PREFIX+"/"+p for p in required})


if __name__=="__main__":
    unittest.main()
