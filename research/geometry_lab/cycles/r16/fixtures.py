"""R16 source UVs authored from original input loops, not R10 output."""
from cycles.r13.fixtures import cases as old
from cycles.r7.fixtures import build

FRESH=(
 ("r16_circle", 20, 25, "circle", .83, (.18,-.09), .10,.07,.09,.04,-.05,5,False),
 ("r16_ellipse", 28, 18, "ellipse", .76, (.25,.12), .14,.08,.10,-.04,.06,7,True),
 ("r16_lobed", 23, 30, "lobed", .95, (-.17,.21), .12,.10,.12,.03,-.07,9,False),
 ("r16_offset", 21, 29, "circle", .88, (.63,-.19), .20,.09,.11,-.06,.04,8,True),
 ("r16_taper", 30, 13, "ellipse", .46, (.35,.12), .11,.07,.10,.04,-.06,6,False),
 ("r16_sparse", 11, 24, "circle", .71, (.19,.24), .09,.06,.08,.05,-.04,3,True),
 ("r16_wave", 26, 33, "lobed", 1.03, (.16,-.27), .16,.12,.14,-.05,.07,10,True),
 ("r16_skew", 32, 19, "ellipse", .91, (-.36,.31), .17,.09,.12,.07,-.05,11,False),
)
SEEN=("r13_cont_circle","r13_cont_ellipse","r13_alt_lobed","r13_multi_circle")

def cases():
    known={c["name"]:c for c in old()}
    for n in SEEN: yield dict(known[n],split="development")
    for spec in FRESH: yield dict(build(spec),split="holdout")
