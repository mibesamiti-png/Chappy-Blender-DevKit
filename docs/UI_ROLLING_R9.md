# Team C R9 — Scene RNA attribute deletion failure and safe cleanup retry

**Scope:** UI-001 / BUILD-001 R9, assigned by A's latest
`docs/PARALLEL_ROLLING_QUEUE.md` after the R8 integration in
[PR #73](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/73),
exact development merge commit
`ded947f85f46fb8cce0943314d6e1a9fb41717ef`.
A confirmed seven separate post-merge workflow families at that commit.
R9 is authorized by merged coordinator assignment PR #74. The source base
is the latest descendant of `feature/v0.18-shape-diagnostics` at branch
creation, not a historical specialist or experimental integration branch.

## Purpose, design and safety

R8 observed class detachment failures. R9 explores a *different* failure:
the preview's operator classes successfully detach, but the native
`bpy.types.Scene` attribute deletion raises once. The CBDK code is expected
to **retain** the failing property name and exact owned RNA descriptor token
until a successful retry, reject `importlib.reload` while the ledger is
pending, and refuse a subsequent registration that would claim that name.

The existing C-owned `tests/blender_ui_lifecycle_r5.py` is executed by the
A-owned Blender 4.4.3 / 4.5.15 / 5.2.1 CI. This fixture runs only the
locally generated, allowlisted, preview-only CBDK `modular_all` ZIP with
`read_factory_settings(use_empty=True)`. R9 temporarily shadows the
**module-local** name `delattr` in that trusted generated preview. This
causes one controlled exception when attempting to remove exactly one of
the two CBDK-owned Scene attributes. The original Python builtin and
Blender's metaclass are **never monkeypatched globally**; the shadow is
removed in `finally`.

R9 adds both property-name permutations and checks:

- **`native_r9_scene_delete_failure_retains_ledger`** — the first
  `unregister()` raises `cleanup incomplete`; all operator classes detach
  normally, the other CBDK Scene property is removed, and only the failing
  property and *its exact original token* remain in ownership ledgers.
- **`native_r9_pending_cleanup_reload_rejected`** — reloading or
  registering again while the descriptor ledger is pending must be rejected,
  with the record untouched.
- **`native_r9_foreign_replace_retry_preserved`** — replace the pending
  Scene descriptor with a synthetic CBDK-authored foreign stand-in
  (`StringProperty` or `FloatVectorProperty`) *before* retry.
  A successful second `unregister()` must release the stale CBDK claim
  **without deleting the replacement**; a fresh `register()` refuses the
  collision. Only the exact synthetic stand-in is explicitly removed by
  the fixture, after which reload/register/unregister work normally.
- **`native_r9_owned_delete_retry_recovered`** — perform the same
  one-shot Scene deletion failure without replacement, then restore the
  builtin and ensure a subsequent explicit cleanup removes the **original
  owned** declaration and allows normal re-registration.

Existing R5–R8 assertions and marker records remain intact. All five
reviewed operators and all six authored preview recipes remain supported;
nothing private or untrusted is imported or installed. No real third-party
addon code is involved.

The new `tests/test_ui_lifecycle_r9.py` uses a synthetic Blender API mock
to verify both foreign-replacement permutations, two consecutive
deletion failures retaining the ownership token, a later successful retry,
and the static presence/allowlisted imports of all four native markers.
These Python-only checks are **not evidence of native Blender execution**.

## Code change and test trigger

No product execution behavior was changed in R9: a C-owned comment next to
the existing `delattr(bpy.types.Scene, name)` explains why failures must
retain the ownership list and how the trusted fixture simulates this case.
The comment-only edit under `templates/modular_preview/` also activates the
existing A-owned Blender PR trigger; common CI scripts are untouched.

Verify the **exact R9 PR HEAD** with Python 3.11/3.12/3.13,
Windows PowerShell 3.11/3.13, Chromium, Handoff, and complete native
Blender 4.4.3/4.5.15/5.2.1 jobs. Inspect each real Blender log's
`CBDK_R5_UI_LIFECYCLE_PASS` JSON and ensure it includes all four
`native_r9_*` labels, not merely that the old smoke job is green.
Kit/Skill count only when triggered. Individual R9 green is not
proof of A's combined-code or post-squash merge CI.

## Boundaries and R10 candidate

This tests a *deliberately injected one-shot failure*, not arbitrary
Blender RNA errors, OOM/process crashes, or another developer's real addon.
No actual Windows GUI/Ctrl+Z hotkey test, third-party addon coexistence,
user/private GLBs or source, license/SPDX proof, public Extension install,
release approval, `main` merge, or v0.19+ activation is implied.
STATE/HANDOFF/PROGRESS/Notion/shared CI and unrelated team files are A-owned.

**R10 proposal — design only until A assigns a fresh base:** bounded
combinations of a class-detach failure *and* a Scene-deletion failure within
the same teardown, with deliberate foreign replacement between retries.
Track which class/property ledgers still need cleanup, ensure reload
remains blocked until all claims resolve, and verify no foreign deletion
and no erroneous success reported by the preview. Avoid unbounded
injections and keep all checks within C-owned tests and authored preview.
No extra specialist PR before the R9 draft has been resolved by A.
