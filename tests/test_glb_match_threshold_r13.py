"""R13: reproducible first-probe boundaries; counts are not wall-clock speed."""
import random
from statistics import median
import sys
from time import perf_counter
import tracemalloc
import unittest
from unittest.mock import patch

import cbdk.glb_part_match as match
from test_glb_match_probe_r12 import layout, nearest_evaluations, threshold_contours
from test_glb_match_adaptive_r10 import always_box_report
from test_glb_match_pruning_r8 import original_unpruned
from test_glb_match_determinism_r5 import float32_faces
from test_glb_part_match import nearly_touching_triangles, square_frame


MODES = ('adaptive', 'r8', 'r2')


def threshold_order(rejected, seed, sparse_late):
    """Same segment multiset, controlled probe, changed late reversal position."""
    a, b, part = threshold_contours(rejected)
    dense, sparse, compatible = b[0], b[63], b[-1]
    prefix = [dense] * (64 - rejected) + [sparse] * rejected
    random.Random(seed).shuffle(prefix)
    # Rotate the two late-density blocks across boundary offsets 0/1/63/64.
    tail = [sparse] * 64 + [dense] * 64
    tail = tail[sparse_late:] + tail[:sparse_late]
    return a, prefix + tail + [compatible], part


class R13ThresholdTests(unittest.TestCase):
    def test_seeded_prefix_six_through_nine_and_late_reversal_parity(self):
        for rejected in range(6, 10):
            for seed in (6, 7, 8, 9):
                for offset in (0, 1, 63, 64):
                    with self.subTest(rejected=rejected, seed=seed, offset=offset):
                        a, b, part = threshold_order(rejected, seed, offset)
                        self.assertEqual((a, b, part), threshold_order(rejected, seed, offset))
                        self.assertCountEqual(b, threshold_order(rejected, 6, 0)[1])
                        calls = []
                        original = match._keep_r2_bbox_after_probe
                        def decide(value):
                            calls.append(value)
                            return original(value)
                        with patch.object(match, '_keep_r2_bbox_after_probe', new=decide):
                            actual = layout('adaptive', a, b, part)
                        self.assertEqual(calls, [rejected])
                        self.assertEqual(actual, 'boundary_spatial_layout_mismatch')
                        self.assertEqual(actual, layout('r8', a, b, part))
                        self.assertEqual(actual, layout('r2', a, b, part))

    def test_calibrated_projection_work_and_untraced_balanced_timing(self):
        # Analytic calibration on the R12 unshuffled fixture: three source
        # samples scan 129 target lines; the first reverse sample scans one.
        # R2=388, fixed R8=3*(64-rejected+1); disabled adaptive=388-rejected.
        for rejected in range(6, 10):
            a, b, part = threshold_contours(rejected)
            expected = {'r2': 388, 'r8': 3 * (65 - rejected),
                        'adaptive': 388 - rejected if rejected < 8 else 3 * (65 - rejected)}
            previous = sys.gettrace()
            for mode in MODES:
                result, count = nearest_evaluations(mode, a, b, part)
                self.assertEqual(count, expected[mode])
                self.assertEqual(result, 'boundary_spatial_layout_mismatch')
                self.assertIs(sys.gettrace(), previous)
            # Instrumentation is deliberately absent from timing. Rotate mode
            # order to avoid always giving one implementation the warmest slot.
            samples = {mode: [] for mode in MODES}
            for mode in MODES:
                layout(mode, a, b, part)
            for index in range(6):
                order = MODES[index % 3:] + MODES[:index % 3]
                for mode in order:
                    start = perf_counter()
                    actual = layout(mode, a, b, part)
                    samples[mode].append(1000 * (perf_counter() - start))
                    self.assertEqual(actual, 'boundary_spatial_layout_mismatch')
            peaks = {}
            for mode in MODES:
                tracemalloc.start()
                try:
                    layout(mode, a, b, part)
                    peaks[mode] = tracemalloc.get_traced_memory()[1]
                finally:
                    tracemalloc.stop()
                self.assertLess(peaks[mode], 32 * 1024 * 1024)
            print(f'CBDK_R13_THRESHOLD rejected={rejected} ' + ' '.join(
                f'{mode}_projections={expected[mode]} {mode}_ms={median(samples[mode]):.3f} '
                f'{mode}_peak={peaks[mode]}' for mode in MODES) +
                ' samples=6 timing_traced=false')

    def test_full_float32_reports_seeded_openings_keep_independent_r3(self):
        pairs = [(square_frame(), square_frame(opening_x=x)) for x in (.24, .38)]
        pairs.append((nearly_touching_triangles(), nearly_touching_triangles(touch=True)))
        for left, right in pairs:
            a, b = float32_faces(left), float32_faces(right)
            for seed in (6, 7, 8, 9):
                aa, bb = list(a), list(b)
                random.Random(seed).shuffle(aa)
                random.Random(seed + 1).shuffle(bb)
                counts = [len(a)]
                report = match.suggest_spatial_part_matches(aa, bb, counts, counts)
                self.assertEqual(report, always_box_report(aa, bb, counts, counts))
                self.assertEqual(report, original_unpruned(aa, bb, counts, counts))
                self.assertFalse(report['auto_apply'])
                self.assertFalse(report['cross_file_part_identity_proven'])
                if len(a) == 2:
                    self.assertIn('boundary_component_count_mismatch',
                                  report['reference_parts'][0]['topology_review_reasons'])
