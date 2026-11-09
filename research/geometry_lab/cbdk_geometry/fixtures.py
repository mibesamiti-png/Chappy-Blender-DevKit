"""Authored synthetic fixtures only; no input files or model loaders."""
import numpy as np
from .geometry import Mesh


def pair(kind='cross', scale=1.0):
    a = [[0, 0, 0], [2, 0, 0], [0, 2, 0]]
    cases = {
        'cross': [[.5, .5, -1], [.5, .5, 1], [1.5, .5, 0]],
        'separate': [[0, 0, 1], [2, 0, 1], [0, 2, 1]],
        'coplanar': [[.2, .2, 0], [1.2, .2, 0], [.2, 1.2, 0]],
        'coplanar_separate': [[3, 3, 0], [4, 3, 0], [3, 4, 0]],
        'touch': [[2, 0, 0], [3, 0, 0], [2, 1, 0]],
        'near_miss': [[0, 0, 1e-6], [2, 0, 1e-6], [0, 2, 1e-6]],
    }
    return Mesh(np.array(a+cases[kind])*scale, [[0, 1, 2], [3, 4, 5]])


def soup(n, seed=17):
    rng = np.random.default_rng(seed)
    centers = rng.uniform(-10, 10, (n, 1, 3))
    triangles = centers + rng.normal(0, .15, (n, 3, 3))
    return Mesh(triangles.reshape(-1, 3), np.arange(n*3).reshape(-1, 3))


def sphere(center=(0, 0, 0), radius=1, segments=24, rings=12):
    """Outward-oriented UV sphere with unique poles, no degenerate pole quads."""
    from math import sin, cos, pi
    v = [(0, 0, radius)]
    for j in range(1, rings):
        for i in range(segments):
            p, t = pi*j/rings, 2*pi*i/segments
            v.append((radius*sin(p)*cos(t), radius*sin(p)*sin(t), radius*cos(p)))
    bottom = len(v)
    v.append((0, 0, -radius))
    f = []
    for i in range(segments):
        q = (i+1) % segments
        f.append((0, 1+i, 1+q))
        for j in range(rings-2):
            a, b = 1+j*segments+i, 1+j*segments+q
            f.extend(((a, a+segments, b+segments), (a, b+segments, b)))
        f.append((bottom, 1+(rings-2)*segments+q, 1+(rings-2)*segments+i))
    return Mesh(np.array(v)+center, f)
