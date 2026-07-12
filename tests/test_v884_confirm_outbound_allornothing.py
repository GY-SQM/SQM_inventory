# -*- coding: utf-8 -*-
"""[감사 #3-M1/M2] confirm_outbound All-or-Nothing 회귀 테스트.

M1: sold_table INSERT 가 (미존재가 아닌) 실질 OperationalError 로 실패하면
    조용히 삼키지 말고 재전파 → 판매기록 없는 '반쪽 출고확정'을 막고 전체 롤백.
M2: 무게 재계산·사후검증을 커밋 '전'으로 옮겨, 무게 불변식(LOT_TOTAL_MISMATCH)
    위반을 커밋 전에 잡아 전체 롤백 → 깨진 상태를 애초에 커밋하지 않음.

수정 전:
  M1 → sold_table 기록 실패해도 톤백은 OUTBOUND 로 확정(success=True) → 판매기록 유실.
  M2 → 커밋 후 검증이라 무게 불일치를 발견해도 이미 확정됨(success=True) → wedge.
수정 후:
  둘 다 예외 → 트랜잭션 롤백 → success=False, confirmed=0, 톤백 PICKED 유지.
"""
import os
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


def _seed(e, lot, normals=2, kg=1000):
    db = e.db
    init = normals * kg + 1
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,0,?,'AVAILABLE')",
        (lot, "P1", init, init, normals))
    iid_row = db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,))
    iid = iid_row["id"] if isinstance(iid_row, dict) else iid_row[0]
    for s in range(1, normals + 1):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,?,0,'AVAILABLE')", (iid, lot, s, kg))
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')", (iid, lot))


def _cnt(e, sql, params=()):
    r = e.db.fetchone(sql, params)
    return (r["c"] if isinstance(r, dict) else r[0]) if r else 0


@pytest.fixture()
def eng():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    e = SQMInventoryEngineV3(db_path=path)
    yield e
    try:
        e.close()
    except Exception:
        pass
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def test_m1_sold_insert_failure_rolls_back_whole_confirm(eng, monkeypatch):
    """M1: sold_table INSERT 실질 오류 → 삼키지 않고 롤백."""
    _seed(eng, "LOTM1", normals=2)
    eng.quick_outbound("LOTM1", 2, "ACME")   # 톤백 2개 PICKED
    assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                "WHERE lot_no='LOTM1' AND status='PICKED'") == 2

    # sold_table INSERT 를 실질 OperationalError(락 등)로 강제 실패시킴.
    orig_execute = eng.db.execute

    def boom(sql, *a, **k):
        if isinstance(sql, str) and "sold_table" in sql and "INSERT" in sql.upper():
            raise sqlite3.OperationalError("database is locked")
        return orig_execute(sql, *a, **k)

    monkeypatch.setattr(eng.db, "execute", boom)

    r = eng.confirm_outbound("LOTM1")

    # 삼키지 않고 실패 → 전체 롤백
    assert r["success"] is False
    assert r.get("confirmed", 0) == 0
    assert r.get("errors")
    # 톤백은 PICKED 유지(OUTBOUND 로 넘어가지 않음) — All-or-Nothing
    monkeypatch.undo()   # 이후 검증 쿼리는 정상 execute 로
    assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                "WHERE lot_no='LOTM1' AND status='PICKED'") == 2
    assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                "WHERE lot_no='LOTM1' AND status='OUTBOUND'") == 0
    # 판매기록도 남지 않음
    assert _cnt(eng, "SELECT COUNT(*) c FROM sold_table WHERE lot_no='LOTM1'") == 0


def test_m1_missing_sold_table_is_still_tolerated(eng, monkeypatch):
    """M1 회귀 안전장치: sold_table 미존재('no such table')는 여전히 무시(재전파 안 함).

    (전체 confirm_outbound 경로는 이중출고 가드도 sold_table 을 조회하므로 테이블을
     통째로 지우면 그쪽에서 먼저 막힌다. 따라서 _co_insert_sold_row 의 '미존재' 분기만
     단위로 검증한다 — 이 분기는 구 스키마 방어용 레거시 경로다.)
    """
    _seed(eng, "LOTM1B", normals=1)
    row = eng.db.fetchone("SELECT * FROM inventory_tonbag WHERE lot_no='LOTM1B' LIMIT 1")
    tb = dict(row) if not isinstance(row, dict) else row

    def missing_table(sql, *a, **k):
        raise sqlite3.OperationalError("no such table: sold_table")

    monkeypatch.setattr(eng.db, "execute", missing_table)
    # 'no such table' → 예외를 삼키고 조용히 반환(재전파 X)
    eng._co_insert_sold_row(tb, "2026-07-12 00:00:00")   # 예외 없이 통과해야 함


def test_m2_weight_mismatch_rolls_back_before_commit(eng, monkeypatch):
    """M2: 사후검증(무게 불변식 위반)을 커밋 전에 잡아 전체 롤백."""
    _seed(eng, "LOTM2", normals=2)
    eng.quick_outbound("LOTM2", 2, "ACME")
    assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                "WHERE lot_no='LOTM2' AND status='PICKED'") == 2

    # 재계산 훅을 '무게를 망가뜨리는' 동작으로 교체 → 사후검증이 LOT_TOTAL_MISMATCH 감지.
    def corrupt_weight(lot_no, reason=None):
        eng.db.execute(
            "UPDATE inventory SET current_weight = 999999 WHERE lot_no = ?", (lot_no,))

    monkeypatch.setattr(eng, "_recalc_current_weight", corrupt_weight)

    r = eng.confirm_outbound("LOTM2")

    # 커밋 전 검증 → 예외 → 롤백
    assert r["success"] is False
    assert r.get("confirmed", 0) == 0
    assert r.get("errors")
    monkeypatch.undo()
    # 톤백 PICKED 유지, 무게도 롤백되어 원복
    assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                "WHERE lot_no='LOTM2' AND status='PICKED'") == 2
    assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                "WHERE lot_no='LOTM2' AND status='OUTBOUND'") == 0
    _cw = _cnt(eng, "SELECT current_weight c FROM inventory WHERE lot_no='LOTM2'")
    assert abs(float(_cw) - 999999) > 0.01, "손상된 무게가 커밋되지 않아야 함"
