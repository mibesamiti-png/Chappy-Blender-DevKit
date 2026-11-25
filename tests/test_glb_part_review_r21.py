"""R21 synthetic controls, legacy false suggestion and bounded review."""
import copy
import unittest

from cbdk.glb_part_match import (
    suggest_spatial_part_matches, review_part_surfaces, _review_part_surfaces,
)
from cbdk.glb_surface_distance import _SurfaceWorkBudget
from cbdk.glb_surface_pipeline import _validate_part_review


def tetra(inverted=False, offset=0):
    vertices = [(0.,0.,0.), (1.,1.,0.), (1.,0.,1.), (0.,1.,1.)]
    if inverted:
        vertices = [tuple(1-x for x in v) for v in vertices]
    vertices = [(x+offset,y,z) for x,y,z in vertices]
    return [tuple(vertices[i] for i in f)
            for f in ((0,1,2),(0,3,1),(0,2,3),(1,3,2))]


def planar(x=0, alternate=False):
    a,b,c,d = (x,0.,0.),(x+1,0.,0.),(x+1,1.,0.),(x,1.,0.)
    return [(a,b,d),(b,c,d)] if alternate else [(a,b,c),(a,c,d)]


def envelope(part):
    counts = (part["reference_triangle_counts"], part["candidate_triangle_counts"])
    report = {"status":"review_only", "part_review":part, "part_inventory":{}}
    for side, values in zip(("reference","candidate"), counts):
        report[side+"_triangles"] = sum(values)
        report["part_inventory"][side+"_object_count"] = len(values)
        report["part_inventory"][side+"_triangle_counts"] = sorted(values,reverse=True)[:32]
    return report


class PartReviewR21(unittest.TestCase):
    def test_closed_same_bounds_legacy_false_suggestion(self):
        ref,cand = tetra(),tetra(True)
        old = suggest_spatial_part_matches(ref,cand,[4],[4])
        self.assertEqual(old["reference_parts"][0]["status"],"suggested")
        new = review_part_surfaces(ref,cand,[4],[4])
        row = new["reference_parts"][0]
        self.assertEqual(row["spatial_status"],"suggested")
        self.assertEqual(row["status"],"ambiguous")
        self.assertTrue(row["observations"][0]["surface_difference_observed"])
        self.assertEqual(new["unpaired_candidate_part_ids"],["part_001"])
        _validate_part_review(envelope(new))

    def test_retriangulated_order_and_competition(self):
        ref = planar() + planar(10)
        cand = planar(10,True) + planar(0,True)
        new = review_part_surfaces(ref,cand,[2,2],[2,2])
        self.assertEqual([r["candidate_part_ids"] for r in new["reference_parts"]],
                         [["part_002"],["part_001"]])
        self.assertTrue(all(r["status"]=="suggested" for r in new["reference_parts"]))
        _validate_part_review(envelope(new))
        tied = review_part_surfaces(planar(),planar()+planar(),[2],[2,2])
        self.assertEqual(tied["reference_parts"][0]["status"],"ambiguous")
        self.assertEqual(len(tied["reference_parts"][0]["candidate_part_ids"]),2)
        _validate_part_review(envelope(tied))

    def test_local_move_near_small_and_far_large_missing(self):
        # Same spatial candidate, small independent world-space motion.
        new = review_part_surfaces(tetra(),tetra(offset=.1),[4],[4])
        self.assertEqual(new["reference_parts"][0]["status"],"ambiguous")
        self.assertTrue(new["reference_parts"][0]["observations"][0]["surface_difference_observed"])
        left = planar()+planar(100)
        right = planar()
        missing = review_part_surfaces(left,right,[2,2],[2])
        self.assertEqual(missing["reference_parts"][1]["status"],"unmatched")
        added = review_part_surfaces(right,left,[2],[2,2])
        self.assertIn("part_002",added["unpaired_candidate_part_ids"])
        _validate_part_review(envelope(missing))
        _validate_part_review(envelope(added))

    def test_split_merge_and_degenerate_remain_uncertain(self):
        whole = planar()
        split = review_part_surfaces(whole, whole, [2], [1,1])
        self.assertNotEqual(split["reference_parts"][0]["status"],"suggested")
        merge = review_part_surfaces(whole, whole, [1,1], [2])
        self.assertTrue(all(row["status"] != "suggested" for row in merge["reference_parts"]))
        _validate_part_review(envelope(split))
        _validate_part_review(envelope(merge))
        degenerate = [((0.,0.,0.),(1.,0.,0.),(2.,0.,0.))]
        self.assertEqual(review_part_surfaces(degenerate,whole,[1],[2])["reason"],
                         "invalid_geometry")

    def test_layout_caps_and_budget(self):
        for ref,cand,rc,cc,reason in (
            (planar()*65,planar(),[2]*65,[2],"part_limit"),
            (planar()*1024+planar()[:1],planar(),[2049],[2],"triangle_limit"),
            (planar(),planar(),[0,2],[2],"empty_part"),
            (planar(),planar(),[1],[2],"invalid_part_layout"),
        ):
            self.assertEqual(review_part_surfaces(ref,cand,rc,cc)["reason"],reason)
        for key in ("samples","node_visits","triangle_evaluations"):
            budget = _SurfaceWorkBudget()
            budget.LIMITS = dict(budget.LIMITS,**{key:1})
            result = _review_part_surfaces(planar(),planar(),[2],[2],budget)
            row = result["reference_parts"][0]
            self.assertEqual(row["status"],"ambiguous")
            self.assertEqual(row["observations"][0]["exhausted_counter"],key)
            self.assertNotIn("reference_to_candidate",row["observations"][0])

    def test_forged_evidence_rejected(self):
        new = review_part_surfaces(tetra(),tetra(True),[4],[4])
        for mutate in (
            lambda p:p["reference_parts"][0].update(status="suggested"),
            lambda p:p["reference_parts"][0]["observations"][0].update(relative_sampled_max=float("inf")),
            lambda p:p["work_budget"]["used"].update(samples=0),
            lambda p:p.update(unpaired_candidate_part_ids=[]),
            lambda p:p.update(bvh_build_count=0),
            lambda p:p["reference_parts"][0].update(candidate_part_ids=["part_999"]),
        ):
            bad = copy.deepcopy(new)
            mutate(bad)
            with self.assertRaises(ValueError):
                _validate_part_review(envelope(bad))


if __name__ == "__main__":
    unittest.main()
