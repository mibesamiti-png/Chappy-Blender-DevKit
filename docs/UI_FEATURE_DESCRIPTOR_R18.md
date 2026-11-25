# R18 C — code-owned feature descriptors and sixth authored feature

Candidate based on b32a9eb57d030e2144102623e8be57fda821bf0b. The existing five feature IDs and six checked-in legacy recipes are unchanged. Code-owned descriptors specify the source, parts, context mode, bounded UI hint, operator ID and optional known input contract. Recipe data cannot supply any of those executable contracts. Only selected descriptors and modules enter a ZIP. Existing UI safety guards, preview-only flags and typed nudge settings remain.

New `mesh_center` reports the midpoint of the existing world-aligned base-mesh bounding box, not the vertex centroid, object origin, or evaluated modifier geometry. The same BLCTX-001 and BLGEO-001 helpers are reused; no mesh mutation. The R18 native fixture extends the existing R17 entrypoint and independently checks the expected center on an asymmetric translated/scaled triangle, global/inline UI, execution, edit-mode refusal and cleanup. Static cases check exact selection, source/operator agreement, old five-feature recipe, and unknown/unselected/injected inputs.

## Shared A-owned integration blocker

`cbdk/recipe_matrix.py` explicitly requires `modular_all` and the six legacy recipes to cover *every* trusted feature. A must update that audit and its shared tests to distinguish the frozen five-feature legacy matrix from the new authored feature contract and R18 native fixture coverage. Do not change the existing recipes to include the sixth feature. The legacy smoke script's KNOWN inventory intentionally remains the original five; C-owned registration_audit checks it against LEGACY_FEATURE_IDS; the additional R18 native markers belong to the existing lifecycle lane. The shared audit must fail closed until the scope is updated. C did not edit shared CLI, matrix, CI, parts, STATE or Handoff.

No candidate test or native run is claimed yet. Candidate remains draft; official 5 CI and three native runs required before C completion. No real Windows GUI, arbitrary third-party addon, licensing or distribution claims.
