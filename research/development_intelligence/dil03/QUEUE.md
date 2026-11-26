# Development Intelligence Lab queue after DIL-03 (not started)

1. **DIL-04 — Lightweight evidence-based knowledge retrieval and handoff compression.** Compare no-index search, SQLite FTS5 and compact handoff data on independent labeled tasks; track recall of required constraints and input bytes, with real token counts only if available. Reuse #113 knowledge-intake provenance and avoid rewriting it. A remains owner of official HANDOFF.
2. **DIL-05 — ABCD waiting/duplicate CI reduction.** Reuse #109 preflight + CI metrics; compare identical task traces with current ABCD process in shadow. Do not change team allocation or shared CI directly.
3. **DIL-03 product-hardening candidate (new, requires a separate cycle and A review).** Authenticated writer identity and permission boundary, real Windows/Blender checkpoint persistence, process liveness, post-COMMIT lost acknowledgement handling, safe human unsaved state reconciliation, rollback/power failure, failure injection across adapters. This is not already implemented by DIL-03.
4. **DIL-02 field verification.** Measure human interventions and actual AI work time on matched tasks. Existing artificial 'idea/adopt' study does not prove benefits for natural language prompting.

DIL-01 and DIL-02 remain frozen. No changes to A-owned STATE, HANDOFF, AGENTS, common CI, ABCD branches, Geometry Lab #114 or main. No automatic integration.
