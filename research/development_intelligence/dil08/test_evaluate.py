"""Offline, no external GitHub access; synthetic smoke-tests for field evaluator."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import evaluate
from test_selector import fixture
from selector import validate_catalog

class TestEvaluator(unittest.TestCase):
    def setup_data(self):
        c,m,_ = fixture()
        docs=[]
        for i in m["documents"]:
            docs.append(dict(id=i["id"], project="CBDK", topic=i["id"],
                title=i["path"], text="AI GitHub R16 文書 "+i["id"],
                source="https://example.invalid/"+i["id"],aliases=[],
                status="approved", revision="current" if i["current"] else "historical",
                visibility="public_synthetic"))
        return docs,validate_catalog(c,m)
    def test_real_sqlite_trigram_enabled(self):
        import sqlite3
        conn=sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE evidence USING fts5(txt, tokenize='trigram')")
        conn.execute("INSERT INTO evidence (txt) VALUES (?)",("AI GitHub R16 文書",))
        self.assertEqual(conn.execute("SELECT count(*) FROM evidence WHERE txt MATCH ?", ('"GitHub"',)).fetchone()[0],1)
    def test_score_readonly(self):
        docs,byid=self.setup_data()
        cases=[dict(id="a",question="R16",intent="continue",team="B",official_round="R16",topic_hints=[],gold_required=["agents","r16","state","parallel","roles"])]
        score=evaluate.score(cases,docs,byid)
        self.assertEqual(score["authority_first"]["found"],5)
        self.assertEqual(score["authority_first"]["historical_as_current"],0)
        self.assertGreaterEqual(score["full_context"]["historical_as_current"],1)
    def test_missing_gold_raises(self):
        docs,byid=self.setup_data()
        with self.assertRaises(ValueError):evaluate.score([dict(id="b",question="?",intent="read_only_qa",topic_hints=["ui"],gold_required=["absent"])],docs,byid)
    def test_normalize_existing_question(self):
        x=evaluate.normalized_case({"id":"Q01","query":"R16","topics":["round"],"gold_ids":["r16"]})
        self.assertEqual(x["intent"],"read_only_qa")
    def test_action_default_no_permission(self):
        docs,byid=self.setup_data()
        x=[dict(id="c",question="release",intent="release",team="A",official_round="R16",topic_hints=[],gold_required=["agents","r16","state","parallel"])]
        res=evaluate.score(x,docs,byid)
        self.assertEqual(res["authority_first"]["found"],4)

if __name__=="__main__":unittest.main()
