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

## Windows checkout evidence and isolated unit-test copy
Initial HEAD 5504109b: Windows 45764885697 failed four R27 setUp checks
in each Python version, observed actual checkout SHA
eec6968b7cb5208e0af92279b7b32dc0c8d617ebad6d1cdbb5ca39cc64d1918f
(artifact 15090724909). Reproduced by translating the 2321-byte canonical
LF fixture to CRLF (2388 bytes). Strict helper must reject this checkout;
never normalize production bytes. B tests now explicitly reject the known
CRLF checkout and use a separate exact-SHA test copy via scoped mocks of
the two fixture paths, without changing checkout bytes; also reject an
explicit CRLF negative control on every OS. Unexpected digest fails.
A owns shared checkout configuration: recommend a targeted .gitattributes
entry `fixtures/cbdk_parameter_experiment.py text eol=lf` and confirm real
checkout SHA in the integrated Windows job. B does not edit shared settings.
Native execution/restoration remains C/A scope. New CI pending.
