"""
v8.7.4 출고 현실반영 마이그레이션 테스트.

검증:
  1. 신규 컬럼이 실제 마이그레이션 체인으로 추가되는지
     (allocation_plan.fulfillment_mode / scan_required / outbound_qty_mt,
      inventory_tonbag.location_state, inventory.location_state)
  2. LOT_QTY 이중출고 방지 Partial UNIQUE 인덱스 생성
  3. 멱등성: 마이그레이션 재실행해도 오류 없음
  4. DEFAULT 값: fulfillment_mode='SCAN_TONBAG', scan_required=1 (기존 동작 보존)
  5. Partial UNIQUE 인덱스가 LOT_QTY 출고 중복을 실제로 차단

설계: docs/SQM_출고_현실반영_설계_MVP1.md
"""
import os
import sys
import sqlite3
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


@pytest.fixture()
def db():
    """temp DB 로 엔진 생성 → 전체 마이그레이션 체인(v874 포함) 실행 후 SQMDatabase 반환."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = SQMInventoryEngineV3(db_path=path)
    yield eng.db
    try:
        eng.close()
    except Exception:
        pass
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def _cols(db, table):
    return {r[1].lower() for r in db.execute(f"PRAGMA table_info({table})").fetchall()}


def test_new_columns_added(db):
    ap = _cols(db, "allocation_plan")
    assert "fulfillment_mode" in ap
    assert "scan_required" in ap
    assert "outbound_qty_mt" in ap
    assert "location_state" in _cols(db, "inventory_tonbag")
    assert "location_state" in _cols(db, "inventory")


def test_dedup_index_exists(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_alloc_lotqty_dedup'"
    ).fetchall()
    assert len(rows) == 1


def test_migration_idempotent(db):
    # 재실행해도 예외 없이 통과해야 함 (PRAGMA 체크 + IF NOT EXISTS)
    db._migrate_v874_outbound_reality()
    db._migrate_v874_outbound_reality()
    assert "fulfillment_mode" in _cols(db, "allocation_plan")


def test_defaults_preserve_existing_behavior(db):
    # 기존 코드처럼 fulfillment_mode/scan_required 없이 INSERT → DEFAULT 적용
    db.execute(
        "INSERT INTO allocation_plan (lot_no, customer, sale_ref, qty_mt, status) "
        "VALUES ('LOT-T1', 'ACME', 'SC-1', 1.0, 'RESERVED')"
    )
    row = db.execute(
        "SELECT fulfillment_mode, scan_required, outbound_qty_mt "
        "FROM allocation_plan WHERE lot_no='LOT-T1'"
    ).fetchone()
    assert row[0] == "SCAN_TONBAG"
    assert row[1] == 1
    assert (row[2] or 0) == 0


def test_lotqty_double_outbound_blocked(db):
    # 동일 (lot, customer, sale_ref, date) LOT_QTY 출고 2회 → UNIQUE 위반 차단
    base = ("LOT-T2", "ACME", "SC-2", "2026-06-14", "LOT_QTY", "OUTBOUND")
    db.execute(
        "INSERT INTO allocation_plan "
        "(lot_no, customer, sale_ref, outbound_date, fulfillment_mode, status) "
        "VALUES (?,?,?,?,?,?)", base
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO allocation_plan "
            "(lot_no, customer, sale_ref, outbound_date, fulfillment_mode, status) "
            "VALUES (?,?,?,?,?,?)", base
        )
