# -*- coding: utf-8 -*-
"""[감사 #3-D] PENDING lot 무결성 예외 회귀 테스트.

정책(Option B): PENDING(입고확정 전) lot 은 재고 무게를 0으로 집계한다
(current=0/picked=0/initial>0). AVAILABLE→PENDING 상태복원 후 이 상태가 되는데,
verify_lot_integrity 가 initial=current+picked 를 무조건 검사해 정상 재고를
"무게 불일치"로 오탐하던 문제를 해소한다(검사 #1을 PENDING lot 에서 예외).

수정 전: PENDING lot(initial=1000, current=0) → valid=False.
수정 후: PENDING lot → valid=True (무게검사 예외), 단 다른 검사(샘플정책 등)는 유지.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


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


def _iid(e, lot):
    r = e.db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,))
    return r["id"] if isinstance(r, dict) else r[0]


def test_verify_lot_integrity_exempts_pending_lot(eng):
    db = eng.db
    # AVAILABLE→PENDING 상태복원 후 상태 재현:
    #   inventory 무게 0집계(current=0/picked=0), initial>0, 톤백 전부 PENDING
    # initial = 톤백합(500×2) + 샘플(1) = 1001 (대원칙 총무게 검사 충족)
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES ('LOTP','P1',1001,0,0,2,'PENDING')")
    iid = _iid(eng, "LOTP")
    for s in (1, 2):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,500,0,'PENDING')", (iid, "LOTP", s))
    # 샘플 톤백 1개(샘플정책 검사 충족용)
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'PENDING')", (iid, "LOTP"))

    r = eng.verify_lot_integrity("LOTP")
    # PENDING lot 은 무게 불변식 예외 → valid, '무게 불일치' 오류 없음
    assert r["valid"] is True, r.get("errors")
    assert not any("무게 불일치" in e for e in r.get("errors", []))


def test_verify_lot_integrity_still_flags_available_mismatch(eng):
    """예외가 과하지 않은지 확인: AVAILABLE lot 은 여전히 무게 불일치를 잡아야 함."""
    db = eng.db
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES ('LOTA','P1',1001,0,0,2,'AVAILABLE')")
    iid = _iid(eng, "LOTA")
    for s in (1, 2):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,500,0,'AVAILABLE')", (iid, "LOTA", s))
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')", (iid, "LOTA"))

    r = eng.verify_lot_integrity("LOTA")
    # AVAILABLE 인데 current=0(톤백은 AVAILABLE 500×2) → 불일치 감지되어야 함
    assert r["valid"] is False
