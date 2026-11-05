"""Strict, non-promotional reporting of optional background Blender Undo/Redo.

A completed nudge is not evidence that native Undo or GUI shortcuts worked.
This module never reports a skipped background API as a passed runtime test.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PREFIX = "CBDK_UNDO_PROBE "
_UNDO = {"passed", "unavailable"}
_REDO = {"passed", "unavailable", "not_attempted"}


def build_report(blender_version: str, undo: str, redo: str) -> dict:
    """Describe what was *observed*, with GUI hotkeys explicitly excluded."""
    if not isinstance(blender_version, str) or not blender_version.strip():
        raise ValueError("Missing Blender version")
    if undo not in _UNDO or redo not in _REDO:
        raise ValueError("Invalid Undo/Redo result")
    if (undo == "unavailable") != (redo == "not_attempted"):
        raise ValueError("Redo must be not_attempted exactly when Undo was unavailable")
    if undo == "passed" and redo == "passed":
        status = "verified_background"
    elif undo == "passed":
        status = "partial_background"
    else:
        status = "unavailable_in_background"
    return {
        "schema_version": 1,
        "suite": "native_undo_redo_probe",
        "blender": blender_version,
        "operator_completed": True,
        "nudge_delta_verified": True,
        "undo_status": undo,
        "redo_status": redo,
        "status": status,
        "gui_hotkey_verified": False,
        "user_project_tested": False,
    }


def validate_report(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Undo probe is not a JSON object")
    required = {
        "schema_version", "suite", "blender", "operator_completed",
        "nudge_delta_verified", "undo_status", "redo_status",
        "status", "gui_hotkey_verified", "user_project_tested",
    }
    if set(data) != required:
        raise ValueError("Undo probe report fields missing or unexpected")
    if data["schema_version"] != 1 or data["suite"] != "native_undo_redo_probe":
        raise ValueError("Unknown Undo probe report schema")
    if data["operator_completed"] is not True or data["nudge_delta_verified"] is not True:
        raise ValueError("Nudge was not verified")
    if data["gui_hotkey_verified"] is not False or data["user_project_tested"] is not False:
        raise ValueError("Background suite cannot certify GUI or user scenes")
    expected = build_report(data["blender"], data["undo_status"], data["redo_status"])
    if data != expected:
        raise ValueError("Undo/Redo verification claim does not match observation")
    return data


def parse_log(log: str) -> dict:
    if not isinstance(log, str) or len(log) > 2_000_000:
        raise ValueError("Missing or oversized Undo probe log")
    found = [line.split(PREFIX, 1)[1] for line in log.splitlines()
             if line.startswith(PREFIX)]
    if len(found) != 1:
        raise ValueError("Exactly one Undo probe record is required")
    try:
        return validate_report(json.loads(found[0]))
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Malformed Undo probe record") from exc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate Blender background Undo evidence")
    parser.add_argument("log", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    report = parse_log(args.log.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("Undo/Redo background probe: " + report["status"] +
          " (GUI Ctrl+Z / Ctrl+Shift+Z not tested)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
