# -*- coding: utf-8 -*-
"""
tests/test_db_allowed.py
========================
SQM v9.0.0 — core/db_allowed.py 검증 (smoke + pytest)

Smoke 섹션 (S01~S05):
    - 모듈 import / 기본 동작 / 헬퍼

Pytest 섹션 (T01~T12):
    - validate() true / false / edge case
    - frozenset 불변성
    - helpers (all_tables, all_statuses, stats)

회귀 베이스라인: 557 → 560+ (신규 ~3)
"""
import pytest

from core.db_allowed import (
    ALLOWED_TABLES,
    ALLOWED_STATUS,
    ALLOWED_AREAS,
    validate,
    all_tables,
    all_statuses,
    all_areas,
    stats,
)


# ── Smoke: 모듈 로드 + 기본 동작 ─────────────────────────────

def test_s01_module_imports():
    """core.db_allowed 모듈이 정상 import되는지."""
    assert ALLOWED_TABLES is not None
    assert ALLOWED_STATUS is not None
    assert ALLOWED_AREAS is not None
    assert callable(validate)


def test_s02_validate_basic_true():
    """기본 true 케이스: 알 수 있는 테이블 + 상태."""
    assert validate("inventory", "table", "lot") is True
    assert validate("inventory", "table", "tonbag") is True
    assert validate("outbound", "status", "AVAILABLE") is True
    assert validate("outbound", "status", "PICKED") is True


def test_s03_validate_basic_false():
    """기본 false 케이스: 모르는 값."""
    assert validate("inventory", "table", "sql_injection") is False
    assert validate("outbound", "status", "INVALID") is False


def test_s04_helpers_return_lists():
    """헬퍼 함수가 list 반환하는지."""
    assert isinstance(all_tables(), list)
    assert isinstance(all_statuses(), list)
    assert isinstance(all_areas(), list)
    assert "inventory" in all_tables()
    assert "AVAILABLE" in all_statuses()


def test_s05_stats_dict():
    """stats()가 dict + 합리적 카운트 반환."""
    s = stats()
    assert isinstance(s, dict)
    assert s["tables"] >= 10
    assert s["statuses"] >= 8
    assert s["areas"] >= 5


# ── Pytest: validate() 정밀 ─────────────────────────────────

class TestValidateTable:
    def test_t01_table_known(self):
        assert validate("inventory", "table", "inventory") is True
        assert validate("outbound", "table", "sold_table") is True
        assert validate("audit", "table", "audit_log") is True
        assert validate("parsing", "table", "parsing_log") is True

    def test_t02_table_unknown(self):
        assert validate("inventory", "table", "users_private") is False
        assert validate("inventory", "table", "DROP_TABLE") is False
        assert validate("inventory", "table", "lot; DROP") is False


class TestValidateStatus:
    def test_t03_status_known(self):
        assert validate("inventory", "status", "AVAILABLE") is True
        assert validate("outbound", "status", "PICKED") is True
        assert validate("outbound", "status", "SOLD") is True
        assert validate("allocation", "status", "PENDING_APPROVAL") is True

    def test_t04_status_unknown(self):
        assert validate("inventory", "status", "INVALID") is False
        assert validate("inventory", "status", "available") is False  # 대소문자 구분
        assert validate("inventory", "status", "AVAILABLE_DROP") is False


class TestValidateArea:
    def test_t05_area_known(self):
        assert validate("inventory", "area", "inventory") is True
        assert validate("outbound", "area", "outbound") is True
        assert validate("audit", "area", "audit") is True

    def test_t06_area_unknown(self):
        assert validate("inventory", "area", "unknown_area") is False
        assert validate("inventory", "area", "INVENTORY") is False  # 대소문자


class TestValidateEdge:
    def test_t07_unknown_kind(self):
        """모르는 kind는 False."""
        assert validate("inventory", "column", "qty_mt") is False
        assert validate("inventory", "operation", "delete") is False
        assert validate("inventory", "anything", "x") is False

    def test_t08_empty_or_invalid_value(self):
        """빈 문자열 / None / 비-문자열은 False."""
        assert validate("inventory", "table", "") is False
        assert validate("inventory", "table", None) is False
        assert validate("inventory", "table", 123) is False
        assert validate("inventory", "table", ["lot"]) is False


# ── Pytest: 불변성 + 보조 ───────────────────────────────────

class TestImmutable:
    def test_t09_tables_isfrozenset(self):
        assert isinstance(ALLOWED_TABLES, frozenset)
        # frozenset에 추가 시도 → AttributeError
        with pytest.raises(AttributeError):
            ALLOWED_TABLES.add("hacked")

    def test_t10_status_isfrozenset(self):
        assert isinstance(ALLOWED_STATUS, frozenset)
        with pytest.raises(AttributeError):
            ALLOWED_STATUS.add("HACKED")

    def test_t11_areas_isfrozenset(self):
        assert isinstance(ALLOWED_AREAS, frozenset)
        with pytest.raises(AttributeError):
            ALLOWED_AREAS.add("hacked")


class TestHelpers:
    def test_t12_all_helpers_sorted(self):
        """헬퍼들이 정렬된 list 반환."""
        assert all_tables() == sorted(all_tables())
        assert all_statuses() == sorted(all_statuses())
        assert all_areas() == sorted(all_areas())
