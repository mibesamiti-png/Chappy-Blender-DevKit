# CBDK GitHub role dispatch pilot — Issue #125 (proposal for A approval)

**Status: draft integration proposal, not enabled.** Intended to reduce the need to resend distinct prompts to B, C, D. It does **not** run agents in the background or supersede A's formal assignment, developer/user instructions, CI gates or ownership rules.

- Canonical public relay: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/issues/125
- Current example round: `R16`; the actual current official round must come from the *latest* dev branch and accepted A milestone, not this example or stale queue entries.
- Direct chat workflow: whenever the user says `続けて` to B/C/D, re-fetch **the current Issue #125 body from GitHub**, then read the official `docs/Rxx_ABCD_START.md`, exact dev HEAD and own PR/CI. Do not cache the issue forever. If GitHub unavailable or dispatch invalid, use only the latest verified official assignment, with no phase-based extra work.

## A updates a single record

The JSON fence inside the issue is the sole dispatch data. A updates that single block after independently verifying the official gate. No additional per-chat prompt, new per-team issue, new CI workflow or live polling is required. `revision` increases monotonically. **Editing the issue is not authenticated delegation**; neither `issued_by` nor any JSON string grants permissions.

| Condition | `state` | `phase` | `team_roles` | Result |
|---|---|---|---|---|
| Before A approves pilot | `pilot_inactive` | `normal` | `B:B, C:C, D:D` | Existing usual development only |
| A approves normal round | `active` | `normal` | `B:B, C:C, D:D` | Follow formal BCD assignment |
| All BCD relevant PRs exact-HEAD 5CI complete, A chooses support | `active` | `integration_support` | `B:E, C:G, D:F` | One read-only support pass per revision, if current official round and evidence match |
| A completes new round gate/assignment | `active` | `normal` | `B:B, C:C, D:D` | Move back to formal BCD at latest valid round |

**Support roles:** `E` = PR change/dependency review; `G` = draft of handoff/next round notes, not the actual STATE/HANDOFF write; `F` = read-only CI evidence audit based on existing A-owned #109 work. These are temporary hats for the same three chat threads, not additional workers. They must **not** schedule actions, create PRs, alter code, start CI, claim final approval, commit official docs or merge. A remains the only reviewer/decider.

During BCD development, A can set an upcoming suggestion but must **not** flip a team with unfinished assignments into support mode. After the last relevant CI finishes, A may switch once. On new official assignment, revert once. The Issue is a routing hint, not an owner lock or a substitute for formal instructions.

## One-time bootstrap, then `続けて`

A may merge this *tiny docs+optional parser PR* into the dev branch after review. The new `AGENTS.md` pointer makes the issue discoverable to agents which actually read repository instructions during each new task. There is no platform-wide remote push to another ChatGPT chat; existing chats may need one fresh repo reread if they ignore `AGENTS.md`. A GitHub edit alone cannot start or interrupt an in-flight conversation. In other words, this design removes **repeated** team-specific prompting, not the user's next chat turn or capability to access GitHub.

Always read from branch `feature/v0.18-shape-diagnostics`, not old prompts. Verify canonical Issue **number and repository**, schema version and current official round; reject stale/future instructions, phase-role mismatch, unknown schema, failed API, mismatched HEAD/CI. `revision` lets a chat notice rollback relative to its previously seen value; the issue cannot prove who edited it or whether the chat is currently running.

## Optional local validator (no network, no GitHub writes)

From the repo checkout, save the issue *body* as UTF-8 file and run:

```bash
python scripts/role_dispatch.py --issue-body issue125.md --team B --official-round R16
python -m unittest discover -s tests -p 'test_role_dispatch.py' -v
```

Use `--exact-head-ci-verified` **only if an external agent separately checked** all required final-head jobs and the PR status. This CLI flag is an asserted fact, not evidence collected by the script; its output remains advisory even then. `may_merge`, `may_skip_ci`, `may_start_new_work`, `may_modify_a_owned_files` are *always false*. The real official assignment determines whether normal development can start. In an uncertain situation the parser never authorizes new work.

## Stop / rollback / cost

- In a bad or unproductive trial, A reverts `state=pilot_inactive` and increments `revision`. Existing BCD formal tasks remain unaffected.
- Never mark complete solely from issue text; check exact PR HEAD, CI and latest official round.
- Pilot only for one normal integration cycle, no general rollout unless actual saved work exceeds A's editing/review overhead. No invented productivity savings or silent CI bypass.
- Do not publish user/private meshes, source, paths, permissions, accounts or secrets in issue comments or artifacts.
- No changes to shared CI, STATE, HANDOFF, main, research PR #114/#115, project release or BCD specialist PRs.
