"""R7 preregistered non-planar synthetic loops (dev=4, holdout=6).

These are *new* synthetic models, NOT user-supplied models or third-party blind
ground truth. The fixture specifications remain immutable after first holdout.
"""
import numpy as np
from cycles.r4.fixtures import ring

# name, lower_N, upper_N, kind, upper_radius, upper_xy_offset,
# upper_phase, lower_warp_amp, upper_warp_amp, lower_tilt_x, upper_tilt_x,
# roll, reverse
DEV = (
    ("dev_gentle_circle", 16, 22, "circle", .85, (.12, .05), .03, .06, .08, .03, -.04, 4, False),
    ("dev_wave_ellipse", 20, 24, "ellipse", .75, (.25, -.10), .08, .10, .12, .05, .03, 5, True),
    ("dev_tilted_lobed", 24, 18, "lobed", .90, (.40, .10), .06, .06, .09, .12, -.11, 7, True),
    ("dev_offset", 26, 14, "circle", .72, (.85, -.17), .04, .07, .09, -.08, .11, 5, False),
)
HOLDOUT = (
    ("r7_lobed_wave", 19, 29, "lobed", .72, (.32, -.18), .14, .13, .16, .08, -.10, 8, True),
    ("r7_ellipse_tilt", 28, 17, "ellipse", 1.02, (-.25, .26), .19, .08, .13, .15, .12, 4, False),
    ("r7_sparse_circle", 7, 16, "circle", .69, (.10, .03), .05, .09, .12, -.04, .05, 9, True),
    ("r7_slender_offset", 37, 12, "ellipse", .24, (.70, .25), .12, .09, .11, .09, -.08, 5, False),
    ("r7_far_lobed", 18, 27, "lobed", .92, (1.55, -.07), .10, .08, .14, .04, -.02, 11, True),
    ("r7_opposed_waves", 22, 33, "circle", .83, (-.36, .30), .21, .18, .17, -.08, .10, 12, True),
)


def _warp(loop, amplitude, tilt_x, offset):
    p = np.array(loop, dtype=float, copy=True)
    dx = p[:, 0] - offset[0]
    dy = p[:, 1] - offset[1]
    theta = np.arctan2(dy, dx)
    p[:, 2] += amplitude * np.sin(2 * theta + .3) + tilt_x * dx
    return p


def build(spec, density=None):
    (name, n, m, kind, radius, offset, phase, amp_a,
     amp_b, tilt_a, tilt_b, shift, reverse) = spec
    count_a = n if density is None else density
    count_b = m if density is None else density
    a = _warp(ring(count_a, 0, kind), amp_a, tilt_a, (0.0, 0.0))
    b = _warp(ring(count_b, 1, kind, radius, offset, phase), amp_b, tilt_b, offset)
    if density is None:
        if reverse:
            b = b[::-1]
        b = np.roll(b, shift, axis=0)
    return dict(name=name, a=a, b=b, kind=kind, spec=spec)


def cases():
    for split, items in (("development", DEV), ("holdout", HOLDOUT)):
        for spec in items:
            yield dict(build(spec), split=split, origin="r7_synthetic")
