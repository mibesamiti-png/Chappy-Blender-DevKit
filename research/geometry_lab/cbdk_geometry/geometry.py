"""Floating point SAT experiments; not exact arithmetic or an IPC implementation."""
from dataclasses import dataclass
from collections import Counter
from itertools import combinations
import math
import numpy as np


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    faces: np.ndarray

    def __post_init__(self):
        v = np.array(self.vertices, dtype=float, copy=True)
        raw = np.asarray(self.faces)
        if v.ndim != 2 or v.shape[1] != 3 or not np.isfinite(v).all():
            raise ValueError('finite Nx3 vertices required')
        if raw.ndim != 2 or raw.shape[1] != 3 or raw.dtype.kind not in 'iu':
            raise ValueError('integer Mx3 triangles required')
        if len(raw) > 20000 or len(v) > 60000:
            raise ValueError('mesh budget exceeded')
        f = np.array(raw, dtype=np.int64, copy=True)
        if not len(f) or f.min() < 0 or f.max() >= len(v):
            raise ValueError('empty or invalid face indices')
        if any(len(set(t)) != 3 for t in f):
            raise ValueError('repeated face indices')
        t = v[f]
        lengths = np.linalg.norm(t[:, 1:] - t[:, :1], axis=2)
        area2 = np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1)
        if np.any(area2 <= 1e-12 * np.max(lengths, axis=1)**2):
            raise ValueError('degenerate or nearly degenerate triangle')
        v.setflags(write=False)
        f.setflags(write=False)
        object.__setattr__(self, 'vertices', v)
        object.__setattr__(self, 'faces', f)


def overlap(a, b, eps):
    """Separating-axis test including in-plane axes for coplanar triangles."""
    ea = np.roll(a, -1, axis=0) - a
    eb = np.roll(b, -1, axis=0) - b
    na, nb = np.cross(ea[0], ea[1]), np.cross(eb[0], eb[1])
    na /= np.linalg.norm(na)
    nb /= np.linalg.norm(nb)
    ea /= np.linalg.norm(ea, axis=1)[:, None]
    eb /= np.linalg.norm(eb, axis=1)[:, None]
    axes = np.vstack((na, nb, np.cross(ea[:, None], eb).reshape(-1, 3),
                      np.cross(na, ea), np.cross(nb, eb)))
    lengths = np.linalg.norm(axes, axis=1)
    axes = axes[lengths > 1e-12] / lengths[lengths > 1e-12, None]
    # Recenter to avoid amplification of large absolute coordinates.
    pa, pb = (a-a[0]) @ axes.T, (b-a[0]) @ axes.T
    return not np.any((pa.max(0) < pb.min(0)-eps) | (pb.max(0) < pa.min(0)-eps))


def candidates(triangles, method, eps):
    if method == 'brute':
        yield from combinations(range(len(triangles)), 2)
    elif method == 'sweep':
        lo, hi = triangles.min(1), triangles.max(1)
        active = []
        for i in np.argsort(lo[:, 0], kind='stable'):
            active = [j for j in active if hi[j, 0] >= lo[i, 0]-eps]
            for j in active:
                if np.all(hi[j] >= lo[i]-eps) and np.all(hi[i] >= lo[j]-eps):
                    yield min(int(i), int(j)), max(int(i), int(j))
            active.append(int(i))
    else:
        raise ValueError('unknown method')


def detect(mesh, method='sweep', tolerance=1e-9, pair_budget=2000000):
    """Contacts count as hits for nonadjacent faces.

    Adjacent triangles are inset by 1e-7 of their local size to exclude their
    expected shared simplex. This is an explicitly approximate diagnostic:
    very small overlap near shared vertices/edges may be missed.
    """
    if not math.isfinite(tolerance) or tolerance <= 0 or pair_budget < 1:
        raise ValueError('positive tolerance/budget required')
    t = mesh.vertices[mesh.faces]
    scale = float(np.max(np.ptp(mesh.vertices, axis=0)))
    eps = tolerance * scale
    hits, tested, adjacent = [], 0, 0
    for i, j in candidates(t, method, eps):
        tested += 1
        if tested > pair_budget:
            return dict(status='budget_exceeded', pairs=None, tested=tested-1,
                        adjacent_tests=adjacent, certified=False)
        a, b = t[i], t[j]
        common = set(mesh.faces[i]) & set(mesh.faces[j])
        if common and len(common) < 3:
            adjacent += 1
            a = a + 1e-7 * (a.mean(0)-a)
            b = b + 1e-7 * (b.mean(0)-b)
            local_eps = min(eps, 1e-10 * max(np.ptp(a, axis=0)))
        else:
            local_eps = eps
        if overlap(a, b, local_eps):
            hits.append((i, j))
    return dict(status='measured', pairs=sorted(hits), tested=tested,
                adjacent_tests=adjacent, certified=False)


def guarded_step(mesh, displacement, max_halvings=20):
    """Conservative swept-AABB guard for independent triangle soups ONLY.

    The swept boxes enclose all linear vertex trajectories. Overlapping boxes
    cause backtracking even if triangles never touch. No sampled-time CCD claim.
    Shared-index meshes are rejected: adjacency needs a proper CCD backend.
    """
    d = np.asarray(displacement, dtype=float)
    if d.shape != mesh.vertices.shape or not np.isfinite(d).all():
        raise ValueError('invalid displacement')
    if not isinstance(max_halvings, int) or not 0 <= max_halvings <= 30:
        raise ValueError('invalid iteration budget')
    if len(mesh.faces) > 512:
        raise ValueError('motion face budget exceeded')
    if len(np.unique(mesh.faces)) != mesh.faces.size:
        raise ValueError('shared-index motion requires CCD backend')
    initial = detect(mesh)
    if initial['status'] != 'measured' or initial['pairs']:
        return dict(status='initial_collision', alpha=0.0, mesh=mesh)
    t = mesh.vertices[mesh.faces]
    eps = max(np.ptp(mesh.vertices, axis=0)) * 1e-9
    for k in range(max_halvings+1):
        alpha = 2.0**-k
        v = mesh.vertices + alpha*d
        target = v[mesh.faces]
        lo = np.minimum(t.min(1), target.min(1))
        hi = np.maximum(t.max(1), target.max(1))
        if all(np.any(hi[i] < lo[j]-eps) or np.any(hi[j] < lo[i]-eps)
               for i, j in combinations(range(len(t)), 2)):
            try:
                result = Mesh(v, mesh.faces)
            except ValueError:
                continue
            return dict(status='accepted', alpha=alpha, mesh=result)
    return dict(status='blocked', alpha=0.0, mesh=mesh)


def quality(mesh):
    t = mesh.vertices[mesh.faces]
    cross = np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0])
    area = np.linalg.norm(cross, axis=1)/2
    edges = Counter(tuple(sorted((int(a), int(b)))) for f in mesh.faces
                    for a, b in zip(f, np.roll(f, -1)))
    graph = {int(i): set() for i in np.unique(mesh.faces)}
    for a, b in edges:
        graph[a].add(b)
        graph[b].add(a)
    unseen, components = set(graph), 0
    while unseen:
        stack = [unseen.pop()]
        components += 1
        while stack:
            for j in graph[stack.pop()] & unseen:
                unseen.remove(j)
                stack.append(j)
    e2 = ((np.roll(t, -1, axis=1)-t)**2).sum((1, 2))
    centered = t - mesh.vertices.mean(0)
    volume = abs(float(np.einsum('ij,ij->i', centered[:, 0],
                 np.cross(centered[:, 1], centered[:, 2])).sum()/6))
    return dict(triangles=len(t), boundary_edges=sum(n == 1 for n in edges.values()),
                nonmanifold_edges=sum(n > 2 for n in edges.values()),
                components=components, volume=volume,
                min_triangle_quality=float(np.min(4*np.sqrt(3)*area/e2)))
