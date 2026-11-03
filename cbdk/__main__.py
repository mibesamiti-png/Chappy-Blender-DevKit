"""Command line entry: python -m cbdk ..."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dedup import duplicates
from .report import write_json, write_report
from .scanner import scan
from .search import search


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cbdk", description="Blender addon static code inventory and similarity inspection")
    sub = parser.add_subparsers(dest="command", required=True)
    scan_cmd = sub.add_parser("scan", help="Analyze source tree without running code")
    scan_cmd.add_argument("sources", nargs="+", help="Files or directories")
    scan_cmd.add_argument("--output", default="reports/latest", help="Output folder")
    scan_cmd.add_argument("--threshold", type=float, default=.82, help="Near match heuristic threshold")
    scan_cmd.add_argument("--limit", type=int, default=200, help="Maximum near matches saved")
    search_cmd = sub.add_parser("search", help="Search generated static catalog")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    search_cmd.add_argument("--limit", type=int, default=15)
    compare_cmd = sub.add_parser("compare", help="Re-run duplicate inspection on a catalog")
    compare_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    compare_cmd.add_argument("--threshold", type=float, default=.82)
    args = parser.parse_args(argv)
    if args.command == "scan":
        if not 0 <= args.threshold <= 1:
            parser.error("--threshold must be 0..1")
        cat = scan(args.sources)
        if not cat["files"]:
            print("No Python files found. Check sources.")
            return 2
        dup = duplicates(cat, threshold=args.threshold, limit=args.limit)
        folder = Path(args.output)
        write_json(folder / "catalog.json", cat)
        write_json(folder / "duplicates.json", dup)
        summary = write_report(folder / "report.md", cat, dup)
        write_json(folder / "metrics.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"Reports: {folder.resolve()}")
        return 0 if not summary["parse_errors"] else 1
    if args.command == "search":
        cat = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        results = search(cat, args.query, limit=args.limit)
        if not results:
            print("No matching symbols.")
        for item in results:
            print(f"{item['score']:>2}  {item['id']}  {item['source']}:{item['line']}  {item['name']} [{item['category']}]")
        return 0
    if args.command == "compare":
        cat = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        dup = duplicates(cat, threshold=args.threshold)
        print(json.dumps({"exact_groups": len(dup["exact_groups"]), "shape_groups": len(dup["shape_groups"]),
                          "near_candidate_pairs": dup["near_total"], "near_candidates": dup["near_candidates"][:15]},
                         ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
