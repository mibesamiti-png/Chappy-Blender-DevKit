"""Regression tests for the reusable evaluation layer, no Blender required."""
import unittest
from phase212_design_evaluation import Limit,evaluate,select_candidate,qualification

class EvidenceTests(unittest.TestCase):
    def test_boundaries_and_first_failure(self):
        limits=[Limit("tracking",upper=.04),Limit("gap",lower=.02)]
        r=evaluate(limits,{"tracking":[(1,"foot",.04),(4,"foot",.06),(5,"foot",.09)],
                           "gap":[(1,"cam",.02),(3,"cam",.01)]})
        self.assertEqual(r["status"],"fail")
        self.assertEqual(r["first"],dict(metric="gap",frame=3,part="cam",value=.01))
        self.assertEqual(r["metrics"]["tracking"]["first"]["frame"],4)
        self.assertEqual(r["metrics"]["tracking"]["max"],.09)
        self.assertEqual(evaluate(limits,{"tracking":[(1,"foot",.04)],"gap":[(1,"cam",.02)]})["status"],"pass")
    def test_missing_and_bad_data(self):
        for series in ([],[(1,"part",float("nan"))],[(1,"part",True)],[(1,"part",float("inf"))],[(3,"part",0),(2,"part",0)],[(0,"part",0)]):
            self.assertEqual(evaluate([Limit("x",upper=1)],{"x":series})["status"],"unverified")
        self.assertEqual(evaluate([Limit("x",upper=1)],{})["status"],"unverified")
        self.assertEqual(evaluate([Limit("x",upper=1),Limit("y",upper=1)],{"x":[(1,"part",2)]})["status"],"fail")
        for args in (("x",None,None),("x",2,1),("x",None,float("nan")),("x",True,None)):
            with self.assertRaises(ValueError):Limit(*args)
        with self.assertRaises(ValueError):evaluate([], {})
    def test_budget_and_candidate_selection(self):
        ids=["baseline","pivot","mass","mass_drive"]
        self.assertEqual(select_candidate(ids,dict.fromkeys(ids,"fail"),4)["action"],"stop_and_redesign")
        self.assertEqual(select_candidate(ids,{"baseline":"fail","pivot":"pass"},4)["action"],"collect_missing_evidence")
        self.assertEqual(select_candidate(ids,dict(zip(ids,["fail","fail","fail","pass"])),4)["selected"],"mass_drive")
        self.assertEqual(select_candidate(ids,dict(zip(ids,["fail","pass","pass","pass"])),4)["selected"],"pivot")
        with self.assertRaises(ValueError):select_candidate(ids,{},3)
        with self.assertRaises(ValueError):select_candidate(ids,{"extra":"pass"},4)
        with self.assertRaises(ValueError):select_candidate(["x","x"],{},2)
    def test_no_implicit_qualification(self):
        base=dict(geometry="pass",screen="pass",full_motion="fail",negative_controls="unverified")
        self.assertFalse(qualification({**base,"user_demo":"pass","ci":"pass"})["certified"])
        self.assertEqual(qualification({**base,"full_motion":"pass"})["status"],"unverified")
        self.assertTrue(qualification(dict.fromkeys(base,"pass"))["certified"])
    def test_phase211_replay_summary(self):
        # Historical native run 45929746273, artifact 15168282701.
        # Summary metrics, not fabricated per-frame observations.
        metrics={"max_foot_error":.0973788070295949,"support_two_fraction":.8109908409658618,
            "max_tilt":5.63440360971482,"travel":19.16493455964335,"forward":3.5565428733825684}
        limits=[Limit("max_foot_error",upper=.04),Limit("support_two_fraction",lower=.95),
            Limit("max_tilt",upper=15),Limit("travel",lower=3*6.283185307179586),Limit("forward",lower=.5)]
        r=evaluate(limits,{k:[(1201,"run_summary",v)] for k,v in metrics.items()})
        self.assertEqual({k for k,v in r["metrics"].items() if v["status"]=="fail"},{"max_foot_error","support_two_fraction"})
        self.assertFalse(qualification(dict(geometry="pass",screen="pass",full_motion=r["status"]))["certified"])

if __name__=="__main__":unittest.main(verbosity=2)
