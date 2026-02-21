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

from core.constants import (
    STATUS_AVAILABLE,
    STATUS_RESERVED,
    STATUS_DEPLETED,
    STATUS_PICKED,
    STATUS_SOLD,
)

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
    
    def process_outbound(self, allocation_data, source: str = 'AUTO', stop_at_picked: bool = False) -> Dict:
        """
        출고 처리 (v3.8.4: All-or-Nothing + 톤백 동기화, v5.9.92: source/stop_at_picked)
        
        source: 출고 경로 구분 (AUTO/QUICK/EXCEL 등). allocation_plan에 기록.
        stop_at_picked: True면 톤백 PICKED까지만 하고 재고·outbound 미반영(빠른 출고용).
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
                    processed = self._process_single_outbound(alloc, source=source, stop_at_picked=stop_at_picked)
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
    
    def _process_single_outbound(
        self, alloc: Dict, source: str = 'AUTO', stop_at_picked: bool = False
    ) -> Optional[Dict]:
        """
        단일 출고 처리 (v3.8.4: inventory + tonbag 동기화, v5.9.92: source, stop_at_picked)
        
        stop_at_picked=True면 톤백 PICKED + allocation_plan 기록만 하고 재고/outbound 미반영.
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
        
        lot = self.db.fetchone(
            "SELECT current_weight, picked_weight FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        if not lot:
            raise ValueError(f"LOT 없음: {lot_no}")
        
        available = lot['current_weight'] or 0
        if available < weight_kg - 0.01:
            raise ValueError(
                f"가용 재고 부족: {lot_no} (가용: {available:.0f}kg, 요청: {weight_kg:.0f}kg)"
            )
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        qty_mt_val = weight_kg / 1000.0
        
        # ★ 1단계: 톤백 PICKED 처리 (가용 톤백에서 필요 수량만큼, 샘플 제외)
        remaining_kg = weight_kg
        tonbags = self.db.fetchall(
            """SELECT id, sub_lt, weight FROM inventory_tonbag 
               WHERE lot_no = ? AND status = ?
                 AND COALESCE(is_sample, 0) = 0
               ORDER BY sub_lt DESC""",
            (lot_no, STATUS_AVAILABLE)
        )
        picked_count = 0
        first_tonbag_id = None
        if tonbags:
            for tb in tonbags:
                if remaining_kg <= 0.01:
                    break
                tb_weight = tb['weight'] or 0
                if tb_weight <= 0:
                    continue
                if first_tonbag_id is None:
                    first_tonbag_id = tb['id']
                self.db.execute(
                    """UPDATE inventory_tonbag SET
                        status = ?,
                        picked_to = ?,
                        picked_date = ?,
                        sale_ref = ?,
                        outbound_date = ?,
                        updated_at = ?
                    WHERE id = ?""",
                    (STATUS_PICKED, customer, now, sale_ref, now, now, tb['id'])
                )
                remaining_kg -= tb_weight
                picked_count += 1
        
        # v5.9.92: allocation_plan에 출고 기록 (source 저장)
        try:
            self.db.execute(
                """INSERT INTO allocation_plan 
                (lot_no, tonbag_id, customer, sale_ref, qty_mt, outbound_date, status, source, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PICKED', ?, ?)""",
                (lot_no, first_tonbag_id, customer, sale_ref, qty_mt_val, now, source, now)
            )
        except (sqlite3.OperationalError, OSError) as e:
            if "allocation_plan" in str(e) and "source" in str(e).lower():
                logger.debug("allocation_plan.source 미존재 시 무시: %s", e)
            else:
                raise
        
        if stop_at_picked:
            return {'lot_no': lot_no, 'weight_kg': weight_kg, 'tonbags_picked': picked_count}
        
        # ★ 2단계: inventory 업데이트
        new_weight = available - weight_kg
        if new_weight < 0:
            new_weight = 0
        new_status = STATUS_DEPLETED if new_weight <= 0 else STATUS_AVAILABLE
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
        
        # ★ 3단계: stock_movement 이력
        self.db.execute(
            """INSERT INTO stock_movement 
            (lot_no, movement_type, qty_kg, remarks, created_at)
            VALUES (?, 'OUTBOUND', ?, ?, ?)""",
            (lot_no, weight_kg, f"customer={customer}" if customer else '', now)
        )
        
        # ★ 4단계: outbound 테이블 기록
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
                    WHEN current_weight - ? <= 0 THEN ?
                    ELSE status
                END,
                updated_at = ?
            WHERE lot_no = ?""",
            (weight_kg, weight_kg, weight_kg, STATUS_DEPLETED, now, lot_no)
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
                
                if tonbag['status'] != STATUS_PICKED:
                    result['errors'].append(f"PICKED 상태가 아님: {lot_no}-{sub_lt} ({tonbag['status']})")
                    return result
                
                weight = tonbag['weight'] or 0
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 1. 톤백: PICKED → AVAILABLE
                self.db.execute("""
                    UPDATE inventory_tonbag SET
                        status = ?,
                        picked_to = NULL,
                        picked_date = NULL,
                        pick_ref = NULL,
                        outbound_date = NULL,
                        updated_at = ?
                    WHERE lot_no = ? AND sub_lt = ?
                """, (STATUS_AVAILABLE, now, lot_no, sub_lt))
                
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
                        WHERE lot_no = ? AND sub_lt = ? AND status = ?
                    """, (lot_no, sub_lt, STATUS_PICKED))
                    
                    if not tonbag:
                        raise ValueError(f"취소 불가: {lot_no}-{sub_lt}")
                    
                    weight = tonbag['weight'] or 0
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    self.db.execute("""
                        UPDATE inventory_tonbag SET
                            status = ?, picked_to = NULL, picked_date = NULL,
                            pick_ref = NULL, outbound_date = NULL, updated_at = ?
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (STATUS_AVAILABLE, now, lot_no, sub_lt))
                    
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
            new_status = STATUS_DEPLETED
        elif cw >= iw:
            new_status = STATUS_AVAILABLE
        else:
            new_status = STATUS_AVAILABLE
        
        self.db.execute(
            "UPDATE inventory SET status = ? WHERE lot_no = ?",
            (new_status, lot_no)
        )

    # ═══════════════════════════════════════════════════════
    # v5.9.3: Allocation 기반 예약/실행/확정
    # ═══════════════════════════════════════════════════════

    def reserve_from_allocation(self, allocation_rows: list, source_file: str = '') -> Dict:
        """
        Allocation 엑셀에서 파싱된 데이터로 톤백 예약 (AVAILABLE → RESERVED).
        allocation_plan 테이블에 계획 기록 + 톤백 상태 변경.

        Args:
            allocation_rows: AllocationRow 또는 dict 리스트
            source_file: 원본 파일명

        Returns:
            {'success': bool, 'reserved': int, 'errors': [], 'plan_ids': []}
        """
        result = {'success': False, 'reserved': 0, 'errors': [], 'plan_ids': []}

        def _alloc_val(alloc, key, default=None):
            """AllocationRow(dataclass) 또는 dict 모두 지원"""
            if isinstance(alloc, dict):
                return alloc.get(key, default)
            return getattr(alloc, key, default)

        try:
            with self.db.transaction("IMMEDIATE"):
                for alloc in allocation_rows:
                    lot_no = str(_alloc_val(alloc, 'lot_no') or '').strip()
                    customer = str(_alloc_val(alloc, 'sold_to') or _alloc_val(alloc, 'customer') or '').strip()
                    sale_ref = str(_alloc_val(alloc, 'sale_ref') or '').strip()
                    qty_mt = float(_alloc_val(alloc, 'qty_mt') or 0)
                    outbound_date = _alloc_val(alloc, 'outbound_date')
                    sublot_count = int(_alloc_val(alloc, 'sublot_count') or _alloc_val(alloc, 'tonbag_count') or 0)

                    if not lot_no:
                        result['errors'].append("LOT 번호 누락")
                        continue

                    weight_kg = qty_mt * 1000 if qty_mt > 0 else sublot_count * 500

                    tonbags = self.db.fetchall(
                        """SELECT id, sub_lt, weight FROM inventory_tonbag
                           WHERE lot_no = ? AND status = ?
                             AND COALESCE(is_sample, 0) = 0
                           ORDER BY sub_lt DESC""",
                        (lot_no, STATUS_AVAILABLE)
                    )

                    if not tonbags:
                        result['errors'].append(f"가용 톤백 없음: {lot_no}")
                        continue

                    pick_count = sublot_count if sublot_count > 0 else max(1, int(weight_kg / 500))
                    reserved_in_lot = 0
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ob_date_str = str(outbound_date) if outbound_date else None

                    for tb in tonbags[:pick_count]:
                        self.db.execute(
                            """UPDATE inventory_tonbag SET
                                status = ?, picked_to = ?, sale_ref = ?, updated_at = ?
                            WHERE id = ?""",
                            (STATUS_RESERVED, customer, sale_ref, now, tb['id'])
                        )

                        self.db.execute(
                            """INSERT INTO allocation_plan
                            (lot_no, tonbag_id, sub_lt, customer, sale_ref,
                             qty_mt, outbound_date, status, source_file, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'RESERVED', ?, ?)""",
                            (lot_no, tb['id'], tb['sub_lt'], customer, sale_ref,
                             qty_mt, ob_date_str, source_file, now)
                        )
                        reserved_in_lot += 1

                    result['reserved'] += reserved_in_lot
                    logger.info(f"[reserve] {lot_no}: {reserved_in_lot}개 톤백 RESERVED → {customer}")

            result['success'] = result['reserved'] > 0
            if result['success']:
                result['message'] = f"예약 완료: {result['reserved']}개 톤백"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"Allocation 예약 오류 (전체 롤백): {e}", exc_info=True)
            result['errors'].append(str(e))

        return result

    def execute_reserved(self, lot_no: str = None, target_date: str = None) -> Dict:
        """
        RESERVED 톤백을 PICKED로 전환 (출고 실행).
        lot_no 지정 시 해당 LOT만, target_date 지정 시 해당 날짜 이하만 실행.

        Returns:
            {'success': bool, 'executed': int, 'errors': []}
        """
        result = {'success': False, 'executed': 0, 'errors': []}

        query = """SELECT ap.id, ap.lot_no, ap.tonbag_id, ap.sub_lt,
                          ap.customer, ap.sale_ref, ap.outbound_date
                   FROM allocation_plan ap
                   WHERE ap.status = 'RESERVED'"""
        params = []

        if lot_no:
            query += " AND ap.lot_no = ?"
            params.append(lot_no)
        if target_date:
            query += " AND ap.outbound_date <= ?"
            params.append(target_date)

        try:
            plans = self.db.fetchall(query, tuple(params))
            if not plans:
                result['message'] = "실행할 예약 건 없음"
                return result

            with self.db.transaction("IMMEDIATE"):
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                processed_lots = set()

                for plan in plans:
                    p_lot = plan['lot_no']
                    tb_id = plan['tonbag_id']

                    tb = self.db.fetchone(
                        "SELECT weight, status, tonbag_uid FROM inventory_tonbag WHERE id = ?",
                        (tb_id,)
                    )
                    if not tb or tb['status'] != STATUS_RESERVED:
                        result['errors'].append(f"톤백 {tb_id} 상태 불일치")
                        continue

                    tb_weight = tb['weight'] or 0
                    tonbag_uid = (tb.get('tonbag_uid') or '').strip() or None

                    self.db.execute(
                        """UPDATE inventory_tonbag SET
                            status = ?, picked_date = ?, outbound_date = ?, updated_at = ?
                        WHERE id = ?""",
                        (STATUS_PICKED, now, plan['outbound_date'] or now, now, tb_id)
                    )

                    self.db.execute(
                        """UPDATE inventory SET
                            current_weight = MAX(0, current_weight - ?),
                            picked_weight = picked_weight + ?,
                            updated_at = ?
                        WHERE lot_no = ?""",
                        (tb_weight, tb_weight, now, p_lot)
                    )

                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'EXECUTED', executed_at = ?
                        WHERE id = ?""",
                        (now, plan['id'])
                    )

                    self.db.execute(
                        """INSERT INTO stock_movement
                        (lot_no, movement_type, qty_kg, remarks, created_at)
                        VALUES (?, 'OUTBOUND', ?, ?, ?)""",
                        (p_lot, tb_weight,
                         f"customer={plan['customer']}, sale_ref={plan['sale_ref']}", now)
                    )

                    # v6.0: PICKED 이력 기록 (picking_table) — sale_ref 컬럼 없음, remark에 저장 가능
                    try:
                        self.db.execute(
                            """INSERT INTO picking_table
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, reservation_id, customer,
                             picked_qty_kg, status, picking_date, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 'system')""",
                            (p_lot, tb_id, plan['sub_lt'], tonbag_uid, plan['id'],
                             plan.get('customer') or '', tb_weight, now)
                        )
                    except sqlite3.OperationalError as e:
                        if "no such table" not in str(e).lower():
                            logger.debug(f"[picking_table] 기록 스킵: {e}")

                    processed_lots.add(p_lot)
                    result['executed'] += 1

                for pl in processed_lots:
                    self._recalc_lot_status(pl)

            result['success'] = result['executed'] > 0
            result['message'] = f"출고 실행 완료: {result['executed']}건"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"출고 실행 오류 (전체 롤백): {e}", exc_info=True)
            result['errors'].append(str(e))

        return result

    def confirm_outbound(self, lot_no: str = None) -> Dict:
        """
        PICKED → SOLD 확정.

        Returns:
            {'success': bool, 'confirmed': int}
        """
        result = {'success': False, 'confirmed': 0, 'errors': []}

        query = """SELECT id, lot_no, sub_lt, weight, tonbag_uid FROM inventory_tonbag
                   WHERE status = ?"""
        params = [STATUS_PICKED]
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)

        try:
            tonbags = self.db.fetchall(query, tuple(params))
            if not tonbags:
                result['message'] = "확정할 톤백 없음"
                return result

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                for tb in tonbags:
                    tb_id = tb['id']
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status = ?, outbound_date = ?, updated_at = ? WHERE id = ?",
                        (STATUS_SOLD, now, now, tb_id)
                    )
                    # v6.0: SOLD 이력 기록 (sold_table)
                    uid_val = (tb.get('tonbag_uid') or '').strip() or ''
                    if not uid_val:
                        uid_val = str(tb.get('sub_lt') or tb_id)
                    try:
                        pick_row = self.db.fetchone(
                            "SELECT id FROM picking_table WHERE tonbag_id = ? ORDER BY id DESC LIMIT 1",
                            (tb_id,)
                        )
                        picking_id = pick_row['id'] if pick_row else None
                    except sqlite3.OperationalError:
                        picking_id = None
                    try:
                        self.db.execute(
                            """INSERT INTO sold_table
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id, sold_qty_kg, sold_date, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'system')""",
                            (tb['lot_no'], tb_id, tb.get('sub_lt', 0), uid_val, picking_id,
                             tb.get('weight') or 0, now)
                        )
                    except sqlite3.OperationalError as e:
                        if "no such table" not in str(e).lower():
                            logger.debug(f"[sold_table] 기록 스킵: {e}")
                    result['confirmed'] += 1

            result['success'] = result['confirmed'] > 0
            result['message'] = f"출고 확정: {result['confirmed']}건 SOLD"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"출고 확정 오류: {e}")
            result['errors'].append(str(e))

        return result

    def cancel_reservation(self, lot_no: str = None, plan_id: int = None) -> Dict:
        """
        RESERVED 예약 취소 → AVAILABLE 복원.

        Returns:
            {'success': bool, 'cancelled': int}
        """
        result = {'success': False, 'cancelled': 0, 'errors': []}

        query = "SELECT id, lot_no, tonbag_id FROM allocation_plan WHERE status = 'RESERVED'"
        params = []
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        if plan_id:
            query += " AND id = ?"
            params.append(plan_id)

        try:
            plans = self.db.fetchall(query, tuple(params))
            if not plans:
                result['message'] = "취소할 예약 없음"
                return result

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                for plan in plans:
                    self.db.execute(
                        """UPDATE inventory_tonbag SET
                            status = ?, picked_to = NULL, sale_ref = NULL, updated_at = ?
                        WHERE id = ?""",
                        (STATUS_AVAILABLE, now, plan['tonbag_id'])
                    )
                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'CANCELLED', cancelled_at = ?
                        WHERE id = ?""",
                        (now, plan['id'])
                    )
                    result['cancelled'] += 1

            result['success'] = result['cancelled'] > 0
            result['message'] = f"예약 취소: {result['cancelled']}건"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"예약 취소 오류: {e}")
            result['errors'].append(str(e))

        return result
