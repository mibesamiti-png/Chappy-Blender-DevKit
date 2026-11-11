"""R6 untouched synthetic holdout + exposed R4/R5 regression cases.

Freeze this file before running Blender R6. New cases are not third-party blind.
"""
import numpy as np
from cycles.r4.fixtures import ring
from cycles.r5.fixtures import cases as prior_cases

R6_FRESH = (
    ("r6_twisted_lobed", 14, 29, "lobed", 0.78, (0.54, -0.17), 0.11, 6, True),
    ("r6_ellipse_tall", 25, 17, "ellipse", 1.05, (-0.31, 0.23), 0.19, 4, False),
    ("r6_sparse_circle", 6, 14, "circle", 0.62, (0.09, 0.0), 0.05, 8, True),
    ("r6_slender_shift", 37, 12, "ellipse", 0.22, (0.70, 0.26), 0.15, 5, False),
    ("r6_far_lobed", 18, 26, "lobed", 0.95, (1.74, -0.08), 0.12, 10, True),
)


def cases():
    for case in prior_cases():
        yield dict(case, split="seen", origin=case["origin"])
    for name, n, m, kind, radius, offset, phase, shift, reverse in R6_FRESH:
        a = ring(n, 0, kind)
        b = ring(m, 1, kind, radius, offset, phase)
        if reverse:
            b = b[::-1]
        b = np.roll(b, shift, axis=0)
        yield dict(name=name, split="holdout", origin="r6_new", a=a,
                   b=b, kind=kind, radius=radius, offset=offset)
