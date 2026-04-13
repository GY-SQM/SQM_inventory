"""
OutboundQuery — Outbound DB 조회 전담 클래스
★ SELECT만 담당 — INSERT/UPDATE/DELETE 절대 금지
원본: engine_modules/inventory_modular/outbound_mixin.py
분리일: 2026-04-08 | SQM v8.7.1
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OutboundQuery:
    """
    Outbound 조회 전용 클래스
    - self.db: 기존 SQM DB 객체 (fetchone/fetchall 인터페이스 유지)
    """

    def __init__(self, db):
        """
        Args: db — SQM 기존 DB 객체 (sqlite3 Connection 또는 SQM DB wrapper)
        """
        self.db = db

    # ================================================================
    # 출고 상태 조회
    # ================================================================

    def get_outbound_status(self, outbound_no: str) -> str:
        """
        출고번호별 상태 문자열 반환 (배너용)
        [원본 이관] OutboundMixin._get_outbound_status()
        """
        if not outbound_no:
            return ""
        try:
            row = self.db.fetchone(
                "SELECT status FROM outbound WHERE outbound_no = ? LIMIT 1",
                (outbound_no,),
            )
            if row:
                return (row.get("status") if isinstance(row, dict) else row[0]) or ""
        except Exception:
            logger.debug("[SUPPRESSED] get_outbound_status exception")
        return ""

    def get_outbound_event_log(self, limit: int = 50) -> List[Dict]:
        """
        출고 이벤트 로그 최근 N건 조회 (타임라인 UI용)
        [원본 이관] OutboundMixin.get_outbound_event_log()
        """
        try:
            rows = self.db.fetchall(
                "SELECT id, outbound_no, event_type, message, created_at "
                "FROM outbound_event_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            if not rows:
                return []
            out = []
            for r in rows:
                if isinstance(r, dict):
                    out.append(dict(r))
                else:
                    out.append({
                        "id": r[0], "outbound_no": r[1] or "",
                        "event_type": r[2] or "", "message": r[3] or "",
                        "created_at": r[4] or "",
                    })
            return out
        except Exception as e:
            logger.debug(f"get_outbound_event_log: {e}")
            return []

    # ================================================================
    # RESERVED (예약) 조회
    # ================================================================

    def load_reserved_plans(
        self,
        lot_no: str = None,
        target_date: str = None
    ) -> list:
        """
        RESERVED 상태 allocation_plan 조회
        [원본 이관] OutboundMixin._er_load_reserved_plans()
        """
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
            return self.db.fetchall(query, tuple(params)) or []
        except Exception as e:
            logger.error(f"load_reserved_plans 실패: {e}")
            return []

    def warn_stale_plans(self, plans: list) -> list:
        """
        outbound_date 30일 초과 만료 예약 목록 반환
        [원본 이관] OutboundMixin._er_warn_stale_plans()
        Returns: 만료 예약 목록
        """
        if not plans:
            return []
        try:
            threshold = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            stale = [
                p for p in plans
                if p.get('outbound_date') and str(p.get('outbound_date', '')) < threshold
            ]
            if stale:
                stale_lots = list({p.get('lot_no', '') for p in stale})[:5]
                logger.warning(
                    f"[STALE_RESERVATION] 출고일 30일 초과 예약 {len(stale)}건 "
                    f"— LOT: {', '.join(stale_lots)} / 담당자 확인 권장"
                )
            return stale
        except Exception as e:
            logger.debug(f"warn_stale_plans: {e}")
            return []

    # ================================================================
    # PICKED (피킹완료) 조회
    # ================================================================

    def load_picked_tonbags(self, lot_no: str = None) -> list:
        """
        PICKED 상태 톤백 조회
        [원본 이관] OutboundMixin._co_load_picked_tonbags()
        """
        query = """SELECT id, lot_no, sub_lt, weight, tonbag_uid, status,
                          is_sample, customer, sale_ref
                   FROM inventory_tonbag
                   WHERE status = 'PICKED'"""
        params = []
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        try:
            return self.db.fetchall(query, tuple(params)) or []
        except Exception as e:
            logger.error(f"load_picked_tonbags 실패: {e}")
            return []

    def check_double_sold(self, tonbag_id) -> bool:
        """
        이중 SOLD 차단 확인
        sold_table에 동일 tonbag_id가 이미 존재하면 True (차단 필요)
        [원본 이관] OutboundMixin._co_check_double_sold()
        """
        if not tonbag_id:
            return False
        try:
            row = self.db.fetchone(
                "SELECT id FROM sold_table "
                "WHERE tonbag_id=? AND status IN ('OUTBOUND','SOLD')",
                (tonbag_id,)
            )
            return bool(row)
        except Exception:
            return False

    def guard_against_double_outbound(self, tonbags: list) -> list:
        """
        이중 출고 차단 — 이미 sold_table에 존재하는 톤백 ID 반환
        [원본 이관] OutboundMixin._co_guard_against_double_outbound()
        Returns: 이미 출고된 tonbag_id 목록 (비어있으면 안전)
        """
        tb_ids = [tb['id'] if isinstance(tb, dict) else tb[0] for tb in tonbags]
        if not tb_ids:
            return []
        try:
            ph = ','.join('?' * len(tb_ids))
            already_sold = self.db.fetchall(
                f"SELECT tonbag_id FROM sold_table WHERE tonbag_id IN ({ph})",
                tuple(tb_ids)
            ) or []
            return [
                r.get('tonbag_id') if isinstance(r, dict) else r[0]
                for r in already_sold
            ]
        except Exception as e:
            logger.error(f"guard_against_double_outbound 실패: {e}")
            return []

    def validate_customer_sale_ref(self, tonbags: list) -> dict:
        """
        고객/sale_ref 검증 — 불일치 목록 반환
        [원본 이관] OutboundMixin._co_validate_customer_sale_ref()
        Returns: {"ok": bool, "conflicts": []}
        """
        result = {"ok": True, "conflicts": []}
        if not tonbags:
            return result
        try:
            customers = set()
            sale_refs = set()
            for tb in tonbags:
                t = tb if isinstance(tb, dict) else {}
                if t.get('customer'):
                    customers.add(t['customer'])
                if t.get('sale_ref'):
                    sale_refs.add(t['sale_ref'])

            if len(customers) > 1:
                result["ok"] = False
                result["conflicts"].append(f"고객 불일치: {customers}")
            if len(sale_refs) > 1:
                result["ok"] = False
                result["conflicts"].append(f"sale_ref 불일치: {sale_refs}")
        except Exception as e:
            result["ok"] = False
            result["conflicts"].append(str(e))
        return result

    def verify_weight_conservation(self, lot_no: str) -> dict:
        """
        출고 확정 후 무게 보존 검증
        initial_weight == current_weight + picked_weight (±1.0kg 허용)
        [원본 이관] OutboundMixin._co_verify_weight_conservation()
        """
        try:
            lot = self.db.fetchone(
                "SELECT initial_weight, current_weight, picked_weight "
                "FROM inventory WHERE lot_no = ?",
                (lot_no,)
            )
            if not lot:
                return {"ok": False, "error": f"LOT 없음: {lot_no}"}

            _g = lot.get if hasattr(lot, 'get') else lambda k, d=0: lot[{'initial_weight':0,'current_weight':1,'picked_weight':2}[k]]
            initial = float(_g('initial_weight', 0) or 0)
            current = float(_g('current_weight', 0) or 0)
            picked  = float(_g('picked_weight', 0)  or 0)
            diff    = abs(initial - (current + picked))

            if diff > 1.0:
                return {
                    "ok": False,
                    "error": (
                        f"중량 불일치 [{lot_no}]: "
                        f"initial={initial:.2f} ≠ current({current:.2f}) "
                        f"+ picked({picked:.2f}) → diff={diff:.2f}kg"
                    )
                }
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ================================================================
    # 재고 조회
    # ================================================================

    def get_available_tonbags(
        self,
        lot_no: str = None,
        material_code: str = None
    ) -> list:
        """출고 가능(AVAILABLE) 톤백 조회"""
        sql = ("SELECT id, lot_no, sub_lt, weight, tonbag_uid, is_sample "
               "FROM inventory_tonbag WHERE status = 'AVAILABLE'")
        params = []
        if lot_no:
            sql += " AND lot_no = ?"
            params.append(lot_no)
        if material_code:
            sql += " AND lot_no IN (SELECT lot_no FROM inventory WHERE product_code = ?)"
            params.append(material_code)
        try:
            return self.db.fetchall(sql, tuple(params)) or []
        except Exception as e:
            logger.error(f"get_available_tonbags 실패: {e}")
            return []

    def get_lot_tonbag_status_counts(self, lot_no: str) -> dict:
        """
        LOT별 톤백 상태 카운트 집계
        [원본 이관] OutboundMixin._recalc_lot_status() 내부 쿼리
        Returns: {"AVAILABLE": n, "RESERVED": n, "PICKED": n, "OUTBOUND": n, ...}
        """
        try:
            rows = self.db.fetchall(
                "SELECT status, COUNT(*) AS cnt "
                "FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
                (lot_no,)
            ) or []
            cnt_map = {}
            for r in rows:
                st = str(r.get('status', '') if isinstance(r, dict) else r[0]).strip().upper()
                c  = int(r.get('cnt', 0) if isinstance(r, dict) else r[1])
                cnt_map[st] = c
            return cnt_map
        except Exception as e:
            logger.error(f"get_lot_tonbag_status_counts 실패: {e}")
            return {}

    def get_picking_info(self, tonbag_id) -> Optional[dict]:
        """picking_table에서 tonbag 피킹 정보 조회"""
        try:
            row = self.db.fetchone(
                "SELECT id, sales_order_no, picking_no, customer, outbound_id "
                "FROM picking_table WHERE tonbag_id = ? ORDER BY id DESC LIMIT 1",
                (tonbag_id,)
            )
            return dict(row) if row else {}
        except Exception as e:
            logger.debug(f"get_picking_info: {e}")
            return {}

    def get_inventory_info(self, lot_no: str) -> dict:
        """inventory 테이블에서 LOT 기본 정보 조회 (sold_row payload용)"""
        try:
            row = self.db.fetchone(
                "SELECT sap_no, bl_no, product_code, product, gross_weight, "
                "net_weight, mxbg_pallet, sold_to, sale_ref "
                "FROM inventory WHERE lot_no = ?",
                (lot_no,)
            )
            return dict(row) if row else {}
        except Exception as e:
            logger.debug(f"get_inventory_info: {e}")
            return {}

    def get_allocation_info(self, tonbag_id) -> dict:
        """allocation_plan에서 고객/sale_ref fallback 조회"""
        try:
            row = self.db.fetchone(
                "SELECT customer, sale_ref FROM allocation_plan "
                "WHERE tonbag_id = ? ORDER BY id DESC LIMIT 1",
                (tonbag_id,)
            )
            return dict(row) if row else {}
        except Exception as e:
            logger.debug(f"get_allocation_info: {e}")
            return {}

    # ================================================================
    # 사전 검증 (allocation 전)
    # ================================================================

    def preflight_alloc_cols(self) -> dict:
        """
        allocation_plan 테이블 컬럼 존재 확인
        [원본 이관] OutboundMixin._preflight_alloc_cols()
        """
        try:
            rows = self.db.fetchall(
                "PRAGMA table_info(allocation_plan)"
            ) or []
            cols = set()
            for r in rows:
                col_name = r.get('name') if isinstance(r, dict) else r[1]
                if col_name:
                    cols.add(col_name)
            return {"cols": cols, "ok": True}
        except Exception as e:
            return {"cols": set(), "ok": False, "error": str(e)}

    def aggregate_picking_qty(self, picking_rows: list) -> dict:
        """
        피킹 수량 집계 (LOT별)
        [원본 이관] OutboundMixin._g1_aggregate_picking_qty()
        Returns: {lot_no: {"qty": n, "weight": kg}, ...}
        """
        result = {}
        for row in (picking_rows or []):
            r = row if isinstance(row, dict) else {}
            lot = r.get('lot_no', '')
            if lot not in result:
                result[lot] = {"qty": 0, "weight": 0.0}
            result[lot]["qty"] += 1
            result[lot]["weight"] += float(r.get('weight', 0) or 0)
        return result
