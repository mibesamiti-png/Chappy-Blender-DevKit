"""Compare the original and proposed R13 reader on disposable Windows fixtures."""
import json
from collections import Counter
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT)]
import test_extension_source_reference_round13 as r13
from native_clocks import set_creation_older, inspect

CANDIDATE = r13._fingerprint
CASES = ("stable", "append", "same_size_mtime", "creation_changed", "replacement")

def legacy(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

def one(case, fn):
    fixture = r13.R13FrozenReferenceTests()
    fixture.setUp()
    try:
        set_creation_older(fixture.path)
        mapping, _ = inspect(fixture.path)
        assert mapping["creation_change_distinct"], "native clock distinction missing"
        invoked = False

        def mutate():
            nonlocal invoked
            invoked = True
            p = fixture.path
            if case == "append":
                with p.open("ab") as stream:
                    stream.write(b"x")
            elif case == "same_size_mtime":
                prior = p.stat()
                p.write_bytes(b"x" * len(fixture.initial))
                os.utime(p, ns=(prior.st_atime_ns, prior.st_mtime_ns-2000000000))
            elif case == "creation_changed":
                set_creation_older(p)
            elif case == "replacement":
                prior = p.stat()
                replacement = p.with_name("replacement.bin")
                replacement.write_bytes(fixture.initial)
                os.utime(replacement, ns=(prior.st_atime_ns, prior.st_mtime_ns))
                os.replace(replacement, p)
                assert p.stat().st_ino != prior.st_ino, "replacement identity not distinct"

        with patch.object(r13, "_fingerprint", fn):
            status, data = r13._stable_reference_read(
                fixture.source, requested_root=fixture.root, pinned_root=fixture.root,
                after_read=mutate if case != "stable" else None)
        expected = ("stable_repo_bytes" if case == "stable"
                    else "inconclusive_reference_changed")
        correct = (status == expected and
                   (data == fixture.initial.replace(b"\r\n", b"\n")
                    if case == "stable" else data is None and invoked))
        return dict(status=status, data_returned=data is not None,
                    mutation_reached=invoked, correct=correct)
    finally:
        fixture.doCleanups()

def main():
    rows, failures = Counter(), []
    for mode, fn in (("legacy", legacy), ("candidate", CANDIDATE)):
        for case in CASES:
            for iteration in range(20):
                result = one(case, fn)
                rows[json.dumps(dict(mode=mode, case=case, **result), sort_keys=True)] += 1
                expected_correct = mode == "candidate" or sys.version_info[:2] == (3,11)
                # Legacy rejection is not a safety breach; the mutation callback
                # must run to count as genuine post-read detection evidence.
                if result["correct"] != expected_correct or (
                    case != "stable" and result["data_returned"]):
                    failures.append([mode, case, iteration, "unexpected_observation"])
    print("CBDK_R13_REPAIR " + json.dumps(dict(
        python=sys.version.split()[0],
        rows=[dict(json.loads(k), count=v) for k,v in sorted(rows.items())],
        failures=failures), sort_keys=True), flush=True)
    return int(bool(failures))

if __name__ == "__main__":
    raise SystemExit(main())
