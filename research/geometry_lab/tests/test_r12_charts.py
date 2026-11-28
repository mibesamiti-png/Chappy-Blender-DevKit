"""Tests only on the already-seen R11 synthetic cases, not R12 holdouts."""
import unittest
import numpy as np
from cbdk_geometry.quality_router import conditional_flip_loft
from cbdk_geometry.uv_charts import label_chart_offsets
from cycles.r11.fixtures import cases


def boundary_edges(faces):
    from collections import Counter
    c=Counter(tuple(sorted((int(u),int(v))))
              for tri in faces for u,v in zip(tri,np.roll(tri,-1)))
    return sorted(e for e,count in c.items() if count==1)


class ChartTransferTests(unittest.TestCase):
    def test_previous_r11_seen_geometry(self):
        for case in cases():
            if case["split"]!="holdout":
                continue
            a=case["a"].astype(np.float32).astype(float)
            b=case["b"].astype(np.float32).astype(float)
            mesh=conditional_flip_loft(a,b)["mesh"]
            edges=boundary_edges(mesh.faces)
            for mode in ("continuous","split"):
                constraints={}
                for i,edge in enumerate(edges):
                    constraints[edge]=(.25 if mode=="split" and i%2==0 else 0.,0.)
                x,s=label_chart_offsets(mesh.vertices,mesh.faces,constraints)
                self.assertEqual(s["boundary_count"],len(a)+len(b))
                self.assertEqual(x.shape,(len(mesh.faces),2))
                self.assertLessEqual(s["internal_seam_fraction"],.6)
                self.assertEqual(s["internal_seam_edges"]==0, mode=="continuous")
                y,t=label_chart_offsets(mesh.vertices,mesh.faces,constraints)
                np.testing.assert_array_equal(x,y)
                self.assertEqual(s,t)

    def test_invalid_constraints(self):
        c=next(c for c in cases() if c["name"]=="r11_clean_circle")
        mesh=conditional_flip_loft(c["a"],c["b"])["mesh"]
        edges=boundary_edges(mesh.faces)
        fixed={e:(0.,0.) for e in edges}
        offsets,metrics=label_chart_offsets(mesh.vertices,mesh.faces,fixed)
        self.assertEqual(metrics["internal_seam_edges"],0)
        with self.assertRaises(ValueError):
            label_chart_offsets(mesh.vertices,mesh.faces,dict(list(fixed.items())[:-1]))
        with self.assertRaises(ValueError):
            label_chart_offsets(mesh.vertices,mesh.faces,{**fixed,edges[0]:(float("nan"),0.)})


if __name__=="__main__":
    unittest.main()
