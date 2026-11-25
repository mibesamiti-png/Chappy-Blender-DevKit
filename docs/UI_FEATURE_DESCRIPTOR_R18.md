# R18 C — code-owned feature descriptors and sixth authored feature

Candidate based on b32a9eb57d030e2144102623e8be57fda821bf0b. The existing five feature IDs and six checked-in legacy recipes are unchanged. Code-owned descriptors specify the source, parts, context mode, bounded UI hint, operator ID and optional known input contract. Recipe data cannot supply any of those executable contracts. Only selected descriptors and modules enter a ZIP. Existing UI safety guards, preview-only flags and typed nudge settings remain.

New `mesh_center` reports the midpoint of the existing world-aligned base-mesh bounding box, not the vertex centroid, object origin, or evaluated modifier geometry. The same BLCTX-001 and BLGEO-001 helpers are reused; no mesh mutation. The R18 native fixture extends the existing R17 entrypoint and independently checks the expected center on an asymmetric translated/scaled triangle, global/inline UI, execution, edit-mode refusal and cleanup. Static cases check exact selection, source/operator agreement, old five-feature recipe, and unknown/unselected/injected inputs.

## Legacy audit integration

A authorized C on PR #140 (comment 7152571199) to edit the shared recipe matrix and its tests. The six legacy recipe files, report rows/count and expected feature sets stay unchanged; a separate fixed synthetic R18 coverage section independently pins the sixth feature, exact dependency closure and all three target versions. All seven legacy helpers remain mandatory. The registration audit also builds the new synthetic example with the existing static checks. The legacy smoke script and workflow recipe inventory remain unchanged; new native markers use the existing R17 lifecycle entrypoint. No shared CLI/CI/parts/STATE/Handoff edits.

The first candidate failed with shared matrix coverage and legacy synthetic UI namespace errors. The second candidate fixed R2/R4; the remaining R3 namespace is corrected in the same batch as the authorized audit. Final exact-head CI and native evidence are required before completion. No real Windows GUI, arbitrary third-party addon, licensing or distribution claims.
