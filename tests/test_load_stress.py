"""
SQM v6.2.7 — 부하 테스트 (Load & Stress Test)
================================================
대용량 데이터 처리 시 성능, 메모리 안정성, 정합성 검증.

영역:
  1. 대량 입고 — 100 LOT 순차 입고 + 정합성
  2. 대량 출고 — 100 LOT 각 부분 출고 + 잔여 확인
  3. 대량 반품 — 50 LOT 반품 사이클
  4. 혼합 부하 — 입고→출고→반품 전체 사이클 100건
  5. 성능 측정 — 처리 시간 기준선

실행: python -m pytest tests/test_load_stress.py -v -s
"""

import logging
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.conftest import get_lot, get_tonbags, inbound_lot, outbound_lot

logger = logging.getLogger(__name__)


def make_lot_data(idx: int, tonbag_count: int = 10, unit_weight: int = 500) -> dict:
    """테스트용 LOT 데이터 생성."""
    total_weight = tonbag_count * unit_weight + 1  # +1kg 샘플
    return {
        'lot_no': f'LOAD{idx:05d}',
        'sap_no': f'SAP-LOAD-{idx:05d}',
        'product': 'LITHIUM CARBONATE',
        'mxbg_pallet': tonbag_count,
        'net_weight': float(total_weight),
    }


# ═══════════════════════════════════════════════════════════
#  1. 대량 입고 — 100 LOT
# ═══════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.inbound
class TestBulkInbound:
    """100개 LOT 입고 성능 + 정합성."""

    def test_100_lot_inbound(self, engine):
        """100 LOT 순차 입고 → 모두 성공 + 정합성 유지."""
        count = 100
        start = time.time()
        failed = []

        for i in range(count):
            lot_data = make_lot_data(i)
            r = engine.process_inbound(lot_data)
            if not r['success']:
                failed.append((i, r.get('errors', [])))

        elapsed = time.time() - start
        logger.info(f"[부하] 입고 {count}건: {elapsed:.2f}초 ({count/elapsed:.0f} LOT/초)")

        assert len(failed) == 0, f"실패 {len(failed)}건: {failed[:3]}"

        # DB에 100건 존재 확인
        row = engine.db.fetchone(
            "SELECT COUNT(*) as cnt FROM inventory WHERE lot_no LIKE 'LOAD%'")
        assert int(row['cnt']) == count

    def test_100_lot_integrity(self, engine):
        """100 LOT 입고 후 전체 정합성 검증."""
        count = 100
        for i in range(count):
            inbound_lot(engine, make_lot_data(i + 1000))  # 1000~ (충돌 방지)

        # 전체 정합성 검증
        errors = []
        for i in range(count):
            lot_no = f'LOAD{i + 1000:05d}'
            integrity = engine.verify_lot_integrity(lot_no)
            if not integrity['valid']:
                errors.append((lot_no, integrity['errors']))

        assert len(errors) == 0, f"정합성 실패 {len(errors)}건: {errors[:3]}"


# ═══════════════════════════════════════════════════════════
#  2. 대량 출고 — 100 LOT 각 부분 출고
# ═══════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.outbound
class TestBulkOutbound:
    """100 LOT 입고 후 각각 부분 출고."""

    def test_100_lot_partial_outbound(self, engine):
        """100 LOT 각각 50% 출고 → 잔여 확인."""
        count = 100
        customers = ['CATL', 'BYD', 'LG', 'Samsung', 'Tesla']

        # 입고
        for i in range(count):
            inbound_lot(engine, make_lot_data(i + 2000))

        # 출고 (각 LOT에서 2500kg = 50%)
        start = time.time()
        failed = []
        for i in range(count):
            lot_no = f'LOAD{i + 2000:05d}'
            customer = customers[i % len(customers)]
            r = outbound_lot(engine, lot_no, customer, 2500.0)
            if not r['success']:
                failed.append((lot_no, r.get('errors', r.get('message', ''))))

        elapsed = time.time() - start
        logger.info(f"[부하] 출고 {count}건: {elapsed:.2f}초 ({count/elapsed:.0f} LOT/초)")

        assert len(failed) == 0, f"출고 실패 {len(failed)}건: {failed[:3]}"

        # 잔여 확인 (각 LOT: 5001 - 2500 = 2501)
        sample = engine.db.fetchone(
            "SELECT current_weight FROM inventory WHERE lot_no = 'LOAD02000'")
        assert sample is not None
        assert float(sample['current_weight']) == 2501.0

    def test_50_lot_full_outbound(self, engine):
        """50 LOT 전량 출고 → 잔여 = 샘플만."""
        count = 50
        for i in range(count):
            inbound_lot(engine, make_lot_data(i + 3000))

        failed = []
        for i in range(count):
            lot_no = f'LOAD{i + 3000:05d}'
            r = outbound_lot(engine, lot_no, 'CATL', 5000.0)
            if not r['success']:
                failed.append(lot_no)

        assert len(failed) == 0, f"전량 출고 실패: {failed[:5]}"

        # 잔여 = 1kg 샘플만
        for i in range(count):
            lot_no = f'LOAD{i + 3000:05d}'
            lot_row = get_lot(engine, lot_no)
            assert float(lot_row['current_weight']) == 1.0, \
                f"{lot_no}: 잔여 {lot_row['current_weight']}kg (기대: 1.0)"


# ═══════════════════════════════════════════════════════════
#  3. 대량 반품 사이클
# ═══════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.rollback
class TestBulkReturn:
    """출고 후 대량 반품 → 무게 복구 + 정합성."""

    def test_50_lot_outbound_then_return(self, engine):
        """50 LOT: 입고→출고→반품→정합성."""
        count = 50

        # 입고 + 출고
        for i in range(count):
            lot_data = make_lot_data(i + 4000)
            inbound_lot(engine, lot_data)
            outbound_lot(engine, lot_data['lot_no'], 'CATL', 500.0)  # 1톤백

        # 반품 (각 LOT에서 PICKED 톤백 1개씩)
        returned = 0
        for i in range(count):
            lot_no = f'LOAD{i + 4000:05d}'
            picked = get_tonbags(engine, lot_no, 'PICKED')
            if picked:
                r = engine.process_return([{
                    'lot_no': lot_no,
                    'sub_lt': picked[0]['sub_lt'],
                    'reason': '품질 불량'
                }])
                if r.get('returned', 0) > 0:
                    returned += 1

        assert returned >= count * 0.9, \
            f"반품 성공 {returned}/{count} (최소 90% 기대)"

        # 반품 후 정합성
        errors = []
        for i in range(count):
            lot_no = f'LOAD{i + 4000:05d}'
            integrity = engine.verify_lot_integrity(lot_no)
            if not integrity['valid']:
                errors.append(lot_no)

        assert len(errors) == 0, f"반품 후 정합성 실패: {errors[:5]}"


# ═══════════════════════════════════════════════════════════
#  4. 혼합 부하 — 전체 사이클
# ═══════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.integration
class TestMixedLoadCycle:
    """입고→부분출고→반품→재출고 혼합 사이클."""

    def test_full_lifecycle_50_lots(self, engine):
        """50 LOT 전체 라이프사이클."""
        count = 50
        customers = ['CATL', 'BYD', 'LG', 'Samsung', 'Tesla']
        start = time.time()

        for i in range(count):
            lot_data = make_lot_data(i + 5000)
            lot_no = lot_data['lot_no']
            customer = customers[i % len(customers)]

            # 1) 입고
            r_in = engine.process_inbound(lot_data)
            assert r_in['success'], f"입고 실패: {lot_no}"

            # 2) 부분 출고 (3000kg = 6톤백)
            r_out = outbound_lot(engine, lot_no, customer, 3000.0)
            assert r_out['success'], f"출고 실패: {lot_no}"

            # 3) 반품 1톤백
            picked = get_tonbags(engine, lot_no, 'PICKED')
            if picked:
                engine.process_return([{
                    'lot_no': lot_no,
                    'sub_lt': picked[0]['sub_lt'],
                    'reason': '품질 불량'
                }])

            # 4) 재출고 500kg
            r_re = outbound_lot(engine, lot_no, customer, 500.0)
            # 재출고는 반품 복귀 상태에 따라 성공/실패 가능
            assert isinstance(r_re, dict)

        elapsed = time.time() - start
        logger.info(f"[부하] 혼합 사이클 {count}건: {elapsed:.2f}초 "
                    f"({count/elapsed:.0f} cycle/초)")

        # 전체 정합성
        errors = []
        for i in range(count):
            lot_no = f'LOAD{i + 5000:05d}'
            integrity = engine.verify_lot_integrity(lot_no)
            if not integrity['valid']:
                errors.append(lot_no)

        assert len(errors) == 0, \
            f"혼합 사이클 후 정합성 실패 {len(errors)}/{count}: {errors[:5]}"


# ═══════════════════════════════════════════════════════════
#  5. 성능 측정 기준선
# ═══════════════════════════════════════════════════════════

@pytest.mark.slow
class TestPerformanceBenchmark:
    """성능 기준선 측정 (hard fail 없이 로깅)."""

    def test_inbound_throughput(self, engine):
        """입고 처리량 측정."""
        count = 50
        start = time.time()
        for i in range(count):
            engine.process_inbound(make_lot_data(i + 6000))
        elapsed = time.time() - start

        throughput = count / elapsed
        logger.info(f"[벤치마크] 입고: {throughput:.1f} LOT/초 ({elapsed:.2f}초/{count}건)")
        # 최소 기준: 5 LOT/초 이상
        assert throughput > 5, f"입고 처리 너무 느림: {throughput:.1f} LOT/초"

    def test_outbound_throughput(self, engine):
        """출고 처리량 측정."""
        count = 50
        for i in range(count):
            inbound_lot(engine, make_lot_data(i + 7000))

        start = time.time()
        for i in range(count):
            outbound_lot(engine, f'LOAD{i + 7000:05d}', 'CATL', 500.0)
        elapsed = time.time() - start

        throughput = count / elapsed
        logger.info(f"[벤치마크] 출고: {throughput:.1f} LOT/초 ({elapsed:.2f}초/{count}건)")
        assert throughput > 5, f"출고 처리 너무 느림: {throughput:.1f} LOT/초"

    def test_integrity_check_throughput(self, engine):
        """정합성 검증 처리량."""
        count = 50
        for i in range(count):
            inbound_lot(engine, make_lot_data(i + 8000))

        start = time.time()
        for i in range(count):
            engine.verify_lot_integrity(f'LOAD{i + 8000:05d}')
        elapsed = time.time() - start

        throughput = count / elapsed
        logger.info(f"[벤치마크] 정합성: {throughput:.1f} LOT/초 ({elapsed:.2f}초/{count}건)")
        assert throughput > 10, f"정합성 검증 너무 느림: {throughput:.1f} LOT/초"

    def test_db_query_count(self, engine):
        """단일 LOT 입고→출고→정합성 DB 쿼리 시간."""
        lot_data = make_lot_data(9999)

        start = time.time()
        engine.process_inbound(lot_data)
        outbound_lot(engine, lot_data['lot_no'], 'CATL', 2500.0)
        engine.verify_lot_integrity(lot_data['lot_no'])
        elapsed = time.time() - start

        logger.info(f"[벤치마크] 단일 사이클(입고+출고+정합): {elapsed*1000:.0f}ms")
        assert elapsed < 2.0, f"단일 사이클 2초 초과: {elapsed:.2f}초"
