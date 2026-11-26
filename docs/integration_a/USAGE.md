# Bounded rotary integration preview

This is an unapproved development preview for a new artificial rotary joint.
It does not edit an existing model, install CJM, or grant redistribution rights.

## Local setup

Use this branch's checkout with Blender 4.4.3, 4.5.15 or 5.2.1. In Blender's
Python console, add the checkout directory to `sys.path`, then run:

```python
from parts.blender import joint_preview
joint_preview.register()
```

Open the 3D View sidebar's CBDK tab. Supply the original local CJM v0.4.2 ZIP
and a separate frozen GL `research/geometry_lab` snapshot. The connector accepts
only the reviewed ZIP digest and the four pinned GL source digests. No source
is fetched automatically. CJM is extracted into a temporary local directory and
imported without registering its addon. Do not load another CJM instance in the
same Blender process. After providers load, changes to either resolved source path
are refused; restart Blender to select other paths. This is session binding, not
hot reload or same-path file-change detection. Use a fresh synthetic scene; origin cursor, Object mode,
unit scale 1 are required. Coordinates are explicit internal world units, not
a claim of millimetres or manufacturing fit.

## Operations

The fixed artificial mechanism has Z axis, axle diameter 2, widths 3.5,
radial/axial clearance 0.4 and fixed wall/tip dimensions. Original outer diameter
defaults to 5, declared comparison target to 4. Only the outer diameter is allowed
to vary. This is an explicit design target, not an inferred optimum.

Select FREE, PREFERRED or LOCKED. Generate/inspect runs a baseline, a negative
direction control, a midpoint and a declared target through local CJM numerical
repair and the actual standalone rotary Boolean generator. GL checks each
evaluated indexed part separately. The CBDK reducer checks measured radial
dimensions, unchanged axial dimensions and the protected-scene signature.
Inter-part single-pose overlap is checked by the existing CJM generator.

The panel shows candidate IDs, measured error and acceptance/rejection reasons.
Choose the candidate row and explicitly adopt. Only this panel's diameter is
written after fresh geometry verification and RNA readback; generated trial
objects have already been deleted. This is dimension adoption, not a mesh commit.
Restore returns that dimension to its pre-run value. Adoption and restore use a separate UNDO-enabled operator; review, retry, rejection and cancellation are not explicitly added to native undo history. Undo/redo callbacks invalidate cached candidates and stop stale modal work; rerun before adopting. A previously blocked state is conservatively retained across history in this synthetic session. Ordinary Ctrl+Z / Ctrl+Shift+Z behavior remains unverified until interactive testing. Reject/cancel removes the
candidate authorization. Retry starts a fresh run. Editing inputs or the source
scene invalidates adoption. PREFERRED permits changing that dimension only
because every other dimension is fixed; the change remains explicit and visible.

Interactive execution yields between the baseline and candidates. Cancel or Esc
stops at the next boundary. Status stays RUNNING until the timer processes
cancellation; new runs, adoption, rejection and restoration are refused meanwhile.
Restore or retry explicitly after the previous operator ends. One Boolean or detector invocation is synchronous;
this is not preemptive cancellation inside Blender. GL is bounded to 512 triangles
per part, 200000 scanned pairs, cooperative 10 seconds. Unknown/timeout/missing
results fail closed. A cleanup or restoration failure latches BLOCKED; no retry
is permitted in that scene session. Diagnose it in a fresh synthetic process.

## Validation scope

The native smoke executes the actual provider chain with explicit pinned
arguments. Public CI now has the owner-authorized CJM ZIP and fetches the exact
frozen GL sources. The separate sentinel-only run still excludes providers.
The direct history-callback test is not an actual Undo/Redo test. A separate
isolated background history experiment uses a single explicit baseline push,
the actual ADOPT operator and native ed.undo/redo (no post-adopt manual push).
It compares semantic scene content rather than RNA pointers after traversal.
Its report may be passed, failed or unavailable; failure/unavailability does
not count as success or release approval. The GUI gate remains separate.
Native `Panel.draw` and operators are not Windows mouse/keyboard or Ctrl+Z proof.
Continuous collision, arbitrary models, physical strength and printing remain
unverified. No core registry/recipe catalog automatically enables this preview.

```powershell
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/blender_joint_integration_smoke.py -- --cjm-zip <local-original.zip> --gl-root <frozen-GL-folder> --output <fresh-local-result.json>
```

Remove the preview with `joint_preview.unregister()`. The numerical evaluator
`cbdk.joint_integration` is independent of Blender. It reuses R28/GLB-022 review
principles rather than their fixed sphere/cube schema, metrics or identities.
