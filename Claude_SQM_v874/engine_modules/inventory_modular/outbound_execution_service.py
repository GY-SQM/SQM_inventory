# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 실행 서비스 Mixin (GB)
=================================================

outbound_mixin.py에서 분리된 출고 실행 메서드.
Lines 611-1075 원본 기준.

작성자: Ruby (남기동)
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional

from engine_modules.constants import (
    STATUS_AVAILABLE,
    STATUS_DEPLETED,
    STATUS_PICKED,
)

logger = logging.getLogger(__name__)


class OutboundExecutionMixin:
    """출고 실행 처리 Mixin."""

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

        except (ValueError, TypeError, AttributeError,
                sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
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
            # ★ S4-1 FIX (S3-BUG-1): inventory 무게 갱신 추가
            # 이전: 톤백만 PICKED 변경, inventory 무게 미갱신 → 정합성 실패 → 롤백
            # 수정: current_weight↓ + picked_weight↑ → 정합성 유지
            self._update_lot_after_pick(lot_no, weight_kg)
            if hasattr(self, '_recalc_current_weight'):
                self._recalc_current_weight(lot_no, reason='P2_STOP_AT_PICK')
            self._recalc_lot_status(lot_no)
            # PICK 이력 기록 (OUTBOUND와 구분)
            self.db.execute(
                """INSERT INTO stock_movement
                (lot_no, movement_type, qty_kg, remarks, created_at)
                VALUES (?, 'PICK', ?, ?, ?)""" ,
                (lot_no, weight_kg, f"customer={customer},source={source}", now)
            )
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
        if hasattr(self, '_recalc_current_weight'):
            self._recalc_current_weight(lot_no, reason='P2_OUTBOUND_STAGE2')
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

        # v8.3.0 [Phase 9]: OUTBOUND audit_log
        try:
            from engine_modules.audit_helper import write_audit, EVT_OUTBOUND
            write_audit(self.db, EVT_OUTBOUND, lot_no=lot_no, detail={
                'customer':      customer,
                'weight_kg':     weight_kg,
                'tonbags_picked': picked_count,
            })
        except Exception as _ae:
            logger.debug(f"[OUTBOUND audit] 스킵: {_ae}")

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
        # v8.0.3 [P2]: 피킹 후 중앙 재계산 추가
        if hasattr(self, '_recalc_current_weight'):
            self._recalc_current_weight(lot_no, reason='P2_UPDATE_LOT_AFTER_PICK')

    def cancel_outbound_tonbag(self, lot_no: str, sub_lt: int) -> Dict:
        """
        출고 취소: 톤백 PICKED → AVAILABLE + inventory.current_weight 복구

        All-or-Nothing: 톤백 + inventory 모두 성공해야 commit
        """
        from datetime import datetime
        from engine_modules.constants import (
            STATUS_AVAILABLE, STATUS_PICKED, STATUS_SOLD, STATUS_OUTBOUND,
        )
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

                # v6.9.3 [RT-FIX]: SOLD 상태도 직접 반품 허용
                # 설계 원칙: 출고 취소 = SOLD → AVAILABLE 직접 복귀 (PICKED 경유 없음)
                _allowed_cancel = (STATUS_PICKED, STATUS_SOLD)
                if tonbag['status'] not in _allowed_cancel:
                    result['errors'].append(
                        f"[RETURN_INVALID_STATUS] 반품 불가 상태: "
                        f"{lot_no}-{sub_lt} ({tonbag['status']}) "
                        f"— PICKED 또는 SOLD 상태만 반품 가능"
                    )
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

                # v7.2.0 [RT-FIX]: OUTBOUND/SOLD 상태 반품 시 sold_table / picking_table 정리
                was_sold = tonbag['status'] in (STATUS_OUTBOUND, STATUS_SOLD, 'SHIPPED', 'CONFIRMED')
                if was_sold:
                    try:
                        self.db.execute(
                            "UPDATE sold_table SET status='RETURNED', sold_date=? "
                            "WHERE lot_no=? AND sub_lt=? AND status IN ('ACTIVE','SOLD','CONFIRMED')",
                            (now, lot_no, sub_lt)
                        )
                    except Exception:
                        logger.debug("[SUPPRESSED] exception in outbound_mixin.py")  # noqa
                    try:
                        self.db.execute(
                            "UPDATE picking_table SET status='RETURNED', sold_date=? "
                            "WHERE lot_no=? AND sub_lt=? AND status IN ('ACTIVE','SOLD','CONFIRMED')",
                            (now, lot_no, sub_lt)
                        )
                    except Exception:
                        logger.debug("[SUPPRESSED] exception in outbound_mixin.py")  # noqa
                    try:
                        self.db.execute(
                            "UPDATE allocation_plan SET status='CANCELLED', cancelled_at=? "
                            "WHERE lot_no=? AND sub_lt=? AND status IN ('EXECUTED','RESERVED','STAGED')",
                            (now, lot_no, sub_lt)
                        )
                    except Exception:
                        logger.debug("[SUPPRESSED] exception in outbound_mixin.py")  # noqa

                # 3. inventory summary/status 재계산
                if hasattr(self, '_recalc_current_weight'):
                    self._recalc_current_weight(lot_no, reason='P2_CANCEL_OUTBOUND_TONBAG')
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

            # v7.1.0 [CANCEL-INTEGRITY-1]: 취소 후 verify_lot_integrity 강화
            # 기존 _assert_lot_integrity → verify_lot_integrity로 교체
            # 경고 발생 시 result['warnings']에 기록 (중단 아님)
            if result['success']:
                try:
                    if hasattr(self, 'verify_lot_integrity'):
                        _integ = self.verify_lot_integrity(lot_no)
                        if not _integ.get('valid', True):
                            _iw = (
                                f"[CANCEL-INTEGRITY-1] 취소 후 정합성 경고: {lot_no} "
                                f"— {'; '.join(_integ.get('errors', []))[:100]} "
                                f"(재고 복구 완료, DB 재계산 권장)"
                            )
                            result.setdefault('warnings', []).append(_iw)
                            logger.warning(_iw)
                        else:
                            logger.info(f"[CANCEL-INTEGRITY-1] 정합성 OK: {lot_no}")
                    elif hasattr(self, '_assert_lot_integrity'):
                        self._assert_lot_integrity(lot_no)
                except Exception as _ie:
                    logger.debug(f"[CANCEL-INTEGRITY-1] 스킵: {_ie}")

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
        from engine_modules.constants import STATUS_AVAILABLE, STATUS_PICKED
        result = {'success': False, 'cancelled': 0, 'errors': []}

        try:
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                # v8.2.0 N+1 최적화: 루프 전 tonbag 일괄 pre-fetch
                _keys = [
                    (str(it.get('lot_no') or '').strip(), it.get('sub_lt'))
                    for it in items
                ]
                _placeholders = ','.join('(?,?)' for _ in _keys)
                _params = [v for k in _keys for v in k]
                _tb_rows = self.db.fetchall(
                    f"SELECT lot_no, sub_lt, weight, status, picked_to "
                    f"FROM inventory_tonbag "
                    f"WHERE status = ? AND (lot_no, sub_lt) IN ({_placeholders})",
                    tuple([STATUS_PICKED] + _params)
                ) if _placeholders else []
                # SQLite는 row value IN 미지원 — fallback to dict lookup
                if not _tb_rows:
                    _tb_rows = []
                    for _k_lot, _k_sub in _keys:
                        _r = self.db.fetchone(
                            "SELECT lot_no, sub_lt, weight, status, picked_to "
                            "FROM inventory_tonbag "
                            "WHERE lot_no=? AND sub_lt=? AND status=?",
                            (_k_lot, _k_sub, STATUS_PICKED)
                        )
                        if _r: _tb_rows.append(_r)
                _tonbag_cache = {
                    (str(r.get('lot_no') if isinstance(r, dict) else r[0]),
                     r.get('sub_lt') if isinstance(r, dict) else r[1]): r
                    for r in (_tb_rows or [])
                }

                for item in items:
                    lot_no = str(item.get('lot_no') or '').strip()
                    sub_lt = item.get('sub_lt')

                    tonbag = _tonbag_cache.get((lot_no, sub_lt))
                    if not tonbag:
                        raise ValueError(f"취소 불가: {lot_no}-{sub_lt}")

                    weight = (tonbag.get('weight') if isinstance(tonbag, dict)
                              else tonbag[2]) or 0
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
                    # v8.0.3 [P2]: bulk 취소 후 중앙 재계산
                    if hasattr(self, '_recalc_current_weight'):
                        self._recalc_current_weight(lot_no, reason='P2_CANCEL_OUTBOUND_BULK')

                result['success'] = True
                result['message'] = f"일괄 취소 완료: {result['cancelled']}건"

        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['errors'].append(str(e))
            logger.error(f"일괄 출고 취소 오류: {e}")

        return result
