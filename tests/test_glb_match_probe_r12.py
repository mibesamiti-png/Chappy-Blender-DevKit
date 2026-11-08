"""R12: first-64 threshold/permutation work counts without product changes."""
import ast
from contextlib import ExitStack
import inspect
import random
from statistics import median
import sys
from time import perf_counter
import tracemalloc
import unittest
from unittest.mock import patch

import cbdk.glb_part_match as match
from test_glb_match_bias_r11 import biased_contours
from test_glb_match_adaptive_r10 import always_box_report
from test_glb_match_pruning_r8 import original_unpruned
from test_glb_match_budget_r4 import open_edge_fixture
from test_glb_match_adversarial_r7 import slightly_perturbed_budget
from test_glb_match_determinism_r5 import float32_faces
from test_glb_part_match import nearly_touching_triangles


def threshold_contours(rejected):
    a, b, part = biased_contours(False)
    # First 64 checks: exactly 7 or 8 true rejects; reverse the late trend
    # using the same bounded dense/sparse ingredients, no changed predicate.
    dense, sparse, compatible = b[0], b[64], b[-1]
    return a, [dense]*(64-rejected)+[sparse]*rejected+[sparse]*64+[compatible], part


def layout(mode, a, b, part):
    with ExitStack() as stack:
        if mode == 'r8':
            stack.enter_context(patch.object(match, '_keep_r2_bbox_after_probe', new=lambda _: True))
        elif mode == 'r2':
            stack.enter_context(patch.object(match, '_outside_expanded_boundary_segment_box',
                                             new=lambda *_: False))
        return match._boundary_layout_issue(a, b, part, part)


def nearest_evaluations(mode, a, b, part):
    """Count the original nondegenerate projection evaluation via line trace.

    Tracing is for work counts only, NEVER timed as a performance benchmark.
    No replacement of the R2 distance math; restore any prior tracer.
    """
    source, first = inspect.getsourcelines(match._boundary_layout_issue)
    tree = ast.parse(''.join(source))
    lines = [first+n.lineno-1 for n in ast.walk(tree)
             if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
             and isinstance(n.test.left, ast.Name) and n.test.left.id == 'norm2']
    if len(lines) != 1:
        raise AssertionError('R2 projection instrumentation needs explicit review')
    count = [0]
    filename = match._boundary_layout_issue.__code__.co_filename
    def trace(frame, event, arg):
        if (event == 'line' and frame.f_code.co_filename == filename
                and frame.f_code.co_name == 'within_any' and frame.f_lineno == lines[0]
                and frame.f_locals['norm2'] > 0):
            count[0] += 1
        return trace
    previous = sys.gettrace()
    try:
        sys.settrace(trace)
        result = layout(mode, a, b, part)
    finally:
        sys.settrace(previous)
    return result, count[0]


class R12ProbeWorkTests(unittest.TestCase):
    def test_seven_eight_actual_prefix_decision_and_nearest_work(self):
        part = {'center': (0., 0., 0.), 'size': (1., 1., 0.)}
        # Calibrate exactly six endpoint/midpoint samples in two directions.
        a = [(1, .1, .1, 0., .9, .1, 0.)]
        b = [(1, .1, .1001, 0., .9, .1001, 0.)]
        self.assertEqual(nearest_evaluations('r2', a, b, part), (None, 6))
        for rejected in (7, 8):
            a, b, part = threshold_contours(rejected)
            decisions = []
            original = match._keep_r2_bbox_after_probe
            def decide(value):
                decisions.append(value)
                return original(value)
            with patch.object(match, '_keep_r2_bbox_after_probe', new=decide):
                actual = layout('adaptive', a, b, part)
            self.assertEqual(decisions, [rejected])
            counts = {}
            previous = sys.gettrace()
            for mode in ('r8', 'adaptive', 'r2'):
                result, counts[mode] = nearest_evaluations(mode, a, b, part)
                self.assertEqual(result, actual)
                self.assertIs(sys.gettrace(), previous)
            self.assertLess(counts['r8'], counts['r2'])
            if rejected == 7:
                self.assertGreater(counts['adaptive'], counts['r8'])
            else:
                self.assertEqual(counts['adaptive'], counts['r8'])
            print(f'CBDK_R12_WORK rejected={rejected} r8={counts["r8"]} '
                  f'adaptive={counts["adaptive"]} r2={counts["r2"]}')

    def test_fixed_seed_permutations_and_late_density_reversal(self):
        for sparse_first in (False, True):
            a, b, part = biased_contours(sparse_first)
            expected = layout('r2', a, b, part)
            for seed in (0, 1, 17, 2026):
                shuffled = list(b)
                random.Random(seed).shuffle(shuffled)
                self.assertCountEqual(shuffled, b)
                for mode in ('r8', 'adaptive', 'r2'):
                    self.assertEqual(layout(mode, a, shuffled, part), expected)

    def test_full_report_seed_order_float32_and_independent_r3(self):
        for edges in (255, 256, 257):
            a = float32_faces(open_edge_fixture(edges))
            b = float32_faces(slightly_perturbed_budget(a))
            for seed in (0, 17):
                left, right = list(a), list(b)
                random.Random(seed).shuffle(left)
                random.Random(seed+1).shuffle(right)
                counts = [len(a)]
                report = match.suggest_spatial_part_matches(left, right, counts, counts)
                self.assertEqual(report, always_box_report(left, right, counts, counts))
                self.assertEqual(report, original_unpruned(left, right, counts, counts))
                self.assertIs(report['auto_apply'], False)
                self.assertIs(report['cross_file_part_identity_proven'], False)
        a, b = nearly_touching_triangles(), nearly_touching_triangles(touch=True)
        report = match.suggest_spatial_part_matches(a, b, [2], [2])
        self.assertEqual(report, original_unpruned(a, b, [2], [2]))
        self.assertIn('boundary_component_count_mismatch',
                      report['reference_parts'][0]['topology_review_reasons'])

    def test_untraced_paired_medians_and_peak(self):
        for rejected in (7, 8):
            a, b, part = threshold_contours(rejected)
            samples = {mode: [] for mode in ('r8', 'adaptive', 'r2')}
            for mode in samples:
                layout(mode, a, b, part)
            for _ in range(5):
                for mode in samples:
                    start = perf_counter()
                    self.assertEqual(layout(mode, a, b, part), 'boundary_spatial_layout_mismatch')
                    samples[mode].append(1000*(perf_counter()-start))
            peaks = {}
            for mode in samples:
                tracemalloc.start()
                try:
                    layout(mode, a, b, part)
                    peaks[mode] = tracemalloc.get_traced_memory()[1]
                finally:
                    tracemalloc.stop()
                self.assertLess(peaks[mode], 32*1024*1024)
            print(f'CBDK_R12_PERF rejected={rejected} '+ ' '.join(
                f'{m}_ms={median(samples[m]):.3f} {m}_peak={peaks[m]}' for m in samples)+
                ' samples=5 tracing=false')
