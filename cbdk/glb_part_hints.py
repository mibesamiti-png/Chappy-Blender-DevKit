"""Review-only, anonymous GLB part-size candidate hints.

Triangle counts are not shape fingerprints. Only unique equal counts in
complete inventories can be surfaced as weak inspection candidates.
No names, coordinates, paths, or source code are stored here.
"""
from __future__ import annotations

from collections import Counter

MAX_LISTED = 32


def count_based_part_hints(reference_counts, candidate_counts, *,
                           reference_total=None, candidate_total=None):
    """Return bounded weak hypotheses; never assert object correspondence."""
    for label, counts, total in (
        ("reference", reference_counts, reference_total),
        ("candidate", candidate_counts, candidate_total),
    ):
        if (not isinstance(counts, list) or len(counts) > MAX_LISTED
                or any(isinstance(x, bool) or not isinstance(x, int) or x < 0
                       for x in counts)):
            raise ValueError(label + " counts must be bounded nonnegative integers")
        if (total is None or isinstance(total, bool)
                or not isinstance(total, int) or total < len(counts)
                or len(counts) != min(total, MAX_LISTED)):
            raise ValueError(label + " total disagrees with listed counts")

    complete = reference_total <= MAX_LISTED and candidate_total <= MAX_LISTED
    left, right = Counter(reference_counts), Counter(candidate_counts)
    unique = sorted(
        n for n in left.keys() & right.keys()
        if left[n] == 1 and right[n] == 1 and n > 0
    ) if complete else []
    return {
        "kind": "cbdk_anonymous_part_count_hints",
        "status": "review_only" if complete else "insufficient_inventory",
        "basis": "unique_equal_triangle_count_only",
        "weak_candidate_triangle_counts": unique,
        "candidate_count": len(unique),
        "complete_inventories": complete,
        "correspondence_verified": False,
        "shape_equivalence_verified": False,
        "identifies_changed_part": False,
        "auto_apply": False,
        "notes": "Count equality is not object or geometry identity",
    }
