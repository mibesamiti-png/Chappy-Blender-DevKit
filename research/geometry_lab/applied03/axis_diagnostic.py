"""Applied03 follow-up: compare fixed stagger against tilted folding axes.
Prior CI job 138940610640: baseline 48, rear6 16, depth stagger 15,
vertical and combined 6/84. Frozen before follow-up actual-mesh results.
All candidates are diagnostic, not physical hinge designs.
"""
import argparse
import itertools
import math
import json
from pathlib import Path
import numpy as np
from applied02.contact_diagnostic import transformed, hit_pairs, intended_pair

# Each side: rear offset mm, vertical offset mm, common global X tilt degrees.
# Common X tilt produces opposite vertical excursions on opposite fold directions.
CANDIDATES = {
    "baseline": ((0,0,0),(0,0,0)),
    "rear6": ((6,0,0),(6,0,0)),
    "vertical3": ((6,3,0),(6,-3,0)),
    "vertical4": ((6,4,0),(6,-4,0)),
    "vertical5": ((6,5,0),(6,-5,0)),
    "vertical6": ((6,6,0),(6,-6,0)),
    "tilt2": ((6,0,2),(6,0,2)),
    "tilt4": ((6,0,4),(6,0,4)),
    "tilt6": ((6,0,6),(6,0,6)),
    "tilt8": ((6,0,8),(6,0,8)),
    "tilt_minus4": ((6,0,-4),(6,0,-4)),
    "tilt_minus8": ((6,0,-8),(6,0,-8)),
}

def pose(m, angle, config):
    dy, dz, tilt = config
    offset = np.array([0.,dy/1000.,dz/1000.])
    side = m["parent"]
    if side is None or tilt == 0:
        return transformed(m, angle, angle) + offset
    sign = 1 if side == "Hinge_R" else -1
    pivot = np.array([sign*.069,.005,.003])
    b = math.radians(tilt)
    axis = np.array([math.sin(b),0.,math.cos(b)])
    t = math.radians(sign*angle)
    q = np.asarray(m["vertices"],float) - pivot
    # Rodrigues rotation; exact open identity, same original pivot before offset.
    if angle == 0:
        return np.asarray(m["vertices"],float) + offset
    return q*math.cos(t) + np.cross(axis,q)*math.sin(t) + (q@axis)[:,None]*axis*(1-math.cos(t)) + pivot + offset

def run(d):
    raw = json.loads((d / "raw.json").read_text())
    evaluation = json.loads((d / "evaluation.json").read_text())
    prior = json.loads((d / "contact_diagnostic.json").read_text())
    if not evaluation["gate"] or not raw["roundtrip_exact"]:
        raise ValueError("frozen B mesh gate not passed")
    base = raw["open"]
    pairs = [(x, y) for x, y in itertools.combinations(sorted(base), 2)
             if (base[x]["parent"] or base[y]["parent"]) and not intended_pair(x, y, base)]
    angles = range(0, 86, 5)
    states = sorted(set((r,l) for t in angles for r,l in ((t,0),(0,t),(85,t),(t,85),(t,t))))
    if len(states) != 84 or len(pairs) != 24 or prior["states_with_contact"] != 48:
        raise ValueError("unexpected baseline dimensions")
    triangles = {}
    hits = {}
    def key(name, r, l, dr, dl):
        side = base[name]["parent"]
        if side == "Hinge_R":
            return (name, r, dr)
        if side == "Hinge_L":
            return (name, l, dl)
        if side is not None:
            raise ValueError(f"unknown moving group {side}")
        return (name, 0, (0, 0, 0))
    def geometry(k):
        if k not in triangles:
            name, a, config = k
            m = base[name]
            v = pose(m, a, config)
            triangles[k] = v[np.array(m["triangles"], int)]
        return triangles[k]
    result = {}
    for label, (dr, dl) in CANDIDATES.items():
        rows = []
        for r, l in states:
            contacts = {}
            for x, y in pairs:
                k = (key(x,r,l,dr,dl), key(y,r,l,dr,dl))
                if k not in hits:
                    hits[k] = hit_pairs(geometry(k[0]), geometry(k[1]))
                if hits[k]:
                    contacts[x+"+"+y] = hits[k]
            rows.append(dict(right_deg=r,left_deg=l,nonexempt_surface_contacts=contacts))
        if label == "baseline" and rows != prior["rows"]:
            raise ValueError("baseline differs from archived CGAL diagnostic")
        count = sum(bool(row["nonexempt_surface_contacts"]) for row in rows)
        if label in ("rear6","vertical3") and count != {"rear6":16,"vertical3":6}[label]:
            raise ValueError("prior control count differs")
        pair_counts = {x+"+"+y: sum(x+"+"+y in row["nonexempt_surface_contacts"] for row in rows)
                       for x,y in pairs}
        result[label] = dict(placement_mm_mm_deg=[dr,dl], states_with_contact=count,
                             open_contacts=rows[0]["nonexempt_surface_contacts"],
                             pair_pose_counts={k:v for k,v in pair_counts.items() if v}, rows=rows)
        print("APPLIED03_AXIS", label, count, result[label]["pair_pose_counts"], flush=True)
    return dict(approved=False, diagnostic_only=True, states=84, pairs=24,
                baseline_reproduced=True, candidates=result,
                limitations=["Rigid placement and analytical axis tilt only; pin/sleeve geometry and endpiece not redesigned",
                             "Adjacent hinge pairs and static-static excluded; no mechanical fit or containment proof",
                             "Discrete surface contacts, not continuous collision or positive clearance",
                             "No native Blender candidate, fit, independent holdout, or hinge alignment proof; tilt preserves open vertical placement only"])
if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a=p.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(run(a.dir),indent=2))
