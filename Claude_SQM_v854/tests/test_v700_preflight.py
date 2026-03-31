# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — Preflight 검증기 테스트 (15개)
All-or-Nothing 원칙 테스트
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine_modules.preflight import (
    PreflightResult, PreflightIssue, PreflightErrorLevel,
    PreflightValidator
)


class TestPreflightResult:

    def test_T801_new_result_is_valid(self):
        r = PreflightResult(operation='INBOUND', total_rows=10)
        assert r.is_valid is True

    def test_T802_new_result_can_proceed(self):
        r = PreflightResult(operation='INBOUND', total_rows=10)
        assert r.can_proceed is True

    def test_T803_fatal_makes_invalid_and_blocked(self):
        r = PreflightResult(operation='INBOUND', total_rows=1)
        r.add_issue(PreflightIssue(
            level=PreflightErrorLevel.FATAL, row=1, field='lot_no', value=None, message='치명', code='F001'
        ))
        assert r.is_valid is False
        assert r.can_proceed is False

    def test_T804_error_increases_error_count(self):
        r = PreflightResult(operation='INBOUND', total_rows=1)
        r.add_issue(PreflightIssue(
            level=PreflightErrorLevel.ERROR, row=1, field='weight', value=None, message='오류', code='E001'
        ))
        assert r.error_count == 1
        assert r.is_valid is False

    def test_T805_warning_does_not_block(self):
        r = PreflightResult(operation='INBOUND', total_rows=1)
        r.add_issue(PreflightIssue(
            level=PreflightErrorLevel.WARNING, row=1, field='lot_no', value='', message='경고', code='W001'
        ))
        assert r.is_valid is True
        assert r.can_proceed is True
        assert r.warning_count == 1

    def test_T806_has_blocking_errors_with_fatal(self):
        r = PreflightResult(operation='INBOUND', total_rows=1)
        r.add_issue(PreflightIssue(
            level=PreflightErrorLevel.FATAL, row=1, field='lot_no', value=None, message='치명', code='F001'
        ))
        assert r.has_blocking_errors() is True

    def test_T807_has_blocking_errors_false_only_warning(self):
        r = PreflightResult(operation='INBOUND', total_rows=1)
        r.add_issue(PreflightIssue(
            level=PreflightErrorLevel.WARNING, row=1, field='lot_no', value='', message='경고', code='W001'
        ))
        assert r.has_blocking_errors() is False

    def test_T808_get_summary_contains_operation(self):
        r = PreflightResult(operation='INBOUND', total_rows=5)
        assert 'INBOUND' in r.get_summary()

    def test_T809_multiple_issues_counted_correctly(self):
        r = PreflightResult(operation='OUTBOUND', total_rows=10)
        for i in range(3):
            r.add_issue(PreflightIssue(
                level=PreflightErrorLevel.WARNING, row=i, field='lot_no', value='', message='경고', code='W'
            ))
        r.add_issue(PreflightIssue(
            level=PreflightErrorLevel.ERROR, row=4, field='weight', value=None, message='오류', code='E'
        ))
        assert r.warning_count == 3
        assert r.error_count == 1
        assert r.is_valid is False

    def test_T810_get_errors_for_gui_returns_list(self):
        r = PreflightResult(operation='INBOUND', total_rows=1)
        r.add_issue(PreflightIssue(
            level=PreflightErrorLevel.ERROR, row=1, field='weight', value=None, message='오류', code='E001'
        ))
        errors = r.get_errors_for_gui()
        assert isinstance(errors, list)
        assert errors[0]['code'] == 'E001'


class TestPreflightValidator:

    def test_T811_valid_row_passes(self):
        v = PreflightValidator()
        data = [{'lot_no': '1125072340', 'sub_lt': 1, 'weight': 500.0}]
        r = v.validate_inbound(data, check_db=False)
        assert r.fatal_count == 0
        assert r.error_count == 0

    def test_T812_missing_lot_no_gives_error(self):
        v = PreflightValidator()
        data = [{'lot_no': '', 'sub_lt': 1, 'weight': 500.0}]
        r = v.validate_inbound(data, check_db=False)
        assert r.is_valid is False

    def test_T813_missing_weight_gives_error(self):
        v = PreflightValidator()
        data = [{'lot_no': '1125072340', 'sub_lt': 1, 'weight': None}]
        r = v.validate_inbound(data, check_db=False)
        assert r.is_valid is False

    def test_T814_result_has_operation_field(self):
        v = PreflightValidator()
        data = [{'lot_no': '1125072340', 'sub_lt': 1, 'weight': 500.0}]
        r = v.validate_inbound(data, check_db=False)
        assert hasattr(r, 'operation')

    def test_T815_all_or_nothing_one_bad_row_blocks_all(self):
        """All-or-Nothing: 한 행 오류 시 전체 is_valid False"""
        v = PreflightValidator()
        data = [
            {'lot_no': '1125072340', 'sub_lt': 1, 'weight': 500.0},  # 정상
            {'lot_no': '',           'sub_lt': 2, 'weight': 500.0},  # 오류
            {'lot_no': '1125072341', 'sub_lt': 1, 'weight': 500.0},  # 정상
        ]
        r = v.validate_inbound(data, check_db=False)
        assert r.is_valid is False
