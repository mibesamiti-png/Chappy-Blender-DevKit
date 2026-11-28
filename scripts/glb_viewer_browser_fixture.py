"""Generate only CBDK-authored synthetic browser data (never user GLBs)."""
from __future__ import annotations

from pathlib import Path
import sys

from cbdk.glb_diff_colors import classify_faces
from cbdk.glb_diff_viewer import render_local_diff_viewer


def triangle(x, z=0.0):
    return [(x, 0., z), (x + 1., 0., z), (x, 1., z)]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Provide a local temporary destination HTML path")
    target = Path(sys.argv[1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    reference = [triangle(0), triangle(3)]
    # Deliberately swapped part ordering with one shifted part.
    candidate = [triangle(3, .3), triangle(0)]
    values = classify_faces(reference, candidate)
    html = render_local_diff_viewer(
        reference, candidate,
        values["reference_labels"], values["candidate_labels"],
        [1, 1], [1, 1],
        # Synthetic UI injection only: exercises sensitivity-border toggle.
        sampling_flags={"reference": [True, False],
                        "candidate": [False, False]},
    )
    target.write_text(html, encoding="utf-8")
    assert len(html.encode("utf-8")) > 1000
    print("CBDK_BROWSER_SYNTHETIC_FIXTURE_PASS")


if __name__ == "__main__":
    main()
