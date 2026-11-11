import copy
import unittest
from selector import select, validate_catalog, ACTION_INTENTS

DOC_IDS = ("agents", "parallel", "r16", "r15", "roles", "release",
           "future", "vision", "extension", "ui", "glb", "state")
def fixture():
    topics = {
      "agents": ["policy"], "parallel": ["workflow"], "r16": ["round"],
      "r15": ["round"], "roles": ["roles"], "release": ["release"],
      "future": ["future"], "vision": ["vision"], "extension": ["extension"],
      "ui": ["ui"], "glb": ["glb"], "state": ["state"]}
    catalog = {"schema": "dil08-tag-catalog-v1", "source_commit": "a"*40,
        "documents": [
           {"id": i, "topic": topics[i],
            "lifecycle": "historical" if i=="r15" else ("future_inactive" if i in ("future","vision") else "current_at_pinned_commit"),
            "authority": "historical" if i=="r15" else ("official_assignment" if i=="r16" else "operational_reference")}
           for i in DOC_IDS]}
    manifest = {"source_commit": "a"*40, "documents": [{"id": i, "current": i!="r15"} for i in DOC_IDS]}
    src = {i: {"text": f"source {i}"} for i in DOC_IDS}
    return catalog, manifest, src

class TestSelector(unittest.TestCase):
    def setUp(self):
        self.cat, self.manifest, self.docs = fixture()
        self.by_id = validate_catalog(self.cat, self.manifest)
    def run_case(self, **kw):
        return select(kw, self.docs, self.by_id)
    def test_catalog_valid(self): self.assertEqual(len(self.by_id),12)
    def test_catalog_wrong_commit(self):
        c=copy.deepcopy(self.cat);c["source_commit"]="b"*40
        with self.assertRaises(ValueError):validate_catalog(c,self.manifest)
    def test_catalog_r15_current_rejected(self):
        c=copy.deepcopy(self.cat);c["documents"][3]["lifecycle"]="current_at_pinned_commit"
        with self.assertRaises(ValueError):validate_catalog(c,self.manifest)
    def test_catalog_r15_as_official_rejected(self):
        c=copy.deepcopy(self.cat);c["documents"][3]["authority"]="official_assignment"
        with self.assertRaises(ValueError):validate_catalog(c,self.manifest)
    def test_catalog_missing_document_rejected(self):
        c=copy.deepcopy(self.cat);c["documents"].pop()
        with self.assertRaises(ValueError):validate_catalog(c,self.manifest)
    def test_continue_is_blocked_without_live_evidence(self):
        r=self.run_case(intent="continue",team="B",official_round="R16")
        self.assertEqual(r["status"],"blocked_pending_live_issue_and_ci")
        self.assertTrue(set(("agents","r16","state","parallel","roles")).issubset(r["selected"]))
    def test_wrong_round_rejected(self):
        r=self.run_case(intent="continue",team="B",official_round="R15",topic_hints=["round"])
        self.assertEqual(r["status"],"blocked_wrong_round");self.assertNotIn("r15",r["selected"])
    def test_future_round_rejected(self):
        self.assertEqual(self.run_case(intent="continue",team="C",official_round="R17")["status"],"blocked_wrong_round")
    def test_unknown_team_rejected(self):
        self.assertEqual(self.run_case(intent="continue",team="E",official_round="R16")["status"],"blocked_invalid_request")
    def test_missing_policy_fail_closed(self):
        del self.docs["agents"]
        self.assertEqual(self.run_case(intent="continue",team="B",official_round="R16")["status"],"blocked_missing_authority")
    def test_missing_r16_fail_closed(self):
        del self.docs["r16"]
        self.assertEqual(self.run_case(intent="continue",team="B",official_round="R16")["status"],"blocked_missing_authority")
    def test_no_unknown_permission(self):
        for i in ACTION_INTENTS:
            r=self.run_case(intent=i,team="B" if i=="continue" else "A",official_round="R16")
            self.assertFalse(r["may_execute"]);self.assertFalse(r["may_merge"]);self.assertFalse(r["may_skip_ci"])
    def test_readonly_ui(self):
        self.assertEqual(self.run_case(intent="read_only_qa",topic_hints=["ui"])["selected"],["ui"])
    def test_readonly_future_is_nonexecution(self):
        r=self.run_case(intent="read_only_qa",topic_hints=["future"])
        self.assertIn("future",r["selected"]);self.assertFalse(r["may_execute"])
    def test_unknown_query_needs_review(self):
        self.assertEqual(self.run_case(intent="read_only_qa")["status"],"needs_review_unclassified_query")
    def test_unknown_hint_needs_review(self):
        self.assertEqual(self.run_case(intent="read_only_qa",topic_hints=["gibberish"])["status"],"needs_review_no_source")
    def test_action_never_uses_r15(self):
        r=self.run_case(intent="modify",official_round="R16",topic_hints=["round"])
        self.assertNotIn("r15",r["selected"])
    def test_malformed_input(self):
        self.assertEqual(self.run_case(intent="read_only_qa",topic_hints=10)["status"],"blocked_invalid_request")
    def test_invalid_intent(self):
        self.assertEqual(self.run_case(intent="automerge")["status"],"blocked_invalid_request")
    def test_no_mutation(self):
        saved=copy.deepcopy(self.docs);self.run_case(intent="read_only_qa",topic_hints=["ui"])
        self.assertEqual(saved,self.docs)

if __name__=="__main__":unittest.main()
