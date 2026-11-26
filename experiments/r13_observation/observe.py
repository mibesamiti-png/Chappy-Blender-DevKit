"""Diagnostic-only R13 observation; unchanged reader, tests and expectations."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT)]
import test_extension_source_reference_round13 as r13

FIELDS = ("device", "inode", "size", "mtime_ns", "ctime_ns")
READ = r13._stable_reference_read
FINGERPRINT = r13._fingerprint
OBSERVATIONS = Counter()
CONTROLS = (
    "test_r13_changed_source_between_read_and_final_stat_is_inconclusive",
    "test_r13_stable_reference_normalizes_line_endings_without_rewriting",
    "test_r13_windows_root_case_alias_canonicalizes_but_source_case_denied",
)

def differing(a, b):
    return [name for name, x, y in zip(FIELDS, a, b) if x != y]

def observed_read(source_rel, *, requested_root, pinned_root, after_read=None):
    samples = []
    callback_called = False

    def capture(info):
        value = FINGERPRINT(info)
        samples.append(value)
        return value

    def callback():
        nonlocal callback_called
        callback_called = True
        return after_read()

    with patch.object(r13, "_fingerprint", capture):
        status, data = READ(
            source_rel, requested_root=requested_root, pinned_root=pinned_root,
            after_read=callback if after_read is not None else None,
        )
    # No extra stat, sleep, read, path, raw timestamps or private contents.
    # The original reader evaluates before/opened then before/final.
    row = {
        "mutating_control": after_read is not None,
        "root_spelling_differs": str(requested_root) != str(pinned_root),
        "callback_called": callback_called,
        "status": status,
        "data_returned": data is not None,
        "fingerprints": len(samples),
        "before_vs_handle": differing(*samples[:2]) if len(samples) >= 2 else None,
        "before_vs_final": differing(*samples[2:4]) if len(samples) >= 4 else None,
    }
    OBSERVATIONS[json.dumps(row, sort_keys=True)] += 1
    return status, data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("full", "focused"))
    args = parser.parse_args()
    with patch.object(r13, "_stable_reference_read", observed_read):
        if args.mode == "full":
            suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        else:
            suite = unittest.TestSuite(
                r13.R13FrozenReferenceTests(name)
                for _ in range(20) for name in CONTROLS
            )
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    print("CBDK_R13_OBSERVATION " + json.dumps({
        "mode": args.mode, "python": sys.version.split()[0],
        "tests": result.testsRun, "failures": [t.id() for t, _ in result.failures],
        "errors": [t.id() for t, _ in result.errors],
        "skips": len(result.skipped),
        "rows": [dict(json.loads(k), count=v) for k, v in sorted(OBSERVATIONS.items())],
        "instrumented": True,
    }, sort_keys=True), flush=True)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    raise SystemExit(main())
