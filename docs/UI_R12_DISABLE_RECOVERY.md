# R12 C — failed disable is not completed cleanup

Common experimental base: `faab6ab023f50495c719d091b29f320aa6ab36df`
(R11 integration candidate, not development). This changes only C tests/docs.

The native probe tests class-only, Scene-only and simultaneous failures,
with/without a synthetic foreign replacement for each of the two Scene names
(12 scenarios). The first disable reports an error and sets the Blender enabled
flag false while CBDK keeps pending ownership. A second disable skips cleanup;
reload remains blocked. Re-enable fails closed at register and Blender evicts
the failed module from sys.modules. Retain the original module reference,
explicitly unregister it, preserve the foreign token, remove only the test's
foreign fixture, then enable/disable again after complete cleanup.

This is an observed Blender lifecycle boundary, not evidence that class leaks
are silently repaired or that arbitrary reimports are safe. No production
change is justified: the existing ownership guard refuses registration.
No automatic retry/reimport/foreign deletion is added to the product.

Local Python 3.12.14: two new tests passed. Local Blender 4.3.2: all prior and
four native_r12 markers passed on the first run. This is supplemental evidence;
4.4.3/4.5.15/5.2.1 are verified separately on the exact PR/candidate HEAD.
R5–R11 probes and five features/six recipes remain intact. No Windows GUI,
private addon or real third-party coexistence is exercised. Actual final CI,
stacked PR topology and timings are recorded in the separate R12 benchmark PR.
