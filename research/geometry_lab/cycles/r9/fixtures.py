"""R9 fresh synthetic benchmark; previous R7/R8 cases are seen data.

No user/private geometry. Freeze FRESH before the first heldout CI run.
"""
from cycles.r8.fixtures import cases as r8_cases
from cycles.r7.fixtures import build

# name, n, m, kind, radius, XY_offset, phase, low_wave, high_wave,
# low_tilt, high_tilt, shift, reverse. Unique new parameter combinations.
FRESH = (
    ("r9_reverse_narrow", 8, 43, "ellipse", .23, (-.72, .12), .12, .12, .14, -.06, .09, 5, True),
    ("r9_forward_narrow", 42, 9, "ellipse", .19, (.81, -.22), .17, .11, .13, .07, -.12, 6, False),
    ("r9_reverse_skew", 12, 36, "ellipse", .35, (-.54, .32), .09, .13, .10, -.10, .05, 9, False),
    ("r9_lobed_offset", 21, 35, "lobed", .87, (1.32, -.23), .16, .08, .13, .04, -.07, 7, True),
    ("r9_sparse_ridge", 10, 24, "circle", .57, (-.25, .09), .18, .16, .17, -.06, .08, 4, False),
    ("r9_opposed_waves", 23, 30, "circle", .86, (.25, -.39), .22, .18, .13, -.10, .09, 10, True),
)


def cases():
    for case in r8_cases():
        yield dict(case, split="development", origin="r7_r8_seen")
    for spec in FRESH:
        yield dict(build(spec), split="holdout", origin="r9_new_synthetic")
