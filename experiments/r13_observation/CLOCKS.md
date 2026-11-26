# R13 phase 2: clock semantics

Previous run 45837112669 (commit eec4955c4a919ca9fe220b16c5cc4964ccdc4006): both full suites 1369 tests, 16 skipped, no failures. Windows 3.11 focused 60/60, Windows 3.13 focused 59/60. Job 139968792216 reproduced root-case-alias false refusal, before-vs-opened difference exclusively ctime_ns; callback not reached, no bytes returned. Both versions' changed-source controls passed 20/20 in the focused suite. Original Work changed-source failure remains unreproduced.

Source audit of CPython tags v3.11.9 and v3.13.17:
- https://github.com/python/cpython/blob/v3.11.9/Python/fileutils.c : creation timestamp -> ctime in _Py_attribute_data_to_stat, used for path and fd.
- https://github.com/python/cpython/blob/v3.13.17/Modules/posixmodule.c : win32_xstat copies birthtime into ctime for legacy compatibility (2226–2227); os_fstat_impl uses FSTAT = _Py_fstat_noraise without that copy.
- https://github.com/python/cpython/blob/v3.13.17/Python/fileutils.c : basic_info maps CreationTime -> birthtime and ChangeTime -> ctime (1140–1141); _Py_fstat_noraise uses FileBasicInfo and returns directly.
- https://docs.python.org/3.13/library/os.html : ctime_ns deprecated on Windows from 3.12; use birthtime_ns for creation.
- https://github.com/python/cpython/issues/157671 : upstream same-symptom report found in search; issue page not fully retrieved, status not asserted.
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_basic_info : creation and metadata-change clocks are distinct.

Pre-registered follow-up: use exact original interpreter versions on Windows 2022, 20 fresh and 20 deliberately distinct creation/change-clock synthetic files each. Compare Python stat/fstat to GetFileInformationByHandleEx(FileBasicInfo) on the same open handle; record deltas and equality only. Append and explicit same-size mtime change controls. No sleeps or tolerances. Prior observation script and failure history retained. No full-suite rerun here because the semantic question is now narrower. No production/old-test changes. A future test-only fix may compare birthtime when available on Windows and preserve legacy creation fallback, but that alone is not a guarantee against metadata/content races; evaluate native change-time checks if the contract needs that property. Do not infer original Work failure cause from this experiment alone.
