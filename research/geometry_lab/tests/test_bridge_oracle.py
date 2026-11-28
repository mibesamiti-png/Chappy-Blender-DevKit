"""Independent intersection oracle plus exact boundary-edge contract."""
import unittest
from collections import Counter
from cbdk_geometry.bridge import bridge_loops
from cycles.r4.fixtures import cases
from cycles.r2.oracle import mesh_hits

class BridgeOracleTests(unittest.TestCase):
    def test_development_oracle_and_boundary_edges(self):
        for c in cases():
            n,m=len(c['a']),len(c['b'])
            expected={tuple(sorted((i,(i+1)%n))) for i in range(n)}
            expected|={tuple(sorted((n+j,n+(j+1)%m))) for j in range(m)}
            for method in ('phase','dp'):
                mesh=bridge_loops(c['a'],c['b'],method)['mesh']
                edges=Counter(tuple(sorted((int(f[i]),int(f[(i+1)%3])))) for f in mesh.faces for i in range(3))
                self.assertEqual({e for e,k in edges.items() if k==1},expected)
                self.assertEqual(mesh_hits(mesh),[])
