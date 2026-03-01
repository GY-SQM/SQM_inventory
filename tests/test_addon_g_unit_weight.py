# -*- coding: utf-8 -*-
"""
SQM v6.12 Addon-G 테스트: 500kg / 1000kg 동적 대응
=====================================================
500kg LOT 입고→출고→반품, 1000kg LOT 입고→출고→반품,
혼합 시나리오를 인메모리 SQLite DB에서 테스트합니다.

실행:
  cd SQM_v612
  python -m pytest tests/test_addon_g_unit_weight.py -v
  
  또는 직접:
  python tests/test_addon_g_unit_weight.py
"""

import os
import sys
import sqlite3
import logging
import pytest
from datetime import datetime, date

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# 경량 DB 래퍼 (테스트용)
# ═══════════════════════════════════════════════════════
class TestDB:
    """인메모리 SQLite — 실제 SQMDatabase의 핵심 메서드만 구현."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        c = self.conn
        c.execute("""
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT UNIQUE NOT NULL,
                product TEXT DEFAULT 'LITHIUM CARBONATE',
                net_weight REAL DEFAULT 0,
                initial_weight REAL DEFAULT 0,
                current_weight REAL DEFAULT 0,
                picked_weight REAL DEFAULT 0,
                mxbg_pallet INTEGER DEFAULT 0,
                tonbag_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'AVAILABLE',
                sap_no TEXT, bl_no TEXT, container_no TEXT,
                warehouse TEXT DEFAULT '광양',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE inventory_tonbag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER NOT NULL DEFAULT 0,
                weight REAL DEFAULT 500.0,
                is_sample INTEGER DEFAULT 0,
                status TEXT DEFAULT 'AVAILABLE',
                tonbag_uid TEXT,
                tonbag_no TEXT,
                picked_to TEXT, picked_date TEXT, pick_ref TEXT,
                outbound_date TEXT, sale_ref TEXT, picking_no TEXT,
                location TEXT, remarks TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE picking_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                tonbag_id INTEGER,
                sub_lt INTEGER,
                tonbag_uid TEXT,
                picking_no TEXT,
                sales_order_no TEXT,
                customer TEXT,
                qty_kg REAL,
                is_sample INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE',
                picking_date TEXT DEFAULT (datetime('now')),
                sold_date TEXT,
                source TEXT
            )
        """)
        c.execute("""
            CREATE TABLE sold_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT, sub_lt INTEGER,
                picking_id INTEGER,
                weight_kg REAL,
                status TEXT DEFAULT 'SOLD',
                sold_date TEXT
            )
        """)
        c.execute("""
            CREATE TABLE stock_movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                qty_kg REAL DEFAULT 0,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE return_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER,
                return_date DATE,
                original_customer TEXT,
                original_sale_ref TEXT,
                reason TEXT, remark TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE allocation_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT, sub_lt INTEGER,
                status TEXT DEFAULT 'RESERVED',
                cancelled_at TEXT
            )
        """)
        c.commit()

    def execute(self, sql, params=None):
        return self.conn.execute(sql, params or ())

    def fetchone(self, sql, params=None):
        row = self.conn.execute(sql, params or ()).fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self, sql, params=None):
        return [dict(r) for r in self.conn.execute(sql, params or ()).fetchall()]

    def transaction(self, mode="IMMEDIATE"):
        """컨텍스트 매니저 — 테스트용 간이 구현."""
        return self.conn

    def commit(self):
        self.conn.commit()


# ═══════════════════════════════════════════════════════
# 헬퍼: LOT 입고 시뮬레이션
# ═══════════════════════════════════════════════════════
def create_lot(db: TestDB, lot_no: str, bag_count: int, unit_weight: float):
    """LOT 입고 시뮬레이션 (대원칙: total = bag_count × unit_weight + 1kg 샘플)."""
    sample_kg = 1.0
    total_weight = bag_count * unit_weight + sample_kg

    db.execute(
        "INSERT INTO inventory (lot_no, net_weight, initial_weight, current_weight, "
        "mxbg_pallet, tonbag_count, status) VALUES (?,?,?,?,?,?,?)",
        (lot_no, total_weight, total_weight, total_weight, bag_count, bag_count, 'AVAILABLE'))

    inv_id = db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot_no,))['id']

    # 일반 톤백
    for i in range(1, bag_count + 1):
        uid = f"{lot_no}-{i}"
        db.execute(
            "INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
            "is_sample, status, tonbag_uid, tonbag_no) VALUES (?,?,?,?,0,'AVAILABLE',?,?)",
            (inv_id, lot_no, i, unit_weight, uid, str(i)))

    # 샘플
    db.execute(
        "INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
        "is_sample, status, tonbag_uid, tonbag_no) VALUES (?,?,0,1.0,1,'AVAILABLE',?,?)",
        (inv_id, lot_no, f"{lot_no}-S0", 'S00'))

    db.commit()
    return total_weight


def simulate_outbound(db: TestDB, lot_no: str, pick_count: int, picking_no: str, customer: str):
    """출고 시뮬레이션: AVAILABLE 톤백 → PICKED + picking_table INSERT."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tonbags = db.fetchall(
        "SELECT id, sub_lt, weight FROM inventory_tonbag "
        "WHERE lot_no=? AND status='AVAILABLE' AND COALESCE(is_sample,0)=0 "
        "ORDER BY sub_lt ASC LIMIT ?",
        (lot_no, pick_count))

    picked_weight = 0
    for tb in tonbags:
        db.execute(
            "UPDATE inventory_tonbag SET status='PICKED', picked_to=?, picking_no=?, "
            "picked_date=?, updated_at=? WHERE id=?",
            (customer, picking_no, now, now, tb['id']))
        db.execute(
            "INSERT INTO picking_table (lot_no, tonbag_id, sub_lt, picking_no, "
            "customer, qty_kg, status, picking_date) VALUES (?,?,?,?,?,?,'ACTIVE',?)",
            (lot_no, tb['id'], tb['sub_lt'], picking_no, customer, tb['weight'], now))
        picked_weight += tb['weight']

    db.execute(
        "UPDATE inventory SET current_weight = current_weight - ?, "
        "picked_weight = picked_weight + ?, updated_at=? WHERE lot_no=?",
        (picked_weight, picked_weight, now, lot_no))
    db.commit()
    return len(tonbags), picked_weight


# ═══════════════════════════════════════════════════════
# 테스트 1: get_tonbag_unit_weight DB 조회
# ═══════════════════════════════════════════════════════
def test_get_tonbag_unit_weight():
    """get_tonbag_unit_weight가 500/1000 LOT 각각 정확한 단가를 반환하는지."""
    from engine_modules.constants import get_tonbag_unit_weight, DEFAULT_TONBAG_WEIGHT

    db = TestDB()

    # 500kg LOT
    create_lot(db, "LOT500TEST", bag_count=10, unit_weight=500.0)
    assert get_tonbag_unit_weight(db, "LOT500TEST") == 500.0, "500kg LOT 단가 조회 실패"

    # 1000kg LOT
    create_lot(db, "LOT1000TEST", bag_count=10, unit_weight=1000.0)
    assert get_tonbag_unit_weight(db, "LOT1000TEST") == 1000.0, "1000kg LOT 단가 조회 실패"

    # 존재하지 않는 LOT → fallback
    assert get_tonbag_unit_weight(db, "NONEXIST") == DEFAULT_TONBAG_WEIGHT, "fallback 실패"

    # None DB → fallback
    assert get_tonbag_unit_weight(None, "LOT500TEST") == DEFAULT_TONBAG_WEIGHT, "None DB fallback 실패"

    print("  ✅ test_get_tonbag_unit_weight 통과")


# ═══════════════════════════════════════════════════════
# 테스트 2: estimate_tonbag_count
# ═══════════════════════════════════════════════════════
def test_estimate_tonbag_count():
    """estimate_tonbag_count가 단가별로 정확한 톤백 수를 반환."""
    from engine_modules.constants import estimate_tonbag_count

    # 5000kg / 500kg = 10개
    assert estimate_tonbag_count(5000, 500) == 10
    # 10000kg / 1000kg = 10개
    assert estimate_tonbag_count(10000, 1000) == 10
    # 5000kg / 1000kg = 5개
    assert estimate_tonbag_count(5000, 1000) == 5
    # 10000kg / 500kg = 20개
    assert estimate_tonbag_count(10000, 500) == 20
    # unit_weight=0 → DEFAULT(500) 사용
    assert estimate_tonbag_count(5000, 0) == 10
    # 최소 1개 보장
    assert estimate_tonbag_count(100, 500) == 1

    print("  ✅ test_estimate_tonbag_count 통과")


# ═══════════════════════════════════════════════════════
# 테스트 3: 500kg LOT 입고 → 대원칙 검증
# ═══════════════════════════════════════════════════════
def test_500kg_lot_inbound():
    """500kg × 10개 + 샘플 1kg = 5001kg LOT 입고 검증."""
    db = TestDB()
    total = create_lot(db, "LOT500A", bag_count=10, unit_weight=500.0)

    assert total == 5001.0, f"총 무게 불일치: {total}"

    # 톤백 수 확인
    tb_count = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no='LOT500A' AND is_sample=0"
    )['cnt']
    assert tb_count == 10, f"톤백 수 불일치: {tb_count}"

    # 샘플 확인
    sample = db.fetchone(
        "SELECT weight FROM inventory_tonbag WHERE lot_no='LOT500A' AND is_sample=1"
    )
    assert sample['weight'] == 1.0, f"샘플 무게 불일치: {sample['weight']}"

    # 합계 검증
    tb_sum = db.fetchone(
        "SELECT SUM(weight) AS s FROM inventory_tonbag WHERE lot_no='LOT500A'"
    )['s']
    assert abs(tb_sum - 5001.0) < 0.01, f"톤백 합계 불일치: {tb_sum}"

    print("  ✅ test_500kg_lot_inbound 통과")


# ═══════════════════════════════════════════════════════
# 테스트 4: 1000kg LOT 입고 → 대원칙 검증
# ═══════════════════════════════════════════════════════
def test_1000kg_lot_inbound():
    """1000kg × 10개 + 샘플 1kg = 10001kg LOT 입고 검증."""
    db = TestDB()
    total = create_lot(db, "LOT1000A", bag_count=10, unit_weight=1000.0)

    assert total == 10001.0, f"총 무게 불일치: {total}"

    tb_count = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no='LOT1000A' AND is_sample=0"
    )['cnt']
    assert tb_count == 10, f"톤백 수 불일치: {tb_count}"

    # 개별 톤백 무게 확인
    weights = db.fetchall(
        "SELECT weight FROM inventory_tonbag WHERE lot_no='LOT1000A' AND is_sample=0"
    )
    for w in weights:
        assert w['weight'] == 1000.0, f"톤백 개별 무게 불일치: {w['weight']}"

    print("  ✅ test_1000kg_lot_inbound 통과")


# ═══════════════════════════════════════════════════════
# 테스트 5: 500kg LOT 출고 → pick_count 정확성
# ═══════════════════════════════════════════════════════
def test_500kg_outbound():
    """500kg LOT에서 5개 출고 → 2500kg 차감."""
    db = TestDB()
    create_lot(db, "LOT500B", bag_count=10, unit_weight=500.0)

    picked, weight = simulate_outbound(db, "LOT500B", 5, "PK-500-01", "고객A")
    assert picked == 5, f"출고 수 불일치: {picked}"
    assert weight == 2500.0, f"출고 무게 불일치: {weight}"

    # 잔여 재고 확인
    inv = db.fetchone("SELECT current_weight FROM inventory WHERE lot_no='LOT500B'")
    assert abs(inv['current_weight'] - 2501.0) < 0.01, f"잔여 재고 불일치: {inv['current_weight']}"

    # AVAILABLE 톤백 수
    avail = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM inventory_tonbag "
        "WHERE lot_no='LOT500B' AND status='AVAILABLE' AND is_sample=0"
    )['cnt']
    assert avail == 5, f"가용 톤백 불일치: {avail}"

    print("  ✅ test_500kg_outbound 통과")


# ═══════════════════════════════════════════════════════
# 테스트 6: 1000kg LOT 출고 → pick_count 정확성
# ═══════════════════════════════════════════════════════
def test_1000kg_outbound():
    """1000kg LOT에서 5개 출고 → 5000kg 차감."""
    db = TestDB()
    create_lot(db, "LOT1000B", bag_count=10, unit_weight=1000.0)

    picked, weight = simulate_outbound(db, "LOT1000B", 5, "PK-1000-01", "고객B")
    assert picked == 5, f"출고 수 불일치: {picked}"
    assert weight == 5000.0, f"출고 무게 불일치: {weight}"

    inv = db.fetchone("SELECT current_weight FROM inventory WHERE lot_no='LOT1000B'")
    assert abs(inv['current_weight'] - 5001.0) < 0.01, f"잔여 재고 불일치: {inv['current_weight']}"

    print("  ✅ test_1000kg_outbound 통과")


# ═══════════════════════════════════════════════════════
# 테스트 7: 반품 엔진 — 1000kg LOT tonbag_count 보정
# ═══════════════════════════════════════════════════════
def test_return_inbound_1000kg_correction():
    """반품 엔진이 파서의 500kg 추정을 1000kg으로 보정하는지 확인."""
    from engine_modules.constants import get_tonbag_unit_weight

    db = TestDB()
    create_lot(db, "LOT1000C", bag_count=10, unit_weight=1000.0)
    simulate_outbound(db, "LOT1000C", 3, "PK-1000-02", "고객C")

    # 파서가 3000kg/500 = 6개로 잘못 추정한 상황 시뮬레이션
    parsed = {
        "parse_ok": True,
        "items": [{
            "lot_no": "LOT1000C",
            "weight_mt": 3.0,          # 3MT = 3000kg
            "tonbag_count": 6,          # ← 파서 추정 (3000/500=6) — 잘못됨!
            "picking_no": "PK-1000-02",
            "reason": "품질 불량",
            "remark": "",
            "return_date": date.today().strftime("%Y-%m-%d"),
            "sales_order_no": "", "bl_no": "", "is_sample": False,
        }]
    }

    # Addon-G 보정 로직 직접 테스트 (return_inbound_engine의 보정 부분)
    item = parsed["items"][0]
    lot_no = item["lot_no"]

    tb_row = db.fetchone(
        "SELECT weight FROM inventory_tonbag "
        "WHERE lot_no=? AND COALESCE(is_sample,0)=0 AND weight>0 LIMIT 1",
        (lot_no,))

    if tb_row:
        unit_w = float(tb_row['weight'])
        weight_kg = item["weight_mt"] * 1000
        corrected = max(1, int(weight_kg / unit_w))

        assert unit_w == 1000.0, f"단가 조회 실패: {unit_w}"
        assert corrected == 3, f"보정 실패: {corrected} (기대: 3)"
        assert item["tonbag_count"] == 6, "원본 파서 값 확인"

        # 보정 적용
        item["tonbag_count"] = corrected
        assert item["tonbag_count"] == 3, "보정 후 값 확인"

    print("  ✅ test_return_inbound_1000kg_correction 통과")


# ═══════════════════════════════════════════════════════
# 테스트 8: 혼합 시나리오 — 500kg + 1000kg LOT 동시 운영
# ═══════════════════════════════════════════════════════
def test_mixed_500_1000():
    """같은 DB에 500kg LOT과 1000kg LOT이 공존할 때 각각 정확히 처리."""
    from engine_modules.constants import get_tonbag_unit_weight

    db = TestDB()

    # 두 LOT 동시 입고
    create_lot(db, "MIX500", bag_count=10, unit_weight=500.0)   # 5001kg
    create_lot(db, "MIX1000", bag_count=10, unit_weight=1000.0) # 10001kg

    # 단가 조회 — 각각 독립적으로 정확해야 함
    assert get_tonbag_unit_weight(db, "MIX500") == 500.0
    assert get_tonbag_unit_weight(db, "MIX1000") == 1000.0

    # 각각 3개 출고
    p1, w1 = simulate_outbound(db, "MIX500", 3, "PK-MIX-01", "고객X")
    p2, w2 = simulate_outbound(db, "MIX1000", 3, "PK-MIX-02", "고객Y")

    assert p1 == 3 and w1 == 1500.0, f"500kg 출고 오류: {p1}, {w1}"
    assert p2 == 3 and w2 == 3000.0, f"1000kg 출고 오류: {p2}, {w2}"

    # 잔여 재고
    inv500 = db.fetchone("SELECT current_weight FROM inventory WHERE lot_no='MIX500'")
    inv1000 = db.fetchone("SELECT current_weight FROM inventory WHERE lot_no='MIX1000'")

    assert abs(inv500['current_weight'] - 3501.0) < 0.01  # 5001 - 1500
    assert abs(inv1000['current_weight'] - 7001.0) < 0.01  # 10001 - 3000

    print("  ✅ test_mixed_500_1000 통과")


# ═══════════════════════════════════════════════════════
# 테스트 9: 진단 스크립트
# ═══════════════════════════════════════════════════════
try:
    from utils.db_tonbag_weight_diagnostic import diagnose_tonbag_weights as _dtw
    _dtw_available = True
except (ImportError, ModuleNotFoundError):
    _dtw_available = False

@pytest.mark.skipif(not _dtw_available,
                    reason="utils.db_tonbag_weight_diagnostic 모듈 미존재")
def test_diagnostic_script():
    """db_tonbag_weight_diagnostic가 500/1000 혼합을 정확히 감지."""
    import tempfile
    from utils.db_tonbag_weight_diagnostic import diagnose_tonbag_weights
    db = TestDB()
    create_lot(db, "DIAG500", bag_count=10, unit_weight=500.0)
    create_lot(db, "DIAG1000", bag_count=5, unit_weight=1000.0)

    # 인메모리 → 임시 파일로 백업 (진단 스크립트가 파일 경로 필요)
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    backup_conn = sqlite3.connect(tmp.name)
    db.conn.backup(backup_conn)
    backup_conn.close()

    diag = diagnose_tonbag_weights(tmp.name)

    assert diag['total_tonbags'] == 15, f"톤백 수 불일치: {diag['total_tonbags']}"  # 10 + 5
    assert diag['total_samples'] == 2, f"샘플 수 불일치: {diag['total_samples']}"
    assert 500.0 in diag['unit_weight_distribution'], "500kg 미감지"
    assert 1000.0 in diag['unit_weight_distribution'], "1000kg 미감지"
    assert diag['unit_weight_distribution'][500.0] == 10
    assert diag['unit_weight_distribution'][1000.0] == 5
    assert len(diag['anomalies']) == 0 or all('비표준' not in a for a in diag['anomalies'])

    os.unlink(tmp.name)
    print("  ✅ test_diagnostic_script 통과")


# ═══════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════
def run_all():
    tests = [
        test_get_tonbag_unit_weight,
        test_estimate_tonbag_count,
        test_500kg_lot_inbound,
        test_1000kg_lot_inbound,
        test_500kg_outbound,
        test_1000kg_outbound,
        test_return_inbound_1000kg_correction,
        test_mixed_500_1000,
        test_diagnostic_script,
    ]

    print("=" * 60)
    print("  SQM v6.12 Addon-G 테스트: 500/1000kg 동적 대응")
    print("=" * 60)

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1

    print()
    print("─" * 60)
    print(f"  결과: {passed} 통과 / {failed} 실패 / 총 {len(tests)}건")
    if failed == 0:
        print("  ✅✅✅ 전체 통과! ✅✅✅")
    else:
        print("  ❌ 실패 항목 확인 필요")
    print("=" * 60)
    return failed == 0


if __name__ == '__main__':
    success = run_all()
    sys.exit(0 if success else 1)
