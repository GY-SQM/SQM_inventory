# -*- coding: utf-8 -*-
"""
B11: Query Count Guard — AST-based detection of N+1 patterns.

Verifies that key engine/gui files do not contain obvious N+1 patterns
(DB execute/fetch calls inside for-loops).
"""
import ast
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# DB method names that indicate a query
_DB_METHODS = frozenset({'execute', 'fetchone', 'fetchall', 'fetchmany'})

# Key files to guard — these are high-traffic paths where N+1 hurts most.
# We allow a maximum number of N+1 patterns per file.
# Files not listed here are not checked (low-traffic or acceptable).
_GUARDED_FILES = {
    # (relative_path, max_allowed_n_plus_1)
    # Baseline thresholds = current count as of B11.
    # These act as a ratchet: new N+1 patterns must not be added.
    'gui_app_modular/tabs/dashboard_tab.py': 1,      # baseline 1 (line ~1037)
    'gui_app_modular/tabs/inventory_tab.py': 0,
    'gui_app_modular/tabs/tonbag_tab.py': 0,
    'gui_app_modular/mixins/refresh_mixin.py': 0,
    'engine_modules/inventory_modular/query_mixin.py': 2,   # baseline 2
    'engine_modules/inventory_modular/outbound_mixin.py': 19,  # baseline 19 — high priority for future refactor
}

# Files to guard against per-item Treeview delete (should use batch)
_TREE_DELETE_GUARDED = {
    # These files should NOT have per-item delete in for-loops
    'gui_app_modular/tabs/dashboard_tab.py': 0,
    'gui_app_modular/tabs/inventory_tab.py': 0,
    'gui_app_modular/tabs/tonbag_tab.py': 0,
    'gui_app_modular/mixins/refresh_mixin.py': 0,
}


def _count_n_plus_1(filepath: str) -> list:
    """Return list of (line, method) tuples for DB calls inside for-loops."""
    try:
        with open(filepath, encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return []

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        for child in ast.walk(node):
            if child is node:
                continue
            if (isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr in _DB_METHODS):
                findings.append((node.lineno, child.func.attr))
                break  # one finding per for-loop is enough
    return findings


def _count_per_item_tree_delete(filepath: str) -> list:
    """Return list of line numbers where per-item tree delete is found."""
    try:
        with open(filepath, encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return []

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        # Check if iter is .get_children()
        iter_call = node.iter
        if not isinstance(iter_call, ast.Call):
            continue
        if not isinstance(iter_call.func, ast.Attribute):
            continue
        if iter_call.func.attr != 'get_children':
            continue
        # Check body for .delete(loop_var)
        target_name = node.target.id if isinstance(node.target, ast.Name) else None
        if not target_name:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if (isinstance(call.func, ast.Attribute)
                        and call.func.attr == 'delete'
                        and any(isinstance(a, ast.Name) and a.id == target_name
                                for a in call.args)):
                    findings.append(node.lineno)
    return findings


class TestNPlus1QueryGuard(unittest.TestCase):
    """Verify no N+1 DB query patterns in key files."""

    def test_no_n_plus_1_in_guarded_files(self):
        """Key high-traffic files should not exceed allowed N+1 count."""
        violations = []
        for rel_path, max_allowed in _GUARDED_FILES.items():
            fpath = os.path.join(PROJECT_ROOT, rel_path.replace('/', os.sep))
            findings = _count_n_plus_1(fpath)
            if len(findings) > max_allowed:
                violations.append(
                    f"{rel_path}: {len(findings)} N+1 patterns "
                    f"(max {max_allowed}). Lines: {[f[0] for f in findings]}")
        self.assertEqual(violations, [],
                         f"N+1 query violations:\n" + "\n".join(violations))


class TestTreeviewBatchDeleteGuard(unittest.TestCase):
    """Verify key files use batch tree.delete(*tree.get_children())."""

    def test_no_per_item_delete_in_guarded_files(self):
        """Key tab files should use batch delete, not per-item delete."""
        violations = []
        for rel_path, max_allowed in _TREE_DELETE_GUARDED.items():
            fpath = os.path.join(PROJECT_ROOT, rel_path.replace('/', os.sep))
            findings = _count_per_item_tree_delete(fpath)
            if len(findings) > max_allowed:
                violations.append(
                    f"{rel_path}: {len(findings)} per-item deletes "
                    f"(max {max_allowed}). Lines: {findings}")
        self.assertEqual(violations, [],
                         f"Per-item delete violations:\n" + "\n".join(violations))


class TestPerfScriptsExist(unittest.TestCase):
    """Verify perf measurement scripts are present."""

    def test_measure_tree_refresh_exists(self):
        fpath = os.path.join(PROJECT_ROOT, 'scripts', 'perf', 'measure_tree_refresh.py')
        self.assertTrue(os.path.isfile(fpath), f"Missing: {fpath}")

    def test_measure_dashboard_load_exists(self):
        fpath = os.path.join(PROJECT_ROOT, 'scripts', 'perf', 'measure_dashboard_load.py')
        self.assertTrue(os.path.isfile(fpath), f"Missing: {fpath}")


if __name__ == '__main__':
    unittest.main()
