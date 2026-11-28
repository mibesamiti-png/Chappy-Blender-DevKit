"""R21 new frozen compatible rectangular chart geometries."""
from cycles.r7.fixtures import build
FRESH=(
 ("r21_round", 24, 31, "circle", .91, (.14,-.21), .17,.08,.10,.04,-.06,9,True),
 ("r21_oval", 34, 23, "ellipse", .82, (-.21,.17), .15,.10,.11,-.06,.04,8,False),
 ("r21_lobed", 29, 22, "lobed", .89, (.26,.16), .11,.11,.08,.07,-.04,7,True),
 ("r21_offset", 23, 33, "circle", .85, (.52,-.23), .18,.08,.12,-.04,.07,12,False),
 ("r21_taper", 32, 16, "ellipse", .58, (.28,.16), .13,.09,.10,.06,-.05,8,True),
 ("r21_sparse", 13, 21, "circle", .79, (-.17,-.19), .08,.07,.11,-.05,.04,5,False),
 ("r21_wave", 31, 35, "lobed", .98, (.19,-.25), .20,.14,.12,-.06,.07,13,True),
 ("r21_skew", 27, 20, "ellipse", .94, (.32,.24), .16,.12,.08,.08,-.05,9,False),
)
def cases():
    return [dict(build(s),split="holdout") for s in FRESH]
