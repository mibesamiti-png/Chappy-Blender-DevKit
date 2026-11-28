"""R11: adversarial ordering of the optional first-64 AABB probe.

Synthetic contours only; no new geometric identity or hole claims.
"""
from statistics import median
from time import perf_counter
import tracemalloc
import unittest
from unittest.mock import patch

from cbdk.glb_part_match import (
    _boundary_layout_issue, _outside_expanded_boundary_segment_box,
    suggest_spatial_part_matches,
)
from test_glb_match_adaptive_r10 import always_box_layout, always_box_report
from test_glb_match_stress_r9 import unpruned_layout
from test_glb_match_pruning_r8 import original_unpruned
from test_glb_match_adversarial_r7 import slightly_perturbed_budget
from test_glb_match_budget_r4 import open_edge_fixture, many_rings
from test_glb_match_determinism_r5 import float32_faces, reorder_faces
from test_glb_part_match import square_frame, nearly_touching_triangles


def biased_contours(sparse_first):
    # The first point must scan past 64 boxes before the matching horizontal
    # segment. Dense diagonals contain the point but fail the R2 distance;
    # sparse horizontal boxes safely reject it. The reverse scan rejects the
    # added contours independently. Both orders have exactly the same lines.
    source = [(1, .30, .12, 0., .38, .12, 0.)]
    dense = [(1, 0., 0., 0., 1., 1., 0.)] * 64
    sparse = [(1, 0., .8, 0., 1., .8, 0.)] * 64
    target = (sparse + dense if sparse_first else dense + sparse)
    target += [(1, .20, .12, 0., .80, .12, 0.)]
    return source, target, {"center": (0., 0., 0.), "size": (1., 1., 0.)}


class R11ProbeBiasTests(unittest.TestCase):
    def test_nonrepresentative_prefix_changes_work_only(self):
        for sparse_first in (False, True):
            a, b, part = biased_contours(sparse_first)
            counts = [0, 0]
            def counted(*args):
                counts[0] += 1
                outside = _outside_expanded_boundary_segment_box(*args)
                counts[1] += int(outside)
                return outside
            with patch('cbdk.glb_part_match._outside_expanded_boundary_segment_box',
                       new=counted):
                actual = _boundary_layout_issue(a, b, part, part)
            self.assertEqual(actual, 'boundary_spatial_layout_mismatch')
            self.assertEqual(actual, always_box_layout(a, b, part))
            self.assertEqual(actual, unpruned_layout(a, b, part))
            if sparse_first:
                self.assertGreater(counts[0], 64)
                self.assertGreaterEqual(counts[1], 64)
            else:
                self.assertEqual(counts, [64, 0])
            print(f'CBDK_R11_PROBES sparse_first={sparse_first} '
                  f'boxes={counts[0]} rejected={counts[1]}')

    def test_full_reports_float32_order_r3_and_edge_budgets(self):
        cases = []
        for edges in (255, 256, 257):
            a = float32_faces(open_edge_fixture(edges))
            b = float32_faces(slightly_perturbed_budget(a))
            cases.append((a, b, [len(a)]))
        for b in (square_frame(opening_x=.24),
                  square_frame(flip_diagonal=True)):
            cases.append((square_frame(), b, [8]))
        cases.append((nearly_touching_triangles(),
                      nearly_touching_triangles(touch=True), [2]))
        groups = many_rings()
        cases.append(([f for g in groups for f in g],
                      [f for g in reversed(groups) for f in reorder_faces(g)],
                      [8]*64))
        for a, b, counts in cases:
            for ref, cand in ((a, b), (reorder_faces(a), reorder_faces(b))):
                actual = suggest_spatial_part_matches(ref, cand, counts, counts)
                self.assertEqual(actual, always_box_report(ref, cand, counts, counts))
                self.assertEqual(actual, original_unpruned(ref, cand, counts, counts))
                self.assertIs(actual['auto_apply'], False)
                self.assertIs(actual['cross_file_part_identity_proven'], False)
        # R3 must stay independent even where the sampled R2 gap is tiny.
        report = suggest_spatial_part_matches(*cases[-2][:2], [2], [2])
        self.assertIn('boundary_component_count_mismatch',
                      report['reference_parts'][0]['topology_review_reasons'])

    def test_zero_length_and_over_budget_order_do_not_gain_shortcuts(self):
        zero = [(1, 0., 0., 0., 0., 0., 0.)]
        part = {'center': (0., 0., 0.), 'size': (1., 1., 0.)}
        self.assertEqual(_boundary_layout_issue(zero, zero, part, part),
                         'boundary_spatial_layout_mismatch')
        a, b, part = biased_contours(False)
        self.assertEqual(_boundary_layout_issue(a, b*2, part, part),
                         'boundary_layout_budget_exceeded')

    def test_warmed_order_sensitive_medians_and_peak(self):
        for order in (False, True):
            a, b, part = biased_contours(order)
            runners = (lambda: always_box_layout(a, b, part),
                       lambda: _boundary_layout_issue(a, b, part, part),
                       lambda: unpruned_layout(a, b, part))
            timings = []
            for run in runners:
                run()
                samples = []
                for _ in range(5):
                    start = perf_counter()
                    self.assertEqual(run(), 'boundary_spatial_layout_mismatch')
                    samples.append(1000*(perf_counter()-start))
                timings.append(median(samples))
            tracemalloc.start()
            try:
                runners[1]()
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
            self.assertLess(peak, 32*1024*1024)
            print(f'CBDK_R11_BIAS sparse_first={order} r8_ms={timings[0]:.3f} '
                  f'r10_ms={timings[1]:.3f} r2_ms={timings[2]:.3f} '
                  f'peak_bytes={peak} samples=5')
