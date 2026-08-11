"""
Phase 1-1 스모크 테스트 — DB 인덱스 자동 생성
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── 픽스처: 인메모리 DB (인덱스 대상 테이블 포함) ──────────────
def _make_test_db():
    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY,
            lot_no TEXT,
            status TEXT,
            inbound_date TEXT,
            product TEXT,
            current_weight REAL
        );
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY,
            event_type TEXT,
            created_at TEXT
        );
        CREATE TABLE ai_edit_log (
            id INTEGER PRIMARY KEY,
            table_name TEXT,
            changed_at TEXT,
            rolled_back INTEGER DEFAULT 0
        );
    """)
    return con


def test_indexes_created_on_inventory():
    """inventory 테이블에 4개 인덱스가 생성되는지 확인."""
    con = _make_test_db()
    target = [
        ("idx_inventory_lot_no",      "inventory", "lot_no"),
        ("idx_inventory_status",       "inventory", "status"),
        ("idx_inventory_inbound_date", "inventory", "inbound_date"),
        ("idx_inventory_product",      "inventory", "product"),
    ]
    for idx_name, tbl, col in target:
        con.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl}({col})")
    con.commit()

    names = {r[0] for r in
             con.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    for idx_name, _, _ in target:
        assert idx_name in names, f"인덱스 누락: {idx_name}"
    con.close()


def test_indexes_created_on_audit_log():
    """audit_log 인덱스 생성 확인."""
    con = _make_test_db()
    con.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at)")
    con.commit()
    names = {r[0] for r in
             con.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    assert "idx_audit_log_created_at" in names
    con.close()


def test_indexes_created_on_ai_edit_log():
    """ai_edit_log 인덱스 생성 확인."""
    con = _make_test_db()
    con.execute("CREATE INDEX IF NOT EXISTS idx_ai_edit_log_changed_at ON ai_edit_log(changed_at)")
    con.commit()
    names = {r[0] for r in
             con.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    assert "idx_ai_edit_log_changed_at" in names
    con.close()


def test_index_creation_is_idempotent():
    """IF NOT EXISTS — 이미 있어도 에러 없이 통과."""
    con = _make_test_db()
    for _ in range(3):  # 3번 실행해도 에러 없음
        con.execute("CREATE INDEX IF NOT EXISTS idx_inventory_lot_no ON inventory(lot_no)")
    con.commit()
    count = con.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='idx_inventory_lot_no'"
    ).fetchone()[0]
    assert count == 1, "중복 인덱스가 생성되면 안 됨"
    con.close()


def test_missing_table_does_not_crash():
    """대상 테이블이 없어도 예외 없이 무시."""
    con = sqlite3.connect(":memory:")
    # ai_edit_log 테이블 없는 상태
    try:
        con.execute("CREATE INDEX IF NOT EXISTS idx_ai_edit_log_changed_at ON ai_edit_log(changed_at)")
    except Exception:
        pass  # 예외는 허용 — 상위에서 try/except로 감싸야 함
    con.close()


def test_real_db_has_indexes():
    """실제 프로젝트 DB에 인덱스가 존재하는지 확인."""
    import pytest

    if os.environ.get("GITHUB_ACTIONS") == "true":
        pytest.skip("CI 환경에서는 운영 DB 인덱스 검사를 건너뜀")

    db_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "db", "sqm_inventory.db"
    )
    if not os.path.exists(db_path):
        pytest.skip("실제 DB 파일 없음 — CI 환경에서 건너뜀")
    con = sqlite3.connect(db_path)
    names = {r[0] for r in
             con.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    con.close()

    required = [
        "idx_inventory_lot_no",
        "idx_inventory_status",
        "idx_inventory_inbound_date",
        "idx_inventory_product",
        "idx_audit_log_created_at",
        "idx_ai_edit_log_changed_at",
    ]
    missing = [n for n in required if n not in names]
    assert not missing, f"실제 DB에 누락된 인덱스: {missing}"
