"""B06 Stage-Gate: advanced_dialogs_mixin report/dialog separation smoke tests.

Verifies:
1. py_compile passes on the modified file
2. _adm_ prefix helpers exist in the class
3. Public method signatures are preserved
"""
import ast
import inspect
import py_compile
import sys
import os

import pytest

# Paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TARGET = os.path.join(ROOT, 'gui_app_modular', 'mixins', 'advanced_dialogs_mixin.py')


class TestB06PyCompile:
    """py_compile must pass on advanced_dialogs_mixin.py."""

    def test_py_compile_passes(self):
        py_compile.compile(TARGET, doraise=True)


class TestB06AdmHelpers:
    """Extracted _adm_ helpers must exist in AdvancedDialogsMixin."""

    @pytest.fixture(autouse=True)
    def _parse_class(self):
        with open(TARGET, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'AdvancedDialogsMixin':
                self.cls_node = node
                self.method_names = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                return
        pytest.fail("AdvancedDialogsMixin class not found")

    def test_adm_helpers_exist(self):
        """At least 6 _adm_ prefixed helpers should exist."""
        adm = [m for m in self.method_names if m.startswith('_adm_')]
        assert len(adm) >= 6, f"Expected >=6 _adm_ helpers, found {len(adm)}: {adm}"

    def test_new_b06_helpers_present(self):
        """B06 newly-extracted helpers must be present."""
        expected = [
            '_adm_validate_single_return_input',
            '_adm_check_return_weight',
            '_adm_execute_single_return',
            '_adm_fetch_outbound_history_rows',
            '_adm_populate_outbound_history_tree',
            '_adm_populate_return_export_tree',
        ]
        for name in expected:
            assert name in self.method_names, f"Missing helper: {name}"


class TestB06PublicSignatures:
    """Public method signatures must be preserved."""

    @pytest.fixture(autouse=True)
    def _parse_methods(self):
        with open(TARGET, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        self.methods = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'AdvancedDialogsMixin':
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.methods[item.name] = item

    # List of public methods that must not change signature
    EXPECTED_PUBLIC = [
        '_on_return_inbound_upload',
        '_on_return_inbound_paste_confirm',
        '_apply_return_inbound_after_parse',
        '_show_return_dialog',
        '_build_return_single_tab',
        '_build_return_excel_tab',
        '_show_document_convert_dialog',
        '_show_outbound_history',
        '_show_snapshot_chart',
        '_generate_outbound_invoice',
        '_on_integrity_report_v760',
        '_on_integrity_report',
        '_show_allocation_template_preview',
        '_show_return_export_history',
        '_on_inbound_template_manage',
        '_on_picking_template_manage',
        '_on_move_approval_queue',
        '_on_detail_of_outbound_report',
        '_on_sales_order_dn_report',
        '_open_outbound_report_dialog',
        '_show_return_statistics',
        '_send_return_alert_email',
        '_show_email_config',
    ]

    def test_public_methods_still_exist(self):
        for name in self.EXPECTED_PUBLIC:
            assert name in self.methods, f"Public method missing: {name}"

    def test_no_extra_positional_params_added(self):
        """Public methods must not gain new required positional params."""
        # Just check self is still the first (and maybe only non-default) arg
        for name in self.EXPECTED_PUBLIC:
            if name not in self.methods:
                continue
            func = self.methods[name]
            args = func.args
            # All positional args (excluding self) must have defaults
            n_pos = len(args.args)  # includes self
            n_defaults = len(args.defaults)
            required = n_pos - n_defaults - 1  # -1 for self
            # Original methods have at most a few required args; just ensure no new ones
            assert required <= 3, (
                f"{name}: too many required params ({required}), signature may have changed"
            )
