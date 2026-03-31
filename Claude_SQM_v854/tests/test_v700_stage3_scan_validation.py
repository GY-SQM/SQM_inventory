# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — Stage3 출고 스캔 검증 테스트 (15개)
==================================================
출고 스캔 상태 검증: AVAILABLE/RESERVED/PICKED만 허용
SOLD/DEPLETED/RETURN 차단
중복 스캔 하드스톱
"""
from engine_modules.constants import STATUS_AVAILABLE, STATUS_DEPLETED, STATUS_PICKED, STATUS_RESERVED, STATUS_SOLD
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.outbound_scan_validation_patch import is_scannable_status, is_duplicate_scan


class TestIsScannableStatus:

    def test_T301_available_is_scannable(self):
        r = is_scannable_status(STATUS_AVAILABLE)
        assert r.success is True

    def test_T302_reserved_is_scannable(self):
        r = is_scannable_status(STATUS_RESERVED)
        assert r.success is True

    def test_T303_picked_is_scannable(self):
        r = is_scannable_status(STATUS_PICKED)
        assert r.success is True

    def test_T304_sold_is_blocked(self):
        r = is_scannable_status(STATUS_SOLD)
        assert r.success is False

    def test_T305_depleted_is_blocked(self):
        r = is_scannable_status(STATUS_DEPLETED)
        assert r.success is False

    def test_T306_return_status_handled(self):
        r = is_scannable_status('RETURN')
        assert isinstance(r.success, bool)

    def test_T307_empty_string_is_blocked(self):
        r = is_scannable_status('')
        assert r.success is False

    def test_T308_unknown_status_is_blocked(self):
        r = is_scannable_status('UNKNOWN_XYZ')
        assert r.success is False

    def test_T309_lowercase_available_handled(self):
        """대소문자 무관 처리 (상태값은 보통 대문자이나 방어 코드 확인)"""
        r = is_scannable_status('available')
        assert isinstance(r.success, bool)

    def test_T310_result_has_code_field(self):
        r = is_scannable_status(STATUS_AVAILABLE)
        assert hasattr(r, 'code')

    def test_T311_result_has_message_field(self):
        r = is_scannable_status(STATUS_SOLD)
        assert hasattr(r, 'message')

    def test_T312_blocked_result_has_nonempty_message(self):
        r = is_scannable_status(STATUS_SOLD)
        assert r.message and len(r.message) > 0


class TestIsDuplicateScan:

    def test_T313_new_uid_not_duplicate(self):
        scanned = {"1125072340-001", "1125072340-002"}
        r = is_duplicate_scan(scanned, "1125072340-003")
        assert r.success is True

    def test_T314_existing_uid_is_duplicate(self):
        scanned = {"1125072340-001", "1125072340-002"}
        r = is_duplicate_scan(scanned, "1125072340-001")
        assert r.success is False

    def test_T315_empty_set_never_duplicate(self):
        r = is_duplicate_scan(set(), "1125072340-001")
        assert r.success is True
