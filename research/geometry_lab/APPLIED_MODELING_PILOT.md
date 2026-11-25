# Applied modeling pilot — phase one handoff (2026-11-25)

Status: proposed bounded experiment, research only; approved=false for product. Geometry Lab phase one closed; no R23 by default. DIL remains under its existing owner and its [DIL-09 status](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/blob/69dce01fa36b485dbaad6486c219157b665cd4c4/research/development_intelligence/dil09/STATUS.md): no research expansion, no new mandatory A work, no new authority. Existing DIL task workflow may be used on one actual owner-approved code task. No new Garment Lab or mandatory management layers.

## What to test
Use a single synthetic garment modeling task: a basic sewn-panel bra with separately editable cup, bridge, band, straps and back closure. This is a practical test of decomposition and method choice, not a requirement that every bra use separate cups. Compare against a simple continuous-shell sports-bra design only as a planning contrast, not an aesthetic score between unlike garments. Do not copy reference mesh topology or claim the private reference was independently evaluated in Blender. No private reference assets, filenames, geometry or derived data are to be committed or published. Public fixtures must be wholly synthetic.

## Existing techniques, chosen conditionally
- DIL: decide part boundaries, interfaces, dependencies, choice of generator, completion criteria and evidence. Record short rationale and a fallback where needed, not a new planner framework.
- Geometry Lab: reuse frozen operations only for matching preconditions. R10/R16/R17/R20/R21 concern compatible annular bridge geometry and rectangular pinned UV charts; do not force them onto arbitrary cup, lace, strap or garment seam. Use patch grids for cups, swept curves for straps, band loft or grid for continuous cloth, independent hardware meshes where appropriate. Preserve separate pieces when the construction requires it. A continuous sports top may use a different construction.
- Validation: actual geometry, part editability (change one cup or strap parameter and test dependencies), source/interface preservation, expected boundary/topology, UV per intended island/overlap policy, intersection checks with intentional contacts distinguished from unwanted penetration, actual Blender roundtrip and front/back/side views. Measure total work/time if available; no claimed speedup without comparable measurements. Visual judgement remains separate from numeric metrics.
- Deliver a small editable synthetic sample and recorded failure causes; do not require production completeness, rigging, fit, or all garment types. Classify issues as planning/choice, geometry operation, integration, or visual/fit gap. Stop after one task and decide from observed evidence whether more research is warranted. No new research round automatically.

## Scope
Geometry Lab owns this note only. No DIL branch changes, no assignments to A/B/C/D, no shared STATE/HANDOFF, no product merge or rollout. Use private files locally only with user's explicit permission for any external sharing. Current evidence: R22 corrected job 138903546091, R21 first frozen gate 8/8 safe and 5/8 improved, R19 failure retained; see cycles/r22/RESULTS.md. DIL may read this note; it is not a task queue or a formal adoption request.


## Applied 01 outcome — closed

[Actual results](applied01/RESULTS.md) / [status](applied01/STATUS.json). Native Blender validation and metric UV correction passed (14/14); only expected two parts change. The default square chart was an identified planning error. Visual quality, budget and garment fit remain separate, unproven. No new task by default; no DIL workload or production adoption.
