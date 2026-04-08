"""
OutboundRepository v2 — P2-C-04 BaseRepository 상속 적용
★ 기존 메서드 시그니처 100% 유지
★ _fetch_one / _fetch_all / _execute 헬퍼 활용으로 코드 간결화
생성일: 2026-04-08 | SQM v8.7.1

배치 위치: features/repositories/outbound_repository.py
(기존 파일 덮어쓰기)
"""
import sqlite3
import logging
from datetime import datetime
from typing import Dict

from features.repositories.base_repository import BaseRepository
from features.repositories.outbound_query import OutboundQuery
from features.services.outbound_state_rules import OutboundStateRules

logger = logging.getLogger(__name__)


class OutboundRepository(BaseRepository):
    """
    Outbound DB 변경 전담 클래스
    ★ P2-C: BaseRepository 상속 → 공통 헬퍼 사용
    ★ 상태전이는 반드시 OutboundStateRules 검증 후 실행
    """

    def __init__(self, db):
        super().__init__(db)
        self.query = OutboundQuery(db)

    # ================================================================
    # RESERVED → PICKED 전환
    # ================================================================

    def apply_pick_transition(self, plan: dict, tb_weight: float, now: str = None) -> dict:
        """RESERVED → PICKED 상태전이 + inventory weight 갱신 + plan EXECUTED"""
        now = now or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        validation = OutboundStateRules.validate_transition('RESERVED', 'PICKED')
        if not validation["ok"]:
            return {"ok": False, "error": validation["error"]}

        try:
            self._execute(
                """UPDATE inventory_tonbag SET
                    status = 'PICKED', picked_date = ?,
                    outbound_date = ?, updated_at = ?
                WHERE id = ?""",
                (now, plan.get('outbound_date') or now, now, plan.get('tonbag_id'))
            )
            self._execute(
                """UPDATE inventory SET
                    current_weight = MAX(0, current_weight - ?),
                    picked_weight  = picked_weight + ?,
                    updated_at     = ?
                WHERE lot_no = ?""",
                (tb_weight, tb_weight, now, plan.get('lot_no'))
            )
            self._execute(
                "UPDATE allocation_plan SET status = 'EXECUTED', executed_at = ? WHERE id = ?",
                (now, plan.get('id'))
            )
            return {"ok": True, "error": None}
        except Exception as e:
            self._log.error(f"apply_pick_transition 실패: {e}")
            return {"ok": False, "error": str(e)}

    def record_pick_movement(self, plan: dict, tb_weight: float, now: str = None) -> dict:
        """stock_movement에 PICKED_MOVE 이력 INSERT"""
        now = now or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            self._execute(
                """INSERT INTO stock_movement
                   (lot_no, movement_type, qty_kg, remarks, created_at)
                   VALUES (?, 'PICKED_MOVE', ?, ?, ?)""",
                (plan.get('lot_no'), tb_weight,
                 f"RESERVED→PICKED, customer={plan.get('customer')}, "
                 f"sale_ref={plan.get('sale_ref')}", now)
            )
            return {"ok": True, "error": None}
        except Exception as e:
            self._log.error(f"record_pick_movement 실패: {e}")
            return {"ok": False, "error": str(e)}

    def insert_picking_row(self, plan: dict, tb_weight: float, tonbag_uid, now: str = None) -> dict:
        """picking_table에 PICKED 이력 INSERT — 중복 시 스킵"""
        now = now or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            existing = self._fetch_one(
                "SELECT id FROM picking_table WHERE tonbag_id = ?",
                (plan.get('tonbag_id'),)
            )
            if existing:
                return {"ok": False, "error": "중복 피킹", "skipped": True}

            self._execute(
                """INSERT INTO picking_table
                   (lot_no, tonbag_id, sub_lt, tonbag_uid,
                    customer, sale_ref, weight, picked_date, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (plan.get('lot_no'), plan.get('tonbag_id'), plan.get('sub_lt', 0),
                 tonbag_uid or '', plan.get('customer', ''), plan.get('sale_ref', ''),
                 tb_weight, now, now)
            )
            return {"ok": True, "error": None}
        except Exception as e:
            self._log.error(f"insert_picking_row 실패: {e}")
            return {"ok": False, "error": str(e)}

    # ================================================================
    # PICKED → OUTBOUND 확정
    # ================================================================

    def insert_sold_row(self, tb: dict, now: str = None) -> dict:
        """sold_table에 출고 이력 INSERT — status='OUTBOUND'"""
        now = now or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        validation = OutboundStateRules.validate_transition('PICKED', 'OUTBOUND')
        if not validation["ok"]:
            return {"ok": False, "error": validation["error"]}
        try:
            values = self._build_sold_row_payload(tb, now)
            self._execute(
                """INSERT INTO sold_table
                (lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id,
                 sold_qty_kg, sold_qty_mt, gross_weight_kg, sold_date,
                 status, created_by, sap_no, bl_no, customer, sku,
                 sales_order_no, picking_no, delivery_date, ct_plt, is_sample)
                VALUES (?, ?, ?, ?, ?,
                        ?, ?, ?, ?, 'OUTBOUND', 'system',
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?)""",
                values
            )
            return {"ok": True, "error": None}
        except sqlite3.OperationalError as e:
            if "no such table" not in str(e).lower():
                self._log.warning(f"insert_sold_row 실패: tonbag_id={tb.get('id')}, {e}")
            return {"ok": False, "error": str(e)}
        except Exception as e:
            self._log.error(f"insert_sold_row 예외: {e}")
            return {"ok": False, "error": str(e)}

    def insert_outbound_movement(self, tb: dict, now: str = None) -> dict:
        """stock_movement에 OUTBOUND 이력 INSERT"""
        now = now or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            self._execute(
                "INSERT INTO stock_movement "
                "(lot_no, movement_type, qty_kg, remarks, created_at) "
                "VALUES (?, 'OUTBOUND', ?, ?, ?)",
                (tb.get('lot_no'), tb.get('weight', 0),
                 f"confirm_outbound, sub_lt={tb.get('sub_lt', 0)}", now)
            )
            return {"ok": True, "error": None}
        except Exception as e:
            self._log.error(f"insert_outbound_movement 실패: {e}")
            return {"ok": False, "error": str(e)}

    # ================================================================
    # LOT 상태 갱신
    # ================================================================

    def update_lot_after_pick(self, lot_no: str, weight_kg: float) -> dict:
        """피킹 후 LOT 잔량 업데이트"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            self._execute(
                """UPDATE inventory SET
                    current_weight = MAX(0, current_weight - ?),
                    picked_weight  = picked_weight + ?,
                    status = CASE
                        WHEN current_weight - ? <= 0 THEN 'DEPLETED'
                        ELSE status
                    END,
                    updated_at = ?
                WHERE lot_no = ?""",
                (weight_kg, weight_kg, weight_kg, now, lot_no)
            )
            return {"ok": True, "error": None}
        except Exception as e:
            self._log.error(f"update_lot_after_pick 실패: {e}")
            return {"ok": False, "error": str(e)}

    def recalc_lot_status(self, lot_no: str) -> dict:
        """
        LOT status 재계산 (v7.2.0 판정 규칙)
        ★ BaseRepository.row_count() 활용
        """
        try:
            lot = self._fetch_one(
                "SELECT current_weight FROM inventory WHERE lot_no = ?", (lot_no,)
            )
            if not lot:
                return {"ok": False, "error": f"LOT 없음: {lot_no}"}

            cnt_map  = self.query.get_lot_tonbag_status_counts(lot_no)
            total    = sum(cnt_map.values())
            avail    = cnt_map.get('AVAILABLE', 0)
            reserved = cnt_map.get('RESERVED', 0)
            picked   = cnt_map.get('PICKED', 0)
            ret      = cnt_map.get('RETURN', 0)
            outbound = (cnt_map.get('OUTBOUND', 0) + cnt_map.get('SOLD', 0)
                        + cnt_map.get('SHIPPED', 0) + cnt_map.get('CONFIRMED', 0))

            if avail > 0 and outbound == 0:
                new_status = 'AVAILABLE'
            elif avail > 0 and outbound > 0:
                new_status = 'PARTIAL'
            elif total > 0 and outbound >= total:
                new_status = 'OUTBOUND'
            elif ret > 0:
                new_status = 'RETURN'
            elif picked > 0:
                new_status = 'PICKED'
            elif reserved > 0:
                new_status = 'RESERVED'
            else:
                cw = lot.get('current_weight') if hasattr(lot, 'keys') else lot[0]
                new_status = 'DEPLETED' if (cw or 0) <= 0 else 'AVAILABLE'

            self._execute(
                "UPDATE inventory SET status = ? WHERE lot_no = ?",
                (new_status, lot_no)
            )
            return {"ok": True, "new_status": new_status, "error": None}
        except Exception as e:
            self._log.error(f"recalc_lot_status 실패 [{lot_no}]: {e}")
            return {"ok": False, "error": str(e)}

    def cancel_allocation_plan(self, plan_ids: list, reason: str = '') -> dict:
        """allocation_plan 취소 — RESERVED → CANCELLED"""
        if not plan_ids:
            return {"ok": True, "cancelled": 0}
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            ph = ','.join('?' * len(plan_ids))
            self._execute(
                f"""UPDATE allocation_plan SET
                    status = 'CANCELLED', rejected_reason = ?, updated_at = ?
                WHERE id IN ({ph}) AND status = 'RESERVED'""",
                (reason or 'CANCELLED', now, *plan_ids)
            )
            return {"ok": True, "cancelled": len(plan_ids), "error": None}
        except Exception as e:
            self._log.error(f"cancel_allocation_plan 실패: {e}")
            return {"ok": False, "cancelled": 0, "error": str(e)}

    # ================================================================
    # BaseRepository 추상 메서드 구현
    # ================================================================

    def save(self, items: list) -> dict:
        """BaseRepository 호환 인터페이스"""
        return {"saved": 0, "failed": 0, "errors": [],
                "note": "OutboundRepository는 개별 전이 메서드를 사용하세요."}

    # ================================================================
    # 내부 헬퍼
    # ================================================================

    def _build_sold_row_payload(self, tb: dict, now: str) -> tuple:
        """sold_table INSERT용 페이로드 — query 클래스로 조회"""
        tb_id   = tb.get('id') or tb.get('tonbag_id')
        uid_val = (tb.get('tonbag_uid') or '').strip() or str(tb.get('sub_lt') or tb_id)

        pick_info = self.query.get_picking_info(tb_id)
        inv       = self.query.get_inventory_info(tb.get('lot_no', ''))
        alloc     = self.query.get_allocation_info(tb_id)

        is_sample   = tb.get('is_sample', 0) or (1 if tb.get('sub_lt', -1) == 0 else 0)
        tb_gw_kg    = 0.0
        if is_sample:
            tb_gw_kg = (tb.get('weight') or 0) * 1.025
        elif inv.get('mxbg_pallet') and inv.get('gross_weight'):
            tb_gw_kg = float(inv['gross_weight']) / int(inv['mxbg_pallet'])

        customer    = (pick_info.get('customer') or alloc.get('customer')
                       or inv.get('sold_to') or '')
        sold_qty_kg = tb.get('weight') or 0
        sold_qty_mt = round(sold_qty_kg / 1000.0, 6) if sold_qty_kg else 0
        sku         = inv.get('product_code') or ''
        if is_sample and sku and 'Sample' not in sku:
            sku = f"{sku} Sample"

        return (
            tb.get('lot_no'), tb_id, tb.get('sub_lt', 0), uid_val, pick_info.get('id'),
            sold_qty_kg, sold_qty_mt, tb_gw_kg, now,
            inv.get('sap_no', ''), inv.get('bl_no', ''),
            customer, sku,
            pick_info.get('sales_order_no', ''), pick_info.get('picking_no', ''),
            now[:10], 1, 1 if is_sample else 0
        )
