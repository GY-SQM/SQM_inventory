"""
SQM 재고관리 시스템 - 출고 처리 Mixin
======================================

v3.6.6: SQLAlchemy → SQMDatabase API 전환 (self.db 기반)

작성자: Ruby (남기동)
버전: v3.6.6
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional

from core.constants import (
    STATUS_AVAILABLE,
    STATUS_DEPLETED,
    STATUS_PICKED,
    STATUS_RESERVED,
    STATUS_SOLD,
)
from core.types import normalize_lot

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
            self._recalc_lot_status(lot_no)
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
        self._recalc_lot_status(lot_no)

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
                touched_lots = set()
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
                    if lot_no:
                        touched_lots.add(lot_no)

                # 모든 관련 LOT status 재계산
                for lot_no in touched_lots:
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
        # 톤백 상태 우선(판매배정/판매화물 결정/출고 등) → 없으면 잔량 기반
        try:
            status_rows = self.db.fetchall(
                "SELECT status, COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
                (lot_no,)
            )
            status_set = {str(r.get('status', '')).strip().upper() for r in (status_rows or [])}
        except (sqlite3.Error, ValueError, TypeError):
            status_set = set()

        if 'SOLD' in status_set:
            new_status = STATUS_SOLD
        elif 'SHIPPED' in status_set:
            new_status = 'SHIPPED'
        elif 'PICKED' in status_set:
            new_status = STATUS_PICKED
        elif 'RESERVED' in status_set:
            new_status = STATUS_RESERVED
        else:
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
        result = {'success': False, 'reserved': 0, 'errors': [], 'plan_ids': [], 'requested_rows': len(allocation_rows)}

        def _alloc_val(alloc, key, default=None):
            """AllocationRow(dataclass) 또는 dict 모두 지원"""
            if isinstance(alloc, dict):
                return alloc.get(key, default)
            return getattr(alloc, key, default)

        # 중복 Allocation 파일 감지 (basename 기준, UX 경고용)
        if source_file and source_file != '(붙여넣기)':
            try:
                import os
                fname = os.path.basename(source_file)
                dup = self.db.fetchone(
                    """SELECT COUNT(*) AS cnt FROM allocation_plan
                       WHERE status = 'RESERVED' AND source_file LIKE ?""",
                    (f"%{fname}",)
                )
                dup_cnt = dup.get('cnt', 0) if isinstance(dup, dict) else (dup[0] if dup else 0)
                if dup_cnt > 0:
                    result['duplicate_file'] = True
                    result['duplicate_count'] = int(dup_cnt)
                    result['duplicate_file_name'] = fname
            except Exception as e:
                logger.debug(f"중복 Allocation 파일 감지 실패: {e}")

        try:
            with self.db.transaction("IMMEDIATE"):
                for alloc in allocation_rows:
                    lot_no = (normalize_lot(_alloc_val(alloc, 'lot_no')) or '').strip()
                    customer = str(_alloc_val(alloc, 'sold_to') or _alloc_val(alloc, 'customer') or '').strip()
                    sale_ref = str(_alloc_val(alloc, 'sale_ref') or '').strip()
                    qty_mt = float(_alloc_val(alloc, 'qty_mt') or 0)
                    outbound_date = _alloc_val(alloc, 'outbound_date')
                    sublot_count = int(_alloc_val(alloc, 'sublot_count') or _alloc_val(alloc, 'tonbag_count') or 0)

                    if not lot_no:
                        result['errors'].append("LOT 번호 누락")
                        continue

                    # v6.12 Addon-G: DB에서 실제 톤백 단가 조회 (500/1000kg 동적 대응)
                    from engine_modules.constants import get_tonbag_unit_weight
                    _unit_w = get_tonbag_unit_weight(self.db, lot_no)
                    weight_kg = qty_mt * 1000 if qty_mt > 0 else sublot_count * _unit_w

                    tonbags = self.db.fetchall(
                        """SELECT id, sub_lt, weight FROM inventory_tonbag
                           WHERE lot_no = ? AND status = ?
                           ORDER BY sub_lt DESC""",
                        (lot_no, STATUS_AVAILABLE)
                    )

                    if not tonbags:
                        # 원인 구분: DB에 LOT 없음 vs 톤백이 이미 예약/출고됨
                        exists = self.db.fetchone(
                            "SELECT 1 FROM inventory_tonbag WHERE lot_no = ? LIMIT 1",
                            (lot_no,)
                        )
                        if not exists:
                            result['errors'].append(f"가용 톤백 없음: {lot_no} (LOT 미등록 → 입고 먼저 반영)")
                        else:
                            status_rows = self.db.fetchall(
                                "SELECT status, COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
                                (lot_no,)
                            )
                            status_summary = ", ".join(
                                f"{r.get('status', 'UNKNOWN')}={r.get('cnt', 0)}" for r in (status_rows or [])
                            ) or "상태 집계 없음"
                            avail_row = self.db.fetchone(
                                "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? AND status = ?",
                                (lot_no, STATUS_AVAILABLE)
                            )
                            avail_sample_row = self.db.fetchone(
                                "SELECT COUNT(*) AS cnt FROM inventory_tonbag "
                                "WHERE lot_no = ? AND status = ? AND COALESCE(is_sample, 0) = 1",
                                (lot_no, STATUS_AVAILABLE)
                            )
                            avail_cnt = (avail_row.get('cnt') if isinstance(avail_row, dict) else avail_row[0]) if avail_row else 0
                            avail_sample_cnt = (avail_sample_row.get('cnt') if isinstance(avail_sample_row, dict) else avail_sample_row[0]) if avail_sample_row else 0
                            if avail_cnt > 0:
                                extra_reason = f"판매가능 톤백 {avail_cnt}개 (샘플 {avail_sample_cnt}개 포함)"
                            else:
                                extra_reason = "판매가능 톤백 0개"
                            result['errors'].append(
                                f"가용 톤백 없음: {lot_no} (중복 배정 | {extra_reason} | 상태: {status_summary} | 조치: [예약 취소] 후 재시도)"
                            )
                        continue

                    pick_count = sublot_count if sublot_count > 0 else max(1, int(weight_kg / _unit_w))
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
                    if reserved_in_lot > 0:
                        self._recalc_lot_status(lot_no)
                        # v6.12.1: stock_movement 'RESERVED' 이력
                        self.db.execute(
                            "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                            "VALUES (?, 'RESERVED', ?, ?, ?)",
                            (lot_no, reserved_in_lot * _unit_w,
                             f"allocation, tonbags={reserved_in_lot}, customer={customer}", now))
                    logger.info(f"[reserve] {lot_no}: {reserved_in_lot}개 톤백 RESERVED → {customer}")

            result['success'] = result['reserved'] > 0
            if result['success']:
                result['message'] = f"예약 완료: {result['reserved']}개 톤백"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"Allocation 예약 오류 (전체 롤백): {e}", exc_info=True)
            result['errors'].append(str(e))

        # 모든 LOT이 이미 예약 상태인 경우 안내 메시지 추가
        if result['reserved'] == 0 and result['errors']:
            all_dup = all("중복 배정" in err or "이미 예약/출고됨" in err for err in result['errors'])
            if all_dup:
                result['errors'].append(
                    "⚠️ 모든 LOT이 이미 예약 상태입니다.\n"
                    "• 다시 예약: [예약 취소] 후 재시도\n"
                    "• 기존 예약 진행: [출고 실행]"
                )

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

                    # v6.0: PICKED 이력 기록 (picking_table) — remark에 plan_id/sale_ref 추적
                    try:
                        self.db.execute(
                            """INSERT INTO picking_table
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, customer, qty_kg, status, picking_date, created_by, remark)
                            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 'system', ?)""",
                            (p_lot, tb_id, plan['sub_lt'], tonbag_uid,
                             plan.get('customer') or '', tb_weight, now,
                             f"plan_id={plan['id']}, sale_ref={plan.get('sale_ref', '')}")
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
                touched_lots = set()
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
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id, sold_qty_kg, sold_date, status, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'SOLD', 'system')""",
                            (tb['lot_no'], tb_id, tb.get('sub_lt', 0), uid_val, picking_id,
                             tb.get('weight') or 0, now)
                        )
                    except sqlite3.OperationalError as e:
                        if "no such table" not in str(e).lower():
                            logger.debug(f"[sold_table] 기록 스킵: {e}")
                    # v6.12.1: stock_movement 'SOLD' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'SOLD', ?, ?, ?)",
                        (tb['lot_no'], tb.get('weight', 0),
                         f"confirm_outbound, sub_lt={tb.get('sub_lt', 0)}", now))
                    result['confirmed'] += 1
                    if tb.get('lot_no'):
                        touched_lots.add(tb['lot_no'])
                for lot in touched_lots:
                    self._recalc_lot_status(lot)

            result['success'] = result['confirmed'] > 0
            result['message'] = f"출고 확정: {result['confirmed']}건 SOLD"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"출고 확정 오류: {e}")
            result['errors'].append(str(e))

        return result

    def gate1_verify_picking(
        self,
        picking_result,
        picking_no: str = '',
    ) -> dict:
        """
        Gate-1: 피킹리스트 LOT ↔ allocation_plan RESERVED LOT 교차검증.

        v6.12.1 강화:
        - LOT 존재 여부 대조 (기존)
        - 톤백 수/무게 대조 (신규): 피킹 요청 수량 vs RESERVED 수량
        - 결과 상세 리포트 생성
        """
        result = {
            'passed': False,
            'picking_lots': set(),
            'reserved_lots': set(),
            'only_in_picking': set(),
            'only_in_reserved': set(),
            'matched_lots': set(),
            'qty_mismatches': [],       # v6.12.1: 수량 불일치 상세
            'lot_details': [],          # v6.12.1: LOT별 상세 비교
            'error_report': '',
        }
        try:
            # --- 피킹 LOT 추출 ---
            if hasattr(picking_result, 'tonbag'):
                picking_lots = {getattr(item, 'lot_no', str(item.get('lot_no', '')))
                                for item in picking_result.tonbag}
            elif isinstance(picking_result, dict) and 'items' in picking_result:
                picking_lots = {item['lot_no'] for item in picking_result['items']
                                if item.get('lot_no')}
            else:
                picking_lots = set()

            result['picking_lots'] = picking_lots
            if not picking_lots:
                result['error_report'] = 'Gate-1 실패: 피킹 LOT 없음'
                return result

            # --- 피킹 LOT별 요청 수량 집계 ---
            picking_qty = {}  # {lot_no: {'qty_kg': float, 'tonbag_count': int}}
            if hasattr(picking_result, 'tonbag'):
                for item in picking_result.tonbag:
                    lot = getattr(item, 'lot_no', '')
                    kg = getattr(item, 'qty_kg', 0) or getattr(item, 'weight_kg', 0) or 0
                    if lot:
                        if lot not in picking_qty:
                            picking_qty[lot] = {'qty_kg': 0, 'tonbag_count': 0}
                        picking_qty[lot]['qty_kg'] += float(kg)
                        picking_qty[lot]['tonbag_count'] += 1
            elif isinstance(picking_result, dict):
                for item in picking_result.get('items', []):
                    lot = item.get('lot_no', '')
                    kg = float(item.get('qty_kg', 0) or 0)
                    if lot:
                        if lot not in picking_qty:
                            picking_qty[lot] = {'qty_kg': 0, 'tonbag_count': 0}
                        picking_qty[lot]['qty_kg'] += kg
                        picking_qty[lot]['tonbag_count'] += 1

            # --- DB 대조 ---
            placeholders = ','.join('?' * len(picking_lots))
            rows = self.db.fetchall(
                f"""SELECT DISTINCT lot_no FROM allocation_plan
                    WHERE status = 'RESERVED' AND lot_no IN ({placeholders})""",
                tuple(picking_lots)
            )
            reserved_in_db = {r['lot_no'] for r in rows}
            all_reserved = self.db.fetchall(
                "SELECT DISTINCT lot_no FROM allocation_plan WHERE status = 'RESERVED'"
            )
            all_reserved_lots = {r['lot_no'] for r in all_reserved}
            result['reserved_lots'] = all_reserved_lots

            only_in_picking = picking_lots - reserved_in_db
            only_in_reserved = all_reserved_lots - picking_lots
            matched = picking_lots & reserved_in_db
            result['only_in_picking'] = only_in_picking
            result['only_in_reserved'] = only_in_reserved
            result['matched_lots'] = matched

            # --- v6.12.1: 수량 교차 검증 ---
            qty_mismatches = []
            lot_details = []
            for lot_no in sorted(matched):
                # DB에서 RESERVED 톤백 수/총 무게 조회
                db_row = self.db.fetchone(
                    """SELECT COUNT(*) AS tb_count,
                              COALESCE(SUM(t.weight), 0) AS total_kg
                       FROM allocation_plan ap
                       JOIN inventory_tonbag t ON t.id = ap.tonbag_id
                       WHERE ap.lot_no = ? AND ap.status = 'RESERVED'""",
                    (lot_no,)
                )
                db_count = db_row['tb_count'] if db_row else 0
                db_kg = float(db_row['total_kg']) if db_row else 0

                pk = picking_qty.get(lot_no, {'qty_kg': 0, 'tonbag_count': 0})
                pk_kg = pk['qty_kg']
                pk_count = pk['tonbag_count']

                detail = {
                    'lot_no': lot_no,
                    'picking_kg': pk_kg,
                    'picking_count': pk_count,
                    'reserved_kg': db_kg,
                    'reserved_count': db_count,
                    'kg_match': abs(pk_kg - db_kg) < 1.0,
                    'count_match': pk_count == 0 or pk_count == db_count,
                }
                lot_details.append(detail)

                if not detail['kg_match']:
                    qty_mismatches.append(
                        f"LOT {lot_no}: 피킹 {pk_kg:,.0f}kg vs RESERVED {db_kg:,.0f}kg "
                        f"(차이: {abs(pk_kg - db_kg):,.0f}kg)"
                    )

            result['qty_mismatches'] = qty_mismatches
            result['lot_details'] = lot_details

            # --- 리포트 생성 ---
            lines = [
                '=' * 60,
                f'[Gate-1 교차검증] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                f'피킹리스트: {picking_no}',
                f'피킹 LOT: {len(picking_lots)}개 | RESERVED: {len(all_reserved_lots)}개 | 매칭: {len(matched)}개',
                '',
            ]

            # LOT 존재 불일치
            if only_in_picking:
                lines.append(f'❌ 피킹에만 있고 RESERVED 없는 LOT ({len(only_in_picking)}개):')
                for lot in sorted(only_in_picking)[:10]:
                    lines.append(f'   - {lot}')
                if len(only_in_picking) > 10:
                    lines.append(f'   ... 외 {len(only_in_picking)-10}개')
                lines.append('')

            if only_in_reserved:
                lines.append(f'⚠️ RESERVED에만 있고 피킹 없는 LOT ({len(only_in_reserved)}개):')
                for lot in sorted(only_in_reserved)[:10]:
                    lines.append(f'   - {lot}')
                lines.append('')

            # v6.12.1: 수량 불일치
            if qty_mismatches:
                lines.append(f'⚠️ 수량 불일치 ({len(qty_mismatches)}건):')
                for m in qty_mismatches[:10]:
                    lines.append(f'   - {m}')
                if len(qty_mismatches) > 10:
                    lines.append(f'   ... 외 {len(qty_mismatches)-10}건')
                lines.append('')

            # 매칭 LOT 요약
            if lot_details:
                ok_count = sum(1 for d in lot_details if d['kg_match'])
                lines.append(f'📊 매칭 LOT 수량 검증: {ok_count}/{len(lot_details)} 일치')
                lines.append('')

            # 최종 판정
            if not only_in_picking:
                if qty_mismatches:
                    lines.append('⚠️ Gate-1 조건부 통과 — LOT 매칭 OK, 수량 불일치 있음')
                    lines.append('   수량 차이를 확인 후 진행하세요')
                    result['passed'] = True  # LOT 매칭은 통과, 수량 경고만
                else:
                    lines.append('✅ Gate-1 완전 통과 — LOT 매칭 + 수량 검증 모두 OK')
                    result['passed'] = True
            else:
                lines.append('🚫 Gate-1 실패 — 전체 출고 처리 중단됨')
                lines.append('   allocation_plan 확인 후 재시도하세요')

            lines.append('=' * 60)
            result['error_report'] = '\n'.join(lines)
            logger.info('[Gate-1] passed=%s, matched=%s, missing=%s, qty_mismatch=%s',
                        result['passed'], len(matched), len(only_in_picking), len(qty_mismatches))
        except (sqlite3.Error, AttributeError) as e:
            result['error_report'] = f'Gate-1 DB 오류: {e}'
            logger.error(f'[Gate-1] 오류: {e}', exc_info=True)
        return result

    @staticmethod
    def _gate1_to_json(gate1: dict) -> str:
        """Gate-1 결과를 JSON 문자열로 변환 (DB 저장용). set→list 자동 변환."""
        import json as _json
        try:
            serializable = {}
            for k, v in gate1.items():
                if isinstance(v, set):
                    serializable[k] = sorted(v)
                elif k == 'error_report':
                    continue  # 텍스트 리포트는 별도 저장
                else:
                    serializable[k] = v
            return _json.dumps(serializable, ensure_ascii=False)
        except (TypeError, ValueError):
            return _json.dumps({'passed': gate1.get('passed', False)})

    def execute_from_picking(
        self,
        picking_result,
        picking_no: str = '',
        sales_order: str = '',
    ) -> dict:
        """Gate-1 통과 후 피킹리스트 기반 RESERVED → PICKED 전환."""
        result = {'success': False, 'executed': 0, 'gate1': {}, 'errors': []}
        gate1 = self.gate1_verify_picking(picking_result, picking_no)
        result['gate1'] = gate1
        if not gate1['passed']:
            result['errors'].append(gate1['error_report'])
            logger.warning('[execute_from_picking] Gate-1 실패 → 중단')
            return result

        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            meta = picking_result.meta
            with self.db.transaction('IMMEDIATE'):
                self.db.execute(
                    """INSERT INTO picking_list_order
                       (sales_order, customer_ref, picking_date, status,
                        total_lots, total_weight, picking_no, delivery_terms,
                        port_loading, port_discharge, containers,
                        contact_person, contact_email,
                        total_nw_kg, total_gw_kg, gate1_result,
                        created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        sales_order or getattr(meta, 'sales_order', ''),
                        getattr(meta, 'outbound_id', ''),
                        getattr(meta, 'creation_date', ''),
                        'EXECUTED',
                        len(gate1['matched_lots']),
                        picking_result.summary.get('total_mt', 0) * 1000,
                        getattr(meta, 'picking_no', ''),
                        getattr(meta, 'delivery_terms', ''),
                        getattr(meta, 'port_loading', ''),
                        getattr(meta, 'port_discharge', ''),
                        getattr(meta, 'containers', '1'),
                        getattr(meta, 'contact_person', ''),
                        getattr(meta, 'contact_email', ''),
                        getattr(meta, 'total_nw_kg', ''),
                        getattr(meta, 'total_gw_kg', ''),
                        self._gate1_to_json(gate1),
                        now, now,
                    )
                )
                row = self.db.fetchone('SELECT last_insert_rowid() AS id')
                picking_order_id = row['id'] if row else None
                executed = 0
                for lot_no in gate1['matched_lots']:
                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'EXECUTED', executed_at = ?
                           WHERE lot_no = ? AND status = 'RESERVED'""",
                        (now, lot_no)
                    )
                    tonbags = self.db.fetchall(
                        """SELECT id, weight FROM inventory_tonbag
                           WHERE lot_no = ? AND status = 'RESERVED'""",
                        (lot_no,)
                    )
                    for tb in tonbags:
                        self.db.execute(
                            """UPDATE inventory_tonbag SET
                                status = ?, picked_date = ?, updated_at = ?
                               WHERE id = ?""",
                            (STATUS_PICKED, now, now, tb['id'])
                        )
                        if picking_order_id is not None:
                            try:
                                self.db.execute(
                                    """INSERT INTO picking_list_detail
                                       (picking_order_id, lot_no, weight, picked_status, picked_at)
                                       VALUES (?, ?, ?, 'PICKED', ?)""",
                                    (picking_order_id, lot_no, tb.get('weight', 0), now)
                                )
                            except sqlite3.OperationalError:
                                pass
                    self._recalc_lot_status(lot_no)
                    executed += 1
                result['success'] = executed > 0
                result['executed'] = executed
                result['message'] = f'피킹 실행 완료: {executed}개 LOT → 판매화물 결정'
        except (sqlite3.Error, ValueError) as e:
            result['errors'].append(str(e))
            logger.error(f'[execute_from_picking] 오류: {e}', exc_info=True)
        return result

    def cancel_reservation(
        self,
        lot_no: str = None,
        plan_id: int = None,
        plan_ids: list = None,
    ) -> Dict:
        """
        RESERVED 예약 취소 → AVAILABLE 복원.
        plan_ids: 여러 건 일괄 취소 시 [id, ...] 전달.

        Returns:
            {'success': bool, 'cancelled': int}
        """
        result = {'success': False, 'cancelled': 0, 'errors': []}

        query = "SELECT id, lot_no, tonbag_id FROM allocation_plan WHERE status = 'RESERVED'"
        params = []
        if plan_ids:
            if not isinstance(plan_ids, (list, tuple)) or not plan_ids:
                result['message'] = "취소할 배정(plan_ids)이 비어 있습니다."
                return result
            query += " AND id IN (" + ",".join("?" * len(plan_ids)) + ")"
            params.extend(plan_ids)
        else:
            if lot_no:
                query += " AND lot_no = ?"
                params.append(lot_no)
            if plan_id is not None:
                query += " AND id = ?"
                params.append(plan_id)

        try:
            plans = self.db.fetchall(query, tuple(params))
            if not plans:
                result['message'] = "취소할 예약 없음"
                return result

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
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
                    # v6.12.1: stock_movement 'CANCEL_RESERVE' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'CANCEL_RESERVE', 0, ?, ?)",
                        (plan.get('lot_no', ''), f"plan_id={plan['id']}", now))
                    if plan.get('lot_no'):
                        touched_lots.add(plan['lot_no'])
                for lot_no in touched_lots:
                    self._recalc_lot_status(lot_no)

            result['success'] = result['cancelled'] > 0
            result['message'] = f"예약 취소: {result['cancelled']}건"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"예약 취소 오류: {e}")
            result['errors'].append(str(e))

        return result

    def revert_picked_to_reserved(self, lot_no: str = None) -> Dict:
        """
        판매화물 결정 취소: PICKED → 판매 배정(RESERVED)으로 되돌림.
        allocation_plan EXECUTED → RESERVED, inventory_tonbag PICKED → RESERVED.
        """
        result = {'success': False, 'reverted': 0, 'errors': []}
        query = """SELECT id, lot_no, tonbag_id FROM allocation_plan WHERE status = 'EXECUTED'"""
        params = [] if not lot_no else [lot_no]
        if lot_no:
            query += " AND lot_no = ?"
        try:
            rows = self.db.fetchall(query, tuple(params))
            if not rows:
                result['message'] = "되돌릴 판매화물 결정(EXECUTED) 건이 없습니다."
                return result
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                for r in rows:
                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'RESERVED', executed_at = NULL WHERE id = ?""",
                        (r['id'],)
                    )
                    self.db.execute(
                        """UPDATE inventory_tonbag SET status = ?, picked_date = NULL, updated_at = ?
                           WHERE id = ?""",
                        (STATUS_RESERVED, now, r['tonbag_id'])
                    )
                    result['reverted'] += 1
                    # v6.12.1: stock_movement 'REVERT_PICKED' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_PICKED', 0, ?, ?)",
                        (r['lot_no'], f"plan_id={r['id']}, PICKED→RESERVED", now))
                    self._recalc_lot_status(r['lot_no'])
            result['success'] = True
            result['message'] = f"판매화물 결정 취소: {result['reverted']}건 → 판매 배정(RESERVED)"
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error(f"revert_picked_to_reserved 오류: {e}")
            result['errors'].append(str(e))
        return result

    def revert_sold_to_picked(self, lot_no: str = None) -> Dict:
        """
        출고 취소(→ 판매화물 결정): SOLD → PICKED로 되돌림.
        inventory_tonbag SOLD → PICKED, sold_table 해당 톤백 행 삭제.
        """
        result = {'success': False, 'reverted': 0, 'errors': []}
        query = """SELECT id, lot_no FROM inventory_tonbag WHERE status = ?"""
        params = [STATUS_SOLD]
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        try:
            tonbags = self.db.fetchall(query, tuple(params))
            if not tonbags:
                result['message'] = "되돌릴 출고(SOLD) 톤백이 없습니다."
                return result
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                for tb in tonbags:
                    tb_id = tb['id']
                    self.db.execute(
                        """UPDATE inventory_tonbag SET status = ?, outbound_date = NULL, updated_at = ?
                           WHERE id = ?""",
                        (STATUS_PICKED, now, tb_id)
                    )
                    try:
                        self.db.execute("DELETE FROM sold_table WHERE tonbag_id = ?", (tb_id,))
                    except sqlite3.OperationalError:
                        pass
                    result['reverted'] += 1
                    # v6.12.1: stock_movement 'REVERT_SOLD' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_SOLD', 0, ?, ?)",
                        (tb.get('lot_no', ''), f"tonbag_id={tb_id}, SOLD→PICKED", now))
                    if tb.get('lot_no'):
                        touched_lots.add(tb['lot_no'])
                for lot in touched_lots:
                    self._recalc_lot_status(lot)
            result['success'] = True
            result['message'] = f"출고 취소: {result['reverted']}건 → 판매화물 결정(PICKED)"
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error(f"revert_sold_to_picked 오류: {e}")
            result['errors'].append(str(e))
        return result

    # ═══════════════════════════════════════════════════════
    # v6.12 Stage4: 빠른 출고 (Quick Outbound)
    # ═══════════════════════════════════════════════════════

    def quick_outbound(self, lot_no: str, count: int, customer: str,
                        reason: str = '', operator: str = '') -> Dict:
        """
        빠른 출고: Allocation 없이 소량 즉시 출고.
        최대 QUICK_OUTBOUND_MAX_TONBAGS개, PICKED에서 멈춤.
        allocation_plan source='QUICK' 자동 기록.
        """
        from engine_modules.constants import QUICK_OUTBOUND_MAX_TONBAGS
        result = {'success': False, 'picked_count': 0, 'total_weight_kg': 0, 'errors': []}

        if count > QUICK_OUTBOUND_MAX_TONBAGS:
            result['errors'].append(f"빠른 출고 최대 {QUICK_OUTBOUND_MAX_TONBAGS}개 (요청: {count}개)")
            return result
        if not customer.strip():
            result['errors'].append("고객명 필수")
            return result
        lot_no = str(lot_no).strip()
        if not lot_no:
            result['errors'].append("LOT 번호 필요")
            return result

        try:
            with self.db.transaction("IMMEDIATE"):
                tonbags = self.db.fetchall(
                    """SELECT id, sub_lt, weight, tonbag_uid FROM inventory_tonbag
                       WHERE lot_no = ? AND status = ? AND COALESCE(is_sample,0) = 0
                       ORDER BY sub_lt DESC LIMIT ?""",
                    (lot_no, STATUS_AVAILABLE, count))

                if len(tonbags) < count:
                    raise ValueError(f"가용 톤백 부족: {len(tonbags)}개 (요청: {count}개)")

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                quick_ref = f"QUICK-{now.replace(' ','_').replace(':','')}"
                total_weight = 0.0

                for tb in tonbags:
                    tb_w = tb['weight'] or 0
                    # AVAILABLE → RESERVED
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status=?, picked_to=?, sale_ref=?, updated_at=? WHERE id=?",
                        (STATUS_RESERVED, customer, quick_ref, now, tb['id']))
                    # allocation_plan QUICK
                    self.db.execute(
                        """INSERT INTO allocation_plan
                        (lot_no, tonbag_id, sub_lt, customer, sale_ref, qty_mt, status, source_file, created_at)
                        VALUES (?,?,?,?,?,?,'RESERVED',?,?)""",
                        (lot_no, tb['id'], tb['sub_lt'], customer, quick_ref, tb_w/1000.0, f"QUICK:{reason}:{operator}", now))
                    # RESERVED → PICKED
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status=?, picked_date=?, outbound_date=?, updated_at=? WHERE id=?",
                        (STATUS_PICKED, now, now, now, tb['id']))
                    # allocation_plan EXECUTED
                    self.db.execute(
                        "UPDATE allocation_plan SET status='EXECUTED', executed_at=? WHERE tonbag_id=? AND sale_ref=? AND status='RESERVED'",
                        (now, tb['id'], quick_ref))
                    # picking_table
                    try:
                        self.db.execute(
                            """INSERT INTO picking_table
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, customer, qty_kg, status, picking_date, created_by, remark)
                            VALUES (?,?,?,?,?,?,'ACTIVE',?,'system',?)""",
                            (lot_no, tb['id'], tb['sub_lt'], tb.get('tonbag_uid') or '', customer, tb_w, now,
                             f"QUICK: {reason}, op={operator}"))
                    except Exception: pass
                    total_weight += tb_w
                    result['picked_count'] += 1

                # inventory 차감
                self.db.execute(
                    "UPDATE inventory SET current_weight=MAX(0,current_weight-?), picked_weight=picked_weight+?, updated_at=? WHERE lot_no=?",
                    (total_weight, total_weight, now, lot_no))
                # stock_movement
                self.db.execute(
                    "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) VALUES (?,'QUICK_OUTBOUND',?,?,?)",
                    (lot_no, total_weight, f"customer={customer}, reason={reason}, op={operator}, count={count}", now))

                self._recalc_lot_status(lot_no)
                if hasattr(self, 'verify_lot_integrity'):
                    integrity = self.verify_lot_integrity(lot_no)
                    if not integrity.get('valid', True):
                        raise ValueError(f"빠른 출고 정합성 실패 ({lot_no}): {integrity.get('errors',[])}")

                result['success'] = True
                result['total_weight_kg'] = total_weight
                result['message'] = f"빠른 출고: {result['picked_count']}개 → PICKED ({total_weight:,.0f}kg)"
                logger.info(result['message'])

        except (ValueError, TypeError) as e:
            result['errors'].append(str(e))
            logger.error(f"빠른 출고 오류: {e}", exc_info=True)
        return result

