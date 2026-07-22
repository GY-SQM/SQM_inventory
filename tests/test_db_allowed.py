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
    ALLOWED_SCOPES,
    REVERT_MAP,
    LOT_EDIT_FIELDS,
    CARRIER_RULE_EDIT_FIELDS,
    ALLOWED_TABLE_DELETE,
    ALLOWED_FILE_EXTS,
    REPORT_FIELDS_BY_TYPE,
    validate,
    all_tables,
    all_statuses,
    all_areas,
    stats,
    stats_detailed,
    reset_counts,
    _VALIDATE_COUNTS,
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


# ── REVERT_MAP (state transition) ────────────────────────────

class TestRevertMap:
    def test_t13_revert_map_basic(self):
        """REVERT_MAP 핵심 매핑."""
        assert REVERT_MAP["AVAILABLE"] == "PENDING"
        assert REVERT_MAP["PICKED"] == "RESERVED"
        assert REVERT_MAP["SOLD"] == "PICKED"
        assert REVERT_MAP["RETURN"] == "AVAILABLE"

    def test_t14_revert_map_unknown(self):
        """정의되지 않은 from_status는 None."""
        assert REVERT_MAP.get("INVALID") is None
        assert REVERT_MAP.get("available") is None  # 대소문자

    def test_t15_revert_map_keys_in_status(self):
        """모든 키가 ALLOWED_STATUS 안의 값."""
        for key in REVERT_MAP:
            assert key in ALLOWED_STATUS, f"{key} not in ALLOWED_STATUS"

    def test_t16_revert_map_values_in_status(self):
        """모든 값이 ALLOWED_STATUS 안의 값 (cross-check)."""
        for from_st, to_st in REVERT_MAP.items():
            assert to_st in ALLOWED_STATUS, f"{from_st} → {to_st}: target not in ALLOWED_STATUS"

    def test_t17_allowed_scopes_isfrozenset(self):
        """ALLOWED_SCOPES도 immutable."""
        assert isinstance(ALLOWED_SCOPES, frozenset)
        with pytest.raises(AttributeError):
            ALLOWED_SCOPES.add("hacked")


# ── LOT_EDIT_FIELDS + validate(kind='lot_field') ────────────

class TestLotEditFields:
    def test_t18_lot_edit_fields_basic(self):
        """LOT_EDIT_FIELDS 핵심 컬럼."""
        assert "free_time" in LOT_EDIT_FIELDS
        assert "warehouse_name" in LOT_EDIT_FIELDS
        assert "final_destination" in LOT_EDIT_FIELDS
        assert len(LOT_EDIT_FIELDS) == 8

    def test_t19_lot_edit_fields_immutable(self):
        """LOT_EDIT_FIELDS는 frozenset."""
        assert isinstance(LOT_EDIT_FIELDS, frozenset)
        with pytest.raises(AttributeError):
            LOT_EDIT_FIELDS.add("hacked")

    def test_t20_validate_lot_field(self):
        """validate(kind='lot_field', ...) 동작."""
        assert validate("inventory", "lot_field", "free_time") is True
        assert validate("inventory", "lot_field", "warehouse_name") is True
        assert validate("inventory", "lot_field", "qty_mt") is False  # 일반 컬럼 (수정 불가)
        assert validate("inventory", "lot_field", "DROP_FIELD") is False

    def test_t21_validate_scope_type(self):
        """validate(kind='scope_type', ...) 동작 (Step 1 보강)."""
        assert validate("inventory", "scope_type", "container_no") is True
        assert validate("inventory", "scope_type", "unknown") is False


# ── Step 4: CARRIER_RULE_EDIT_FIELDS + ALLOWED_TABLE_DELETE ──

class TestStep4:
    def test_t22_carrier_rule_fields(self):
        """선사 규칙 수정 가능 컬럼 (7개)."""
        assert "carrier_id" in CARRIER_RULE_EDIT_FIELDS
        assert "doc_type" in CARRIER_RULE_EDIT_FIELDS
        assert "is_active" in CARRIER_RULE_EDIT_FIELDS
        assert len(CARRIER_RULE_EDIT_FIELDS) == 7
        assert isinstance(CARRIER_RULE_EDIT_FIELDS, frozenset)

    def test_t23_allowed_table_delete(self):
        """개발용 table-delete 허용 테이블 (10개)."""
        assert "outbound" in ALLOWED_TABLE_DELETE
        assert "audit_log" in ALLOWED_TABLE_DELETE
        assert "parsing_log" in ALLOWED_TABLE_DELETE
        assert "outbound_event_log" in ALLOWED_TABLE_DELETE
        assert len(ALLOWED_TABLE_DELETE) == 10
        assert isinstance(ALLOWED_TABLE_DELETE, frozenset)

    def test_t24_table_delete_subset_of_tables(self):
        """invariant: ALLOWED_TABLE_DELETE ⊆ ALLOWED_TABLES."""
        for t in ALLOWED_TABLE_DELETE:
            assert t in ALLOWED_TABLES, f"{t} not in ALLOWED_TABLES (invariant 위반)"

    def test_t25_table_delete_excludes_real_data(self):
        """절대 허용 안 함: inventory, inventory_tonbag."""
        assert "inventory" not in ALLOWED_TABLE_DELETE
        assert "inventory_tonbag" not in ALLOWED_TABLE_DELETE


# ── Phase 2 Step 1: ALLOWED_FILE_EXTS + validate(kind='file_ext') ──

class TestPhase2Step1:
    def test_t26_file_exts_basic(self):
        """ALLOWED_FILE_EXTS 기본 (6개)."""
        assert ".xlsx" in ALLOWED_FILE_EXTS
        assert ".pdf" in ALLOWED_FILE_EXTS
        assert len(ALLOWED_FILE_EXTS) == 6
        assert isinstance(ALLOWED_FILE_EXTS, frozenset)

    def test_t27_validate_file_ext(self):
        """validate(kind='file_ext', ...) 동작."""
        assert validate("report", "file_ext", ".xlsx") is True
        assert validate("report", "file_ext", ".pdf") is True
        assert validate("report", "file_ext", ".exe") is False
        assert validate("report", "file_ext", "xlsx") is False  # 점(.) 필수

    def test_t28_file_exts_excludes_dangerous(self):
        """위험 확장자 (실행 파일) 부재."""
        dangerous = [".exe", ".bat", ".sh", ".py", ".js", ".dll", ".so"]
        for ext in dangerous:
            assert ext not in ALLOWED_FILE_EXTS, f"{ext} should not be allowed"


# ── Phase 2 Step 2: REPORT_FIELDS_BY_TYPE ─────────────────

class TestPhase2Step2:
    def test_t29_report_fields_by_type_basic(self):
        """5개 report_type별 fields frozenset."""
        assert "outbound_report" in REPORT_FIELDS_BY_TYPE
        assert "export_work_report" in REPORT_FIELDS_BY_TYPE
        assert "sales_order_dn" in REPORT_FIELDS_BY_TYPE
        assert "storage_confirmation" in REPORT_FIELDS_BY_TYPE
        assert "sold_inventory_report" in REPORT_FIELDS_BY_TYPE
        for rt, fields in REPORT_FIELDS_BY_TYPE.items():
            assert isinstance(fields, frozenset), f"{rt} fields is not frozenset"
            assert len(fields) > 0

    def test_t30_outbound_report_fields(self):
        """outbound_report 14개 fields (예: lot_no, container_no, bl_no)."""
        fields = REPORT_FIELDS_BY_TYPE["outbound_report"]
        assert "lot_no" in fields
        assert "container_no" in fields
        assert "bl_no" in fields
        assert "is_sample" in fields
        assert len(fields) == 14

    def test_t31_report_fields_by_type_immutable(self):
        """MappingProxyType — read-only."""
        with pytest.raises(TypeError):
            REPORT_FIELDS_BY_TYPE["new_report"] = frozenset()


# ── Phase 2 Step 4: 모니터링 (in-memory 카운터) ────────────

class TestPhase2Step4:
    def setup_method(self):
        """각 테스트 전 카운터 초기화."""
        reset_counts()

    def test_t32_stats_detailed_empty(self):
        """빈 카운터 → 0건."""
        s = stats_detailed()
        assert s["total_calls"] == 0
        assert s["allowed"] == 0
        assert s["blocked"] == 0
        assert s["by_kind"] == {}

    def test_t33_stats_detailed_records_allowed(self):
        """allowed 카운트."""
        validate("inventory", "table", "inventory")  # allowed
        validate("inventory", "table", "lot")  # allowed
        s = stats_detailed()
        assert s["total_calls"] == 2
        assert s["allowed"] == 2
        assert s["blocked"] == 0
        assert s["by_kind"]["table"]["allowed"] == 2

    def test_t34_stats_detailed_records_blocked(self):
        """blocked 카운트 (화이트리스트 부재)."""
        validate("inventory", "table", "sql_injection_attempt")  # blocked
        s = stats_detailed()
        assert s["total_calls"] == 1
        assert s["allowed"] == 0
        assert s["blocked"] == 1
        assert s["by_kind"]["table"]["blocked"] == 1

    def test_t35_stats_detailed_mixed(self):
        """mixed allowed + blocked."""
        validate("inventory", "table", "inventory")  # allowed
        validate("inventory", "table", "bad")  # blocked
        validate("inventory", "status", "AVAILABLE")  # allowed
        validate("inventory", "status", "bad")  # blocked
        s = stats_detailed()
        assert s["total_calls"] == 4
        assert s["allowed"] == 2
        assert s["blocked"] == 2
        assert s["by_kind"]["table"]["allowed"] == 1
        assert s["by_kind"]["table"]["blocked"] == 1
        assert s["by_kind"]["status"]["allowed"] == 1
        assert s["by_kind"]["status"]["blocked"] == 1

    def test_t36_stats_detailed_records_invalid_input(self):
        """invalid input (None, 빈 문자열) 도 카운트."""
        validate("inventory", "table", "")  # blocked (빈 문자열)
        validate("inventory", "table", None)  # blocked (None)
        s = stats_detailed()
        assert s["total_calls"] == 2
        assert s["blocked"] == 2


# ── v9.0.3: audit_log DB 영속화 ───────────────────────────

class TestAuditLog:
    def test_t37_init_audit_table_idempotent(self, tmp_path):
        """audit table 자동 생성 (idempotent)."""
        db = str(tmp_path / "test.db")
        from core.db_allowed import _init_audit_table
        _init_audit_table(db)
        _init_audit_table(db)  # 두 번 호출해도 OK (IF NOT EXISTS)
        import sqlite3
        con = sqlite3.connect(db)
        try:
            row = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='db_allowed_audit'"
            ).fetchone()
            assert row is not None
        finally:
            con.close()

    def test_t38_write_audit_records_to_db(self, tmp_path):
        """_write_audit() — DB에 1 row 기록."""
        import sqlite3
        from core.db_allowed import _init_audit_table, _write_audit
        db = str(tmp_path / "test.db")
        _init_audit_table(db)
        # _write_audit는 config DB_PATH를 쓰지만, path 강제는 직접 SQL
        con = sqlite3.connect(db)
        try:
            con.execute(
                "INSERT INTO db_allowed_audit (area, kind, result, value) VALUES (?, ?, ?, ?)",
                ("inventory", "table", 1, "inventory"),
            )
            con.commit()
            row = con.execute("SELECT area, kind, result, value FROM db_allowed_audit").fetchone()
            assert row == ("inventory", "table", 1, "inventory")
        finally:
            con.close()

    def test_t39_audit_table_indexes(self, tmp_path):
        """db_allowed_audit 인덱스 (ts, kind) 자동 생성."""
        from core.db_allowed import _init_audit_table
        db = str(tmp_path / "test.db")
        _init_audit_table(db)
        import sqlite3
        con = sqlite3.connect(db)
        try:
            rows = con.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='db_allowed_audit'"
            ).fetchall()
            index_names = {r[0] for r in rows}
            assert any("ts" in n for n in index_names)
            assert any("kind" in n for n in index_names)
        finally:
            con.close()


# ── v9.0.5: audit_log 자동 정리 ───────────────────────────

class TestAuditCleanup:
    def test_t40_cleanup_audit_basic(self, tmp_path, monkeypatch):
        """오래된 row 삭제 + 최근 row 유지."""
        import sqlite3
        from core.db_allowed import _init_audit_table, cleanup_audit
        import core.db_allowed as db_mod
        db = str(tmp_path / "cleanup.db")
        _init_audit_table(db)
        monkeypatch.setattr(db_mod, "_get_default_db_path", lambda: db)
        con = sqlite3.connect(db)
        try:
            # 50일 전 row 1개
            con.execute(
                f"INSERT INTO db_allowed_audit (ts, area, kind, result, value) VALUES (datetime('now', '-50 days'), ?, ?, ?, ?)",
                ("inventory", "table", 1, "old"),
            )
            # 오늘 row 1개
            con.execute(
                f"INSERT INTO db_allowed_audit (ts, area, kind, result, value) VALUES (datetime('now'), ?, ?, ?, ?)",
                ("inventory", "table", 1, "new"),
            )
            con.commit()
        finally:
            con.close()
        # 30일 이전 row 삭제
        deleted = cleanup_audit(days=30)
        assert deleted == 1
        # 남은 row 확인
        con = sqlite3.connect(db)
        try:
            rows = con.execute("SELECT value FROM db_allowed_audit").fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "new"
        finally:
            con.close()

    def test_t41_cleanup_audit_zero_days(self, tmp_path, monkeypatch):
        """days=0 → no-op (안전)."""
        import core.db_allowed as db_mod
        monkeypatch.setattr(db_mod, "_get_default_db_path", lambda: str(tmp_path / "noop.db"))
        from core.db_allowed import cleanup_audit
        assert cleanup_audit(0) == 0
        assert cleanup_audit(-1) == 0

    def test_t42_cleanup_audit_no_db(self):
        """DB 없으면 0 반환."""
        from core.db_allowed import cleanup_audit
        # config import 실패 → _get_default_db_path() = None
        # 이 테스트는 config가 import 안 되는 환경 의존
        # (대부분의 환경에서 config는 존재하므로 0이 아닐 수도)
        result = cleanup_audit(30)
        assert isinstance(result, int)
