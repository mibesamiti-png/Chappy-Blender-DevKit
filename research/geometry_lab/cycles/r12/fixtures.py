"""Frozen R12 author-generated UV-chart corpus; no private assets."""
from cycles.r11.fixtures import cases as r11_cases
from cycles.r7.fixtures import build

FRESH = (
 ("r12_cont_circle", 18, 27, "circle", .84, (.16, -.12), .08, .07, .10, -.02, .05, 6, True, "continuous"),
 ("r12_cont_lobed", 21, 29, "lobed", .90, (-.24, .18), .11, .10, .11, .04, -.06, 8, False, "continuous"),
 ("r12_cont_ellipse", 29, 17, "ellipse", .67, (.35, .16), .14, .10, .13, -.06, .08, 7, True, "continuous"),
 ("r12_alt_circle", 20, 33, "circle", .92, (-.30, .14), .12, .11, .13, .07, -.05, 11, True, "split"),
 ("r12_alt_ellipse", 34, 13, "ellipse", .49, (.54, -.22), .14, .08, .10, -.07, .09, 9, False, "split"),
 ("r12_alt_lobed", 25, 35, "lobed", 1.02, (.21, .29), .09, .13, .14, .04, -.06, 7, True, "split"),
 ("r12_block_lobed", 23, 28, "lobed", .86, (.76, -.13), .12, .09, .12, -.04, .07, 5, False, "blocks"),
 ("r12_multi_circle", 24, 31, "circle", .85, (-.24, .22), .15, .12, .11, .06, -.06, 9, True, "multi"),
)
SEEN=("r11_clean_circle","r11_lobed_collar","r11_split_circle","r11_split_lobed")


def cases():
    old={c["name"]:c for c in r11_cases()}
    for name in SEEN:
        yield dict(old[name],split="development",origin="r11_seen")
    for record in FRESH:
        *spec,mode=record
        yield dict(build(tuple(spec)),split="holdout",uv_mode=mode,
                   origin="r12_new_synthetic")
