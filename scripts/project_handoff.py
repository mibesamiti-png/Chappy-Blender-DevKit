"""Validate and render CBDK's durable GitHub development state.

This script only reads public-safe tracked metadata; it does not execute private
Blender addon source, infer legal approval or claim unavailable CI results.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path("docs/project/STATE.json")
HANDOFF = Path("docs/PROJECT_HANDOFF.md")
BT = chr(96)
STATES = {"implemented": "実装済", "partial": "一部実装",
          "not_implemented": "未実装", "deferred": "保留"}
VERIFY = {"python": "Pythonテスト", "blender_ci": "Blender CI",
          "manual_pending": "手動確認待ち", "not_tested": "未検証"}
ISSUES = {"open", "mitigated", "fixed"}
ACTIONS = {"todo", "in_progress", "done", "deferred"}
REPO_URL = "https://github.com/mibesamiti-png/Chappy-Blender-DevKit/"


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 600:
        raise ValueError("Missing or invalid text: " + field)
    if any(ord(ch) < 32 and ch != "\t" for ch in value):
        raise ValueError("Invalid control character: " + field)
    return value


def _read_json(path, *, max_bytes=100_000):
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError("Missing or oversized state file: " + str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("State file must contain JSON object: " + str(path))
    return data


def _ident(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{2,8}-\d{3}", value):
        raise ValueError("Invalid " + label + " ID")
    return value


def _records(items, label, allowed):
    if not isinstance(items, list):
        raise ValueError(label + " must be a list")
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid " + label + " entry")
        code = _ident(item.get("id"), label)
        if code in ids:
            raise ValueError("Duplicate " + label + " ID: " + code)
        ids.add(code)
        _text(item.get("title"), label + ".title")
        if item.get("status") not in allowed:
            raise ValueError("Unexpected status for " + code)
    return items


def validate_state(root=ROOT):
    root = root.resolve()
    state = _read_json(root / STATE)
    if state.get("schema_version") != 1 or state.get("repository") != "mibesamiti-png/Chappy-Blender-DevKit":
        raise ValueError("Unsupported project state schema or repository")
    release = state.get("release")
    if not isinstance(release, dict):
        raise ValueError("Release details missing")
    current = release.get("current")
    if not isinstance(current, str) or not re.fullmatch(r"\d+\.\d+\.\d+", current):
        raise ValueError("Invalid release version")
    with (root / "pyproject.toml").open("rb") as source:
        actual_version = tomllib.load(source)["project"]["version"]
    if actual_version != current:
        raise ValueError("State version differs from pyproject.toml: " + current + " vs " + actual_version)

    catalog = _read_json(root / "catalog/authored_parts.json")
    features = _read_json(root / "catalog/addon_features.json")
    if catalog.get("schema_version") != 1 or features.get("schema_version") != 1:
        raise ValueError("Catalog schema mismatch")
    parts_list, features_list = catalog.get("parts"), features.get("features")
    if not isinstance(parts_list, list) or not isinstance(features_list, list):
        raise ValueError("Catalog entry list missing")
    try:
        part_ids = [x["part_id"] for x in parts_list]
        feature_ids = [x["id"] for x in features_list]
    except (TypeError, KeyError) as exc:
        raise ValueError("Missing authored IDs") from exc
    if (len(part_ids) != len(set(part_ids)) or len(feature_ids) != len(set(feature_ids))):
        raise ValueError("Duplicate authored IDs")
    for item in parts_list:
        path = item.get("source", "")
        if (not isinstance(path, str) or not path.startswith("parts/blender/")
                or not (root / path).is_file() or item.get("approved") is not False):
            raise ValueError("Unexpected source or approval for authored part")
    for item in features_list:
        path = item.get("source", "")
        if (not isinstance(path, str) or not path.startswith("templates/modular_preview/features/")
                or not (root / path).is_file() or not set(item.get("required_parts", [])).issubset(part_ids)):
            raise ValueError("Unexpected source/dependencies for authored feature")

    requirements = _records(state.get("requirements"), "requirements", set(STATES))
    for item in requirements:
        if item.get("verification") not in VERIFY:
            raise ValueError("Invalid requirement verification")
        source = item.get("source")
        if not isinstance(source, str):
            raise ValueError("Requirement source must be a file path or empty")
        if source:
            path = root / source
            if not path.resolve().is_relative_to(root) or not path.is_file():
                raise ValueError("Requirement source missing: " + source)
        _text(item.get("note"), "requirement note")
    issues = _records(state.get("known_issues"), "known_issues", ISSUES)
    tasks = _records(state.get("next_actions"), "next_actions", ACTIONS)
    all_requirements = {x["id"] for x in requirements}
    for issue in issues:
        if issue.get("related_requirement") not in all_requirements:
            raise ValueError("Unknown requirement on issue: " + issue["id"])
        _text(issue.get("workaround"), "issue workaround")
    priorities = set()
    for task in tasks:
        rank = task.get("priority")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1 or rank in priorities:
            raise ValueError("Invalid or duplicate task priority")
        priorities.add(rank)
        _text(task.get("acceptance"), "task acceptance")
    decisions = state.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("Architectural decisions missing")
    seen_decisions = set()
    for decision in decisions:
        code = _ident(decision.get("id"), "decision")
        if code in seen_decisions:
            raise ValueError("Duplicate decision ID")
        seen_decisions.add(code)
        _text(decision.get("decision"), "decision")
        _text(decision.get("note"), "decision note")

    verified = state.get("last_verified")
    if not isinstance(verified, dict) or verified.get("result") != "success":
        raise ValueError("Unverified test evidence cannot be recorded as success")
    last = verified.get("release")
    if not isinstance(last, str) or not re.fullmatch(r"\d+\.\d+\.\d+", last):
        raise ValueError("Invalid verified version")
    if tuple(map(int, last.split("."))) > tuple(map(int, current.split("."))):
        raise ValueError("Verified release is newer than current source")
    for link in (verified.get("pr_url"), *(verified.get(k, {}).get("run_url") for k in
                                        ("python", "windows", "blender", "package"))):
        if not isinstance(link, str) or not link.startswith(REPO_URL):
            raise ValueError("Missing or unrecognized GitHub test evidence URL")
    count = verified["python"].get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("Invalid recorded unittest count")
    if not isinstance(state.get("maintenance_policy"), dict):
        raise ValueError("Maintenance policy is required")
    return {"state": state, "parts": sorted(part_ids), "features": sorted(feature_ids)}


def _safe(value):
    return str(value).replace("|", "｜").replace("\n", " ")


def _code(value):
    return BT + _safe(value) + BT


def render_handoff(data):
    s = data["state"]
    current = s["release"]["current"]
    ev = s["last_verified"]
    lines = [
        "# CBDK｜新しいチャットの開発引き継ぎ",
        "",
        "このファイルが新しい会話の入口。GitHub main と最新の実際のCIを優先する。古いREADMEやチャットの印象で開発状況を判断しない。",
        "",
        "## 新しいチャットで最初にすること",
        "",
        "1. リポジトリ mibesamiti-png/Chappy-Blender-DevKit の main を確認する。",
        "2. このファイル、docs/project/STATE.json、docs/PROJECT_SPEC.md、AGENTS.md を読む。",
        "3. pyproject.tomlのバージョンと、部品/機能カタログを照合する。",
        "4. 前回のCI成功が現行コミットのものか確認する。未実施テストを成功とみなさない。",
        "5. 次の優先タスクをブランチで実装し、テストと状態を更新してPRを作る。",
        "",
        "## 最新の開発状況",
        "",
        "- 現在のバージョン: " + _code(current),
        "- 開発段階: " + _safe(s["release"]["stage"]),
        "- 最新の節目: " + _safe(s["release"]["milestone"]),
        "- 次の予定リリース: " + _code(s["release"]["next_planned"]),
        "- 自作部品: " + str(len(data["parts"])) + "件 (" + ", ".join(data["parts"]) + ")",
        "- 組み込み機能: " + str(len(data["features"])) + "件 (" + ", ".join(data["features"]) + ")",
        "- 部品の正式採用と再配布ライセンス確認は未完了。個人用プレビューのみ。",
        "",
        "## 仕様・実装・未実装の一覧",
        "",
        "| 要件 | 機能 | 状態 | 検証種別 | 備考 |",
        "|---|---|---|---|---|",
    ]
    for item in s["requirements"]:
        lines.append("| " + _code(item["id"]) + " | " + _safe(item["title"]) + " | "
                     + STATES[item["status"]] + " | " + VERIFY[item["verification"]]
                     + " | " + _safe(item["note"]) + " |")
    lines.extend(["", "## 既知の問題・制約", "", "| ID | 重要度 | 状態 | 内容と回避策 |",
                  "|---|---|---|---|"])
    for item in s["known_issues"]:
        lines.append("| " + _code(item["id"]) + " | " + _safe(item["severity"])
                     + " | " + _safe(item["status"]) + " | "
                     + _safe(item["title"]) + "。回避策: " + _safe(item["workaround"]) + " |")
    lines.extend(["", "## 次にやること（優先順）", ""])
    for item in sorted(s["next_actions"], key=lambda x: x["priority"]):
        lines.append(str(item["priority"]) + ". " + _code(item["id"]) + " **"
                     + _safe(item["title"]) + "** (" + _safe(item["status"])
                     + ")。完了条件: " + _safe(item["acceptance"]))
    lines.extend(["", "## 前回、実際に確認されたテスト", "",
        "- 対象リリース: v" + _safe(ev["release"]) + " / " + _safe(ev["observed_on"]),
        "- Python: " + str(ev["python"]["count"]) + "件成功; "
          + ", ".join(ev["python"]["versions"]) + " [実行記録](" + ev["python"]["run_url"] + ")",
        "- Windows PowerShell: " + ", ".join(ev["windows"]["versions"])
          + " [実行記録](" + ev["windows"]["run_url"] + ")",
        "- Blender: " + ", ".join(ev["blender"]["versions"])
          + "; 共通部品 " + str(ev["blender"]["part_count"]) + "件; 生成レシピ "
          + str(ev["blender"]["recipe_count"]) + "構成 [実行記録](" + ev["blender"]["run_url"] + ")",
        "- Windowsキット生成 [実行記録](" + ev["package"]["run_url"] + ")",
        "- 前回の[PR](" + ev["pr_url"] + ")",
        "- 注意: " + _safe(ev["limitations"]),
        "",
        "## 継続する設計判断", ""])
    for item in s["decisions"]:
        lines.append("- " + _code(item["id"]) + " " + _safe(item["decision"])
                     + "。" + _safe(item["note"]))
    lines.extend([
        "", "## 更新・プライバシールール", "",
        "- 元の私有アドオンソース、派生レポート、個人情報、認証情報をGitHubに上げない。",
        "- CIの成功は部品の正式承認・ライセンス許諾・GUIの操作感を証明しない。",
        "- GitHubからBlenderへの直接インストールは保留。ユーザーの意思なく実装しない。",
        "- 各節目でdocs/project/STATE.jsonを更新し、この引き継ぎを再生成する。",
        "- 実行: python scripts/project_handoff.py --write",
        "- 照合: python scripts/project_handoff.py --check",
        "",
        "## 詳細と正本", "",
        "- [開発状態台帳](project/STATE.json)（正本、機能・バグ・タスク・CI）",
        "- [最新の開発仕様](PROJECT_SPEC.md)",
        "- [実装履歴](PROGRESS.md)",
        "- [開発時の安全ルール](../AGENTS.md)",
        "",
        "この文書はSTATE.jsonから自動生成。内容の編集はSTATE.json側で行う。",
        "",
    ])
    return "\n".join(lines)


def write_ci_snapshot(root, output, log):
    """Require a successful actual unittest log before writing any success."""
    text = log.read_text(encoding="utf-8")
    tests = re.findall(r"^Ran (\d+) tests? in .+$", text, flags=re.MULTILINE)
    if not tests or not re.search(r"^OK(?: \(.+\))?$", text, flags=re.MULTILINE) or "FAILED" in text:
        raise ValueError("Cannot record a missing or unsuccessful Python unittest run")
    state = validate_state(root)["state"]
    result = {
        "schema_version": 1,
        "kind": "cbdk_python_ci_observation",
        "release": state["release"]["current"],
        "python_tests_passed": int(tests[-1]),
        "python_version": sys.version.split()[0],
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "blender_runtime_verified_by_this_job": False,
        "note": "This job does not verify Blender GUI or legal code approval.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None, *, root=ROOT):
    parser = argparse.ArgumentParser(description="GitHub development-state handoff")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--validate", action="store_true")
    choice.add_argument("--write", action="store_true")
    choice.add_argument("--check", action="store_true")
    choice.add_argument("--ci-snapshot", type=Path)
    parser.add_argument("--python-log", type=Path)
    args = parser.parse_args(argv)
    try:
        data = validate_state(root)
        target = root / HANDOFF
        if args.write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_handoff(data), encoding="utf-8")
            print("Wrote " + str(HANDOFF))
        elif args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != render_handoff(data):
                raise ValueError("Handoff out of sync; run python scripts/project_handoff.py --write")
            print("Project handoff is current")
        elif args.ci_snapshot:
            if args.python_log is None:
                raise ValueError("--python-log is required for --ci-snapshot")
            write_ci_snapshot(root, args.ci_snapshot, args.python_log)
            print("Wrote CI test observation: " + str(args.ci_snapshot))
        else:
            print("Valid v" + data["state"]["release"]["current"] + " state, "
                  + str(len(data["parts"])) + " parts, " + str(len(data["features"])) + " features")
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("Development state validation failed: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
