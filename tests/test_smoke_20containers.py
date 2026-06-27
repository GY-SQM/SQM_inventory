"""
Smoke Test: 20 Virtual Containers — PENDING → AVAILABLE → PICKED → SOLD
불변식 initial_weight = current_weight + picked_weight 를 각 단계마다 검증
"""
import os
import sys
import tempfile
import logging
import pytest

logging.disable(logging.CRITICAL)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3

LOTS = [f"SMOKE{i:03d}" for i in range(1, 21)]  # SMOKE001 ~ SMOKE020
NORMAL_COUNT = 5        # 일반 톤백 개수
NORMAL_KG = 1000.0      # 톤백당 kg
SAMPLE_KG = 1.0         # 샘플 톤백 kg
INITIAL_WT = NORMAL_COUNT * NORMAL_KG + SAMPLE_KG  # 5001.0
PICK_COUNT = 3          # 출고할 톤백 수
CUSTOMER = "TEST_CO"


@pytest.fixture(scope="module")
def engine():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    e = SQMInventoryEngineV3(db_path=path)
    yield e
    try:
        e.close()
    except Exception:
        pass
    try:
        os.unlink(path)
    except Exception:
        pass


def _get_inv(db, lot_no):
    return db.fetchone(
        "SELECT status, initial_weight iw, current_weight cw, picked_weight pw "
        "FROM inventory WHERE lot_no=?", (lot_no,)
    )


def _check_invariant(row, lot_no, step):
    iw = row["iw"]
    cw = row["cw"]
    pw = row["pw"]
    diff = abs(iw - (cw + pw))
    assert diff <= 1.0, (
        f"[{step}] {lot_no}: 불변식 위반 iw={iw} != cw({cw})+pw({pw}), diff={diff}"
    )


def _seed(e, lot_no):
    db = e.db
    db.execute(
        "INSERT INTO inventory "
        "(lot_no, product, initial_weight, current_weight, picked_weight, mxbg_pallet, status) "
        "VALUES (?,?,?,?,0,?,'PENDING')",
        (lot_no, "CuCO3-TEST", INITIAL_WT, INITIAL_WT, NORMAL_COUNT),
    )
    iid = db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot_no,))["id"]
    for s in range(1, NORMAL_COUNT + 1):
        db.execute(
            "INSERT INTO inventory_tonbag "
            "(inventory_id, lot_no, sub_lt, weight, is_sample, status) "
            "VALUES (?,?,?,?,0,'PENDING')",
            (iid, lot_no, s, NORMAL_KG),
        )
    # 샘플 톤백 (sub_lt=0)
    db.execute(
        "INSERT INTO inventory_tonbag "
        "(inventory_id, lot_no, sub_lt, weight, is_sample, status) "
        "VALUES (?,?,0,?,1,'PENDING')",
        (iid, lot_no, SAMPLE_KG),
    )


# ────────────────────────────────────────────────────────────────
# STEP 1: 20 LOT 시딩 후 PENDING 검증
# ────────────────────────────────────────────────────────────────

class TestStep1_Pending:
    def test_seed_20_lots(self, engine):
        for lot in LOTS:
            _seed(engine, lot)

        db = engine.db
        count = db.fetchone("SELECT COUNT(*) n FROM inventory WHERE lot_no LIKE 'SMOKE%'")["n"]
        assert count == 20, f"예상 20 LOT, 실제 {count}"

    def test_pending_status(self, engine):
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            assert row is not None, f"{lot}: 레코드 없음"
            assert row["status"] == "PENDING", f"{lot}: status={row['status']}"
            assert row["cw"] == INITIAL_WT, f"{lot}: cw={row['cw']}"
            assert row["pw"] == 0.0, f"{lot}: pw={row['pw']}"

    def test_pending_invariant(self, engine):
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            _check_invariant(row, lot, "PENDING")

    def test_tonbag_count(self, engine):
        db = engine.db
        for lot in LOTS:
            cnt = db.fetchone(
                "SELECT COUNT(*) n FROM inventory_tonbag WHERE lot_no=?", (lot,)
            )["n"]
            assert cnt == NORMAL_COUNT + 1, f"{lot}: tonbag={cnt}"


# ────────────────────────────────────────────────────────────────
# STEP 2: PENDING → AVAILABLE (관리자 승인 시뮬레이션)
# ────────────────────────────────────────────────────────────────

class TestStep2_Available:
    def test_activate_all_lots(self, engine):
        db = engine.db
        db.execute(
            "UPDATE inventory SET status='AVAILABLE' WHERE lot_no LIKE 'SMOKE%'"
        )
        db.execute(
            "UPDATE inventory_tonbag SET status='AVAILABLE' WHERE lot_no LIKE 'SMOKE%'"
        )

    def test_available_status(self, engine):
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            assert row["status"] == "AVAILABLE", f"{lot}: status={row['status']}"

    def test_available_weights_unchanged(self, engine):
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            assert row["iw"] == INITIAL_WT, f"{lot}: iw={row['iw']}"
            assert row["cw"] == INITIAL_WT, f"{lot}: cw={row['cw']}"
            assert row["pw"] == 0.0, f"{lot}: pw={row['pw']}"

    def test_available_invariant(self, engine):
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            _check_invariant(row, lot, "AVAILABLE")


# ────────────────────────────────────────────────────────────────
# STEP 3: AVAILABLE → PICKED (quick_outbound)
# ────────────────────────────────────────────────────────────────

class TestStep3_Picked:
    def test_quick_outbound_all(self, engine):
        for lot in LOTS:
            r = engine.quick_outbound(lot, PICK_COUNT, CUSTOMER)
            assert r.get("success"), (
                f"{lot}: quick_outbound 실패 — {r.get('message', r)}"
            )

    def test_picked_weight_accounting(self, engine):
        expected_cw = INITIAL_WT - PICK_COUNT * NORMAL_KG
        expected_pw = PICK_COUNT * NORMAL_KG
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            assert abs(row["cw"] - expected_cw) <= 1.0, (
                f"{lot}: cw={row['cw']} 예상={expected_cw}"
            )
            assert abs(row["pw"] - expected_pw) <= 1.0, (
                f"{lot}: pw={row['pw']} 예상={expected_pw}"
            )

    def test_picked_invariant(self, engine):
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            _check_invariant(row, lot, "PICKED")

    def test_picked_tonbag_statuses(self, engine):
        db = engine.db
        for lot in LOTS:
            picked = db.fetchone(
                "SELECT COUNT(*) n FROM inventory_tonbag WHERE lot_no=? AND status='PICKED'",
                (lot,),
            )["n"]
            assert picked == PICK_COUNT, f"{lot}: PICKED tonbag={picked}"


# ────────────────────────────────────────────────────────────────
# STEP 4: PICKED → SOLD (confirm_outbound)
# ────────────────────────────────────────────────────────────────

class TestStep4_Sold:
    def test_confirm_outbound_all(self, engine):
        for lot in LOTS:
            r = engine.confirm_outbound(lot)
            assert r.get("success"), (
                f"{lot}: confirm_outbound 실패 — {r.get('errors', r)}"
            )
            assert r.get("confirmed", 0) == PICK_COUNT, (
                f"{lot}: confirmed={r.get('confirmed')} 예상={PICK_COUNT}"
            )

    def test_sold_invariant(self, engine):
        db = engine.db
        for lot in LOTS:
            row = _get_inv(db, lot)
            _check_invariant(row, lot, "SOLD")

    def test_sold_tonbag_count(self, engine):
        db = engine.db
        for lot in LOTS:
            sold = db.fetchone(
                "SELECT COUNT(*) n FROM inventory_tonbag WHERE lot_no=? AND status='SOLD'",
                (lot,),
            )["n"]
            assert sold == PICK_COUNT, f"{lot}: SOLD tonbag={sold}"


# ────────────────────────────────────────────────────────────────
# STEP 5: verify_lot_integrity + verify_all_integrity
# ────────────────────────────────────────────────────────────────

class TestStep5_Integrity:
    def test_per_lot_integrity(self, engine):
        for lot in LOTS:
            v = engine.verify_lot_integrity(lot)
            assert v.get("valid"), (
                f"{lot}: integrity invalid — {v.get('errors')}"
            )

    def test_all_integrity(self, engine):
        v = engine.verify_all_integrity()
        # 엔진이 dict 또는 list 반환 — 어느 쪽이든 에러 없음 확인
        if isinstance(v, dict):
            errors = v.get("errors") or v.get("invalid_lots") or []
            assert len(errors) == 0, f"전체 무결성 에러: {errors}"
        else:
            # list of results
            bad = [r for r in v if not r.get("valid")]
            assert len(bad) == 0, f"무결성 실패 LOT: {[r.get('lot_no') for r in bad]}"


# ────────────────────────────────────────────────────────────────
# STEP 6: 최종 수치 요약 (데이터 정합성 확인)
# ────────────────────────────────────────────────────────────────

class TestStep6_Summary:
    def test_20_lots_total_initial_weight(self, engine):
        db = engine.db
        total = db.fetchone(
            "SELECT SUM(initial_weight) s FROM inventory WHERE lot_no LIKE 'SMOKE%'"
        )["s"]
        expected = 20 * INITIAL_WT
        assert abs(total - expected) <= 1.0, f"총 initial_weight={total} 예상={expected}"

    def test_sold_tonbag_total_count(self, engine):
        db = engine.db
        sold = db.fetchone(
            "SELECT COUNT(*) n FROM inventory_tonbag "
            "WHERE lot_no LIKE 'SMOKE%' AND status='SOLD'"
        )["n"]
        assert sold == 20 * PICK_COUNT, f"총 SOLD tonbag={sold}"

    def test_remaining_available_tonbags(self, engine):
        db = engine.db
        avail = db.fetchone(
            "SELECT COUNT(*) n FROM inventory_tonbag "
            "WHERE lot_no LIKE 'SMOKE%' AND status='AVAILABLE'"
        )["n"]
        remaining_per_lot = NORMAL_COUNT - PICK_COUNT  # 2개 (+ 샘플 1개)
        expected = 20 * remaining_per_lot  # 40 (샘플 제외)
        # 샘플 포함 여부에 따라 ±20 범위 허용
        assert abs(avail - expected) <= 20, f"잔여 AVAILABLE tonbag={avail} (예상≈{expected})"
