"""R10 frozen synthetic holdout. R7/R8/R9 samples are SEEN only.

This module is frozen before first R10 workflow run.
Not artist/user/private data or a third-party blind collection.
"""
from cycles.r9.fixtures import cases as r9_cases
from cycles.r7.fixtures import build

# (name, n, m, kind, radius, XY offset, phase, lower_wave, upper_wave,
#  lower tilt, upper tilt, cyclic shift, reverse)
FRESH = (
    ("r10_circle_mild", 20, 25, "circle", .87, (.18, -.07), .09, .06, .09, .03, -.05, 4, False),
    ("r10_lobed_waves", 22, 31, "lobed", .91, (-.25, .19), .13, .13, .12, -.06, .08, 6, True),
    ("r10_slender_reversed", 10, 37, "ellipse", .30, (-.57, .20), .12, .10, .14, -.07, .08, 7, False),
    ("r10_slender_forward", 39, 10, "ellipse", .25, (.77, -.17), .15, .11, .13, .08, -.09, 7, True),
    ("r10_narrow_opposed", 11, 40, "ellipse", .27, (-.61, .15), .16, .10, .15, -.05, .10, 5, True),
    ("r10_far_lobed", 19, 32, "lobed", 1.04, (1.31, -.12), .09, .10, .13, .07, -.10, 8, False),
    ("r10_skew_ellipse", 28, 16, "ellipse", .56, (.44, .27), .17, .12, .11, .09, .06, 9, True),
    ("r10_wave_circle", 16, 29, "circle", .88, (-.28, .32), .24, .18, .16, -.08, .11, 10, False),
)


def cases():
    for case in r9_cases():
        yield dict(case, split="development", origin="r7_r8_r9_seen")
    for spec in FRESH:
        yield dict(build(spec), split="holdout", origin="r10_new_synthetic")
