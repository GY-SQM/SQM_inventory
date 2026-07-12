"""
v8.7.4: confirm_outbound (PICKED→SOLD) 무결성 버그 수정 회귀 테스트.

수정 전 버그 3종:
  1. _co_insert_outbound_movement: stock_movement INSERT "4 values for 5 columns"
     → confirm_outbound 전체 롤백 (PICKED→SOLD 확정 자체가 동작 안 함)
  2. _co_insert_sold_row: "19 values for 20 columns" + status='system' 오삽입
     → sold_table 기록이 조용히 실패 (0행)
  3. _recalc_current_weight: picked_weight 를 PICKED 만 합산
     → SOLD 전환 후 무게가 current/picked 어디에도 없어 initial=current+picked 깨짐

검증:
  - confirm_outbound 성공 + post_check_errors 없음
  - SOLD 후 verify_lot_integrity valid (initial=current+picked)
  - sold_table 에 행 생성 + status='SOLD'
  - 부분 확정 → LOT=PARTIAL, 전량 확정 → 잔여 가용 0
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


def _v(row, key, idx):
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


def _seed(e, lot="LOTX", normals=3, kg=1000):
    db = e.db
    init = normals * kg + 1
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,0,?,'AVAILABLE')",
        (lot, "P1", init, init, normals))
    iid = _v(db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,)), "id", 0)
    for s in range(1, normals + 1):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,?,0,'AVAILABLE')", (iid, lot, s, kg))
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')", (iid, lot))


def _lot(e, lot="LOTX"):
    r = e.db.fetchone(
        "SELECT initial_weight iw, current_weight cw, picked_weight pw, status st "
        "FROM inventory WHERE lot_no=?", (lot,))
    return (_v(r, "iw", 0), _v(r, "cw", 1), _v(r, "pw", 2), _v(r, "st", 3))


def test_confirm_outbound_partial_keeps_integrity(eng):
    _seed(eng, normals=3)
    assert eng.quick_outbound("LOTX", 2, "ACME")["success"]
    r = eng.confirm_outbound("LOTX")
    assert r["success"], r.get("errors")
    assert r["confirmed"] == 2
    assert not r.get("post_check_errors")          # 무결성 사후검증 통과

    iw, cw, pw, st = _lot(eng)
    assert abs(iw - (cw + pw)) <= 1.0              # 무게보존 유지
    assert eng.verify_lot_integrity("LOTX")["valid"]
    assert st == "PARTIAL"                          # AVAILABLE+SOLD 혼재

    sold = eng.db.fetchall("SELECT status FROM sold_table WHERE lot_no='LOTX'")
    assert len(sold) == 2                           # sold_table 기록됨
    assert all(_v(s, "status", 0) == "SOLD" for s in sold)


def test_confirm_outbound_stock_movement_recorded(eng):
    _seed(eng, normals=2)
    eng.quick_outbound("LOTX", 1, "ACME")
    eng.confirm_outbound("LOTX")
    mv = eng.db.fetchall(
        "SELECT movement_type FROM stock_movement WHERE lot_no='LOTX'")
    # OUTBOUND movement 가 최소 1건 기록되어야 함 (이전엔 INSERT 실패로 롤백)
    types = [_v(m, "movement_type", 0) for m in mv]
    assert "OUTBOUND" in types


def test_full_lot_confirm_depletes_available(eng):
    _seed(eng, normals=3)
    # 일반 3 + 샘플 1 전량 PICKED 후 확정
    eng.outbound_lot_qty("LOTX", count=None, customer="ACME",
                         sale_ref="SC-FULL", include_sample=True)
    r = eng.confirm_outbound("LOTX")
    assert r["success"], r.get("errors")
    assert not r.get("post_check_errors")
    iw, cw, pw, st = _lot(eng)
    assert abs(iw - (cw + pw)) <= 1.0
    assert eng.verify_lot_integrity("LOTX")["valid"]
    # 전량 출고 → 가용 톤백 0
    avail = eng.db.fetchone(
        "SELECT COUNT(*) c FROM inventory_tonbag "
        "WHERE lot_no='LOTX' AND status='AVAILABLE'")
    assert _v(avail, "c", 0) == 0


def _sold_count(e, lot="LOTX"):
    r = e.db.fetchone("SELECT COUNT(*) c FROM sold_table WHERE lot_no=?", (lot,))
    return _v(r, "c", 0)


def test_confirm_outbound_no_double_when_tonbags_already_sold(eng):
    """[fix F] 동시 확정(TOCTOU) 방지 회귀 테스트.

    톤백 로드/이중출고 가드는 트랜잭션 밖에서 수행된다. 두 요청이 거의 동시에
    진입하면 둘 다 같은 PICKED 톤백을 로드하고 둘 다 가드를 통과할 수 있다.
    '먼저 들어온 요청'이 이미 SOLD 로 확정한 상황을, 가드 통과 직후·트랜잭션
    직전 훅(_co_validate_customer_sale_ref)에서 톤백을 SOLD 로 바꿔 재현한다.

    수정 전(가드 없는 executemany): 두 번째 요청도 톤백을 다시 SOLD 마킹 +
    sold_table/stock_movement 재삽입 → 이중 출고.
    수정 후(status 가드 + rowcount 체크): 이미 SOLD 인 톤백은 rowcount=0 →
    재확정/재삽입하지 않음.
    """
    _seed(eng, normals=3)
    eng.quick_outbound("LOTX", 3, "ACME")     # 3개 PICKED
    assert _sold_count(eng) == 0

    real_validate = eng._co_validate_customer_sale_ref

    def _inject(tonbags, result):
        rv = real_validate(tonbags, result)
        # '동시 첫 요청'이 이미 확정한 상태 재현: 트랜잭션 직전에 SOLD 로 전환
        eng.db.execute(
            "UPDATE inventory_tonbag SET status='SOLD' "
            "WHERE lot_no='LOTX' AND status='PICKED'")
        return rv

    eng._co_validate_customer_sale_ref = _inject
    r = eng.confirm_outbound("LOTX")

    # 이미 SOLD → 이 요청은 재확정하지 않음 (이중 출고 없음)
    assert r.get("confirmed", 0) == 0, r
    assert _sold_count(eng) == 0            # sold_table 이중 삽입 없음
    mv = eng.db.fetchall(
        "SELECT id FROM stock_movement WHERE lot_no='LOTX' AND movement_type='OUTBOUND'")
    assert len(mv) == 0                     # stock_movement 이중 기록 없음
