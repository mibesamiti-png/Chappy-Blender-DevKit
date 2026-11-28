# Team C R10 — combined class and Scene cleanup faults

**Workstream:** UI-001 / BUILD-001. Team A's authoritative
`docs/PARALLEL_ROLLING_QUEUE.md` formally activated R10 in merged
[PR #82](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/82)
after R9 code integration [PR #81](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/81)
and separate post-squash **seven** successful workflow families at
`914f1c8ab8cf8dfe104f46054bfd4c84fc101e61`.
Use the newest development HEAD at R10 branch creation; never merge
individual R9 B/C/D PRs again or derive the branch from their old HEADs.

## Objectives and explicit fault model

Within the **same call** to `unregister()` on the trusted CBDK-authored
generated preview, fail (a) one real `bpy.utils.unregister_class` operation
and (b) one `bpy.types.Scene` RNA property deletion. These are controlled
exceptions delivered by a temporary monkeypatch of `bpy.utils.unregister_class`
and a *module-local* `delattr` shadow on the trusted preview. Restore both
in `finally`. Do not patch Blender's metaclass, import external addons,
or perform unknown code execution.

All other classes and the other Scene declaration should detach normally.
After the first failure verify **both** remaining ledgers contain exactly
the failed class and the failed property name with its **original descriptor
token**. The module must not reload or accept new registration while either
ledger is live.

Exercise a bounded 2 × 2 matrix: either Scene property may fail, and on the
second unregister call **either the class** or **the Scene deletion** fails
again. If the class fails, replace the pending Scene name with a synthetic
foreign descriptor *before* that retry; the Scene ledger must release
without deleting the foreign name while the class ledger remains live.
If the Scene deletion fails again, the class ledger must release first
while the Scene ledger/token stay live; replace its pending descriptor
with a synthetic foreign descriptor *after* that retry. Attempt reload
and registration in each partially cleaned state: both must fail closed.

The **third explicit unregister** must finish all remaining CBDK-owned
work without deleting the synthetic foreign declaration. Registration
while the foreign name still exists must detect collision and refuse it;
the test fixture then explicitly removes only its own stand-in, performs
a detached `importlib.reload`, and verifies clean register/unregister.

**Native R10 markers** appended after the complete relevant assertions:

- `native_r10_dual_failure_retains_both_ledgers`
- `native_r10_class_retry_preserves_foreign`
- `native_r10_scene_retry_preserves_foreign`
- `native_r10_partial_retry_blocks_reload`
- `native_r10_enable_disable_after_dual_recovery_2`

The final marker is assigned only after two real
`addon_utils.enable` / `addon_utils.disable` cycles with checks on
class count, Scene declarations and full cleanup after all four scenarios.
All existing R5–R9 runtime checks, fixed five features and six preview
recipes are preserved.

## Synthetic Python regression and evidence requirements

`tests/test_ui_lifecycle_r10.py` independently exercises the same two
Scene names × two second-failure branches against trusted Python bpy mocks,
plus a stricter **three consecutive double-failure** retry sequence.
Assertions cover identity of the retained owned descriptor, independent
cleanup-claim ledgers, reload refusal, foreign declaration preservation,
collision refusal and clean final recovery. A separate static contract
checks the existence and uniqueness of all five R10 markers and the
preservation of R9 marker labels. Python mocks are *not* headless Blender
evidence.

The already-wired, C-owned `tests/blender_ui_lifecycle_r5.py` is executed
on Blender 4.4.3, 4.5.15 and 5.2.1 by the A-owned workflow, using only
the locally generated **preview-only** CBDK `modular_all` ZIP and
factory settings. No common CI change is needed. A comment-only change
under `templates/modular_preview/__init__.py` documents the existing
independent ownership-ledger behavior, and activates the existing CI
path filter. No product/runtime logic change should be made **unless an
actual bounded regression is reproduced**.

For the exact R10 PR HEAD, confirm completed Python 3.11/3.12/3.13,
Windows PowerShell 3.11/3.13, Chromium, Handoff and Blender 3-version
jobs. Inspect **each Blender version's actual completed log** and parse
its `CBDK_R5_UI_LIFECYCLE_PASS` JSON `checks`, requiring all five R10
marker IDs. Do not report green based on static script content alone.
Kit/Skill count only if triggered. Individual R10 PR pass and A combined
candidate / post-merge developer SHA are separate evidence.

## Guardrails and R11 candidate for A

No third-party addon coexistence, real Windows GUI/Ctrl+Z hotkeys,
user/private GLB, non-CBDK source import/install, OOM/process-crash
resilience, licensing/SPDX, official Extension distribution or public
release is demonstrated. Avoid user data, private path leaks and
untrusted script execution. No modifications to shared STATE/Handoff,
PROGRESS, Notion, CI workflow/scripts, `main`, B GLB or D Extensions.
Five fixed authored preview features / six recipes remain.

**R11 candidate — design only until formally queued by A:**
stress *property deletion retries with changing descriptor identity* in
both directions (owned → missing → foreign → owned-looking replacement)
while a separate operator class ledger remains live; verify identity
rather than names governs deletions and no already-removed class is
unregistered twice. Include explicit tests for a failed `unregister()`
during `addon_utils.disable` and a safe owner-triggered retry, without
claiming the Blender addon manager guarantees atomic disable/re-enable.
Start with bounded synthetic failures and independent 3-version native
logs. Do not create an R11 draft while R10 is unintegrated or its base
is unapproved.
