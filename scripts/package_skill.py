"""Build standalone Codex skill ZIP and portable ChatGPT/Codex skill-only plugin ZIP.

Canonical source: .agents/skills/chappy-blender-devkit/ .
No network access, code execution of source files, or private addon sources.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SKILL_NAME = "chappy-blender-devkit"
VERSION = "1.1.0"
REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / ".agents" / "skills" / SKILL_NAME


def source_files() -> dict[str, bytes]:
    expected = [
        "SKILL.md",
        "agents/openai.yaml",
        "references/WORKFLOW.md",
        "references/QUALITY_GATES.md",
        "references/MILESTONE.md",
        "references/EXAMPLES.md",
    ]
    files = {}
    for rel in expected:
        path = SKILL_ROOT / rel
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing or linked canonical skill file: {rel}")
        # Git on Windows may checkout CRLF; normalize to portable LF so the
        # frontmatter regex and ZIP contents are identical across operating systems.
        files[rel] = path.read_text(encoding="utf-8").encode("utf-8")
    front = files["SKILL.md"].decode("utf-8")
    if not re.search(r"(?m)^name: chappy-blender-devkit$", front):
        raise ValueError("Skill metadata must have its stable name")
    if not re.search(r"(?m)^description: .+", front):
        raise ValueError("Skill metadata must have a description")
    return files


def _zip_entries(path: Path, entries: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for filename, data in sorted(entries.items()):
            info = ZipInfo(filename, (2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)


def build_bundles(output_dir: Path) -> tuple[Path, Path]:
    files = source_files()
    standalone = output_dir / f"CBDK_Skill_v{VERSION}.zip"
    plugin = output_dir / f"CBDK_Skill_Plugin_v{VERSION}.zip"
    _zip_entries(standalone, {f"{SKILL_NAME}/{path}": data for path, data in files.items()})

    manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": SKILL_NAME,
        "version": VERSION,
        "description": ("A skill-only ChatGPT/Codex workflow for safe Blender addon "
                        "development with CBDK, code reuse and verified CI reporting."),
        "repository": "https://github.com/mibesamiti-png/Chappy-Blender-DevKit",
    }
    entries = {"plugin.json": (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")}
    entries.update({f"skills/{SKILL_NAME}/{path}": data for path, data in files.items()})
    _zip_entries(plugin, entries)
    return standalone, plugin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Package CBDK standalone skill + skill-only portable plugin")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "dist")
    args = parser.parse_args(argv)
    for path in build_bundles(args.output_dir):
        print(f"Built {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
