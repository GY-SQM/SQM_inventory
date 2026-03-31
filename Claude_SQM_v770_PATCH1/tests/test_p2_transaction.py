# -*- coding: utf-8 -*-
"""
P2 테스트: finalize_return_to_available() 트랜잭션 원자성 검증
- 정상 케이스: RETURN → AVAILABLE 전환 + current_weight 복구 + stock_movement 기록
- 실패 케이스: 중간 오류 시 전체 롤백
- P4/P5 통합: lot_no 검증 + 상태 전이 검증 포함
"""
import pytest
import sqlite3
from engine_modules.database import SQMDatabase
from engine_modules.inventory_modular.base import InventoryBaseMixin
from engine_modules.inventory_modular.return_mixin import ReturnMixin


class _TestEngine(ReturnMixin, InventoryBaseMixin):
    """테스트용 최소 엔진 (ReturnMixin + BaseMixin 결합)"""
    def __init__(self, db: SQMDatabase):
        self.db = db


class TestFinalizeReturnToAvailable:
    """finalize_return_to_available 트랜잭션 검증"""

    @pytest.fixture(autouse=True)
    def setup_engine(self, db, seed_lot):
        self.db = db
        self.engine = _TestEngine(db)
        self.seed_lot = seed_lot

    # --- 정상 전환 ---
    def test_return_to_available_success(self):
        """RETURN 톤백이 AVAILABLE로 정상 전환되고 current_weight가 복구"""
        lot = self.seed_lot(status='RETURN', tb_status='RETURN', weight=500.0)
        # current_weight를 0으로 설정 (반품 상태이므로 이미 차감된 상태 가정)
        self.db.execute(
            "UPDATE inventory SET current_weight = 0 WHERE lot_no = ?", (lot,))
        self.db.conn.commit()

        result = self.engine.finalize_return_to_available(lot, 1, location='A-01')

        assert result['success'] is True
        assert 'RETURN→AVAILABLE' in result['message']

        # 톤백 status 확인
        tb = self.db.fetchone(
            "SELECT status, location FROM inventory_tonbag "
            "WHERE lot_no = ? AND sub_lt = ?", (lot, 1))
        assert tb['status'] == 'AVAILABLE'
        assert tb['location'] == 'A-01'

        # current_weight 복구 확인
        inv = self.db.fetchone(
            "SELECT current_weight FROM inventory WHERE lot_no = ?", (lot,))
        assert inv['current_weight'] == 500.0

        # stock_movement 기록 확인
        mv = self.db.fetchone(
            "SELECT * FROM stock_movement WHERE lot_no = ? "
            "AND movement_type = 'RETURN_TO_AVAILABLE'", (lot,))
        assert mv is not None
        assert mv['qty_kg'] == 500.0

    # --- P4: lot_no None 거부 ---
    @pytest.mark.edge
    def test_none_lot_no_rejected(self):
        """lot_no=None은 _require_lot_no에서 차단"""
        result = self.engine.finalize_return_to_available(None, 1)
        assert result['success'] is False
        assert 'None' in result['message'] or '오류' in result['message']

    # --- P5: 잘못된 상태 전이 차단 ---
    @pytest.mark.edge
    def test_non_return_status_blocked(self):
        """AVAILABLE 상태 톤백은 다시 AVAILABLE로 전환 불가 (자기자신→자기자신)"""
        lot = self.seed_lot(status='AVAILABLE', tb_status='AVAILABLE')

        result = self.engine.finalize_return_to_available(lot, 1)
        # AVAILABLE→AVAILABLE은 전이 맵에 없으므로 차단
        assert result['success'] is False
        assert '허용되지 않은 상태 전이' in result['message']

    @pytest.mark.edge
    def test_picked_status_blocked(self):
        """PICKED 톤백은 AVAILABLE로 직접 전환 가능 (맵에 있음)"""
        lot = self.seed_lot(status='AVAILABLE', tb_status='PICKED')
        self.db.execute(
            "UPDATE inventory SET current_weight = 0 WHERE lot_no = ?", (lot,))
        self.db.conn.commit()

        result = self.engine.finalize_return_to_available(lot, 1)
        # PICKED → AVAILABLE은 허용됨
        assert result['success'] is True

    # --- 존재하지 않는 톤백 ---
    @pytest.mark.edge
    def test_nonexistent_tonbag(self):
        """존재하지 않는 lot_no/sub_lt 조합 → 톤백 없음"""
        result = self.engine.finalize_return_to_available('9999999999', 99)
        assert result['success'] is False
        assert '톤백 없음' in result['message']

    # --- 트랜잭션 롤백 검증 ---
    @pytest.mark.rollback
    def test_transaction_rollback_on_error(self):
        """트랜잭션 중 오류 발생 시 모든 변경이 롤백"""
        lot = self.seed_lot(status='RETURN', tb_status='RETURN', weight=500.0)
        self.db.execute(
            "UPDATE inventory SET current_weight = 0 WHERE lot_no = ?", (lot,))
        self.db.conn.commit()

        # stock_movement 테이블에 NOT NULL 제약 추가로 INSERT 실패 유도
        # remarks 컬럼에 기본값이 있으므로 다른 방법 사용:
        # stock_movement 테이블을 임시로 DROP하면 INSERT 실패
        self.db.execute("DROP TABLE IF EXISTS stock_movement")
        self.db.conn.commit()

        result = self.engine.finalize_return_to_available(lot, 1, location='B-02')

        # 오류 발생하므로 실패
        assert result['success'] is False

        # 톤백 상태는 RETURN 유지 (롤백)
        tb = self.db.fetchone(
            "SELECT status FROM inventory_tonbag "
            "WHERE lot_no = ? AND sub_lt = ?", (lot, 1))
        assert tb['status'] == 'RETURN'

        # current_weight는 0 유지 (롤백)
        inv = self.db.fetchone(
            "SELECT current_weight FROM inventory WHERE lot_no = ?", (lot,))
        assert inv['current_weight'] == 0.0
