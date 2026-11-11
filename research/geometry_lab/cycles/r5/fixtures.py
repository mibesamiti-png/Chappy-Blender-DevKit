"""R5 new held-out synthetic parameter set. NOT used during R5 algorithm design.

The former R4 holdout is now R5 development, never a new blind holdout.
The new cases remain synthetic and authored by the same researcher.
"""
import numpy as np
from cycles.r4.fixtures import ring

NEW_HOLDOUT = (
    ("r5_lobed_asymmetric", 19, 31, "lobed", .6, (.3, -.2), 7, True, .14),
    ("r5_ellipse_offset", 11, 27, "ellipse", .5, (-.65, .1), 9, False, .02),
    ("r5_superellipse_skew", 12, 17, "superellipse", .9, (.8, .1), 5, True, .1),
    ("r5_slender_offset", 35, 10, "ellipse", .18, (.9, .3), 4, True, .11),
    ("r5_lobed_wide", 9, 31, "lobed", 1.2, (-.2, -.4), 12, False, .04),
)


def cases():
    from cycles.r4.fixtures import cases as r4_cases
    for split in ("development", "holdout"):
        for item in r4_cases(split):
            yield dict(item, split="development", origin="r4_" + split)
    for name, n, m, kind, radius, offset, shift, reverse, phase in NEW_HOLDOUT:
        a = ring(n, 0, kind)
        b = ring(m, 1, kind, radius, offset, phase)
        if reverse:
            b = b[::-1]
        b = np.roll(b, shift, axis=0)
        yield dict(name=name, split="holdout", origin="r5_new",
                   a=a, b=b, kind=kind, radius=radius, offset=offset)
