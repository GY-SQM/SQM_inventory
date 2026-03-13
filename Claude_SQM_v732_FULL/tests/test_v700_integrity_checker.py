# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — IntegrityChecker 통합 테스트 (15개)
==================================================
v7.0.0 신규 통합판: 9가지 검사 (v690 6가지 + Stage4 3가지)
MockDB를 활용하여 DB 없이 검사 로직 단위 테스트
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.integrity_check import (
    IntegrityChecker, IntegrityReport, CheckResult
)


# ── MockDB ─────────────────────────────────────────────────────────────────

class MockDB:
    """테스트용 MockDB — fetchall / fetchone 지원"""

    def __init__(self, scenario: str = 'clean'):
        self.scenario = scenario

    def fetchall(self, sql: str, params=None):
        sql_lower = sql.lower()

        if self.scenario == 'clean':
            return []

        if self.scenario == 'duplicate_lot':
            if 'count(*)' in sql_lower and 'having' in sql_lower:
                return [{'lot_no': '1125072340', 'cnt': 2}]
            return []

        if self.scenario == 'orphan_tonbag':
            if 'left join' in sql_lower and 'where i.lot_no is null' in sql_lower:
                return [{'id': 99, 'lot_no': '9999999999', 'tonbag_no': '001'}]
            return []

        if self.scenario == 'negative_weight':
            if 'current_weight < 0' in sql_lower:
                return [{'lot_no': '1125072340', 'current_weight': -100.0}]
            return []

        if self.scenario == 'bad_status':
            if 'from inventory' in sql_lower and 'status' in sql_lower:
                return [{'lot_no': '1125072340', 'status': 'INVALID_STATUS'}]
            return []

        return []

    def fetchone(self, sql: str, params=None):
        return None


# ── 1. CheckResult / IntegrityReport ──────────────────────────────────────

class TestCheckResult:

    def test_T601_passed_true(self):
        r = CheckResult("테스트", passed=True)
        assert r.passed is True

    def test_T602_passed_false_with_count(self):
        r = CheckResult("테스트", passed=False, issue_count=3)
        assert r.issue_count == 3

    def test_T603_default_severity_is_INFO(self):
        r = CheckResult("테스트", passed=True)
        assert r.severity == "INFO"

    def test_T604_critical_severity_set(self):
        r = CheckResult("테스트", passed=False, severity="CRITICAL")
        assert r.severity == "CRITICAL"


class TestIntegrityReport:

    def test_T605_score_100_when_all_pass(self):
        rpt = IntegrityReport(total_checks=9, passed=9, failed=0)
        assert rpt.score == 100

    def test_T606_score_0_when_all_fail(self):
        rpt = IntegrityReport(total_checks=9, passed=0, failed=9)
        assert rpt.score == 0

    def test_T607_score_partial(self):
        rpt = IntegrityReport(total_checks=10, passed=7, failed=3)
        assert rpt.score == 70

    def test_T608_empty_report_score_100(self):
        rpt = IntegrityReport()
        assert rpt.score == 100


# ── 2. IntegrityChecker 검사 로직 ─────────────────────────────────────────

class TestIntegrityCheckerClean:

    def setup_method(self):
        self.checker = IntegrityChecker(MockDB('clean'))

    def test_T609_clean_db_duplicate_check_passes(self):
        r = self.checker._check_duplicate_lots()
        assert r.passed is True

    def test_T610_clean_db_orphan_check_passes(self):
        r = self.checker._check_orphan_tonbags()
        assert r.passed is True

    def test_T611_clean_db_weight_check_passes(self):
        r = self.checker._check_weight_integrity()
        assert r.passed is True

    def test_T612_clean_db_status_check_passes(self):
        r = self.checker._check_status_consistency()
        assert r.passed is True


class TestIntegrityCheckerIssues:

    def test_T613_duplicate_lot_detected(self):
        checker = IntegrityChecker(MockDB('duplicate_lot'))
        r = checker._check_duplicate_lots()
        assert r.passed is False
        assert r.issue_count >= 1

    def test_T614_orphan_tonbag_detected(self):
        checker = IntegrityChecker(MockDB('orphan_tonbag'))
        r = checker._check_orphan_tonbags()
        assert r.passed is False

    def test_T615_negative_weight_detected(self):
        checker = IntegrityChecker(MockDB('negative_weight'))
        r = checker._check_weight_integrity()
        assert r.passed is False
