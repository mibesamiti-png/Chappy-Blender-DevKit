# CBDK-authored Blender helper candidates (v0.6)

These are small original reusable helpers, not auto-extracted third-party code.
They are **Python-unit-tested** but **not yet confirmed in Blender itself**.
Do not put them on the approved-parts list until Blender runtime validation, compatibility and license review are recorded.

| Part ID | Entry point | Preconditions | Side effects | Verification |
|---|---|---|---|---|
| BLCTX-001 | `require_active_mesh(context, mode=None)` | Explicit Blender-like context with active MESH object | None | Python mocks |
| BLCTX-002 | `selected_mesh_objects(context)` | `context.selected_objects` available | None | Python mocks |
| BME-001 | `count_edit_selection(context)` | `EDIT_MESH`; active MESH; exactly one unique edit mesh by default | Reads BMesh only | Python mocks |

Run on a trusted installed Blender build:

```bash
python -m cbdk.blender_test blender --suite parts
```

This runs only `scripts/blender_parts_smoke.py` (from the CBDK repository) in Blender with factory startup. **It does not import or execute scanned third-party addons.**
