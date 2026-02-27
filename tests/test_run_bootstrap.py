# -*- coding: utf-8 -*-
"""
P5-13: run_bootstrap 단위 테스트
=================================
run_self_check 반환 구조, check_dependencies
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from run_bootstrap import run_self_check, check_dependencies, print_self_check_report


class TestRunSelfCheck:
    def test_returns_dict(self):
        results = run_self_check()
        assert isinstance(results, dict)
        assert "passed" in results
        assert "checks" in results
        assert "warnings" in results
        assert "errors" in results

    def test_passed_boolean(self):
        results = run_self_check()
        assert isinstance(results["passed"], bool)

    def test_lists(self):
        results = run_self_check()
        assert isinstance(results["checks"], list)
        assert isinstance(results["warnings"], list)
        assert isinstance(results["errors"], list)


class TestCheckDependencies:
    def test_returns_bool(self):
        out = check_dependencies()
        assert isinstance(out, bool)

    def test_required_present_returns_true(self):
        # pandas, openpyxl, tkinter 있으면 True
        out = check_dependencies()
        assert out is True


class TestPrintSelfCheckReport:
    def test_no_exception(self):
        results = {"passed": True, "checks": ["ok"], "warnings": [], "errors": []}
        print_self_check_report(results)  # no raise
