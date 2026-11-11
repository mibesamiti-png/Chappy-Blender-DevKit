import unittest
from source_probe import score, approximate_bytes
from test_selector import fixture
from selector import validate_catalog

class TestSourceProbe(unittest.TestCase):
    def build(self):
        c,m,_=fixture()
        docs=[{"id":d["id"],"bytes":12,"blob_ok":True,"anchors_ok":True} for d in m["documents"]]
        return docs,validate_catalog(c,m)
    def test_byte_accounting(self):
        docs,_=self.build()
        self.assertEqual(approximate_bytes(docs,["agents","r16"]),27)
    def test_recorded_unsupported_sha_stops(self):
        docs,catalog=self.build();docs[0]["blob_ok"]=False
        with self.assertRaises(ValueError):score(docs,catalog,[])
    def test_probe_matches_required(self):
        docs,catalog=self.build();cases=[{"id":"S","intent":"continue","team":"B","official_round":"R16","topic_hints":[],"gold_required":["agents","r16","state","parallel","roles"]}]
        res=score(docs,catalog,cases)
        self.assertEqual(res["aggregates"]["required_found"],5)
        self.assertEqual(res["aggregates"]["historical_r15_as_current"],0)
    def test_never_claim_full_sqlite(self):
        docs,catalog=self.build();cases=[{"id":"S","intent":"read_only_qa","topic_hints":["ui"],"gold_required":["ui"]}]
        res=score(docs,catalog,cases)
        self.assertFalse(res["full_corpus_SQLite_run_completed"])
    def test_empty_case_list_fails_closed(self):
        docs,catalog=self.build()
        with self.assertRaises(ValueError):score(docs,catalog,[])
    def test_duplicate_source_rejected(self):
        docs,catalog=self.build()
        with self.assertRaises(ValueError):score(docs+[docs[0]],catalog,[])

if __name__=="__main__":unittest.main()
