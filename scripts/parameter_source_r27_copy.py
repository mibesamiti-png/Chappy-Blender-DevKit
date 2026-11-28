"""R27 C fixed-source byte transaction; internal synthetic fixture only."""
from contextlib import contextmanager
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures/cbdk_parameter_experiment.py"
SOURCE_SHA256 = "e645723ff89a99530841e1ccd37ea8d059952eec0f980ac1782d8228e46588e3"
OLD = b'name="Synthetic sphere radius", default=0.75, min=0.2, max=2.0,'
NEW = b'name="Synthetic sphere radius", default=1.15, min=0.2, max=2.0,'
COPY_NAME = "cbdk_parameter_experiment.py"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def candidate_bytes(original):
    # The full pinned SHA limits this to the exact authored class/declaration.
    if type(original) is not bytes or sha(original) != SOURCE_SHA256 or original.count(OLD) != 1 or NEW in original:
        raise ValueError("R27 fixed source or unique token mismatch")
    candidate = original.replace(OLD, NEW, 1)
    if candidate.count(NEW) != 1 or candidate.replace(NEW, OLD, 1) != original:
        raise ValueError("R27 candidate inverse mismatch")
    return candidate


def inverse_bytes(candidate, original):
    if type(candidate) is not bytes or candidate != candidate_bytes(original):
        raise ValueError("R27 candidate bytes are not the permitted change")
    restored = candidate.replace(NEW, OLD, 1)
    if restored != original or sha(restored) != SOURCE_SHA256:
        raise ValueError("R27 restoration mismatch")
    return restored


class FixedCopy:
    """One fixed copy in a newly created, trusted test directory."""
    def __init__(self, directory, original):
        self.path = directory / COPY_NAME
        self.original = original
        self.candidate = candidate_bytes(original)
        with self.path.open("xb") as stream:
            stream.write(original)

    def read_verified(self, stage):
        expected = {"original": self.original, "candidate": self.candidate,
                    "restored": self.original}[stage]
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("R27 isolated copy missing or unsafe")
        actual = self.path.read_bytes()
        if actual != expected:
            raise ValueError("R27 isolated copy differs from fixed permitted bytes")
        return actual

    def _write(self, data):
        # This is a fresh CI-owned directory, not a user-selected source path.
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("R27 refuses unsafe copy replacement")
        with self.path.open("wb") as stream:
            stream.write(data)

    def apply(self):
        self.read_verified("original")
        self._write(self.candidate)
        self.read_verified("candidate")

    def restore(self):
        self._write(inverse_bytes(self.read_verified("candidate"), self.original))
        self.read_verified("restored")

    def recover(self):
        # Failure recovery is not proof of successful inverse restoration.
        if self.path.is_symlink():
            raise ValueError("R27 refuses symlink recovery")
        if not self.path.exists():
            with self.path.open("xb") as stream:
                stream.write(self.original)
        elif self.path.read_bytes() == self.candidate:
            self.restore()
        elif self.path.read_bytes() != self.original:
            self._write(self.original)
        self.read_verified("restored")


@contextmanager
def isolated_copy(directory):
    original = SOURCE.read_bytes()
    candidate_bytes(original)
    directory.mkdir(exist_ok=False)
    tx = FixedCopy(directory, original)
    try:
        yield tx
    finally:
        tx.recover()
        if SOURCE.read_bytes() != original:
            raise AssertionError("R27 original source changed")
