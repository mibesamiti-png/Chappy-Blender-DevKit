"""R13 optimizer tests on previously seen geometry only; no fresh R13 data."""
import unittest
from collections import defaultdict
import numpy as np
from cbdk_geometry.quality_router import conditional_flip_loft
from cbdk_geometry.uv_charts import label_chart_offsets
from cbdk_geometry.seam_opt import optimize_uv_charts
from cycles.r12.fixtures import cases as old_r12_cases


class R13SeamOptimizationTests(unittest.TestCase):
    def test_seen_two_and_four_chart_pins_and_pareto(self):
        selected=("r11_split_circle","r11_split_lobed",
                  "r12_alt_circle","r12_multi_circle")
        lookup={c["name"]:c for c in old_r12_cases()}
        for name in selected:
            case=lookup[name]
            a=case["a"].astype(np.float32).astype(float)
            b=case["b"].astype(np.float32).astype(float)
            mesh=conditional_flip_loft(a,b)["mesh"]
            incidence=defaultdict(list)
            for fi,tri in enumerate(mesh.faces):
                for u,v in zip(tri,np.roll(tri,-1)):
                    incidence[tuple(sorted((int(u),int(v))))].append(fi)
            nlabels=4 if name=="r12_multi_circle" else 2
            pinned={edge:((fi[0] % nlabels)*.25,0.)
                    for edge,fi in incidence.items() if len(fi)==1}
            baseline,previous=label_chart_offsets(mesh.vertices,mesh.faces,pinned)
            revised,stat=optimize_uv_charts(mesh.vertices,mesh.faces,pinned,baseline)
            self.assertLessEqual(stat["new_seams"],stat["old_seams"],name)
            self.assertLessEqual(stat["new_length"],stat["old_length"]+1e-8,name)
            self.assertEqual(revised.shape,baseline.shape)
            for edge,adj in incidence.items():
                if len(adj)==1:
                    self.assertLessEqual(float(np.max(np.abs(revised[adj[0]]-pinned[edge]))),1e-5,name)
            same,second=optimize_uv_charts(mesh.vertices,mesh.faces,pinned,baseline)
            np.testing.assert_array_equal(revised,same)
            self.assertEqual(stat["method"],second["method"])

    def test_zero_chart_and_invalid_inputs(self):
        c=next(c for c in old_r12_cases() if c["name"]=="r11_clean_circle")
        mesh=conditional_flip_loft(c["a"],c["b"])["mesh"]
        incidence=defaultdict(list)
        for i,tri in enumerate(mesh.faces):
            for u,v in zip(tri,np.roll(tri,-1)):
                incidence[tuple(sorted((int(u),int(v))))].append(i)
        boundary={edge:(0.,0.) for edge,faces in incidence.items() if len(faces)==1}
        b,_=label_chart_offsets(mesh.vertices,mesh.faces,boundary)
        opt,meta=optimize_uv_charts(mesh.vertices,mesh.faces,boundary,b)
        self.assertEqual(meta["old_seams"],0)
        self.assertEqual(meta["new_seams"],0)
        np.testing.assert_array_equal(opt,b)
        with self.assertRaises(ValueError):
            optimize_uv_charts(mesh.vertices,mesh.faces,
                               dict(list(boundary.items())[:-1]),b)
        with self.assertRaises(ValueError):
            optimize_uv_charts(mesh.vertices,mesh.faces,boundary,b,seconds=0)


if __name__=="__main__":
    unittest.main()
