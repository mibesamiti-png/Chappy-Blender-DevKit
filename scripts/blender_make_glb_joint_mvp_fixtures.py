"""CBDK-owned, small, joint-like multipart GLB regression fixtures.

No user models, user addons, downloaded assets or Blender Python auto-execution.
The three mesh parts are a hollow socket ring, a faceted ball and a shaft.
Only one feature changes in each baseline test variant. The explicitly
named narrow_placebo changes an unrelated ball position while deliberately
keeping the narrow socket, exclusively for the GLB-021 controlled experiment.
All synthetic files remain in the temporary CI workspace.
"""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

import bpy

SEGMENTS = 12
SOCKET_OPENING_REFERENCE = 1.70
SOCKET_OPENING_DEFECT = 0.78
SOCKET_OPENING_INTERMEDIATE = 1.24


def _generated_grid_values():
    """Only four fixed, arithmetic CBDK synthetic conditions (not user input)."""
    return tuple(Decimal(78 + step * 23) / 100 for step in range(1, 5))


def _mesh(name, coords, triangles):
    mesh = bpy.data.meshes.new(name + "_synthetic_mesh")
    mesh.from_pydata(coords, [], triangles)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.select_set(True)
    return obj


def _ring(*, socket_opening_diameter=SOCKET_OPENING_REFERENCE,
          missing_face=False, grid_only=False):
    """Four concentric 12-vertex rings form an annular hollow socket.

    Only the CBDK-owned explicit 0.78/1.70 synthetic control values are
    accepted; never take or execute arbitrary addon settings as fixture code.
    """
    allowed = ((SOCKET_OPENING_REFERENCE, SOCKET_OPENING_DEFECT,
                SOCKET_OPENING_INTERMEDIATE) if not grid_only
               else tuple(float(v) for v in _generated_grid_values()))
    if (type(socket_opening_diameter) not in (float, int) or
            socket_opening_diameter not in allowed):
        raise ValueError("Synthetic socket experiment value is not allowlisted")
    outer, inner = 1.30, float(socket_opening_diameter) / 2.0
    levels = [(outer, -0.60), (inner, -0.60),
              (outer, 0.60), (inner, 0.60)]
    vertices = [
        (radius * math.cos(math.tau * i / SEGMENTS),
         radius * math.sin(math.tau * i / SEGMENTS), z)
        for radius, z in levels for i in range(SEGMENTS)
    ]
    triangles = []

    def face_band(first, second, *, remove_first=False):
        for i in range(SEGMENTS):
            if remove_first and i == 0:
                continue
            j = (i + 1) % SEGMENTS
            a, b = first * SEGMENTS + i, first * SEGMENTS + j
            c, d = second * SEGMENTS + i, second * SEGMENTS + j
            triangles.extend([(a, b, c), (b, d, c)])

    face_band(0, 1)                  # bottom annular face
    face_band(0, 2)                  # outer cylinder
    face_band(1, 3)                  # inner cylinder
    face_band(2, 3, remove_first=missing_face)  # top lip/cap
    return vertices, triangles


def _ball(*, shifted=False):
    x = 3.80 + (1.10 if shifted else 0.0)
    r = 0.63
    coords = [
        (x, 0.0, r), (x, 0.0, -r),
        (x - r, 0.0, 0.0), (x + r, 0.0, 0.0),
        (x, -r, 0.0), (x, r, 0.0),
    ]
    triangles = [
        (0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2),
        (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5),
    ]
    return coords, triangles


def _shaft():
    x, radius, bottom, top = 3.80, 0.22, -1.72, -0.70
    coords = [
        (x + radius * math.cos(math.tau * i / SEGMENTS),
         radius * math.sin(math.tau * i / SEGMENTS), z)
        for z in (bottom, top) for i in range(SEGMENTS)
    ]
    tris = []
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        tris.extend([(i, j, SEGMENTS + i),
                     (j, SEGMENTS + j, SEGMENTS + i)])
    # Both cylinder caps must be closed in the nominal/negative control.
    # Otherwise the baseline would *correctly* report open edges.
    bottom_center, top_center = len(coords), len(coords) + 1
    coords.extend([(x, 0.0, bottom), (x, 0.0, top)])
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        tris.append((bottom_center, j, i))
        tris.append((top_center, SEGMENTS + i, SEGMENTS + j))
    return coords, tris


def export(target, variant, *, grid_diameter=None):
    if variant not in {"reference", "identical", "narrow", "shifted", "uncapped", "narrow_placebo",
                       "narrow_mid", "narrow_mid_shifted", "grid_candidate"}:
        raise RuntimeError("Invalid fixture variant")
    if (variant == "grid_candidate") != (grid_diameter is not None):
        raise RuntimeError("Grid value is required only for grid_candidate")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ring = _ring(socket_opening_diameter=(
        grid_diameter if variant == "grid_candidate" else
        SOCKET_OPENING_DEFECT if variant in {"narrow", "narrow_placebo"}
        else SOCKET_OPENING_INTERMEDIATE if variant in {"narrow_mid", "narrow_mid_shifted"}
        else SOCKET_OPENING_REFERENCE
    ), missing_face=variant == "uncapped", grid_only=variant == "grid_candidate")
    ball = _ball(shifted=variant in {"shifted", "narrow_placebo", "narrow_mid_shifted"})
    _mesh("CBDK_SYNTH_Ball", *ball)
    _mesh("CBDK_SYNTH_Shaft", *_shaft())
    _mesh("CBDK_SYNTH_Socket", *ring)
    total = sum(len(obj.data.polygons) for obj in bpy.context.scene.objects
                if obj.type == "MESH")
    if not 1 <= total <= 512:
        raise RuntimeError("Joint fixture triangle cap exceeded")
    bpy.ops.export_scene.gltf(filepath=str(target), export_format="GLB",
                              use_selection=True)
    if not target.is_file() or target.stat().st_size < 100:
        raise RuntimeError("Synthetic joint GLB export failed")


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Expected trusted fixture output directory")
    args = sys.argv[sys.argv.index("--") + 1:]
    allowlist = ("reference", "identical", "narrow", "shifted", "uncapped",
                 "narrow_placebo", "narrow_mid", "narrow_mid_shifted")
    grid_diameter = None
    if len(args) == 1:
        variants = allowlist
    elif len(args) == 3 and args[1] == "--single" and args[2] in allowlist:
        # GLB-022's fixed trial runner regenerates each candidate in turn.
        # Arbitrary source scripts / numeric values are not supported.
        variants = (args[2],)
    elif (len(args) == 5 and args[1:4] ==
          ["--single", "grid_candidate", "--socket-diameter"]):
        # This is a bounded test fixture, not a free-form numeric input API.
        try:
            raw = Decimal(args[4])
        except (InvalidOperation, ValueError):
            raise RuntimeError("Invalid synthetic grid value") from None
        if raw not in _generated_grid_values() or str(raw) != f"{raw:.2f}":
            raise RuntimeError("Out-of-grid synthetic socket value refused")
        grid_diameter = float(raw)
        variants = ("grid_candidate",)
    else:
        raise RuntimeError("Only CBDK-owned allowlisted synthetic trial IDs accepted")
    out = Path(args[0]).absolute()
    if out.is_symlink() or out.exists():
        raise RuntimeError("Synthetic output directory must be new")
    out.mkdir(parents=True, exist_ok=False)
    for variant in variants:
        target = out / (variant + ".glb")
        if target.exists() or target.is_symlink():
            raise RuntimeError("Never overwrite source GLB")
        export(target, variant, grid_diameter=grid_diameter)
    print("CBDK_JOINT_MVP_FIXTURES_PASS")


if __name__ == "__main__":
    main()
