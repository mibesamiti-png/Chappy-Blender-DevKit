# Team C R14 — multi-generation stale Blender ownership

## Authority, integration gate and exact source policy

Team A formally allocated [R14 C UI-001 / BUILD-001](R14_ABCD_START.md).
R13 C [PR #102](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/102)
was code-integrated once by A's [PR #104](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/104),
dev squash `0a306a85d6f84ef434eb6b54f12cb4ce93251a6c`.
The A-owned milestone [PR #105](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/105)
merged at `8665a3c136ae81efbd28a820e7de50ef6ee59332`, with
**seven independent completed-success CI families** for that exact SHA.
All branches and verification must use the latest development HEAD at
R14 branch creation, never old R13 specialist branches. No R13 PR remerge.

## Concrete bounded test: three generations, three native live classes

Starting from a detached CBDK-authored generated `modular_all` addon
already loaded by Blender 4.4.3 / 4.5.15 / 5.2.1:

- For **generation 1**, force failure at registered class slot 4 and
  deliberately fail rollback of previously registered slot 3.
- For **generation 2**, import the same package name after the first
  failed enable is evicted from `sys.modules`; force failure at slot 3,
  deliberately fail rollback of slot 2.
- For **generation 3**, repeat with forced registration failure at slot 2,
  and rollback failure for slot 1.

These failures are injected into trusted `bpy.utils.register_class` and
`unregister_class` calls only while running the *synthetic authored
preview*. The hooks are restored in `finally`. No real third-party
addon or user input source is imported.

Each generation's handle remains distinct, its remaining
`_REGISTERED` ledger must contain exactly one live class, Blender
`bpy.types` must expose that class by **object identity**, and no
owned Scene declarations remain from this case. The three distinct
class indices allow three old module handles to coexist without
re-registering the same class.

A fourth, freshly imported Python module of the same name has
**empty class/property/token ledgers**, but this is *unknown*, not a
successful global cleanup. Its `unregister()` must leave all three
native registrations untouched. Assign one CBDK test fixture's
synthetic foreign `bpy.types.Scene.cbdk_modular_result`. Fresh
`register()` must refuse the collision without erasing it. Explicitly
call `unregister()` on *all three old saved module references*, one by
one, while asserting each remaining older generation's native class
and ledger are still intact. Only when all three owned classes are
absent from `bpy.types` and all old ledgers are empty is the result
classified as **recovered**. Remove the foreign fixture descriptor by
identity and require a full successful native enable/disable.

## Separate two-generation Scene RNA ownership case

Starting from a detached module, inject a class registration failure
during `addon_utils.enable` and a one-shot failure deleting the exact
CBDK-owned `Scene.cbdk_modular_result` token during rollback. Its
class rollback succeeds, so only the original Scene RNA token and
ledger remain. The failed enable evicts the module. A new import
has empty ledgers but registration is **refused** because the original
Scene declaration remains; its `unregister()` cannot erase the old
ownership claim. Replace the old token by a synthetic, distinct
foreign descriptor, explicitly call the original module's
`unregister()` and verify its ledger clears **without deleting the
foreign value**. Fresh registration is still refused while the foreign
descriptor exists. Finally remove *only* the fixture's foreign token
and verify a complete enable/disable cycle.

The three outcomes are deliberately distinct:

- **unknown:** a new module has empty ledgers but one or more saved old
  modules still possess a live class or Scene RNA ownership token.
- **refused:** new registration rejects a foreign or pending Scene
  collision. A refusal does not establish that old ownership was
  cleaned.
- **recovered:** every saved old module has an empty class/Scene/token
  ledger, every expected Blender class is actually gone, and retained
  foreign Scene declarations have not been deleted.

No generic global discovery, automatic class eviction, or unknown-add-on
recovery is added to production code: ownership cannot be proven
merely from an imported module's fresh list.

## Test and CI evidence contract

`tests/blender_ui_lifecycle_r5.py` uses the existing A-owned Blender
CI invocation on exactly the three supported versions, with fixed
allowlisted preview-only ZIP and factory settings. Seven new
`native_r14_*` marker IDs are appended after the native scenarios:

- `native_r14_three_generation_class_identity`
- `native_r14_fresh_empty_ledger_is_unknown`
- `native_r14_foreign_collision_refused`
- `native_r14_all_old_references_explicitly_recovered`
- `native_r14_pending_scene_second_generation`
- `native_r14_foreign_scene_identity_recovered`
- `native_r14_reenable_after_all_generations`

`tests/test_ui_lifecycle_r14.py` independently exercises the
three-generation class-ownership ledger via a trusted synthetic
Python mock, a two-generation pending Scene token and foreign
replacement, and a static contract for native marker retention.
The Python mock is not substitute evidence for real Blender.

`templates/modular_preview/__init__.py` receives only a comment
clarifying that fresh imports cannot observe previous generations.
It also triggers the **existing A-owned Blender path filter** with
no modification to shared workflows or scripts. Existing five features,
six authored preview recipes and all R5–R13 native checks are retained.

For final PR HEAD, verify the five actually triggered workflow
families (Python 3.11/3.12/3.13, Windows PowerShell 3.11/3.13,
Blender 4.4.3/4.5.15/5.2.1, Chromium, Handoff), **each** completed
matrix job and **each** Blender job's actual
`CBDK_R5_UI_LIFECYCLE_PASS` JSON containing all seven R14 IDs.
If any red CI appears, fix before marking success. Kit/Skill only if
triggered. A's combined-code/head and post-dev-squash results require
their own tests.

## Safety limits and A handoff

This is bounded fault injection in locally authored Blender addon
preview source, not proof about arbitrary addon modules after a process
crash or third-party coexistence. Private GLB, add-on source files and
derived media are never loaded, executed, published or exposed in logs.
No Windows GUI Ctrl+Z/Ctrl+Shift+Z guarantee, user-specific Blender
assets, rights/license/authenticity decision, official Extensions
upload, main, v0.19, Pages or distribution authorization.

Strict ownership: `templates/modular_preview/`, C-only
`tests/` and `docs/` only. A-owned
STATE/Handoff/PROGRESS/Notion/CI/scripts and B/D work untouched.
No runtime product logic changes unless bounded native failures
reproduce a concrete defect. Team A must independently review the
R14 draft PR and run exact combined-head five families, then distinct
post-squash seven-family CI before assigning R15. Do not create a
second unintegrated specialist PR.

**R15 design only:** investigate whether a minimal, opt-in, read-only
diagnostic of *caller-supplied known old module handles* could report
unverified/pending/recovered without pretending to discover references
silently evicted from `sys.modules`. Add code only if an actual safe
user workflow and acceptance tests justify maintaining it. Never scan
untrusted plugins, delete classes by name, or auto-recover foreign
resources.
