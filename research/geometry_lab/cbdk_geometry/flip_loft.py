"""R9 research-only conservative local diagonal flip over a detached R8 mesh.

Face-only operation. No vertex positions changed; no new vertices or triangles.
This heuristic is NOT guaranteed collision free: a separate CGAL oracle MUST run.
"""
from collections import defaultdict
from time import monotonic
import numpy as np

from .geometry import Mesh, quality
from .tapered_loft import tapered_radial_loft


def _normal(vertices, indices):
    p = vertices[indices]
    return np.cross(p[1]-p[0], p[2]-p[0])


def _triangle_quality(vertices, indices):
    p = vertices[indices]
    area2 = np.linalg.norm(np.cross(p[1]-p[0], p[2]-p[0]))
    sq_edges = np.sum((np.roll(p, -1, axis=0) - p)**2)
    return float(2*np.sqrt(3)*area2/sq_edges) if sq_edges > 0 else 0.0


def _one_pass(vertices, faces):
    # Each candidate is independent of the other chosen candidates in a pass.
    edges = defaultdict(list)
    for i, tri in enumerate(faces):
        for k in range(3):
            u, v = int(tri[k]), int(tri[(k+1) % 3])
            edges[tuple(sorted((u, v)))].append(
                (i, u, v, int(tri[(k+2) % 3])))
    proposals = []
    for edge, refs in edges.items():
        if len(refs) != 2:  # Includes the original boundary edges.
            continue
        (i,u,v,a),(j,vu,uu,b) = refs
        if (vu,uu) != (v,u) or a == b:
            continue
        # Never replace a diagonal with an edge already in use.
        if tuple(sorted((a,b))) in edges:
            continue
        oldq = min(_triangle_quality(vertices, faces[i]),
                   _triangle_quality(vertices, faces[j]))
        if oldq >= .30:
            continue
        n1 = _normal(vertices, faces[i])
        n2 = _normal(vertices, faces[j])
        m1, m2 = np.linalg.norm(n1), np.linalg.norm(n2)
        if min(m1,m2) < 1e-8 or np.dot(n1,n2) < .2*m1*m2:
            continue
        new_a = np.asarray((a,b,v),dtype=np.int64)
        new_b = np.asarray((b,a,u),dtype=np.int64)
        na = _normal(vertices,new_a)
        nb = _normal(vertices,new_b)
        ma,mb = np.linalg.norm(na),np.linalg.norm(nb)
        if min(ma,mb) < 1e-8:
            continue
        avg = n1/m1+n2/m2
        avglen = np.linalg.norm(avg)
        if (np.dot(avg,na) < .15*avglen*ma or
                np.dot(avg,nb) < .15*avglen*mb or
                np.dot(na,nb) < .2*ma*mb):
            continue
        newq = min(_triangle_quality(vertices,new_a),
                   _triangle_quality(vertices,new_b))
        if newq-oldq > 1e-4:
            proposals.append((oldq, -(newq-oldq), i,j,new_a,new_b))
    used = set()
    flipped = 0
    for oldq,neg_gain,i,j,new_a,new_b in sorted(proposals,key=lambda x:(x[0],x[1],x[2],x[3])):
        if i in used or j in used:
            continue
        # A previous disjoint candidate may have changed an adjacent edge;
        # never reuse a face, and recheck the old score deterministically.
        check = min(_triangle_quality(vertices,faces[i]),
                    _triangle_quality(vertices,faces[j]))
        if abs(check-oldq) > 1e-12:
            continue
        faces[i] = new_a
        faces[j] = new_b
        used.add(i)
        used.add(j)
        flipped += 1
    return flipped


def conservative_flip_loft(a, b, cuts=3, seconds=10.0):
    """Build frozen R8 then flip conservative internal diagonals, at most 3 passes."""
    if cuts != 3 or isinstance(seconds,bool) or not np.isfinite(seconds) or not 0 < seconds <= 60:
        raise ValueError("R9 fixes 3 cuts and requires 0 < seconds <= 60")
    begin = monotonic()
    base = tapered_radial_loft(a,b,cuts=3,seconds=seconds)
    mesh = base["mesh"]
    verts = mesh.vertices  # immutable; never changed
    faces = np.array(mesh.faces,copy=True)
    before_q = quality(mesh)["min_triangle_quality"]
    passes = 0
    flipped = 0
    for _ in range(3):  # predeclared research budget, no tuning
        changed = _one_pass(verts,faces)
        if not changed:
            break
        flipped += changed
        passes += 1
        if monotonic()-begin > seconds:
            raise TimeoutError("R9 geometry + local flip exceeded generation budget")
    result = Mesh(verts,faces)
    if (len(result.vertices)!=len(mesh.vertices) or
            len(result.faces)!=len(mesh.faces) or
            not np.array_equal(result.vertices,mesh.vertices)):
        raise RuntimeError("R9 face-only invariant violated")
    return dict(mesh=result,approved=False,method="conservative_flip_r9",
                flips=flipped,passes=passes,
                input_vertices_preserved=True,
                before_min_quality=float(before_q),
                after_min_quality=float(quality(result)["min_triangle_quality"]),
                added_vertices=base["added_vertices"],
                internal_counts=base["internal_counts"])
