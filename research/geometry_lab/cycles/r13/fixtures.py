"""R13 independent synthetic holdout corpus, pre-frozen before new CI.

All earlier R11 and R12 shapes are seen; nothing private or third-party blind.
"""
from cycles.r12.fixtures import cases as r12_cases
from cycles.r7.fixtures import build

FRESH=(
 ("r13_cont_circle", 19, 26, "circle", .81, (.22,-.15), .17, .09, .08, -.06, .04, 5, False, "continuous"),
 ("r13_cont_lobed", 24, 32, "lobed", .99, (-.31,.14), .08, .08, .13, .06, -.02, 8, True, "continuous"),
 ("r13_cont_ellipse", 27, 15, "ellipse", .61, (.43,.23), .12, .11, .09, -.08, .06, 10, True, "continuous"),
 ("r13_alt_circle", 22, 35, "circle", .90, (-.18,.19), .21, .11, .12, -.07, .08, 10, False, "split"),
 ("r13_alt_ellipse", 33, 14, "ellipse", .46, (.68,-.12), .10, .09, .13, .06, -.07, 8, True, "split"),
 ("r13_alt_lobed", 27, 36, "lobed", 1.00, (.32,.35), .14, .12, .12, -.06, .09, 12, False, "split"),
 ("r13_block_lobed", 25, 30, "lobed", .91, (.84,-.26), .16, .12, .10, -.07, .08, 7, True, "blocks"),
 ("r13_multi_circle", 23, 34, "circle", .91, (-.32,.24), .19, .14, .12, .07, -.06, 11, False, "multi"),
)
SEEN=("r11_split_circle","r11_split_lobed","r12_alt_circle","r12_multi_circle")


def cases():
    old={c["name"]:c for c in r12_cases()}
    for name in SEEN:
        yield dict(old[name],split="development",origin="r11_r12_seen")
    for rec in FRESH:
        *spec,mode=rec
        yield dict(build(tuple(spec)),split="holdout",uv_mode=mode,
                   origin="r13_new_synthetic")
