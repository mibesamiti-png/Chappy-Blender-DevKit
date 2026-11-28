# Team C R8 — failed unregister retry and canceled edit invariance

**Task:** R8 UI-001 / BUILD-001, officially assigned by the coordinator-owned
`docs/PARALLEL_ROLLING_QUEUE.md` after R7 was combined in [PR #63](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/63)
and post-merge **seven CI families succeeded** at development SHA
`687b2acdc920253d69eda8c5e9c1c102d02aaef3`. R8 starts from the newest
descendant `feature/v0.18-shape-diagnostics` HEAD, not from the old Team C
PR #62 or any experimental integration branch.

## Failure modes, expectations, and bounded native evidence

The already connected, C-owned `tests/blender_ui_lifecycle_r5.py` runs inside
A-owned Blender CI on the trusted CBDK **preview-only** `modular_all` ZIP
with `read_factory_settings(use_empty=True)`. R8 adds five new checks,
without removing prior R5/R6/R7 markers:

- `native_r8_partial_unregister_foreign_retry`: for **each** of the two
  authored Scene properties, create a real registered preview, inject a single
  failure at the first `bpy.utils.unregister_class` call, and replace that
  Scene descriptor with a synthetic unrelated declaration before raising.
  The first `unregister()` must raise a retryable cleanup error and retain
  exactly the failed class. It must not delete the foreign property. After
  restoring the original unregister function, a second `unregister()` must
  remove the remaining class, release CBDK ledgers and preserve the foreign
  descriptor. Register must reject a foreign name; explicit synthetic fixture
  cleanup must permit a fresh register/unregister.
- `native_r8_partial_unregister_reload_fail_closed`: while the failed
  class is still live, `importlib.reload` must refuse and leave the ledger
  unchanged. After retry and explicit removal of synthetic foreign property,
  reload and register/unregister must work normally. This is a synchronous,
  controlled exception—not natural OOM/process crash recovery.
- `native_r8_validation_cancel_input_unchanged`: in Edit Mesh with all
  vertices deselected, invoke the guarded vertex-nudge operator; on
  `CANCELLED`, snapshot live BMesh vertex coordinates, vertex/edge/face
  selection and hide flags, active object, mode, and Scene result before/after.
- `native_r8_guarded_exception_cancel_input_unchanged`: in valid Edit Mesh
  with selected vertices, replace **only the trusted in-memory helper
  references** with a pair of fixed `BlenderContextError` injections.
  Invoke both the nudge and edit-selection operators, assert `CANCELLED`,
  and verify exact snapshot equality after each. Restore helpers in
  `finally`; never inject a callback that mutates geometry.
- `native_r8_edit_mode_cleanup_after_cancellation`: restore Object Mode
  and unregister the generated preview, asserting no operator/Scene leakage
  and that original triangle coordinates still match their initial values.

No actual third-party add-on or non-CBDK source is executed. The fixture has
one triangle and a fixed two-attempt class detach retry in the Python unit
tests; the native fail-once cases cover both Scene property names. Tests are
bounded and deterministic, no network or user files. They do **not** claim
actual GUI keyboard Undo or protection against helpers that mutate first
and then raise an exception; future partial-mutation rollback needs separate
design and approval.

The new `tests/test_ui_lifecycle_r8.py` checks both Scene property
permutations and a twice-failed class detach followed by a clean retry
against Python-only mocked Blender APIs. Static checks make sure all five
native marker names and explicit live BMesh snapshots are present; **unit
mocks and static checks are not real Blender evidence**.

## CI and safety rules

The existing A-owned Blender workflow triggers on
`templates/modular_preview/__init__.py` changes. R8 adds a documentation-only
module docstring clarifying the existing retry/foreign-property contract
so the existing native runtime matrix is started without touching shared
workflow or scripts. There is **no product logic change unless a test
reproduces an actual defect**.

Before claiming R8 native success, inspect the **exact R8 PR HEAD** Blender
4.4.3 / 4.5.15 / 5.2.1 job outcomes and their
`CBDK_R5_UI_LIFECYCLE_PASS` JSON `checks`, confirming **all five
`native_r8_*` names in each**. Also inspect Python 3.11/3.12/3.13,
Windows 3.11/3.13, Chromium, and Handoff at that same HEAD; Kit/Skill count
only if actually triggered. Individual R8 CI is not combined R8 or a
post-merge seven-workflow result.

Changes stay in `templates/modular_preview/`, C-only `tests/` and
`docs/`. Preserve five fixed operators/six authored recipes, preview_only
status, no `auto_apply`, no user/private GLBs/Blender plugins, no
STATE/HANDOFF/PROGRESS/Notion/shared CI/main/release changes. Real Windows
GUI/Undo shortcut, genuine foreign add-ons, legal/redistribution permission,
official Extensions and v0.19+ remain unverified.

## R9 candidate (design only; A must assign first)

Test **failed property deletion** after a class was successfully removed,
then a synthetic Scene replacement arrives before an explicit cleanup retry.
The ledger must remain until cleanup succeeds, refuse reload while
nonempty, and preserve the foreign declaration; distinguish failure to
detach an owned property from a lost/replaced descriptor. Add a bounded
native 3-Blender-version fixture plus repeated enable/disable only if R8
has been integrated and A confirms the new base. Do not create an
additional unmerged R9 PR while R8 is pending.
