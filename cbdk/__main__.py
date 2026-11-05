"""Command line entry: python -m cbdk ..."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .curation import (build_review_queue, decide, read_registry, register_candidate,
                       render_review_markdown, write_queue, write_registry)
from .isolation import inspect_candidate, extract_candidate
from .bundle import inspect_bundle, extract_bundle
from .crossfile import inspect_crossfile, extract_crossfile
from .blender_audit import audit_blender_dependencies
from .contracts import make_blender_contracts, write_contracts
from .evidence import verify_authored_parts, save_evidence, check_evidence_freshness
from .part_matrix import evidence_paths, summarize_parts, write_matrix, render_matrix_markdown
from .addon_builder import build_addon
from .feature_catalog import load_feature_catalog, plan_features
from .modular_builder import validate_modular_recipe
from .registration_draft import propose_registration, write_draft
from .registration_scaffold import scaffold_from_saved_draft
from .dedup import duplicates
from .report import write_json, write_report
from .scanner import scan
from .search import search


def _json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cbdk", description="Blender addon static inventory and manual curation")
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
    triage_cmd = sub.add_parser("triage", help="Create an evidence-based manual duplicate review queue")
    triage_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    triage_cmd.add_argument("--duplicates", default="reports/latest/duplicates.json")
    triage_cmd.add_argument("--output", default="reports/latest/review_queue.json")
    register_cmd = sub.add_parser("register", help="Assign a durable part ID to a manually reviewed candidate")
    register_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    register_cmd.add_argument("--registry", default="reports/latest/registry.json")
    for opt in ("candidate", "part-id", "name", "purpose", "origin", "license-id", "license-evidence", "reviewer"):
        register_cmd.add_argument("--" + opt, required=True)
    register_cmd.add_argument("--variant-of")
    decide_cmd = sub.add_parser("decide", help="Record a human decision; never auto-approve")
    decide_cmd.add_argument("--registry", default="reports/latest/registry.json")
    for opt in ("part-id", "decision", "reviewer", "reason"):
        decide_cmd.add_argument("--" + opt, required=True)
    list_cmd = sub.add_parser("parts", help="List registered, NOT YET VERIFIED parts")
    list_cmd.add_argument("--registry", default="reports/latest/registry.json")

    isolate_cmd = sub.add_parser("isolate", help="Inspect/extract one conservative top-level function (never execute it)")
    isolate_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    isolate_cmd.add_argument("--candidate", required=True, help="CND-* ID from static catalog")
    isolate_cmd.add_argument("--source", required=True, help="Original Python file to verify by SHA-256")
    isolate_cmd.add_argument("--output", help="New .py file path; omit to inspect only")

    bundle_cmd = sub.add_parser("bundle", help="Inspect/extract reviewed candidate plus same-file helper DAG")
    bundle_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    bundle_cmd.add_argument("--candidate", required=True, help="Root CND-* ID")
    bundle_cmd.add_argument("--source", required=True, help="Original .py file (SHA-verified)")
    bundle_cmd.add_argument("--output", help="New output .py; omit to inspect graph only")
    bundle_cmd.add_argument("--max-functions", type=int, default=64)

    cross_cmd = sub.add_parser("crossfile", help="Inspect/extract a review-only DAG across explicit relative Python imports")
    cross_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    cross_cmd.add_argument("--candidate", required=True)
    cross_cmd.add_argument("--source", required=True)
    cross_cmd.add_argument("--sources-root", required=True)
    cross_cmd.add_argument("--output", help="New .py to write; omit for inspection")
    cross_cmd.add_argument("--max-functions", type=int, default=64)
    cross_cmd.add_argument("--max-files", type=int, default=12)

    audit_cmd = sub.add_parser("audit-blender", help="Static report of bpy/bmesh/mathutils and context dependencies")
    audit_cmd.add_argument("--catalog", default="reports/latest/catalog.json")
    audit_cmd.add_argument("--output", default="reports/latest/blender_audit.json")

    contracts_cmd = sub.add_parser('contracts', help='Create human-review Blender runtime test contracts from an API audit')
    contracts_cmd.add_argument('--audit', default='reports/latest/blender_audit.json')
    contracts_cmd.add_argument('--output', default='reports/latest/blender_contracts.json')

    verify_cmd = sub.add_parser('verify-parts', help='Run trusted Blender parts tests and save environment-specific evidence')
    verify_cmd.add_argument('--blender', required=True, help='Trusted Blender executable path')
    verify_cmd.add_argument('--timeout', type=int, default=90)
    verify_cmd.add_argument('--output', default='reports/latest/parts_evidence.json')

    status_cmd = sub.add_parser('evidence-status', help='Check the current hashes against a parts smoke report (not authentication)')
    status_cmd.add_argument('--evidence', default='reports/latest/parts_evidence.json')

    matrix_cmd = sub.add_parser('part-matrix', help='Compare locally saved smoke evidence across Blender versions (review only)')
    matrix_cmd.add_argument('--catalog', default='catalog/authored_parts.json')
    matrix_cmd.add_argument('--evidence-dir', default=None)
    matrix_cmd.add_argument('--evidence', action='append', default=[])
    matrix_cmd.add_argument('--output', default='reports/latest/parts_matrix.json')

    addon_cmd = sub.add_parser('build-addon', help='Build allowlisted, private development-preview Blender addon ZIP')
    addon_cmd.add_argument('--recipe', default='recipes/mesh_inspector.json')
    addon_cmd.add_argument('--output', default='dist/CBDK_Mesh_Inspector_Preview.zip')
    addon_cmd.add_argument('--preview-unapproved', action='store_true',
                           help='Required explicit opt-in; output is NOT a release or approved component')

    feature_cmd = sub.add_parser('feature-list', help='List trusted authored preview features; no approval implied')
    feature_cmd.add_argument('--output', default=None)

    plan_cmd = sub.add_parser('addon-plan', help='Inspect feature dependency closure and Blender compatibility without building ZIP')
    plan_cmd.add_argument('--recipe', default='recipes/modular_combined.json')
    plan_cmd.add_argument('--target-blender', default=None)
    plan_cmd.add_argument('--output', default=None)

    draft_cmd = sub.add_parser('registration-draft',
                               help='Propose manual registration steps without approving or executing code')
    draft_cmd.add_argument('--feature-id', required=True)
    draft_cmd.add_argument('--requires-part', action='append', required=True)
    draft_cmd.add_argument('--new-part-id')
    draft_cmd.add_argument('--new-part-module')
    draft_cmd.add_argument('--output',
                           help='Optional fresh JSON report under reports/latest/ (never overwrites)')

    scaffold_cmd = sub.add_parser('registration-tests',
                                  help='Create a TODO-failing local unittest skeleton from a saved draft')
    scaffold_cmd.add_argument('--draft', required=True,
                              help='Saved registration draft JSON under reports/latest/')

    addon_cmd.add_argument('--target-blender', default=None,
                           help='Optional target version, e.g. 4.4.3; fail if incompatible')

    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            if not 0 <= args.threshold <= 1 or args.limit < 0:
                parser.error("--threshold must be 0..1 and --limit >= 0")
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
            results = search(_json(args.catalog), args.query, limit=args.limit)
            if not results:
                print("No matching symbols.")
            for item in results:
                print(f"{item['score']:>2}  {item['id']}  {item['source']}:{item['line']}  {item['name']} [{item['category']}]")
            return 0
        if args.command == "compare":
            dup = duplicates(_json(args.catalog), threshold=args.threshold)
            print(json.dumps({"exact_groups": len(dup["exact_groups"]), "shape_groups": len(dup["shape_groups"]),
                              "near_candidate_pairs": dup["near_total"], "near_candidates": dup["near_candidates"][:15]},
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == "triage":
            queue = build_review_queue(_json(args.catalog), _json(args.duplicates))
            write_queue(args.output, queue)
            out_md = Path(args.output).with_suffix(".md")
            out_md.write_text(render_review_markdown(queue), encoding="utf-8")
            print(f"Review findings: {queue['finding_count']} / {args.output} / {out_md}")
            return 0
        if args.command == "register":
            registry = read_registry(args.registry)
            entry = register_candidate(_json(args.catalog), registry, candidate_id=args.candidate,
                                       part_id=args.part_id, name=args.name, purpose=args.purpose,
                                       origin=args.origin, license_id=args.license_id,
                                       license_evidence=args.license_evidence,
                                       reviewer=args.reviewer, variant_of=args.variant_of)
            write_registry(args.registry, registry)
            print(f"Registered {entry['part_id']} ({entry['status']}; NOT approved/verified)")
            return 0
        if args.command == "decide":
            registry = read_registry(args.registry)
            entry = decide(registry, part_id=args.part_id, decision=args.decision,
                           reviewer=args.reviewer, reason=args.reason)
            write_registry(args.registry, registry)
            print(f"{entry['part_id']}: {entry['status']} (NOT verified)")
            return 0
        if args.command == "isolate":
            catalog = _json(args.catalog)
            result = (extract_candidate(catalog, args.candidate, args.source, args.output)
                      if args.output else inspect_candidate(catalog, args.candidate, args.source))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["eligible_for_review_extraction"] else 1
        if args.command == "bundle":
            catalog = _json(args.catalog)
            report = (extract_bundle(catalog, args.candidate, args.source, args.output,
                                     max_functions=args.max_functions) if args.output else
                      inspect_bundle(catalog, args.candidate, args.source, max_functions=args.max_functions))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["eligible_for_review_extraction"] else 1
        if args.command == "crossfile":
            catalog = _json(args.catalog)
            report = (extract_crossfile(catalog, args.candidate, args.source, args.output,
                                        sources_root=args.sources_root,
                                        max_functions=args.max_functions, max_files=args.max_files)
                      if args.output else
                      inspect_crossfile(catalog, args.candidate, args.source,
                                        sources_root=args.sources_root,
                                        max_functions=args.max_functions, max_files=args.max_files))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["eligible_for_review_extraction"] else 1
        if args.command == "audit-blender":
            report = audit_blender_dependencies(_json(args.catalog))
            write_json(Path(args.output), report)
            print(f"Blender API symbols: {report['blender_related_symbols']} / "
                  f"context sensitive: {report['context_sensitive_symbols']} / "
                  f"output: {args.output}")
            return 0
        if args.command == 'contracts':
            contracts = make_blender_contracts(_json(args.audit))
            write_contracts(args.output, contracts)
            print(f"Blender test contracts: {contracts['contracts_count']} / output: {args.output}")
            return 0
        if args.command == 'verify-parts':
            result = verify_authored_parts(args.blender, timeout=args.timeout)
            save_evidence(args.output, result)
            print(f"Blender parts: {result['run_status']}; evidence: {args.output}; "
                  f"parts passed: {len(result['parts'])}; approved: no")
            return 0 if result['run_status'] == 'passed' else 1
        if args.command == 'evidence-status':
            result = check_evidence_freshness(_json(args.evidence))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['fresh'] else 1
        if args.command == 'registration-draft':
            report = propose_registration(args.feature_id, args.requires_part,
                                          new_part_id=args.new_part_id,
                                          new_part_module=args.new_part_module)
            if args.output:
                saved = write_draft(report, relative_path=args.output)
                print(f"Registration proposal saved: {saved} (review-only; NOT approved)")
            else:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'registration-tests':
            target = scaffold_from_saved_draft(args.draft)
            print(f"Review-only failing test skeleton: {target}")
            print("TODO assertions intentionally fail. Not imported, approved, or verified.")
            return 0
        if args.command == 'feature-list':
            catalog = load_feature_catalog(root=Path(__file__).resolve().parent.parent)
            report = {'schema_version': 1, 'kind': 'trusted_preview_features',
                      'preview_only': True, 'approved': False,
                      'features': [catalog[k] for k in sorted(catalog)]}
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if args.output:
                write_json(Path(args.output), report)
            return 0
        if args.command == 'addon-plan':
            recipe = _json(args.recipe)
            _name, selected = validate_modular_recipe(recipe)
            report = plan_features(selected, root=Path(__file__).resolve().parent.parent,
                                   target_blender=args.target_blender)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if args.output:
                write_json(Path(args.output), report)
            return 0
        if args.command == 'build-addon':
            result = build_addon(args.recipe, args.output,
                                 preview_unapproved=args.preview_unapproved,
                                 target_blender=args.target_blender)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'part-matrix':
            chosen_dir = args.evidence_dir if args.evidence_dir is not None else (None if args.evidence else 'reports/latest')
            paths = evidence_paths(chosen_dir, args.evidence)
            matrix = summarize_parts(_json(args.catalog), paths)
            write_matrix(args.output, matrix)
            md = Path(args.output).with_suffix('.md')
            md.write_text(render_matrix_markdown(matrix), encoding='utf-8')
            print(f"Part matrix: {matrix['valid_evidence_count']} valid evidence file(s), "
                  f"{matrix['invalid_evidence_count']} rejected; output: {args.output}")
            for part in matrix['parts']:
                print(f"  {part['part_id']}: {', '.join(part['runtime_versions']) or 'not recorded'} "
                      f"(approved by evidence: no)")
            return 0 if matrix['has_runtime_evidence'] and not matrix['invalid_evidence_count'] else 1
        if args.command == "parts":
            parts = read_registry(args.registry)["parts"]
            for item in sorted(parts, key=lambda x: x["part_id"]):
                print(f"{item['part_id']}  {item['status']:8}  {item['name']}  [{item['license_id']}]")
            print(f"Parts: {len(parts)}. No entries are automatically approved or runtime tested.")
            return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError, FileExistsError) as exc:
        parser.exit(2, f"CBDK error: {exc}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
