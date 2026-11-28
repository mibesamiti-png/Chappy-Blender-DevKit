"""R11 synthetic Blender Edit Mode attribute preservation corpus.

Known R10 fixtures are now seen. All six R11 holdouts remain frozen.
13 fields from cycles.r7.fixtures.build: original rings, no private art.
"""
from cycles.r10.fixtures import cases as r10_cases
from cycles.r7.fixtures import build

DEVELOPMENT=("r10_circle_mild","r10_slender_forward","r10_slender_reversed","r10_far_lobed")
FRESH=(
    ("r11_clean_circle", 18, 24, "circle", .84, (.17, -.06), .05, .05, .08, .04, -.03, 5, True),
    ("r11_lobed_collar", 21, 28, "lobed", .94, (-.24, .27), .11, .12, .09, -.03, .07, 6, False),
    ("r11_tilt_ellipse", 26, 17, "ellipse", .70, (.38, .15), .16, .09, .11, .09, -.06, 9, True),
    ("r11_split_circle", 17, 27, "circle", .89, (-.29, .14), .15, .07, .12, -.06, .05, 7, False),
    ("r11_split_offset", 29, 12, "ellipse", .37, (.42, -.18), .12, .11, .13, .07, -.09, 9, True),
    ("r11_split_lobed", 23, 31, "lobed", .88, (1.07, .04), .20, .10, .11, -.08, .06, 11, False),
)
MODES=("continuous","split")


def cases():
    old={c["name"]:c for c in r10_cases()}
    for name in DEVELOPMENT:
        for mode in MODES:
            yield dict(old[name],split="development",uv_mode=mode)
    for i,spec in enumerate(FRESH):
        mode="continuous" if i<3 else "split"
        yield dict(build(spec),split="holdout",uv_mode=mode,
                   origin="r11_new_synthetic_edit_mode")
