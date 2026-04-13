# -*- coding: utf-8 -*-
"""
B11 Performance Measurement: Dashboard Query Patterns
=====================================================

This script documents dashboard query patterns found in the codebase
and identifies potential N+1 query issues and redundant DB calls.

Usage: python scripts/perf/measure_dashboard_load.py
       (Performs static analysis only — no GUI required)
"""
import ast
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# ─────────────────────────────────────────────────────────────
# Documented Findings: Dashboard Query Patterns
# ─────────────────────────────────────────────────────────────
#
# DASHBOARD TAB (gui_app_modular/tabs/dashboard_tab.py):
#   _refresh_dashboard_products()  — 1 large aggregate query (OK)
#   _refresh_dashboard_period_trend() — 1 aggregate query (OK)
#   _refresh_dashboard_integrity() — 1 integrity + 1 product breakdown (OK)
#   _refresh_dashboard_alerts() — multiple fetchall (see below)
#
# DASHBOARD DATA MIXIN (gui_app_modular/tabs/dashboard_data_mixin.py):
#   Provides data-fetching methods called by dashboard_tab.
#   Multiple independent queries fired on each dashboard refresh.
#
# N+1 PATTERN IN ALLOCATION TAB (allocation_tab.py:315-318):
#   lot_rows = db.fetchall("SELECT DISTINCT lot_no ...")
#   for r in lot_rows:
#       engine._recalc_lot_status(lot_no)  # <-- DB query per LOT
#   IMPACT: If 50 LOTs have reserved tonbags, this fires 50+ extra queries.
#   RECOMMENDATION: Batch recalc or single UPDATE with subquery.
#
# N+1 PATTERN IN AUDIT_HELPER (audit_helper.py:110-122):
#   for ev in events:
#       write_audit(db, ...)  # <-- INSERT per event
#   IMPACT: Bulk audit writes (e.g., 20-event batch) do 20 INSERTs.
#   RECOMMENDATION: Use executemany() or INSERT ... VALUES (),(),...
#
# REDUNDANT QUERY RISK:
#   Dashboard refresh calls _refresh_dashboard_products,
#   _refresh_dashboard_period_trend, _refresh_dashboard_integrity,
#   _refresh_dashboard_alerts — each issues separate DB queries.
#   Some share similar joins (inventory + inventory_tonbag).
#   RECOMMENDATION (future): Combine into single CTE-based query.
# ─────────────────────────────────────────────────────────────


def count_db_calls_in_function(filepath: str, func_name: str) -> int:
    """Count .execute/.fetchall/.fetchone calls inside a specific function."""
    try:
        with open(filepath, encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return -1

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                count = 0
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                        if child.func.attr in ('execute', 'fetchall', 'fetchone', 'fetchmany'):
                            count += 1
                return count
    return -1


def find_n_plus_1_patterns(directory: str) -> list:
    """Find for-loops containing DB execute/fetch calls."""
    findings = []
    db_methods = {'execute', 'fetchone', 'fetchall', 'fetchmany'}

    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if not fname.endswith('.py') or '.bak' in fname:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source, filename=fpath)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.For):
                    continue
                for child in ast.walk(node):
                    if child is node:
                        continue
                    if (isinstance(child, ast.Call)
                            and isinstance(child.func, ast.Attribute)
                            and child.func.attr in db_methods):
                        rel = os.path.relpath(fpath, PROJECT_ROOT)
                        findings.append(
                            f"  {rel}:{node.lineno} -> .{child.func.attr}() at line {child.lineno}")
                        break  # one finding per for-loop
    return findings


def main():
    print("=" * 60)
    print("B11 Dashboard Query Pattern Analysis")
    print("=" * 60)

    # Analyze dashboard_tab.py
    dash_path = os.path.join(PROJECT_ROOT, 'gui_app_modular', 'tabs', 'dashboard_tab.py')
    for fn in ['_refresh_dashboard_products', '_refresh_dashboard_period_trend',
               '_refresh_dashboard_integrity', '_refresh_dashboard_alerts']:
        cnt = count_db_calls_in_function(dash_path, fn)
        print(f"  {fn}: {cnt} DB calls")

    # Scan for N+1 patterns
    print("\nN+1 query patterns (DB call inside for-loop):")
    engine_dir = os.path.join(PROJECT_ROOT, 'engine_modules')
    gui_dir = os.path.join(PROJECT_ROOT, 'gui_app_modular')
    patterns = []
    patterns.extend(find_n_plus_1_patterns(engine_dir))
    patterns.extend(find_n_plus_1_patterns(gui_dir))
    print(f"  Total found: {len(patterns)}")
    for p in patterns:
        print(p)
    return len(patterns)


if __name__ == '__main__':
    cnt = main()
    sys.exit(0)
