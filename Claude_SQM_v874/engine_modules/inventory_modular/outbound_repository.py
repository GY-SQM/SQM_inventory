# -*- coding: utf-8 -*-
"""
P2 Batch B — OutboundWriteRepository
출고 관련 쓰기(INSERT/UPDATE) 전용 레포지토리.
outbound_mixin.py에서 분리한 DB 쓰기 로직.
"""
import logging
from datetime import datetime

from features.repositories.base_repository import BaseRepository
from engine_modules.constants import STATUS_PICKED, STATUS_DEPLETED

logger = logging.getLogger(__name__)


class OutboundWriteRepository(BaseRepository):
    """출고 관련 쓰기 전용 레포지토리."""

    def ensure_outbound_txn_tables(self) -> None:
        """outbound_event_log 테이블 best-effort 생성."""
        try:
            self.execute("""
                CREATE TABLE IF NOT EXISTS outbound_event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    outbound_no TEXT,
                    event_type TEXT,
                    message TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            self.execute(
                "CREATE INDEX IF NOT EXISTS idx_outbound_event_log_created "
                "ON outbound_event_log(created_at DESC)"
            )
        except Exception as e:
            logger.debug(f"outbound_event_log 테이블 생성 스킵: {e}")

    def update_lot_after_pick(self, lot_no: str, weight_kg: float) -> None:
        """피킹 후 LOT 업데이트."""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.execute(
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

    def insert_plan_row(self, payload: dict, alloc_plan_cols: set) -> int:
        """allocation_plan 테이블에 행 삽입, 생성된 row id 반환."""
        cols, vals = [], []
        for k, v in payload.items():
            if k in alloc_plan_cols:
                cols.append(k)
                vals.append(v)
        if not cols:
            raise ValueError("allocation_plan insert 컬럼 없음")
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO allocation_plan ({', '.join(cols)}) VALUES ({placeholders})"
        self.execute(sql, tuple(vals))
        row = self.fetchone("SELECT last_insert_rowid() AS rid")
        return int(row.get("rid", 0) if isinstance(row, dict) else (row[0] if row else 0))

    def insert_sold_row(self, values: tuple) -> None:
        """sold_table에 출고 이력 1건 INSERT."""
        import sqlite3
        try:
            self.execute(
                """INSERT INTO sold_table
                (lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id,
                 sold_qty_kg, sold_qty_mt, gross_weight_kg, sold_date, status, created_by,
                 sap_no, bl_no, customer, sku, sales_order_no, picking_no,
                 delivery_date, ct_plt, is_sample)
                VALUES (?, ?, ?, ?, ?,
                        ?, ?, ?, ?, 'OUTBOUND', 'system',
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?)""",
                values
            )
        except sqlite3.OperationalError as e:
            if "no such table" not in str(e).lower():
                logger.warning(
                    f"[CO_INSERT_SOLD] sold_table 기록 실패: error={e}"
                )

    def insert_outbound_movement(self, lot_no: str, weight: float,
                                 remarks: str, now: str) -> None:
        """stock_movement에 OUTBOUND 이력 INSERT."""
        self.execute(
            "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
            "VALUES (?, 'OUTBOUND', ?, ?, ?)",
            (lot_no, weight, remarks, now))

    def apply_pick_transition(self, plan: dict, tb_weight: float, now: str) -> None:
        """톤백 RESERVED->PICKED 전환 + inventory weight 갱신 + plan EXECUTED."""
        tb_id = plan['tonbag_id']
        p_lot = plan['lot_no']

        self.execute(
            """UPDATE inventory_tonbag SET
                status = ?, picked_date = ?, outbound_date = ?, updated_at = ?
            WHERE id = ?""",
            (STATUS_PICKED, now, plan['outbound_date'] or now, now, tb_id)
        )
        self.execute(
            """UPDATE inventory SET
                current_weight = MAX(0, current_weight - ?),
                picked_weight = picked_weight + ?,
                updated_at = ?
            WHERE lot_no = ?""",
            (tb_weight, tb_weight, now, p_lot)
        )
        self.execute(
            """UPDATE allocation_plan SET status = 'EXECUTED', executed_at = ?
            WHERE id = ?""",
            (now, plan['id'])
        )

    def record_pick_movement(self, lot_no: str, tb_weight: float,
                             customer: str, sale_ref: str, now: str) -> None:
        """stock_movement에 PICKED_MOVE 이력 INSERT."""
        self.execute(
            """INSERT INTO stock_movement
            (lot_no, movement_type, qty_kg, remarks, created_at)
            VALUES (?, 'PICKED_MOVE', ?, ?, ?)""",
            (lot_no, tb_weight,
             f"RESERVED->PICKED, customer={customer}, sale_ref={sale_ref}", now)
        )

    def insert_picking_row(self, plan: dict, tb_weight: float,
                           tonbag_uid, now: str) -> bool:
        """picking_table에 PICKED 이력 INSERT. 중복 시 False."""
        import sqlite3
        try:
            self.execute(
                """INSERT INTO picking_table
                (lot_no, tonbag_id, sub_lt, tonbag_uid, customer, qty_kg, status, picking_date, created_by, remark)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 'system', ?)""",
                (plan['lot_no'], plan['tonbag_id'], plan['sub_lt'], tonbag_uid,
                 plan.get('customer') or '', tb_weight, now,
                 f"plan_id={plan['id']}, sale_ref={plan.get('sale_ref', '')}")
            )
        except sqlite3.OperationalError as e:
            _oe_msg = str(e).lower()
            if "no such table" in _oe_msg:
                pass
            elif "unique" in _oe_msg:
                return False
            else:
                logger.warning(
                    f"[ER_PICKING] INSERT 실패: tonbag_id={plan['tonbag_id']}, error={e}"
                )
        return True

    def recalc_lot_status(self, lot_no: str, cnt_map: dict) -> None:
        """LOT 상태 재계산 후 DB UPDATE."""
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules

        lot = self.fetchone(
            "SELECT current_weight FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        cw = float((lot.get('current_weight') if isinstance(lot, dict) else lot[0]) or 0) if lot else 0

        new_status = OutboundStateRules.compute_lot_status(cnt_map, cw)
        self.execute(
            "UPDATE inventory SET status = ? WHERE lot_no = ?",
            (new_status, lot_no)
        )
