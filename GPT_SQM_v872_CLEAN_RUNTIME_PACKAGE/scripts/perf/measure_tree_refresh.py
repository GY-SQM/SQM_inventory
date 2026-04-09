# -*- coding: utf-8 -*-
"""
B11 Performance Measurement: Treeview Refresh Patterns
======================================================

This script documents Treeview refresh patterns found in the codebase
and identifies per-item delete anti-patterns vs. batch delete patterns.

Usage: python scripts/perf/measure_tree_refresh.py
       (Performs static analysis only — no GUI required)
"""
import ast
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# ─────────────────────────────────────────────────────────────
# Documented Findings: Treeview Refresh Patterns
# ─────────────────────────────────────────────────────────────
#
# BATCH DELETE (Good Pattern):
#   tree.delete(*tree.get_children())
#   Found in: allocation_approval_dialog.py:166, allocation_dialog.py:425/464/507,
#             outbound_handlers.py:196/585/2646, dashboard_tab.py:408/451/801/805,
#             inventory_tab.py:414/1043, advanced_dialogs_mixin.py:761/1094/1705,
#             do_update_dialog.py:257, allocation_template_dialog.py:478,
#             cargo_overview_tab.py:487
#
# PER-ITEM DELETE (Anti-Pattern — O(n) Tk calls instead of 1):
#   for item in tree.get_children(): tree.delete(item)
#   Found in:
#     - allocation_tab.py:307-308  (_refresh_allocation)
#     - allocation_tab.py:398-399  (_on_show_all_allocation)
#     - allocation_tab.py:491-492  (child delete in expand/collapse)
#     - allocation_tab.py:727-728  (child delete)
#     - allocation_lot_overview_mixin.py:333-334
#     - dn_cross_check_dialog.py:139-140
#     - preparse_review_dialog.py:167-168
#     - cargo_overview_tab.py:307-308
#     - sold_tab.py:176, picked_tab.py:220
#
# IMPACT ESTIMATE:
#   Each per-item delete issues a separate Tcl command.
#   For tables with 100-500 rows, switching to batch delete
#   saves ~100-500 Tcl round-trips per refresh.
#   Expected improvement: 2-10x faster tree clear on large datasets.
# ─────────────────────────────────────────────────────────────


def find_per_item_delete_patterns(directory: str) -> list:
    """AST-based scan: find 'for X in tree.get_children(): tree.delete(X)' patterns."""
    findings = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if not fname.endswith('.py') or fname.endswith(('.bak_auto', '.bak_20260402')):
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
                # Check: iter is *.get_children()
                iter_call = node.iter
                if not isinstance(iter_call, ast.Call):
                    continue
                if not isinstance(iter_call.func, ast.Attribute):
                    continue
                if iter_call.func.attr != 'get_children':
                    continue
                # Check body for .delete(target_var)
                target_name = None
                if isinstance(node.target, ast.Name):
                    target_name = node.target.id
                if not target_name:
                    continue
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        if (isinstance(call.func, ast.Attribute)
                                and call.func.attr == 'delete'
                                and any(isinstance(a, ast.Name) and a.id == target_name
                                        for a in call.args)):
                            rel = os.path.relpath(fpath, PROJECT_ROOT)
                            findings.append(f"  {rel}:{node.lineno}")
    return findings


def main():
    print("=" * 60)
    print("B11 Treeview Refresh Pattern Analysis")
    print("=" * 60)

    gui_dir = os.path.join(PROJECT_ROOT, 'gui_app_modular')
    patterns = find_per_item_delete_patterns(gui_dir)
    print(f"\nPer-item delete anti-patterns found: {len(patterns)}")
    for p in patterns:
        print(p)
    print(f"\nRecommendation: Replace with tree.delete(*tree.get_children())")
    print("Expected speedup: 2-10x on tables with 100+ rows")
    return len(patterns)


if __name__ == '__main__':
    cnt = main()
    sys.exit(0)
