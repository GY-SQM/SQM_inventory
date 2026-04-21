#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT_verify_outbound_refactor_v2.py

Purpose
-------
Verify the first-pass refactor result of:
  engine_modules/inventory_modular/outbound_mixin.py

This script is designed for the user's current workflow:
- Claude refactored outbound_mixin.py
- a backup file like outbound_mixin.py.bak_20260402 exists
- a git checkpoint commit like c408df1 exists

What it checks
--------------
1) target file exists
2) optional backup file exists
3) syntax compile ok
4) target public signatures preserved (vs backup or git baseline)
5) main function size reduction
6) expected helper extraction signals (_co_ / _er_ / _ra_)
7) wording cleanup signal (OUTBOUND vs legacy SOLD)
8) risky SOLD write-patterns
9) changed-file scope vs git baseline
10) optional backup existence note

This is a conservative static verifier.
It does NOT prove business correctness.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import py_compile
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_BASELINE = "c408df1"
DEFAULT_TARGET = "engine_modules/inventory_modular/outbound_mixin.py"
DEFAULT_BACKUP_SUFFIX = ".bak_20260402"

TARGET_FUNCTIONS = [
    "confirm_outbound",
    "execute_reserved",
    "reserve_from_allocation",
]

EXPECTED_HELPERS = [
    "_co_guard_against_double_outbound",
    "_co_run_post_checks",
    "_er_load_reserved_plans",
    "_er_warn_stale_plans",
    "_er_insert_picking_row",
    "_ra_parse_allocation_line",
    "_ra_validate_line_inputs",
    "_ra_resolve_pick_count",
]

# Optional helper names from the user's latest summary.
OPTIONAL_HELPERS = [
    "_co_load_picked_tonbags",
    "_co_validate_customer_sale_ref",
    "_co_build_sold_row_payload",
    "_co_insert_sold_row",
    "_co_insert_outbound_movement",
    "_er_validate_tonbag",
    "_er_apply_pick_transition",
    "_er_record_pick_movement",
    "_ra_check_alloc_conflict",
    "_ra_check_lot_dup",
    "_ra_record_reservation_result",
    "_ra_log_random_selection",
]

# Thresholds are intentionally soft: PASS/WARN, not FAIL.
FUNCTION_WARN_THRESHOLDS = {
    "confirm_outbound": 120,
    "execute_reserved": 120,
    "reserve_from_allocation": 520,
}


@dataclass
class CheckResult:
    name: str
    status: str   # PASS / WARN / FAIL
    detail: str


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=check,
    )


def safe_git(repo: Path, *args: str) -> Tuple[bool, str]:
    try:
        cp = run_git(repo, *args, check=False)
        if cp.returncode == 0:
            return True, (cp.stdout or "").strip()
        return False, ((cp.stderr or "") + "\n" + (cp.stdout or "")).strip()
    except Exception as e:
        return False, str(e)


def get_repo_root(repo: Path) -> Path:
    ok, out = safe_git(repo, "rev-parse", "--show-toplevel")
    if not ok:
        raise RuntimeError(out)
    return Path(out)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compile_check(path: Path) -> Tuple[bool, str]:
    try:
        py_compile.compile(str(path), doraise=True)
        return True, "syntax ok"
    except py_compile.PyCompileError as e:
        return False, str(e)


def parse_classes_and_functions(source: str) -> Tuple[Optional[str], Dict[str, ast.FunctionDef]]:
    tree = ast.parse(source)
    class_name = None
    funcs: Dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    funcs[item.name] = item
    return class_name, funcs


def function_line_span(fn: ast.FunctionDef) -> int:
    end = getattr(fn, "end_lineno", None)
    if end is None:
        return 0
    return int(end) - int(fn.lineno) + 1


def signature_of(func: ast.FunctionDef) -> Dict[str, object]:
    a = func.args
    def names(xs):
        return [x.arg for x in xs]
    return {
        "posonlyargs": names(a.posonlyargs),
        "args": names(a.args),
        "vararg": a.vararg.arg if a.vararg else None,
        "kwonlyargs": names(a.kwonlyargs),
        "kwarg": a.kwarg.arg if a.kwarg else None,
        "defaults_count": len(a.defaults),
        "kw_defaults_count": len([x for x in a.kw_defaults if x is not None]),
    }


def git_show_file(repo: Path, rev: str, rel_path: str) -> str:
    ok, out = safe_git(repo, "show", f"{rev}:{rel_path}")
    if not ok:
        raise RuntimeError(out)
    return out


def changed_files_vs_baseline(repo: Path, baseline: str) -> List[str]:
    ok, out = safe_git(repo, "diff", "--name-only", baseline)
    if not ok:
        return []
    return [x.strip() for x in out.splitlines() if x.strip()]


def unified_diff(repo: Path, baseline: str, rel_path: str) -> str:
    ok, out = safe_git(repo, "diff", "--unified=1", baseline, "--", rel_path)
    return out if ok else ""


def detect_new_sold_write_patterns(diff_text: str) -> List[str]:
    patterns = [
        r"^\+.*STATUS_SOLD",
        r"^\+.*status\s*=\s*['\"]SOLD['\"]",
        r"^\+.*SET\s+status\s*=\s*['\"]SOLD['\"]",
        r"^\+.*->\s*SOLD\b",
    ]
    hits = []
    for p in patterns:
        if re.search(p, diff_text, flags=re.MULTILINE):
            hits.append(p)
    return hits


def scan_text_metrics(source: str) -> Dict[str, int]:
    return {
        "bare_except": len(re.findall(r"(?m)^\s*except\s*:\s*$", source)),
        "except_pass": len(re.findall(r"(?ms)^\s*except[^\n]*:\s*\n\s*pass\s*$", source)),
        "status_sold_mentions": len(re.findall(r"STATUS_SOLD|['\"]SOLD['\"]", source)),
        "status_outbound_mentions": len(re.findall(r"STATUS_OUTBOUND|['\"]OUTBOUND['\"]", source)),
        "double_outbound_blocked_tag": len(re.findall(r"DOUBLE_OUTBOUND_BLOCKED", source)),
        "double_sold_blocked_tag": len(re.findall(r"DOUBLE_SOLD_BLOCKED", source)),
    }


def auto_backup_path(target_path: Path, explicit: Optional[str]) -> Optional[Path]:
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else (target_path.parent / p.name)
    candidate = Path(str(target_path) + DEFAULT_BACKUP_SUFFIX)
    if candidate.exists():
        return candidate
    # Try any backup next to file
    for p in target_path.parent.glob(target_path.name + ".bak_*"):
        return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify outbound_mixin first-pass refactor result")
    parser.add_argument("--repo", default=".", help="Git repo path")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE, help="Git baseline commit")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target relative file path")
    parser.add_argument("--backup", default="", help="Optional explicit backup file path")
    parser.add_argument("--json-out", default="", help="Optional JSON report path")
    args = parser.parse_args()

    results: List[CheckResult] = []
    summary: Dict[str, object] = {}

    try:
        repo_root = get_repo_root(Path(args.repo).resolve())
        results.append(CheckResult("git_repo", "PASS", f"repo root: {repo_root}"))
    except Exception as e:
        print(f"[FAIL] git_repo: {e}")
        return 2

    target_path = repo_root / args.target
    if target_path.exists():
        results.append(CheckResult("target_exists", "PASS", str(target_path)))
    else:
        results.append(CheckResult("target_exists", "FAIL", f"missing: {target_path}"))
        _print(results, summary)
        return 2

    backup_path = auto_backup_path(target_path, args.backup or None)
    if backup_path and backup_path.exists():
        results.append(CheckResult("backup_exists", "PASS", str(backup_path)))
    else:
        results.append(CheckResult("backup_exists", "WARN", "backup file not found; git baseline only"))

    ok, out = safe_git(repo_root, "cat-file", "-e", f"{args.baseline}^{{commit}}")
    if ok:
        results.append(CheckResult("baseline_commit", "PASS", args.baseline))
    else:
        results.append(CheckResult("baseline_commit", "FAIL", out))
        _print(results, summary)
        return 2

    syntax_ok, syntax_msg = compile_check(target_path)
    results.append(CheckResult("syntax_compile", "PASS" if syntax_ok else "FAIL", syntax_msg))

    current_source = read_text(target_path)
    current_class, current_funcs = parse_classes_and_functions(current_source)
    summary["class_name"] = current_class or "(unknown)"

    # Comparison source priority: backup file first, then git baseline
    compare_label = f"git:{args.baseline}"
    compare_source = git_show_file(repo_root, args.baseline, args.target)
    if backup_path and backup_path.exists():
        try:
            compare_source = read_text(backup_path)
            compare_label = f"backup:{backup_path.name}"
        except Exception as _e:
            print(f"[verify_v2] backup 읽기 실패, git baseline 유지: {_e}", file=sys.stderr)
    summary["compare_source"] = compare_label

    _, compare_funcs = parse_classes_and_functions(compare_source)

    # Target function presence + signature + size
    for fn in TARGET_FUNCTIONS:
        if fn not in current_funcs:
            results.append(CheckResult(f"func_exists:{fn}", "FAIL", "missing"))
            continue
        results.append(CheckResult(f"func_exists:{fn}", "PASS", "present"))

        if fn in compare_funcs:
            curr_sig = signature_of(current_funcs[fn])
            base_sig = signature_of(compare_funcs[fn])
            if curr_sig == base_sig:
                results.append(CheckResult(f"signature:{fn}", "PASS", "unchanged"))
            else:
                results.append(CheckResult(f"signature:{fn}", "FAIL", f"changed | compare={compare_label}"))
        else:
            results.append(CheckResult(f"signature:{fn}", "WARN", f"not found in {compare_label}"))

        size = function_line_span(current_funcs[fn])
        threshold = FUNCTION_WARN_THRESHOLDS[fn]
        status = "PASS" if size <= threshold else "WARN"
        results.append(CheckResult(f"size:{fn}", status, f"{size} lines (warn>{threshold})"))

    # Helper presence
    for helper in EXPECTED_HELPERS:
        if helper in current_funcs:
            results.append(CheckResult(f"helper:{helper}", "PASS", "present"))
        else:
            results.append(CheckResult(f"helper:{helper}", "WARN", "missing"))

    optional_found = [h for h in OPTIONAL_HELPERS if h in current_funcs]
    summary["optional_helpers_found"] = optional_found
    results.append(CheckResult("optional_helper_signal", "PASS" if optional_found else "WARN",
                               f"found {len(optional_found)} optional helpers"))

    # Wording / sold-outbound
    metrics = scan_text_metrics(current_source)
    summary["text_metrics"] = metrics

    if metrics["status_outbound_mentions"] > 0:
        results.append(CheckResult("outbound_wording_signal", "PASS", f"OUTBOUND mentions={metrics['status_outbound_mentions']}"))
    else:
        results.append(CheckResult("outbound_wording_signal", "WARN", "no OUTBOUND wording detected"))

    if metrics["double_outbound_blocked_tag"] > 0:
        results.append(CheckResult("double_outbound_tag", "PASS", "DOUBLE_OUTBOUND_BLOCKED found"))
    elif metrics["double_sold_blocked_tag"] > 0:
        results.append(CheckResult("double_outbound_tag", "WARN", "legacy DOUBLE_SOLD_BLOCKED still present"))
    else:
        results.append(CheckResult("double_outbound_tag", "WARN", "no guard tag found"))

    # risky sold write patterns in diff
    diff_text = unified_diff(repo_root, args.baseline, args.target)
    sold_hits = detect_new_sold_write_patterns(diff_text)
    if sold_hits:
        results.append(CheckResult("new_sold_write_patterns", "FAIL", f"possible new SOLD write patterns: {sold_hits}"))
    else:
        results.append(CheckResult("new_sold_write_patterns", "PASS", "no obvious new SOLD write patterns"))

    # changed file scope
    changed = changed_files_vs_baseline(repo_root, args.baseline)
    summary["changed_files_vs_baseline"] = changed
    if not changed:
        results.append(CheckResult("changed_files", "WARN", "no diff vs baseline"))
    elif changed == [args.target]:
        results.append(CheckResult("changed_files", "PASS", "only target changed"))
    else:
        # not always bad, but worth attention
        preview = ", ".join(changed[:6])
        extra = "" if len(changed) <= 6 else f" ... +{len(changed)-6} more"
        results.append(CheckResult("changed_files", "WARN", f"{len(changed)} files changed: {preview}{extra}"))

    # Summaries
    counts = {
        "PASS": sum(1 for r in results if r.status == "PASS"),
        "WARN": sum(1 for r in results if r.status == "WARN"),
        "FAIL": sum(1 for r in results if r.status == "FAIL"),
    }
    summary["result_counts"] = counts

    _print(results, summary)

    if args.json_out:
        payload = {
            "results": [asdict(x) for x in results],
            "summary": summary,
        }
        Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON report saved: {args.json_out}")

    return 1 if counts["FAIL"] > 0 else 0


def _print(results: List[CheckResult], summary: Dict[str, object]) -> None:
    print("=" * 88)
    print("Outbound refactor verification report")
    print("=" * 88)
    for r in results:
        print(f"[{r.status:<4}] {r.name}: {r.detail}")

    print("-" * 88)
    print(f"class_name      : {summary.get('class_name')}")
    print(f"compare_source  : {summary.get('compare_source')}")
    print(f"optional_helpers: {len(summary.get('optional_helpers_found', []))}")
    metrics = summary.get("text_metrics", {})
    if metrics:
        print(f"text_metrics    : {metrics}")
    changed = summary.get("changed_files_vs_baseline", [])
    if isinstance(changed, list):
        print(f"changed_files   : {len(changed)}")
    rc = summary.get("result_counts", {})
    print(f"summary         : PASS={rc.get('PASS', 0)} WARN={rc.get('WARN', 0)} FAIL={rc.get('FAIL', 0)}")
    print("=" * 88)


if __name__ == "__main__":
    raise SystemExit(main())
