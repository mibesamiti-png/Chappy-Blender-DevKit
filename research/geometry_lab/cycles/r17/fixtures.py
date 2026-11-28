"""R17 frozen synthetic geometries; R16 output is the baseline."""
from cycles.r16.fixtures import cases as old
from cycles.r7.fixtures import build
SEEN=("r16_circle","r16_ellipse","r16_sparse","r16_skew")
FRESH=(
 ("r17_round", 22, 28, "circle", .87, (.19,.13), .13,.08,.09,.04,-.05,6,True),
 ("r17_oval", 30, 19, "ellipse", .73, (-.29,.19), .12,.09,.10,-.05,.07,8,False),
 ("r17_lobed", 25, 32, "lobed", .96, (.22,-.20), .16,.12,.11,.05,-.06,10,True),
 ("r17_offset", 19, 27, "circle", .81, (.59,.15), .11,.07,.12,-.06,.04,7,False),
 ("r17_taper", 31, 14, "ellipse", .51, (.42,-.17), .15,.08,.11,.03,-.07,9,True),
 ("r17_sparse", 12, 26, "circle", .76, (-.22,.18), .10,.06,.09,-.05,.06,5,False),
 ("r17_wave", 28, 34, "lobed", 1.01, (-.28,-.21), .14,.13,.15,.06,-.08,12,True),
 ("r17_skew", 33, 21, "ellipse", .92, (.37,.29), .19,.10,.13,-.07,.05,11,True),
)
def cases():
    known={c["name"]:c for c in old()}
    for name in SEEN: yield dict(known[name],split="development")
    for spec in FRESH: yield dict(build(spec),split="holdout")
