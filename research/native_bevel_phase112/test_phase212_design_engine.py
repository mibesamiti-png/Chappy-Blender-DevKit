import unittest
from phase212_design_engine import design,STAGES

class EngineTests(unittest.TestCase):
    def run_plan(self,overrides,ids=("a","b"),budget=2):
        calls=[]
        def backend(c,s):
            calls.append((c,s))
            state=overrides.get((c,s),"pass")
            if isinstance(state,Exception):raise state
            if state=="missing":return {"status":"pass"}
            return dict(status=state,evidence={"case":c,"stage":s})
        return design(ids,budget,backend),calls
    def test_first_pass(self):
        r,c=self.run_plan({})
        self.assertEqual(r["selected"],"a")
        self.assertEqual(c,[("a",s) for s in STAGES])
    def test_geometry_rejection(self):
        r,c=self.run_plan({("a","geometry"):"fail"})
        self.assertEqual(r["selected"],"b")
        self.assertEqual(c,[("a","geometry")]+[("b",s) for s in STAGES])
    def test_physical_failure(self):
        r,c=self.run_plan({("a","full_motion"):"fail"})
        self.assertEqual(r["selected"],"b")
        self.assertNotIn(("a","negative_controls"),c)
        self.assertEqual(r["history"][0]["qualification"]["status"],"fail")
    def test_control_failure(self):
        r,c=self.run_plan({("a","negative_controls"):"fail"})
        self.assertEqual(r["selected"],"b")
        self.assertFalse(r["history"][0]["qualification"]["certified"])
    def test_missing_evidence(self):
        for state in ("unverified","missing"):
            r,c=self.run_plan({("a","screen"):state})
            self.assertEqual(r["action"],"collect_missing_evidence")
            self.assertEqual(c,[("a","geometry"),("a","screen")])
    def test_exhaustion(self):
        r,c=self.run_plan({("a","geometry"):"fail",("b","screen"):"fail"})
        self.assertEqual(r["action"],"stop_and_redesign")
        self.assertIsNone(r["selected"])
        self.assertEqual(len(c),3)
    def test_budget(self):
        with self.assertRaises(ValueError):self.run_plan({},budget=1)
        with self.assertRaises(ValueError):self.run_plan({},ids=("a","a"))
    def test_backend_exception(self):
        r,c=self.run_plan({("a","full_motion"):RuntimeError("native backend failed")})
        self.assertEqual(r["action"],"collect_missing_evidence")
        self.assertIsNone(r["selected"])
        self.assertEqual(len(c),3)
        self.assertEqual(r["history"][0]["evidence"]["full_motion"]["error"],"RuntimeError")
if __name__=="__main__":unittest.main()
