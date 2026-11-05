"""Make a clean CBDK Windows test kit using only tracked repository files."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "Chappy-Blender-DevKit"


def build(output: Path) -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    files = [Path(p.decode("utf-8")) for p in tracked if p]
    if not files:
        raise RuntimeError("No tracked files")
    output.parent.mkdir(parents=True, exist_ok=True)
    seen = []
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in sorted(files):
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unexpected path from git ls-files")
            absolute = ROOT / relative
            if absolute.is_symlink() or not absolute.is_file():
                raise ValueError(f"Unexpected tracked file: {relative}")
            if relative.as_posix() == "reports/README.md":
                # Only a public explanatory stub is tracked in this folder.
                continue
            if relative.parts[0] in {"input_sources_private", "reports"}:
                raise ValueError("Refusing to package private or generated sources")
            archive.write(absolute, (Path(PREFIX) / relative).as_posix())
            seen.append(str(relative))
    required = ["run_blender_tests_windows.bat", "scripts/windows_run_blender_tests.ps1",
                "cbdk/evidence.py", "docs/TEST_ENVIRONMENT.md"]
    for name in required:
        if name not in seen:
            raise RuntimeError("Missing required kit file: " + name)
    return len(seen)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "CBDK_v0.10_Windows_Blender_DevKit.zip")
    args = parser.parse_args(argv)
    count = build(args.output)
    print(f"Packaged {count} tracked files into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
