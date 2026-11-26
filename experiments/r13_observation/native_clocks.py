"""Windows-only synthetic clock mapping experiment; no production reader changes."""
import ctypes
from ctypes import wintypes
from collections import Counter
import json
import msvcrt
import os
from pathlib import Path
import sys
import tempfile

class BasicInfo(ctypes.Structure):
    _fields_ = [("creation", ctypes.c_longlong), ("access", ctypes.c_longlong),
                ("write", ctypes.c_longlong), ("change", ctypes.c_longlong),
                ("attributes", wintypes.DWORD)]

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
get_basic = kernel.GetFileInformationByHandleEx
get_basic.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
get_basic.restype = wintypes.BOOL
set_time = kernel.SetFileTime
set_time.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
                     ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME)]
set_time.restype = wintypes.BOOL
EPOCH = 116444736000000000

def basic(stream):
    info = BasicInfo()
    if not get_basic(msvcrt.get_osfhandle(stream.fileno()), 0,
                     ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    return info

def ns(ticks):
    return (ticks - EPOCH) * 100

def set_creation_older(path):
    # Set only the creation timestamp of our own disposable synthetic file.
    # Force distinct clocks without sleeps or dependence on timestamp resolution.
    with path.open("r+b") as stream:
        old = basic(stream).creation - 86400 * 10000000
        value = wintypes.FILETIME(old & 0xffffffff, old >> 32)
        if not set_time(msvcrt.get_osfhandle(stream.fileno()), ctypes.byref(value), None, None):
            raise ctypes.WinError(ctypes.get_last_error())

def birth(info):
    return getattr(info, "st_birthtime_ns", info.st_ctime_ns)

def inspect(path):
    p = os.stat(path, follow_symlinks=False)
    with path.open("rb") as stream:
        f = os.fstat(stream.fileno())
        native = basic(stream)
        raw = stream.read()
    creation, change, write = map(ns, (native.creation, native.change, native.write))
    # Emit only comparisons and relative clock deltas, never paths or timestamps.
    return dict(path_ctime_is_creation=p.st_ctime_ns == creation,
                handle_ctime_is_creation=f.st_ctime_ns == creation,
                handle_ctime_is_change=f.st_ctime_ns == change,
                creation_change_distinct=creation != change,
                ctime_delta_ns=f.st_ctime_ns-p.st_ctime_ns,
                native_delta_ns=change-creation,
                birth_matches_native=birth(p)==birth(f)==creation,
                mtime_matches_native=p.st_mtime_ns==f.st_mtime_ns==write,
                identity_matches=(p.st_dev,p.st_ino)==(f.st_dev,f.st_ino),
                size_matches=p.st_size==f.st_size==len(raw)), (p.st_size,p.st_mtime_ns,birth(p))

def main():
    counts, failures, controls = Counter(), [], Counter()
    for case in ("fresh", "distinct_clocks"):
        for i in range(20):
            with tempfile.TemporaryDirectory() as root:
                path = Path(root) / "synthetic.bin"
                path.write_bytes(b"abcd")
                if case == "distinct_clocks":
                    set_creation_older(path)
                row, before = inspect(path)
                row["case"] = case
                # This is an observation, not a candidate security reader.
                counts[json.dumps(row, sort_keys=True)] += 1
                expected = row["handle_ctime_is_creation"] if sys.version_info[:2] == (3,11) else row["handle_ctime_is_change"]
                if not (expected and row["path_ctime_is_creation"] and row["birth_matches_native"]
                        and row["mtime_matches_native"] and row["identity_matches"] and row["size_matches"]
                        and (case != "distinct_clocks" or row["creation_change_distinct"])):
                    failures.append([case, i, "clock_mapping"])
                # Independently verify that the common-clock projection still
                # distinguishes a size change and a same-size mtime change.
                with path.open("ab") as stream:
                    stream.write(b"e")
                _, after = inspect(path)
                controls["append_detected" if after[0]!=before[0] else "append_missed"] += 1
                path.write_bytes(b"vwxyz")
                os.utime(path, ns=(after[1], after[1]-2000000000))
                _, final = inspect(path)
                controls["same_size_mtime_detected" if final[0]==after[0] and final[1]!=after[1] else "same_size_mtime_missed"] += 1
    print("CBDK_R13_NATIVE_CLOCKS " + json.dumps(dict(
        python=sys.version.split()[0], rows=[dict(json.loads(k), count=v) for k,v in sorted(counts.items())],
        controls=dict(controls), failures=failures, diagnostic_only=True), sort_keys=True), flush=True)
    return int(bool(failures or controls["append_missed"] or controls["same_size_mtime_missed"]))

if __name__ == "__main__":
    raise SystemExit(main())
