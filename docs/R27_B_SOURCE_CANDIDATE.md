# R27 B — fixed-source candidate and inverse

Base f3b0bcf234e5d0c38a148b62aa864db5a9025569; #125 revision 22 active.
Only the fixed repository fixture with the assignment SHA
e645723ff89a99530841e1ccd37ea8d059952eec0f980ac1782d8228e46588e3
is accepted. No arbitrary paths, patches or values; no file writes or code
execution. Reuse R26 fixed static helper and its existing property/usage/flow
analysis. Exact class/property/constructor, unique default token, untouched
bevel_width, same other bytes and same AST after replacing one constant.
Reverse bytes must equal original and original SHA. Checks of original before
and after do not establish authenticity or authority. Candidate is not an
approval, suggested optimal value, or general repair.

A internal contract:
`from cbdk.parameter_source_candidate_r27 import build_fixed_source_candidate, restore_fixed_source_candidate`
`candidate_bytes, observation = build_fixed_source_candidate(run_id=..., source_sha256=..., blender_version=...)`
Observation has case_id=parameter_source_r27, run_id, blender_version,
source_sha256, candidate_sha256, property=sphere_radius, before=0.75,
after=1.15, old_token="0.75", new_token="1.15", byte_offset (zero based),
single_difference_verified=true, restored_sha256.
`restore_fixed_source_candidate(candidate_bytes)` returns original bytes
only for the exact fixed candidate. Parent/C must independently verify the
actual executed copy; B never writes or executes it. The parent owns binding
B/C/D and actual original/candidate/restored measurements.
Tests: exact byte equality against independently constructed token replacement,
fixed identity/source digest, duplicate/other class/unknown default and old
token, wrong constructor, extra edits, wrong offset and invalid reverse.
Original source, seven variants, public API, shared CI, C/D unchanged.
Specialist CI pending; existing native 7-variant regression is not the new
isolated-copy execution or restoration proof.
