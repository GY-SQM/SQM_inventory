# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 처리 Mixin
======================================

v3.6.6: SQLAlchemy → SQMDatabase API 전환 (self.db 기반)

작성자: Ruby (남기동)
버전: v3.6.6
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional

from .base import InventoryBaseMixin

logger = logging.getLogger(__name__)


class OutboundMixin(InventoryBaseMixin):
    def _assert_sample_policy(self, lot_no: str) -> None:
        """v5.3.7: Hard-stop if sample policy is violated (must be exactly 1 sample row per LOT)."""
        row = self.db.fetchone(
            "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? AND COALESCE(is_sample,0)=1",
            (lot_no,)
        )
        cnt = (row['cnt'] if isinstance(row, dict) else row[0]) if row else 0
        if cnt != 1:
            raise ValueError(f"샘플 정책 위반: LOT {lot_no}에 샘플 {cnt}개 (필수 정확히 1개)")

    """출고 처리 Mixin (v3.6.6: SQMDatabase API 기반)"""
    
    def process_outbound(self, allocation_data) -> Dict:
        """
        출고 처리 (v3.8.4: All-or-Nothing + 톤백 동기화)
        
        1건이라도 실패하면 전체 롤백. inventory + tonbag 모두 업데이트.
        """
        result = {
            'success': False,
            'message': '',
            'processed': 0,
            'lots_processed': 0,
            'total_weight_kg': 0,
            'total_picked': 0,
            'errors': [],
            'warnings': [],
        }
        
        try:
            if isinstance(allocation_data, dict):
                allocations = [allocation_data]
            else:
                allocations = list(allocation_data)
            
            if not allocations:
                result['message'] = "처리할 데이터 없음"
                return result
            
            # ★ All-or-Nothing: 전체를 하나의 트랜잭션으로
            with self.db.transaction("IMMEDIATE"):
                processed_lots = []
                for alloc in allocations:
                    # 건별 try/except 제거 → 하나라도 실패하면 전체 롤백
                    processed = self._process_single_outbound(alloc)
                    if processed:
                        result['processed'] += 1
                        result['total_weight_kg'] += processed.get('weight_kg', 0)
                        result['total_picked'] += processed.get('weight_kg', 0) / 1000.0
                        processed_lots.append(processed.get('lot_no'))
                
                # v5.1.4: 트랜잭션 안에서 정합성 검증
                if hasattr(self, 'verify_lot_integrity') and processed_lots:
                    for lot_no in set(processed_lots):
                        integrity = self.verify_lot_integrity(lot_no)
                        if not integrity.get('valid', True):
                            raise ValueError(
                                f"출고 후 정합성 실패 ({lot_no}): {integrity.get('errors', [])}"
                            )
            
            result['lots_processed'] = result['processed']
            
            if result['processed'] > 0:
                result['success'] = True
                result['message'] = f"출고 완료: {result['processed']}건"
            else:
                result['message'] = "처리된 출고 없음"
            
            self._log_operation("출고", {
                'processed': result['processed'],
                'weight_kg': result['total_weight_kg']
            })
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"출고 처리 오류 (전체 롤백): {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    def _process_single_outbound(self, alloc: Dict) -> Optional[Dict]:
        """
        단일 출고 처리 (v3.8.4: inventory + tonbag 동시 업데이트)
        
        호출자의 트랜잭션 안에서 실행됨.
        실패 시 예외 발생 → 호출자 트랜잭션 롤백.
        """
        lot_no = str(alloc.get('lot_no') or '').strip()
        weight_kg = self._safe_parse_float(alloc.get('weight_kg'))
        if weight_kg <= 0:
            qty_mt = self._safe_parse_float(alloc.get('qty_mt'))
            weight_kg = qty_mt * 1000.0
        
        customer = alloc.get('customer') or alloc.get('sold_to', '')
        sale_ref = alloc.get('sale_ref', '')
        
        if not lot_no or weight_kg <= 0:
            return None
        
        # LOT 정보 조회
        lot = self.db.fetchone(
            "SELECT current_weight, picked_weight FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        
        if not lot:
            raise ValueError(f"LOT 없음: {lot_no}")
        
        available = lot['current_weight'] or 0
        
        if available < weight_kg - 0.01:  # 소수점 오차 허용
            raise ValueError(
                f"가용 재고 부족: {lot_no} (가용: {available:.0f}kg, 요청: {weight_kg:.0f}kg)"
            )
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # ★ 1단계: 톤백 PICKED 처리 (가용 톤백에서 필요 수량만큼, 샘플 제외)
        remaining_kg = weight_kg
        tonbags = self.db.fetchall(
            """SELECT id, sub_lt, weight FROM inventory_tonbag 
               WHERE lot_no = ? AND status = 'AVAILABLE'
                 AND COALESCE(is_sample, 0) = 0
               ORDER BY sub_lt""",
            (lot_no,)
        )
        
        picked_count = 0
        if tonbags:
            for tb in tonbags:
                if remaining_kg <= 0.01:
                    break
                tb_weight = tb['weight'] or 0
                if tb_weight <= 0:
                    continue
                
                self.db.execute(
                    """UPDATE inventory_tonbag SET
                        status = 'PICKED',
                        picked_to = ?,
                        picked_date = ?,
                        sale_ref = ?,
                        outbound_date = ?,
                        updated_at = ?
                    WHERE id = ?""",
                    (customer, now, sale_ref, now, now, tb['id'])
                )
                remaining_kg -= tb_weight
                picked_count += 1
        
        # ★ 2단계: inventory 업데이트
        new_weight = available - weight_kg
        if new_weight < 0:
            new_weight = 0
        new_status = 'DEPLETED' if new_weight <= 0 else 'AVAILABLE'
        
        self.db.execute(
            """UPDATE inventory SET
                current_weight = ?,
                picked_weight = picked_weight + ?,
                status = ?,
                sold_to = CASE WHEN ? != '' THEN ? ELSE sold_to END,
                updated_at = ?
            WHERE lot_no = ?""",
            (new_weight, weight_kg, new_status, customer, customer, now, lot_no)
        )
        
        # ★ 3단계: stock_movement 이력 (B1 FIX: 필수 — 실패 시 전체 롤백)
        self.db.execute(
            """INSERT INTO stock_movement 
            (lot_no, movement_type, qty_kg, remarks, created_at)
            VALUES (?, 'OUTBOUND', ?, ?, ?)""",
            (lot_no, weight_kg, f"customer={customer}" if customer else '', now)
        )
        
        # ★ 4단계: outbound 테이블 기록 (B2 FIX: 필수 — 실패 시 전체 롤백)
        self.db.execute(
            """INSERT INTO outbound 
            (customer, total_qty_mt, outbound_date, created_at)
            VALUES (?, ?, ?, ?)""",
            (customer, weight_kg, now, now)
        )
        
        return {'lot_no': lot_no, 'weight_kg': weight_kg, 'tonbags_picked': picked_count}
    
    def _update_lot_after_pick(self, lot_no: str, weight_kg: float) -> None:
        """피킹 후 LOT 업데이트"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.db.execute(
            """UPDATE inventory SET
                current_weight = MAX(0, current_weight - ?),
                picked_weight = picked_weight + ?,
                status = CASE 
                    WHEN current_weight - ? <= 0 THEN 'DEPLETED'
                    ELSE status
                END,
                updated_at = ?
            WHERE lot_no = ?""",
            (weight_kg, weight_kg, weight_kg, now, lot_no)
        )
    

    # NOTE: process_outbound_safe, preflight_check_outbound
    #   → PreflightMixin으로 이관 완료 (v3.8.4 데드코드 정리)

    def cancel_outbound_tonbag(self, lot_no: str, sub_lt: int) -> Dict:
        """
        출고 취소: 톤백 PICKED → AVAILABLE + inventory.current_weight 복구
        
        All-or-Nothing: 톤백 + inventory 모두 성공해야 commit
        """
        from datetime import datetime
        result = {'success': False, 'message': '', 'errors': []}
        
        try:
            with self.db.transaction("IMMEDIATE"):
                # 톤백 정보 조회
                tonbag = self.db.fetchone("""
                    SELECT id, weight, status, picked_to 
                    FROM inventory_tonbag 
                    WHERE lot_no = ? AND sub_lt = ?
                """, (lot_no, sub_lt))
                
                if not tonbag:
                    result['errors'].append(f"톤백 없음: {lot_no}-{sub_lt}")
                    return result
                
                if tonbag['status'] != 'PICKED':
                    result['errors'].append(f"PICKED 상태가 아님: {lot_no}-{sub_lt} ({tonbag['status']})")
                    return result
                
                weight = tonbag['weight'] or 0
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 1. 톤백: PICKED → AVAILABLE
                self.db.execute("""
                    UPDATE inventory_tonbag SET
                        status = 'AVAILABLE',
                        picked_to = NULL,
                        picked_date = NULL,
                        pick_ref = NULL,
                        outbound_date = NULL,
                        updated_at = ?
                    WHERE lot_no = ? AND sub_lt = ?
                """, (now, lot_no, sub_lt))
                
                # 2. inventory: current_weight 복구
                self.db.execute("""
                    UPDATE inventory SET
                        current_weight = current_weight + ?,
                        picked_weight = MAX(0, picked_weight - ?),
                        updated_at = ?
                    WHERE lot_no = ?
                """, (weight, weight, now, lot_no))
                
                # 3. inventory status 재계산
                self._recalc_lot_status(lot_no)
                
                # 4. stock_movement 이력 (B3 FIX: 필수 기록)
                self.db.execute("""
                    INSERT INTO stock_movement 
                    (lot_no, movement_type, qty_kg, remarks, created_at)
                    VALUES (?, 'CANCEL_OUTBOUND', ?, ?, ?)
                """, (lot_no, weight, f"customer={tonbag['picked_to'] or ''}", now))
                
                result['success'] = True
                result['message'] = f"출고 취소 완료: {lot_no}-{sub_lt} ({weight:.0f}kg)"
                logger.info(result['message'])
            
            # v3.8.5: 취소 후 자동 정합성 검증
            if result['success'] and hasattr(self, '_assert_lot_integrity'):
                self._assert_lot_integrity(lot_no)
                
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['errors'].append(str(e))
            logger.error(f"출고 취소 오류: {e}")
        
        return result

    def cancel_outbound_bulk(self, items: list) -> Dict:
        """
        일괄 출고 취소 (All-or-Nothing)
        items: [{'lot_no': '...', 'sub_lt': 1}, ...]
        """
        from datetime import datetime
        result = {'success': False, 'cancelled': 0, 'errors': []}
        
        try:
            with self.db.transaction("IMMEDIATE"):
                for item in items:
                    lot_no = str(item.get('lot_no') or '').strip()
                    sub_lt = item.get('sub_lt')
                    
                    tonbag = self.db.fetchone("""
                        SELECT weight, status, picked_to 
                        FROM inventory_tonbag 
                        WHERE lot_no = ? AND sub_lt = ? AND status = 'PICKED'
                    """, (lot_no, sub_lt))
                    
                    if not tonbag:
                        raise ValueError(f"취소 불가: {lot_no}-{sub_lt}")
                    
                    weight = tonbag['weight'] or 0
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    self.db.execute("""
                        UPDATE inventory_tonbag SET
                            status = 'AVAILABLE', picked_to = NULL, picked_date = NULL,
                            pick_ref = NULL, outbound_date = NULL, updated_at = ?
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (now, lot_no, sub_lt))
                    
                    self.db.execute("""
                        UPDATE inventory SET
                            current_weight = current_weight + ?,
                            picked_weight = MAX(0, picked_weight - ?),
                            updated_at = ?
                        WHERE lot_no = ?
                    """, (weight, weight, now, lot_no))
                    
                    # stock_movement 이력 기록 (v3.8.4 bugfix)
                    self.db.execute("""
                        INSERT INTO stock_movement 
                        (lot_no, movement_type, qty_kg, remarks, created_at)
                        VALUES (?, 'CANCEL_OUTBOUND', ?, ?, ?)
                    """, (lot_no, weight, f"bulk_cancel customer={tonbag['picked_to'] or ''}", now))
                    
                    result['cancelled'] += 1
                
                # 모든 관련 LOT status 재계산
                lot_nos = set(item['lot_no'] for item in items)
                for lot_no in lot_nos:
                    self._recalc_lot_status(lot_no)
                
                result['success'] = True
                result['message'] = f"일괄 취소 완료: {result['cancelled']}건"
                
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['errors'].append(str(e))
            logger.error(f"일괄 출고 취소 오류: {e}")
        
        return result

    def _recalc_lot_status(self, lot_no: str) -> None:
        """LOT status 재계산 (current_weight 기반)"""
        lot = self.db.fetchone(
            "SELECT current_weight, initial_weight FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        if not lot:
            return
        
        cw = lot['current_weight'] or 0
        iw = lot['initial_weight'] or 0
        
        if cw <= 0:
            new_status = 'DEPLETED'
        elif cw >= iw:
            new_status = 'AVAILABLE'
        else:
            new_status = 'AVAILABLE'  # 부분 출고도 AVAILABLE (잔량 있음)
        
        self.db.execute(
            "UPDATE inventory SET status = ? WHERE lot_no = ?",
            (new_status, lot_no)
        )
