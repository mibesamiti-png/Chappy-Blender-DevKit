# EXT-001 R18 — synthetic Extension ZIP generation and official verification

R18 implements a bounded, **non-installable synthetic fixture** path, not a real-addon converter or publishing command.

## API contract

- `render_synthetic_manifest(fields)` requires explicit reviewed metadata, the reserved `cbdk_synthetic_extension_fixture` ID, and type add-on. It emits UTF-8 TOML for the required and two R17 optional fields only, with escaped strings and sorted permission keys. Parse back with tomllib, compare fields, and reapply existing review. Missing, invalid or unsupported fields stop before output. No owner, license, permission purpose or version is inferred.
- `build_synthetic_extension_bytes(fields)` generates exactly two root members: `__init__.py` (fixed raise-on-import sentinel) and `blender_manifest.toml`. Fixed timestamp, order, Unix mode and stored compression yield deterministic bytes. No input source path, arbitrary members, user code, package conversion or install entry point.
- `write_synthetic_extension_zip(fields, output)` validates the complete archive before exclusive creation of a fresh .zip in a caller-controlled existing directory. No overwrite or directory creation; hostile concurrent filesystem manipulation and disk-write failure atomicity are not claimed.
- `verify_synthetic_extension_bytes(data, fields)` checks exact fixed inventory, duplicate names, declared sizes, modes, compression and byte-for-byte expected contents including CRC. No extraction. This checks locally generated fixture bytes, not arbitrary hostile ZIP authenticity. The existing preview preflight is unchanged. Original limits: 16 MiB archive, 2 MiB member, 64 members. Manifest limit: 32 KiB. Diagnostics/reports exclude input values and paths; the actual manifest intentionally contains the supplied synthetic metadata.

## Real Blender checks

Official documentation describes directory/archive validation and build as distinct CLI operations: https://docs.blender.org/manual/en/5.2/advanced/extensions/getting_started.html and https://developer.blender.org/docs/features/extensions/schema/1.0.0/ .

The existing CI script retains six strict directory fixtures and seven R17 optional cases. R18 adds:
1. Generate local deterministic ZIP and check exact members.
2. Run official extension validate on this actual ZIP; require exit zero and recognized success/diagnostic agreement.
3. Run official extension build on an isolated directory holding the same fixed two members, with output outside that directory. Require exit zero and actual ZIP, independently compare exact contents, then validate that ZIP too. Official builder byte-for-byte determinism is not claimed.
4. Verify invalid metadata creates no ZIP and existing output is never overwritten.
5. Emit fixed synthetic ZIP/build pass markers; no raw metadata, filenames from input, or validator log payload in reports.

The synthetic SPDX value is only a test input, not a license decision. No actual addon source is read or executed, no installation or publication. Existing seven preview archives remain release-blocked. Other optional fields, real package generation, owner consent and rights, actual runtime/GUI, and publication are outside this batch. EXT-001 remains partial pending A review. No shared CLI hook is necessary for this CI-only fixture path; if A wants to expose a synthetic test command, the API above is its bounded contract.
