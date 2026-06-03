"""
Phase 2-2 / 2-3 / 2-4 스모크 테스트
- audit_helper: 감사 로그 기록
- validators: 입력값 검증
- db_helper: DB 연결 재시도
"""
import os, sys, sqlite3, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════
# Phase 2-2: audit_helper
# ═══════════════════════════════════════════════════

def test_audit_helper_writes_record(tmp_path):
    """write_audit() 호출 시 audit_log에 행이 생성되어야 한다."""
    from backend.api.audit_helper import write_audit
    db = str(tmp_path / "test.db")
    write_audit(db, "TEST_EVENT",
                table_name="inventory", record_id="LOT-001",
                old_value="10", new_value="8",
                user_note="테스트")
    con = sqlite3.connect(db)
    row = con.execute("SELECT * FROM audit_log WHERE event_type='TEST_EVENT'").fetchone()
    con.close()
    assert row is not None, "audit_log에 기록이 없음"


def test_audit_helper_stores_payload_as_json(tmp_path):
    """event_data에 table_name / record_id 등이 JSON으로 저장되어야 한다."""
    import json
    from backend.api.audit_helper import write_audit
    db = str(tmp_path / "test.db")
    write_audit(db, "TEST_JSON",
                table_name="inventory", record_id="LOT-999",
                old_value="OLD", new_value="NEW")
    con = sqlite3.connect(db)
    row = con.execute("SELECT event_data FROM audit_log WHERE event_type='TEST_JSON'").fetchone()
    con.close()
    data = json.loads(row[0])
    assert data["table_name"] == "inventory"
    assert data["record_id"] == "LOT-999"
    assert data["old_value"] == "OLD"
    assert data["new_value"] == "NEW"


def test_audit_helper_does_not_crash_on_bad_path():
    """잘못된 DB 경로에도 예외 없이 실패를 흡수해야 한다."""
    from backend.api.audit_helper import write_audit
    # 예외가 발생하면 테스트 실패
    write_audit("/nonexistent/path/test.db", "SHOULD_FAIL")


def test_audit_helper_module_exists():
    """audit_helper.py 가 backend/api에 있어야 한다."""
    path = os.path.join(os.path.dirname(__file__), "..", "backend", "api", "audit_helper.py")
    assert os.path.exists(path)


def test_inventory_adjust_has_audit_call():
    """inventory_adjust_api.py에 audit 또는 write_audit 호출이 있어야 한다."""
    path = os.path.join(os.path.dirname(__file__), "..", "backend", "api", "inventory_adjust_api.py")
    code = open(path, encoding="utf-8", errors="ignore").read()
    assert "write_audit" in code or "audit_log" in code


# ═══════════════════════════════════════════════════
# Phase 2-3: validators
# ═══════════════════════════════════════════════════

def test_validate_lot_no_empty():
    from backend.api.validators import validate_lot_no
    errs = validate_lot_no("")
    assert len(errs) > 0, "빈 LOT번호 통과해서는 안 됨"


def test_validate_lot_no_valid():
    from backend.api.validators import validate_lot_no
    assert validate_lot_no("1126012309") == []


def test_validate_quantity_negative():
    from backend.api.validators import validate_quantity
    errs = validate_quantity(-5)
    assert len(errs) > 0, "음수 수량이 통과해서는 안 됨"


def test_validate_quantity_zero():
    """수량 0은 허용 (배차 0건 같은 케이스)."""
    from backend.api.validators import validate_quantity
    assert validate_quantity(0) == []


def test_validate_quantity_valid():
    from backend.api.validators import validate_quantity
    assert validate_quantity(100) == []


def test_validate_date_future():
    from backend.api.validators import validate_date
    errs = validate_date("2099-12-31")
    assert len(errs) > 0, "미래 날짜가 통과해서는 안 됨"


def test_validate_date_valid():
    from backend.api.validators import validate_date
    from datetime import date
    today = date.today().isoformat()
    assert validate_date(today) == []


def test_validate_date_bad_format():
    from backend.api.validators import validate_date
    errs = validate_date("31/12/2026")
    assert len(errs) > 0, "잘못된 날짜 형식이 통과해서는 안 됨"


def test_validate_date_empty_is_ok():
    """빈 날짜는 오류 없이 통과 (필수 여부는 호출자가 결정)."""
    from backend.api.validators import validate_date
    assert validate_date("") == []
    assert validate_date(None) == []


def test_validate_weight_negative():
    from backend.api.validators import validate_weight
    errs = validate_weight(-1.0)
    assert len(errs) > 0, "음수 중량이 통과해서는 안 됨"


def test_validate_weight_valid():
    from backend.api.validators import validate_weight
    assert validate_weight(1000.5) == []


def test_collect_errors_merges_lists():
    from backend.api.validators import collect_errors
    result = collect_errors(["에러A"], [], ["에러B", "에러C"])
    assert result == ["에러A", "에러B", "에러C"]


# ═══════════════════════════════════════════════════
# Phase 2-4: db_helper
# ═══════════════════════════════════════════════════

def test_db_helper_connects_and_returns_connection(tmp_path):
    """get_db_connection()이 유효한 SQLite Connection을 반환해야 한다."""
    from backend.api.db_helper import get_db_connection
    db = str(tmp_path / "test.db")
    con = get_db_connection(db)
    assert con is not None
    result = con.execute("SELECT 1").fetchone()
    assert result[0] == 1
    con.close()


def test_db_helper_applies_wal_mode(tmp_path):
    """WAL 모드가 설정되어야 한다."""
    from backend.api.db_helper import get_db_connection
    db = str(tmp_path / "test.db")
    con = get_db_connection(db)
    mode = con.execute("PRAGMA journal_mode").fetchone()[0]
    con.close()
    assert mode == "wal", f"WAL 모드 아님: {mode}"


def test_db_helper_row_factory(tmp_path):
    """row_factory=True일 때 결과를 컬럼 이름으로 접근 가능해야 한다."""
    from backend.api.db_helper import get_db_connection
    db = str(tmp_path / "test.db")
    con = get_db_connection(db, row_factory=True)
    con.execute("CREATE TABLE t (val INTEGER)")
    con.execute("INSERT INTO t VALUES (42)")
    row = con.execute("SELECT val FROM t").fetchone()
    con.close()
    assert row["val"] == 42


def test_db_helper_raises_on_invalid_path():
    """완전히 잘못된 경로는 예외를 발생시켜야 한다 (재시도 후)."""
    import pytest
    from backend.api.db_helper import get_db_connection
    with pytest.raises(Exception):
        get_db_connection("/totally/invalid/path/that/does/not/exist/test.db",
                          timeout=1, retries=1)
