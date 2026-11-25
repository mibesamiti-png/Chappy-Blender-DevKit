import copy
import json
import os
import unittest
from pathlib import Path
from adapter import route, load_checker
HERE=Path(__file__).parent
class TestContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker=load_checker(os.environ["DIL_CHECKER"])
    def setUp(self):
        self.s=json.loads((HERE/"OBSERVED.json").read_text())
    def check(self,s,state,reason=None,details=0):
        r=route(s,self.checker)
        self.assertEqual(r["state"],state,r)
        if reason is not None: self.assertEqual(r["reason"],reason)
        self.assertEqual(len(r["detail_requests"]),details)
        self.assertFalse(any(r[k] for k in ("may_execute","may_merge","may_skip_ci")))
        return r
    def test_observed_green(self):
        r=self.check(self.s,"summary_ready","family_summary_only")
        self.assertEqual(r["summary"],{"success":7,"required":7})
    def test_changed_head(self):
        self.s["dev_end"]="0"*40
        self.check(self.s,"blocked","dev_head_changed")
    def test_pr_changed(self):
        self.s["pr_end"]["base_sha"]="0"*40
        self.check(self.s,"blocked","pr_or_dispatch_changed")
    def test_issue_changed(self):
        self.s["issue_end"]["dispatch"]["revision"]+=1
        self.check(self.s,"blocked","pr_or_dispatch_changed")
    def test_wrong_event(self):
        self.s["workflow_runs"][0]["event"]="push"
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_wrong_pr(self):
        self.s["workflow_runs"][0]["pull_requests"][0]["number"]=26
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_wrong_base(self):
        self.s["workflow_runs"][0]["pull_requests"][0]["base"]["sha"]="0"*40
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_wrong_branch(self):
        self.s["workflow_runs"][0]["head_branch"]="other"
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_wrong_repo(self):
        self.s["workflow_runs"][0]["pull_requests"][0]["head"]["repo"]["id"]=1
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_wrong_head(self):
        self.s["workflow_runs"][0]["head_sha"]="0"*40
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_page_missing(self):
        self.s["total_count"]+=1
        self.check(self.s,"blocked","incomplete_run_page")
    def test_failure(self):
        self.s["workflow_runs"][0]["conclusion"]="failure"
        self.check(self.s,"blocked","ci_not_all_verified",1)
    def test_cancelled(self):
        self.s["workflow_runs"][0]["conclusion"]="cancelled"
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_running(self):
        self.s["workflow_runs"][0].update(status="in_progress",conclusion=None)
        self.check(self.s,"blocked","ci_not_all_verified")
    def test_latest_failure(self):
        row=copy.deepcopy(self.s["workflow_runs"][0])
        row.update(id=row["id"]+1000000,run_attempt=2,conclusion="failure")
        self.s["workflow_runs"].append(row)
        self.s["total_count"]+=1
        self.check(self.s,"blocked","ci_not_all_verified",1)
    def test_duplicate_id(self):
        self.s["workflow_runs"].append(copy.deepcopy(self.s["workflow_runs"][0]))
        self.s["total_count"]+=1
        self.check(self.s,"blocked","duplicate_or_invalid_run_id")
    def test_revision_rollback(self):
        self.s["minimum_revision"]=self.s["issue_start"]["dispatch"]["revision"]+1
        self.check(self.s,"blocked","dispatch_context_mismatch")
    def test_source_missing(self):
        self.s["source_refs"].pop()
        self.check(self.s,"blocked","source_refs_missing")
    def test_checkpoint_never_authority(self):
        r=self.check(self.s,"summary_ready")
        self.assertEqual(r["checkpoint"]["permissions"],"none; historical observation only")
        self.assertLess(r["sizes"]["checkpoint_bytes"],r["sizes"]["stored_workflow_metadata_bytes"])
if __name__=="__main__":
    unittest.main()
