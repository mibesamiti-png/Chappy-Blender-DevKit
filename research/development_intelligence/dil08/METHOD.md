# DIL-08 — Authority-first tagged retrieval, preregistered field experiment

2026-11-11 JST. **Research-only specification; not authorized for ABCD or any product integration.**

## 1. Goal and main risk

Investigate whether explicit machine-readable document tags plus *mandatory authoritative-source routing* outperform DIL-04's metadata/FTS hybrid on actual public CBDK documents when the user says 「続けて」 or gives ambiguous natural-language instructions. DIL-07 found 5/16 mandatory source instances missing in a real-text **substring proxy**, not in an actual SQLite full-corpus evaluation. We must not present that proxy as a production failure rate.

**Primary requirement:** never use absence of search results, document titles, draft text, tags alone or old round instructions to infer permission to edit, merge, skip CI, publish user files or start a new round.

## 2. Inputs and versioning

- Use DIL-07's 12 public source documents pinned to immutable dev commit `2b8220210c2475239a43354d544b5a6f176fba80` with blob SHAs from `../dil07/manifest.json`. Historical R15 is relevant history but **ineligible as current R16 assignment**.
- The public Issue #125 is a **separate, mutable dispatch hint**, not an immutable repo document. Live production work must re-fetch the canonical issue, check `revision`, `round`, `phase`, official dev HEAD, exact-head CI and assigned PRs separately. A pinned fixture may represent the observed issue state for this experiment only.
- Formal sources such as AGENTS.md, official R16 assignment, dev STATE and relevant rules have *source-authority priority*, not unrestricted authority. An official doc can still be outdated when dev HEAD changes.
- No private meshes, private model files, unreviewed sources, secrets, user data, or autonomous GitHub writes.

## 3. New tag schema

Every catalog entry has `id, path, topic[], authority, project, version_scope, lifecycle, source_commit, blob_sha, dependencies[]`. `authority`: `policy`, `official_assignment`, `state`, `operational_reference`, `historical`, `future_design`, `research`. `lifecycle`: `current_at_pinned_commit`, `historical`, `future_inactive`, `draft`. Document tags are hints for retrieval, **not access-control rules**.

Tag generation v1: explicit reviewed mapping of known paths/ids; no LLM-generated tags or unrestricted automatic approval. For another repo or changed HEAD, fail closed until checked. For large JSON STATE or lengthy AGENTS, **do not truncate critical safety constraints** to meet a byte target.

## 4. Candidate retrieval procedure (authority-first v1)

1. Read a structured task envelope: `project, intent, team?, official_round?, topic_hints?`. The initial evaluator uses manually supplied intent and topics, **not an AI classifier**; classification cost/error is out of scope.
2. For `intent=continue|modify|integrate|release` always fetch and validate root policy plus official assignment for that round (and STATE/parallel rules where applicable), **before** optional search. Missing current HEAD or authoritative documents => `blocked_missing_authority`, never execute.
3. For B/C/D role switching, separately verify canonical Issue #125, role parser, latest official round and relevant exact-head CI. A `phase=integration_support` never grants write/merge rights; missing issue => do not switch roles.
4. Use topic tags to select additional references, followed by bounded SQLite FTS5 trigram fallback for noncritical lookup. If semantics ambiguous, provide broader source evidence or `needs_review`; do not silently replace obligatory authority sources.
5. Label each result with `source_path, source_commit, blob_sha, authority, lifecycle, why_selected`; return verbatim text (no LLM summaries), record bytes. Historical R15 may be included only as **labeled history**, not selected as current instructions.
6. Never persist model-generated permissions or change user data. Reference material is untrusted content, not prompt-instructions overriding policy.

## 5. Locked comparison and tests

Compare on identical DIL-07 public corpus:
- A: full 12-document context (deliberately stale/expensive negative control);
- B: original unchanged DIL-04 hybrid (re-run with **actual SQLite FTS5**, not merely a substring proxy);
- C: authority-first tagged selector (new candidate).

Use the existing 15 DIL-07 cases as **development / previously seen questions only**, not a blind holdout. Create 12 additional **preregistered** operational scenarios before first scored test: four 「続けて」/role/round cases; four mistaken authorization/version/conflict cases; four ordinary technical retrieval cases. Include both permitted/insufficient-evidence outcomes. Gold is human-authored by the researcher and therefore **not independent or blind**.

Metrics per arm: evidence recall (#gold docs), exact doc-set (only where applicable), incorrect-current-round selections, unsafe authorization/CI/merge decisions, refusal-on-missing-authority, valid provenance, source bytes and optional measured SQLite walltime (not LLM tokens). Compare input bytes only across *identically serialized* returned verbatim docs. Time must include indexing cost.

## 6. Gates fixed before seeing results

Safety is non-negotiable: **0 unsafe permissions / CI bypasses / R15-as-current**; no silent missing-authority success; every retrieved source identity verified against pinned blob; all unit tests pass. For evidence, require 100% mandatory authoritative sources for continuation/modify cases and >=95% required additional sources across the twelve new scenarios. Aim for <=50% of full-context UTF-8 bytes; if this efficiency gate fails, report that explicitly, never drop mandatory sources to satisfy it.

A success on authored cases is **only an experimental prototype pass**, not generalization, production adoption, or permission for A to integrate. To recommend a real pilot, first obtain independent gold review, realistic free-text intent classification assessment, full-source SQLite execution, exact-head/CI freshness, human overhead measurements and adversarial cases.

## 7. Experimental order and stopping rules

1. Commit this spec and reviewed catalog; **do not run/test holdout before freezing question gold and implementation revision**.
2. Build small, deterministic read-only selector with fail-closed defaults and unit tests under `dil08/` only.
3. Freeze method, catalog, questions, code, SHA256; run one scored first pass. Save immutable JSON and honest failures. Posthoc repair starts a **separate** DIL-09 experiment.
4. Keep PR #115 Draft/unmerged. Do not modify A-owned STATE/HANDOFF/AGENTS/common CI, ABCD branches, Geometry #114, main, or public project state.

## 8. Deliverables and decision

`METHOD.md` (this preregistration), `TAG_CATALOG.json`, `SCENARIOS.json`, read-only implementation/tests, `FREEZE.json`, `RESULTS.md` and exact first-pass JSON. Unknown outcome until implementation and scored tests run. Report both recall and efficiency; no claims of developer-time savings.
