"""
v8.7.4 MVP-2: 스캔 없는 LOT 수량 출고 outbound_lot_qty() 테스트.

검증:
  1. 전량 출고(count=None) — 일반 전부 + 샘플(기본포함) PICKED, 무게보존 유지
  2. 부분 출고(count=N) — N개만 PICKED, 샘플 미포함(기본), 잔량 AVAILABLE, LOT=PARTIAL
  3. 부분 + include_sample=True — 샘플도 PICKED
  4. 이중출고 차단 — 동일 (lot, customer, sale_ref, date) 재시도
  5. count > 가용 — 에러
  6. unlocated=True — 톤백 location_state='UNLOCATED'
  7. 무결성: 모든 출고 후 verify_lot_integrity valid (initial=current+picked)
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


def _val(row, key, idx):
    if row is None:
        return None
    return row[key] if isinstance(row, dict) else row[idx]


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


def _seed_lot(e, lot_no="LOTX", normals=3, normal_kg=1000, with_sample=True):
    """LOT + 일반 톤백 N개(AVAILABLE) + 샘플 1개 세팅."""
    db = e.db
    init = normals * normal_kg + (1 if with_sample else 0)
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,0,?,'AVAILABLE')",
        (lot_no, "P1", init, init, normals))
    inv = db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot_no,))
    iid = _val(inv, "id", 0)
    for s in range(1, normals + 1):
        db.execute(
            "INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
            "is_sample, status) VALUES (?,?,?,?,0,'AVAILABLE')",
            (iid, lot_no, s, normal_kg))
    if with_sample:
        db.execute(
            "INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
            "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')",
            (iid, lot_no))


def _status_counts(e, lot_no="LOTX"):
    rows = e.db.fetchall(
        "SELECT status, COUNT(*) c FROM inventory_tonbag WHERE lot_no=? GROUP BY status",
        (lot_no,))
    return {_val(r, "status", 0): _val(r, "c", 1) for r in rows}


def test_full_outbound_includes_sample(eng):
    _seed_lot(eng, normals=3)
    r = eng.outbound_lot_qty("LOTX", count=None, customer="ACME", sale_ref="SC-1")
    assert r["success"], r["errors"]
    assert r["picked_count"] == 4          # 일반 3 + 샘플 1
    assert r["sample_picked"] == 1
    counts = _status_counts(eng)
    assert counts.get("PICKED") == 4
    assert counts.get("AVAILABLE", 0) == 0
    assert eng.verify_lot_integrity("LOTX")["valid"]


def test_partial_outbound_excludes_sample_by_default(eng):
    _seed_lot(eng, normals=3)
    r = eng.outbound_lot_qty("LOTX", count=2, customer="ACME", sale_ref="SC-2")
    assert r["success"], r["errors"]
    assert r["picked_count"] == 2
    assert r["sample_picked"] == 0
    counts = _status_counts(eng)
    assert counts.get("PICKED") == 2
    # 일반 1개 + 샘플 1개 = AVAILABLE 2
    assert counts.get("AVAILABLE") == 2
    # 설계 원칙(_recalc_lot_status): AVAILABLE 남아있고 OUTBOUND/SOLD 없으면 LOT=AVAILABLE.
    # PICKED 는 아직 "출고 완료(SOLD)"가 아니므로 PARTIAL 이 아니라 AVAILABLE 유지.
    inv = eng.db.fetchone("SELECT status FROM inventory WHERE lot_no='LOTX'")
    assert _val(inv, "status", 0) == "AVAILABLE"
    assert eng.verify_lot_integrity("LOTX")["valid"]


def test_partial_with_sample_opt_in(eng):
    _seed_lot(eng, normals=3)
    r = eng.outbound_lot_qty("LOTX", count=2, customer="ACME",
                             sale_ref="SC-3", include_sample=True)
    assert r["success"], r["errors"]
    assert r["picked_count"] == 3          # 일반 2 + 샘플 1
    assert r["sample_picked"] == 1
    assert eng.verify_lot_integrity("LOTX")["valid"]


def test_double_outbound_blocked(eng):
    _seed_lot(eng, normals=4)
    r1 = eng.outbound_lot_qty("LOTX", count=1, customer="ACME",
                              sale_ref="SC-X", outbound_date="2026-06-14")
    assert r1["success"], r1["errors"]
    r2 = eng.outbound_lot_qty("LOTX", count=1, customer="ACME",
                              sale_ref="SC-X", outbound_date="2026-06-14")
    assert not r2["success"]
    assert any("DUP_LOT_OUTBOUND" in e for e in r2["errors"])


def test_count_exceeds_available(eng):
    _seed_lot(eng, normals=2)
    r = eng.outbound_lot_qty("LOTX", count=5, customer="ACME", sale_ref="SC-4")
    assert not r["success"]
    assert any("부족" in e for e in r["errors"])


def test_unlocated_marks_location_state(eng):
    _seed_lot(eng, normals=2)
    r = eng.outbound_lot_qty("LOTX", count=1, customer="ACME",
                             sale_ref="SC-5", unlocated=True)
    assert r["success"], r["errors"]
    row = eng.db.fetchone(
        "SELECT location_state FROM inventory_tonbag "
        "WHERE lot_no='LOTX' AND status='PICKED' LIMIT 1")
    assert _val(row, "location_state", 0) == "UNLOCATED"


def test_confirm_true_goes_straight_to_sold(eng):
    _seed_lot(eng, normals=3)
    r = eng.outbound_lot_qty("LOTX", count=2, customer="ACME",
                             sale_ref="SC-CF", confirm=True)
    assert r["success"], r["errors"]
    assert r.get("sold") is True
    assert r.get("confirmed") == 2
    counts = _status_counts(eng)
    assert counts.get("SOLD") == 2          # PICKED 거치지 않고 SOLD 까지
    assert counts.get("PICKED", 0) == 0
    assert eng.verify_lot_integrity("LOTX")["valid"]
    sold = eng.db.fetchall("SELECT status FROM sold_table WHERE lot_no='LOTX'")
    assert len(sold) == 2


def test_confirm_false_stays_picked(eng):
    _seed_lot(eng, normals=3)
    r = eng.outbound_lot_qty("LOTX", count=2, customer="ACME", sale_ref="SC-PK")
    assert r["success"], r["errors"]
    assert not r.get("sold")
    counts = _status_counts(eng)
    assert counts.get("PICKED") == 2        # 기본은 PICKED 까지만
    assert counts.get("SOLD", 0) == 0
