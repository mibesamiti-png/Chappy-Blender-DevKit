"""R8 fresh synthetic frozen holdout on nonplanar boundaries.

Old R7 development+holdout are now SEEN. Fresh R8 designs are untouched by
algorithm tuning. All samples authored from synthetic constants, no user art.
"""
from cycles.r7.fixtures import cases as r7_cases, build as r7_build

# 13 fields in cycles.r7.fixtures.build (same geometric families, novel params).
FRESH=(
    ("r8_slender_tilt", 41, 11, "ellipse", .21, (.75, .18), .13, .11, .12, .07, -.09, 6, True),
    ("r8_slender_opposite", 9, 39, "ellipse", .28, (-.60, .20), .08, .09, .15, -.05, .12, 7, False),
    ("r8_offset_lobed", 17, 31, "lobed", 1.06, (1.25, -.25), .10, .07, .11, .08, -.06, 4, True),
    ("r8_sparse_bend", 8, 21, "circle", .62, (.11, -.07), .17, .12, .14, -.11, .09, 3, False),
    ("r8_ellipse_skew", 32, 14, "ellipse", .58, (.52, .31), .22, .10, .10, .08, .12, 9, True),
    ("r8_wide_lobed", 24, 37, "lobed", 1.17, (-.42, -.31), .05, .16, .11, .03, -.12, 11, False),
)


def cases():
    for old in r7_cases():
        yield dict(old, split="development", origin="r7_seen_" + old["split"])
    for item in FRESH:
        yield dict(r7_build(item), split="holdout", origin="r8_synthetic_new")
