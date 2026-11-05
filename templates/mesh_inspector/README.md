# CBDK Mesh Inspector (private development preview)

Read-only 3D View Sidebar > CBDK panel assembled from three CBDK-authored parts.

- BLCTX-001: require_active_mesh
- BLCTX-002: selected_mesh_objects
- BME-001: count_edit_selection

The template is authored in this repository, not copied from scanned private addons. **These parts are not formally approved or license-cleared for redistribution**. The builder requires an explicit `--preview-unapproved` opt-in and produces a **legacy add-on ZIP**, not a marketplace-ready Blender Extension.

Build: `python -m cbdk build-addon --recipe recipes/mesh_inspector.json --preview-unapproved --output dist/CBDK_Mesh_Inspector_Preview.zip`

The ZIP includes copied, SHA-recorded helper files; no private source directories, arbitrary input modules or code execution are involved during packaging.

Cloud checks must test actual enable, operator execution (Object and Edit Mode), panel registration, disable and cleanup. The three-part smoke suite does **not** by itself prove the generated addon works.
