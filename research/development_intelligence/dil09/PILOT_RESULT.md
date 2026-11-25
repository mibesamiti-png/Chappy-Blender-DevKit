# DIL-09 — bounded real documentation task (pilot record)

2026-11-25 JST; task RESEARCH-DIL-001 / DIL09-DOC-01.
Scope chosen in response to user continuation: remove conflicting historical/current text from the real DIL PR and research index, preserving evidence. Not a product task or a new algorithm. No A approval inferred.

## Start and acceptance

- Starting DIL HEAD 8337d86142a285a2f92e68cfcb352bb85d23a24b; three existing workflows completed/success for that HEAD: 45516381425, 45516381395, 45516381389.
- dev 2b8220210c2475239a43354d544b5a6f176fba80; seven observed family summaries green. Main c5b63ba50f4f53e22dea3ddc72486a17aa9dd939: no matching runs returned in the queried list; not claimed green. Main CI is not a gate for this research-only documentation change.
- Issue #125 revision 1 R16 normal. Read DIL scope, pilot, current status, research results and integration proposal, plus official AGENTS/parallel/R16 references. No ABCD task is taken.
- Existing research scope permits documentation; no code or shared rules change. Stop if research branch moves, PR ceases to be draft, or old evidence cannot be preserved. Acceptance: archive equals original PR body, current PR body is shorter and explicitly research-only, current index links existing evidence, no other paths modified, exact final HEAD CI reported separately, no normal CI log read.

## Measurable output

- Original PR description: 23762 UTF-8 bytes. Proposed replacement: 1827 UTF-8 bytes (92.31% reduction). These are directly measured strings, not tokens or network traffic. Archive retains the original bytes. The replacement must be read back before claiming the observed reduction.
- User continuation prompts at task start: 1. No intermediate user prompt requested so far. Historical matched task, comparative elapsed time, model tokens and total user time: unavailable. No claimed causal speedup.
- Prior to this commit: 18 GitHub read calls (5 initial scope/CI, 11 formal context/CI, 2 final PR/ref checks); no normal CI logs. Counts exclude writes and final verification. Research job-level results from prior phase are retained separately. This doc-only task does not exercise the adapter in a general code task.
- One planned research commit, one PR metadata update, no new PR. After commit verify exact archive text, new PR body, changed paths and final CI. Pending until those observations exist.

## Decision boundary

A smaller live entry point is a genuine documentation improvement only if readback and archive equality succeed. It does not prove generalized task throughput or authorize a production deployment. Preserve all DIL-01–09 frozen experiment files and failures. No A/ABCD/GL scope expansion.
