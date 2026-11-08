# R11 C — pending ownership and explicit disable recovery

Base: `a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`.

Two new Python tests exercise both owned Scene names with missing, foreign
and equal-content-but-distinct descriptors while class cleanup is pending.
Equality, labels and CBDK-looking names never authorize deletion: only exact
original token identity does. A partial retry releases lost property claims
without losing the class ledger; reload/register stay blocked until explicit
successful cleanup. No production defect was reproduced; template unchanged.

The existing C-owned native lifecycle script now performs all six combinations
on real Blender RNA and emits four `native_r11_*` markers. It also injects
one unregister_class failure through actual `addon_utils.disable`, observes
its error handler, checks retained class ownership, explicitly calls
`unregister()`, reloads and successfully enables/disables again. A second
`disable()` alone is not documented as recovery: Blender can already mark
the module disabled before the failing unregister call.

Local Python 3.12.14: two new tests passed. Local Blender 4.3.2: existing and
four R11 native markers passed; this is supplementary, not target-version
certification. Target 4.4.3 / 4.5.15 / 5.2.1 CI evidence belongs to the benchmark
and PR. Existing R5–R10 probes, five features and six recipes are retained.
No Windows mouse/keyboard/Ctrl+Z test or real third-party addon coexistence
was performed. Only CBDK-authored generated preview code was executed.
