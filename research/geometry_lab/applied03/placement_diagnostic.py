"""Applied03: frozen evaluated-mesh placement diagnostic; no Blender redesign."""
import argparse
import itertools
import json
from pathlib import Path
import numpy as np
from applied02.contact_diagnostic import transformed, hit_pairs, intended_pair

# Per side (rear mm, vertical mm), frozen before observing actual mesh results.
CANDIDATES = {
    "baseline": ((0, 0), (0, 0)),
    "rear6": ((6, 0), (6, 0)),
    "depth_stagger": ((6, 0), (12, 0)),
    "vertical_stagger": ((6, 3), (6, -3)),
    "combined": ((6, 3), (12, -3)),
}
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
        return (name, 0, (0, 0))
    def geometry(k):
        if k not in triangles:
            name, a, (dy, dz) = k
            m = base[name]
            v = transformed(m, a, a) + np.array([0., dy/1000., dz/1000.])
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
        pair_counts = {x+"+"+y: sum(x+"+"+y in row["nonexempt_surface_contacts"] for row in rows)
                       for x,y in pairs}
        result[label] = dict(offset_mm=[dr,dl], states_with_contact=count,
                             open_contacts=rows[0]["nonexempt_surface_contacts"],
                             pair_pose_counts={k:v for k,v in pair_counts.items() if v}, rows=rows)
        print("APPLIED03", label, count, result[label]["pair_pose_counts"], flush=True)
    return dict(approved=False, diagnostic_only=True, states=84, pairs=24,
                baseline_reproduced=True, candidates=result,
                limitations=["Rigid offset of all moving meshes only; fixed pin/endpiece not redesigned",
                             "Adjacent hinge pairs and static-static excluded; no mechanical fit or containment proof",
                             "Discrete surface contacts, not continuous collision or positive clearance",
                             "No native Blender candidate, open fit or independent holdout"])
if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a=p.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(run(a.dir),indent=2))
