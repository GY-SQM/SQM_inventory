# -*- coding: utf-8 -*-
"""
tests/test_v700_performance.py
================================
SQM v7.0.0 — 성능 / 부하 테스트 (20개)
=========================================

검증 항목:
  P1. 데이터 생성 속도      (T01~T05)
  P2. DB INSERT 속도        (T06~T10)
  P3. SQL 쿼리 응답 속도    (T11~T15)
  P4. 대규모 중량 계산 속도  (T16~T20)

기준:
  - 660 레코드 INSERT  < 1.0초
  - 단순 SELECT 쿼리   < 0.1초
  - 복잡 JOIN 쿼리     < 0.5초
  - 중량 집계 연산     < 0.2초
"""
import pytest
import time
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.fixtures.sqm_scenario_data import (
    build_scenario, create_scenario_db,
    LOT_TOTAL_WEIGHT_KG,
)


@pytest.fixture(scope="module")
def scenario():
    return build_scenario()


@pytest.fixture(scope="module")
def db():
    conn = create_scenario_db(":memory:")
    yield conn
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# P1. 데이터 생성 속도 (T01~T05)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP1DataGenSpeed:

    def test_T_P01_build_scenario_under_1sec(self):
        start = time.perf_counter()
        _ = build_scenario()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"build_scenario {elapsed:.3f}s > 1.0s"

    def test_T_P02_build_scenario_under_200ms(self):
        start = time.perf_counter()
        _ = build_scenario()
        elapsed = time.perf_counter() - start
        assert elapsed < 0.2, f"build_scenario {elapsed:.3f}s > 200ms"

    def test_T_P03_lot_generation_per_unit_under_1ms(self):
        start = time.perf_counter()
        s = build_scenario()
        elapsed = time.perf_counter() - start
        per_lot = elapsed / len(s['lots']) * 1000  # ms
        assert per_lot < 1.0, f"LOT 1개 생성 {per_lot:.3f}ms > 1ms"

    def test_T_P04_tonbag_generation_per_unit_under_01ms(self):
        start = time.perf_counter()
        s = build_scenario()
        elapsed = time.perf_counter() - start
        per_tb = elapsed / len(s['tonbags']) * 1000
        assert per_tb < 0.1, f"톤백 1개 생성 {per_tb:.4f}ms > 0.1ms"

    def test_T_P05_repeated_build_consistent_speed(self):
        """10회 반복 빌드: 최대/최소 편차 < 200ms"""
        times = []
        for _ in range(10):
            t = time.perf_counter()
            build_scenario()
            times.append(time.perf_counter() - t)
        spread = max(times) - min(times)
        assert spread < 0.2, f"빌드 편차 {spread:.3f}s > 200ms"


# ═══════════════════════════════════════════════════════════════════════════════
# P2. DB INSERT 속도 (T06~T10)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP2DBInsertSpeed:

    def test_T_P06_full_db_insert_under_1sec(self):
        start = time.perf_counter()
        conn = create_scenario_db(":memory:")
        elapsed = time.perf_counter() - start
        conn.close()
        assert elapsed < 1.0, f"전체 INSERT {elapsed:.3f}s > 1.0s"

    def test_T_P07_full_db_insert_under_500ms(self):
        start = time.perf_counter()
        conn = create_scenario_db(":memory:")
        elapsed = time.perf_counter() - start
        conn.close()
        assert elapsed < 0.5, f"전체 INSERT {elapsed:.3f}s > 500ms"

    def test_T_P08_tonbag_insert_rate_over_1000_per_sec(self):
        start = time.perf_counter()
        conn = create_scenario_db(":memory:")
        elapsed = time.perf_counter() - start
        conn.close()
        rate = 660 / elapsed
        assert rate > 1000, f"톤백 INSERT 속도 {rate:.0f}/s < 1000/s"

    def test_T_P09_repeated_db_create_consistent(self):
        """5회 반복 DB 생성: 최대 < 1.0s"""
        for _ in range(5):
            t = time.perf_counter()
            conn = create_scenario_db(":memory:")
            conn.close()
            elapsed = time.perf_counter() - t
            assert elapsed < 1.0, f"DB 생성 {elapsed:.3f}s > 1.0s"

    def test_T_P10_concurrent_inserts_no_error(self):
        """단일 스레드 5회 연속 INSERT: 오류 없음"""
        errors = 0
        for _ in range(5):
            try:
                conn = create_scenario_db(":memory:")
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM inventory_tonbag"
                ).fetchone()[0]
                assert cnt == 660
                conn.close()
            except Exception:
                errors += 1
        assert errors == 0


# ═══════════════════════════════════════════════════════════════════════════════
# P3. SQL 쿼리 응답 속도 (T11~T15)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3QuerySpeed:

    def test_T_P11_simple_count_under_10ms(self, db):
        start = time.perf_counter()
        db.execute("SELECT COUNT(*) FROM inventory").fetchone()
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 10, f"COUNT 쿼리 {elapsed:.2f}ms > 10ms"

    def test_T_P12_full_scan_under_50ms(self, db):
        start = time.perf_counter()
        db.execute("SELECT * FROM inventory_tonbag").fetchall()
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 50, f"전체 스캔 {elapsed:.2f}ms > 50ms"

    def test_T_P13_join_query_under_100ms(self, db):
        start = time.perf_counter()
        db.execute("""
            SELECT i.lot_no, SUM(t.weight_kg) as total
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
        """).fetchall()
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 100, f"JOIN 집계 {elapsed:.2f}ms > 100ms"

    def test_T_P14_allocation_join_under_50ms(self, db):
        start = time.perf_counter()
        db.execute("""
            SELECT a.customer, COUNT(*) as cnt, SUM(a.qty_mt) as total_mt
            FROM allocation_plan a
            JOIN inventory i ON a.lot_no = i.lot_no
            GROUP BY a.customer
        """).fetchall()
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 50, f"Allocation JOIN {elapsed:.2f}ms > 50ms"

    def test_T_P15_repeated_queries_no_degradation(self, db):
        """동일 쿼리 100회 반복: 평균 < 5ms"""
        times = []
        for _ in range(100):
            t = time.perf_counter()
            db.execute("SELECT COUNT(*) FROM inventory_tonbag WHERE is_sample=0").fetchone()
            times.append((time.perf_counter() - t) * 1000)
        avg = sum(times) / len(times)
        assert avg < 5, f"평균 쿼리 시간 {avg:.3f}ms > 5ms"


# ═══════════════════════════════════════════════════════════════════════════════
# P4. 대규모 중량 계산 속도 (T16~T20)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP4WeightCalcSpeed:

    def test_T_P16_total_weight_aggregation_under_20ms(self, db):
        start = time.perf_counter()
        db.execute("SELECT SUM(total_weight_kg) FROM inventory").fetchone()
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 20, f"총중량 집계 {elapsed:.2f}ms > 20ms"

    def test_T_P17_per_lot_weight_calculation_correct(self, db):
        """60 LOT 전체 중량 계산 정확도"""
        rows = db.execute("""
            SELECT lot_no, SUM(weight_kg) as s
            FROM inventory_tonbag
            GROUP BY lot_no
        """).fetchall()
        assert len(rows) == 60
        for r in rows:
            assert abs(r['s'] - LOT_TOTAL_WEIGHT_KG) < 0.01

    def test_T_P18_sample_excluded_weight_correct(self, db):
        """샘플 제외 가용 중량 = 600 × 500kg = 300,000kg"""
        total = db.execute(
            "SELECT SUM(weight_kg) FROM inventory_tonbag WHERE is_sample=0"
        ).fetchone()[0]
        expected = 600 * 500.0
        assert abs(total - expected) < 0.1

    def test_T_P19_customer_weight_sum_correct(self, db):
        """고객별 총 출고 중량: CATL=12×5001, BYD=10×5001, LGE=8×5001"""
        rows = db.execute(
            "SELECT customer, SUM(weight_kg) as s FROM outbound_log GROUP BY customer"
        ).fetchall()
        expected = {'CATL': 12, 'BYD': 10, 'LG Energy Solution': 8}
        for r in rows:
            exp_w = expected[r['customer']] * LOT_TOTAL_WEIGHT_KG
            assert abs(r['s'] - exp_w) < 0.1

    def test_T_P20_weight_calc_1000_iterations_under_1sec(self, db):
        """중량 계산 1000회 반복 < 1.0초"""
        start = time.perf_counter()
        for _ in range(1000):
            db.execute(
                "SELECT SUM(weight_kg) FROM inventory_tonbag WHERE is_sample=0"
            ).fetchone()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"1000회 중량 계산 {elapsed:.3f}s > 1.0s"
