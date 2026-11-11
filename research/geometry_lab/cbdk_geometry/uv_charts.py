"""R12 research-only per-triangle UV chart propagation from boundary constraints.

This is deliberately NOT harmonic/LSCM, minimal seam, nor continuous parametrization.
It keeps given 3D triangles fixed, and only supplies constant UV translations per
face. Conflicting boundary constraints are reported, never silently averaged.
"""
from collections import defaultdict
import heapq
import numpy as np


def label_chart_offsets(vertices, faces, boundary_offsets, tolerance=1e-5):
    """Return (Nx2 offsets, metrics) for every triangle.

    boundary_offsets: {(vertex_id_min,vertex_id_max): (du,dv)} read from
    actual existing Blender source *face-corner* UV. All strip boundary edges
    must be represented. Face-labelled multi-source BFS is deterministic.
    """
    v=np.asarray(vertices,dtype=float)
    f=np.asarray(faces,dtype=int)
    if v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3:
        raise ValueError("R12 requires XYZ vertices and triangle faces")
    edges=defaultdict(list)
    for i,tri in enumerate(f):
        for a,b in zip(tri,np.roll(tri,-1)):
            a,b=int(a),int(b)
            edges[tuple(sorted((a,b)))].append(i)
    boundaries={edge:refs[0] for edge,refs in edges.items() if len(refs)==1}
    if set(boundary_offsets)!=set(boundaries):
        raise ValueError("missing or unexpected boundary UV constraints")
    fixed={}
    for edge in sorted(boundaries):
        face=boundaries[edge]
        offset=np.asarray(boundary_offsets[edge],dtype=float)
        if offset.shape!=(2,) or not np.isfinite(offset).all():
            raise ValueError("nonfinite/invalid boundary UV translation")
        if face in fixed and np.max(np.abs(offset-fixed[face]))>tolerance:
            raise ValueError("conflicting boundary chart constraints on one triangle")
        fixed[face]=offset

    adjacency=[set() for _ in f]
    for refs in edges.values():
        if len(refs)==2:
            u,w=refs
            adjacency[u].add(w)
            adjacency[w].add(u)
        elif len(refs)>2:
            raise ValueError("nonmanifold strip cannot receive chart labels")
    output=np.zeros((len(f),2),dtype=float)
    visited=set()
    queue=[]
    for rank,(face,offset) in enumerate(sorted(fixed.items())):
        heapq.heappush(queue,(0,rank,face,tuple(float(x) for x in offset)))
    while queue:
        dist,rank,face,offset=heapq.heappop(queue)
        if face in visited:
            continue
        visited.add(face)
        output[face]=offset
        for neighbor in sorted(adjacency[face]):
            if neighbor not in visited:
                heapq.heappush(queue,(dist+1,rank,neighbor,offset))
    if len(visited)!=len(f):
        raise ValueError("disconnected face graph / no chart seed")
    for face,offset in fixed.items():
        if np.max(np.abs(output[face]-offset))>tolerance:
            raise RuntimeError("a fixed boundary constraint was not honored")
    seam_edges=[]
    seam_length=0.0
    interior=0
    for edge,refs in edges.items():
        if len(refs)!=2:
            continue
        interior+=1
        if np.max(np.abs(output[refs[0]]-output[refs[1]]))>tolerance:
            seam_edges.append(edge)
            a,b=edge
            seam_length+=float(np.linalg.norm(v[a]-v[b]))
    metrics=dict(boundary_count=len(boundaries),
                 chart_count=len({tuple(np.round(x,4)) for x in output}),
                 internal_edges=interior,
                 internal_seam_edges=len(seam_edges),
                 internal_seam_fraction=len(seam_edges)/interior if interior else 0.0,
                 internal_seam_length=seam_length)
    return output,metrics
