"""NEXT-008: prioritize existing bidirectional observations, never infer causes.

No new surface algorithm or automatic part correspondence. A reference-only
observation must remain visible; equal anonymous IDs on two sides are unrelated.
"""
from __future__ import annotations

import json
from fractions import Fraction

from .glb_synthetic_conditions import aggregate_review_digest
from .glb_visual_property_review import _read_observations

KIND = "cbdk_glb_debug_focus_v1"
FLAGS = {"complete_geometry_proven": False, "part_identity_proven": False,
         "hole_location_proven": False, "executes_source": False,
         "applies_changes": False, "authenticates_evidence": False}


def _derive(observations, digest):
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)):
        raise ValueError("Invalid focus baseline digest")
    if not isinstance(observations, dict) or set(observations) != {"reference", "candidate"}:
        raise ValueError("Missing directional focus observations")
    for side, rows in observations.items():
        if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
            raise ValueError("Invalid focus part count")
        if sum(r.get("triangle_count", 0) for r in rows if isinstance(r, dict)) > 512:
            raise ValueError("Focus triangle budget exceeded")
        for index, row in enumerate(rows, 1):
            if (not isinstance(row, dict) or set(row) != {
                    "part_id", "triangle_count", "medium", "high", "boundary_edges", "tentative_peer"}
                    or row["part_id"] != f"part_{index:03d}"
                    or any(type(row[k]) is not int or row[k] < 0
                           for k in ("triangle_count", "medium", "high", "boundary_edges"))
                    or not 1 <= row["triangle_count"] <= 512
                    or row["medium"] + row["high"] > row["triangle_count"]
                    or row["boundary_edges"] > 3 * row["triangle_count"]):
                raise ValueError("Invalid anonymous focus observation")
    focus, protected = [], []
    for side, rows in observations.items():
        other = "candidate" if side == "reference" else "reference"
        peers = {r["part_id"]: r for r in observations[other]}
        for row in rows:
            peer_id = row["tentative_peer"]
            if peer_id is not None and (not isinstance(peer_id, str) or peer_id not in peers
                                       or peers[peer_id]["tentative_peer"] != row["part_id"]):
                raise ValueError("Nonreciprocal tentative focus association")
            reasons = []
            if row["medium"] + row["high"]:
                reasons.append("sampled_surface_difference")
            if peer_id is not None:
                if row["boundary_edges"] != peers[peer_id]["boundary_edges"]:
                    reasons.append("tentative_boundary_count_mismatch")
            elif row["boundary_edges"]:
                reasons.append("unpaired_boundary_observation")
            if reasons:
                focus.append({"side": side, **row, "reasons": reasons,
                              "observed_affected_fraction": round(
                                  (row["medium"] + row["high"]) / row["triangle_count"], 7)})
            else:
                protected.append({"side": side, "part_id": row["part_id"]})
    # Exact rational ordering avoids rounding ties; fractions are observations
    # of classified triangles, NOT area fractions, distances, or confidence.
    focus.sort(key=lambda r: (-(r["medium"] + r["high"] > 0),
                             -Fraction(r["high"], r["triangle_count"]),
                             -Fraction(r["medium"] + r["high"], r["triangle_count"]),
                             r["side"], r["part_id"]))
    return {"kind": KIND, "schema_version": 1, "status": "review_only",
            "baseline_review_sha256": digest, "observations": observations,
            "focus": focus, "no_observed_change_parts": protected,
            "priority_basis": "sampled_surface_then_high_fraction_then_affected_fraction",
            "fraction_is_surface_area": False, "safety": dict(FLAGS)}


def build_debug_focus(visual):
    _, _, associations = _read_observations(visual)
    reverse = {ref: cand for cand, ref in associations.items()}
    observations = {}
    for side in ("reference", "candidate"):
        peers = reverse if side == "reference" else associations
        observations[side] = [
            {"part_id": row["part_id"], "triangle_count": row["triangle_count"],
             "medium": row["medium"], "high": row["high"],
             "boundary_edges": edge["boundary_edges"],
             "tentative_peer": peers.get(row["part_id"])}
            for row, edge in zip(visual["parts"][side], visual["boundary_edge_audit"]["parts"][side])]
    return _derive(observations, aggregate_review_digest(visual))


def validate_debug_focus(report):
    try:
        expected = _derive(report["observations"], report["baseline_review_sha256"])
        if json.dumps(report, sort_keys=True, allow_nan=False) != json.dumps(
                expected, sort_keys=True, allow_nan=False):
            raise ValueError("Inconsistent focus review")
    except (KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid focus review") from exc
    return report
