"""
OutboundService — Outbound 처리 전체 파이프라인 (S6 Transaction 정리 완료)
★ SQMDatabase.transaction("IMMEDIATE") 컨텍스트 매니저 일관 적용
★ 수동 commit()/rollback() 제거 → with self.db.transaction() 으로 통일
분리일: 2026-04-08 | SQM v8.7.1
"""
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

from .outbound_query import OutboundQuery
from .outbound_repository import OutboundRepository
from .outbound_state_rules import OutboundStateRules, TonbagStatus

# ★ Q3: QueryCache 무효화 — confirm/execute 후 대시보드 즉시 반영
try:
    from engine_modules.query_cache import cache as _qcache
    _CACHE_OK = True
except ImportError:
    _qcache   = None
    _CACHE_OK = False


def _invalidate_dashboard_cache():
    """출고/예약 변경 후 대시보드 캐시 즉시 무효화"""
    if not _CACHE_OK:
        return
    try:
        _qcache.invalidate_table("inventory_tonbag")
        _qcache.invalidate_table("sold_table")
        _qcache.invalidate_table("allocation_plan")
        logger.debug("대시보드 캐시 무효화 완료")
    except Exception as e:
        logger.debug(f"캐시 무효화 스킵: {e}")

logger = logging.getLogger(__name__)


class OutboundService:
    """
    Outbound 처리 파이프라인 — UI(outbound_handlers.py)는 이 클래스만 호출

    실제 흐름 (v8.7.1):
      execute_reserved()       RESERVED → PICKED
      confirm_outbound()       PICKED   → OUTBOUND
      revert_picked_to_reserved() PICKED → RESERVED  (롤백)
      revert_outbound_to_available() OUTBOUND → AVAILABLE (취소)
      cancel_reservation()     RESERVED → CANCELLED
    """

    def __init__(self, db):
        """Args: db — SQMDatabase 인스턴스"""
        self.db    = db
        self.query = OutboundQuery(db)
        self.repo  = OutboundRepository(db)

    # ================================================================
    # RESERVED → PICKED 파이프라인
    # ================================================================

    def execute_reserved(
        self,
        lot_no: str = None,
        target_date: str = None
    ) -> Dict:
        """
        RESERVED 톤백을 PICKED로 전환
        [원본 이관] OutboundMixin.execute_reserved()

        ★ Transaction: with self.db.transaction("IMMEDIATE") — All-or-Nothing
        """
        result = {"success": False, "executed": 0, "errors": [], "warnings": []}
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            # 1) RESERVED plans 로드 (트랜잭션 밖에서 조회)
            plans = self.query.load_reserved_plans(lot_no, target_date)
            stale = self.query.warn_stale_plans(plans)
            if stale:
                result["warnings"].append(f"만료 예약 {len(stale)}건 포함")
            if not plans:
                result["errors"].append("실행할 RESERVED 예약이 없습니다.")
                return result

            # 2) All-or-Nothing 트랜잭션
            with self.db.transaction("IMMEDIATE"):
                for plan in plans:
                    plan_d = self._normalize_plan(plan)
                    tb_id  = plan_d.get('tonbag_id')

                    if not tb_id:
                        result["errors"].append(
                            f"plan_id={plan_d.get('id')}: tonbag_id 없음 (LOT 모드)"
                        )
                        continue

                    # 톤백 중량 조회
                    tb_row    = self.db.fetchone(
                        "SELECT weight, tonbag_uid FROM inventory_tonbag WHERE id = ?",
                        (tb_id,)
                    )
                    tb_weight = float(
                        (tb_row.get('weight') if isinstance(tb_row, dict) else tb_row[0]) or 0
                    ) if tb_row else 0.0
                    uid = (
                        (tb_row.get('tonbag_uid') if isinstance(tb_row, dict) else tb_row[1])
                        or ''
                    ) if tb_row else ''

                    # 상태전이 실행
                    r1 = self.repo.apply_pick_transition(plan_d, tb_weight, now)
                    if not r1["ok"]:
                        result["errors"].append(f"plan_id={plan_d.get('id')}: {r1['error']}")
                        continue

                    self.repo.record_pick_movement(plan_d, tb_weight, now)
                    self.repo.insert_picking_row(plan_d, tb_weight, uid, now)
                    self.repo.recalc_lot_status(plan_d.get('lot_no', ''))
                    result["executed"] += 1

            result["success"] = result["executed"] > 0

        except Exception as e:
            logger.error(f"execute_reserved 예외: {e}", exc_info=True)
            result["errors"].append(f"execute_reserved 오류: {str(e)}")

        # ★ Q3: 예약 실행 성공 시 캐시 무효화
        if result.get("success"):
            _invalidate_dashboard_cache()

        return result

    # ================================================================
    # PICKED → OUTBOUND 파이프라인
    # ================================================================

    def confirm_outbound(
        self,
        lot_no: str = None,
        force_all: bool = False
    ) -> Dict:
        """
        PICKED → OUTBOUND 확정
        [원본 이관] OutboundMixin.confirm_outbound()

        ★ Transaction: with self.db.transaction("IMMEDIATE") — All-or-Nothing
        ★ force_all=True 없이 lot_no=None 호출 시 hard-stop
        """
        result = {"success": False, "confirmed": 0, "errors": [], "warnings": []}
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # [H1] 전체 확정 안전장치
        if not lot_no and not force_all:
            msg = ("[CONFIRM_ALL_BLOCKED] lot_no 미지정 전체 확정은 "
                   "force_all=True 명시 필수 — 실수 호출 차단")
            logger.error(msg)
            result["errors"].append(msg)
            return result

        try:
            # 1) PICKED 톤백 로드 (트랜잭션 밖에서 조회)
            tonbags = self.query.load_picked_tonbags(lot_no)
            if not tonbags:
                result["errors"].append("확정할 PICKED 톤백이 없습니다.")
                return result

            tb_list = [self._normalize_tonbag(tb) for tb in tonbags]

            # 2) 이중 출고 차단 (트랜잭션 밖에서 사전 확인)
            already_sold = self.query.guard_against_double_outbound(tb_list)
            if already_sold:
                result["errors"].append(f"이중 출고 차단: tonbag_id {already_sold}")
                return result

            # 3) 고객/sale_ref 검증
            cv = self.query.validate_customer_sale_ref(tb_list)
            if not cv["ok"]:
                result["warnings"].extend(cv["conflicts"])

            touched_lots = set()

            # 4) All-or-Nothing 트랜잭션
            with self.db.transaction("IMMEDIATE"):
                for tb in tb_list:
                    tb_id = tb.get('id')

                    # 이중 sold 재확인 (트랜잭션 내)
                    if self.query.check_double_sold(tb_id):
                        result["errors"].append(f"tonbag_id={tb_id}: 이미 출고 완료 — 스킵")
                        continue

                    # sold_table INSERT
                    r1 = self.repo.insert_sold_row(tb, now)
                    if not r1["ok"]:
                        result["errors"].append(
                            f"tonbag_id={tb_id}: sold INSERT 실패 — {r1['error']}"
                        )
                        continue

                    # tonbag 상태 OUTBOUND 변경
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status = 'OUTBOUND', updated_at = ? "
                        "WHERE id = ?",
                        (now, tb_id)
                    )
                    self.repo.insert_outbound_movement(tb, now)
                    touched_lots.add(tb.get('lot_no', ''))
                    result["confirmed"] += 1

                # 5) LOT 상태 재계산
                for lot in touched_lots:
                    self.repo.recalc_lot_status(lot)

            # 6) 중량 보존 검증 (트랜잭션 후)
            for lot in touched_lots:
                wv = self.query.verify_weight_conservation(lot)
                if not wv["ok"]:
                    result["warnings"].append(wv["error"])

            result["success"] = result["confirmed"] > 0 and not result["errors"]

            # ★ Q3: 출고 확정 성공 시 대시보드 캐시 즉시 무효화
            if result["success"]:
                _invalidate_dashboard_cache()

        except Exception as e:
            logger.error(f"confirm_outbound 예외: {e}", exc_info=True)
            result["errors"].append(f"confirm_outbound 오류: {str(e)}")

        return result

    # ================================================================
    # 롤백 파이프라인 — PICKED → RESERVED
    # ================================================================

    def revert_picked_to_reserved(self, lot_no: str = None) -> Dict:
        """
        판매화물 결정 취소: PICKED → RESERVED 복귀
        allocation_plan EXECUTED → RESERVED
        inventory current_weight 복구 (차감 역산)
        [원본 이관] OutboundMixin.revert_picked_to_reserved()

        ★ Transaction: with self.db.transaction("IMMEDIATE")
        """
        result = {"success": False, "reverted": 0, "errors": []}
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            # EXECUTED 상태 plan 조회
            query = "SELECT id, lot_no, tonbag_id FROM allocation_plan WHERE status = 'EXECUTED'"
            params = []
            if lot_no:
                query += " AND lot_no = ?"
                params.append(lot_no)

            rows = self.db.fetchall(query, tuple(params))
            if not rows:
                result["message"] = "되돌릴 판매화물 결정(EXECUTED) 건이 없습니다."
                return result

            with self.db.transaction("IMMEDIATE"):
                for r in rows:
                    r_d = dict(r) if hasattr(r, 'keys') else {
                        "id": r[0], "lot_no": r[1], "tonbag_id": r[2]
                    }
                    tb_id = r_d.get('tonbag_id')

                    # 톤백 중량 조회
                    tb_row = self.db.fetchone(
                        "SELECT weight FROM inventory_tonbag WHERE id = ?", (tb_id,)
                    )
                    tb_w = float(
                        (tb_row.get('weight') if isinstance(tb_row, dict) else tb_row[0]) or 0
                    ) if tb_row else 0.0

                    # allocation_plan EXECUTED → RESERVED
                    self.db.execute(
                        "UPDATE allocation_plan SET status = 'RESERVED', executed_at = NULL "
                        "WHERE id = ?",
                        (r_d['id'],)
                    )

                    # tonbag PICKED → RESERVED
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status = 'RESERVED', "
                        "picked_date = NULL, updated_at = ? WHERE id = ?",
                        (now, tb_id)
                    )

                    # inventory current_weight 복구
                    if tb_w > 0 and r_d.get('lot_no'):
                        self.db.execute(
                            """UPDATE inventory SET
                               current_weight = current_weight + ?,
                               picked_weight  = MAX(0, picked_weight - ?),
                               updated_at     = ?
                            WHERE lot_no = ?""",
                            (tb_w, tb_w, now, r_d['lot_no'])
                        )

                    # stock_movement 이력
                    self.db.execute(
                        "INSERT INTO stock_movement "
                        "(lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_PICKED', ?, ?, ?)",
                        (r_d['lot_no'], tb_w,
                         f"plan_id={r_d['id']}, PICKED→RESERVED", now)
                    )

                    self.repo.recalc_lot_status(r_d.get('lot_no', ''))
                    result["reverted"] += 1

            result["success"] = True
            result["message"] = (
                f"판매화물 결정 취소: {result['reverted']}건 → RESERVED 복귀"
            )

        except Exception as e:
            logger.error(f"revert_picked_to_reserved 오류: {e}")
            result["errors"].append(str(e))

        return result

    # ================================================================
    # 롤백 파이프라인 — OUTBOUND → AVAILABLE (출고 취소)
    # ================================================================

    def revert_outbound_to_available(self, lot_no: str = None) -> Dict:
        """
        출고 취소: OUTBOUND/SOLD → AVAILABLE 직접 복귀
        ★ v6.8.5 설계 원칙: PICKED 경유 없이 바로 AVAILABLE
        sold_table 삭제 + allocation_plan EXECUTED→CANCELLED + inventory 복구
        [원본 이관] OutboundMixin.revert_sold_to_picked()

        ★ Transaction: with self.db.transaction("IMMEDIATE")
        """
        result = {"success": False, "reverted": 0, "errors": []}
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            # OUTBOUND/SOLD 톤백 조회
            sql = ("SELECT id, lot_no, weight FROM inventory_tonbag "
                   "WHERE status IN ('OUTBOUND', 'SOLD')")
            params = []
            if lot_no:
                sql += " AND lot_no = ?"
                params.append(lot_no)

            tonbags = self.db.fetchall(sql, tuple(params))
            if not tonbags:
                result["message"] = "되돌릴 출고(OUTBOUND) 톤백이 없습니다."
                return result

            touched_lots = set()

            with self.db.transaction("IMMEDIATE"):
                for tb in tonbags:
                    tb_d = dict(tb) if hasattr(tb, 'keys') else {
                        "id": tb[0], "lot_no": tb[1], "weight": tb[2]
                    }
                    tb_id = tb_d["id"]
                    tb_w  = float(tb_d.get("weight") or 0)

                    # ★ OUTBOUND → AVAILABLE 직접 복귀
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status = 'AVAILABLE', "
                        "outbound_date = NULL, picked_date = NULL, updated_at = ? "
                        "WHERE id = ?",
                        (now, tb_id)
                    )

                    # sold_table 삭제
                    try:
                        self.db.execute(
                            "DELETE FROM sold_table WHERE tonbag_id = ?", (tb_id,)
                        )
                    except Exception as e:
                        logger.debug(f"sold_table DELETE 무시: {e}")

                    # allocation_plan EXECUTED → CANCELLED
                    try:
                        # cancelled_at 컬럼 존재 여부 확인
                        alloc_cols = {
                            str(r.get('name', '') if isinstance(r, dict) else r[1]).lower()
                            for r in (self.db.fetchall(
                                "PRAGMA table_info(allocation_plan)"
                            ) or [])
                        }
                        if 'cancelled_at' in alloc_cols:
                            self.db.execute(
                                "UPDATE allocation_plan SET status = 'CANCELLED', "
                                "cancelled_at = ? WHERE tonbag_id = ? AND status = 'EXECUTED'",
                                (now, tb_id)
                            )
                        else:
                            self.db.execute(
                                "UPDATE allocation_plan SET status = 'CANCELLED' "
                                "WHERE tonbag_id = ? AND status = 'EXECUTED'",
                                (tb_id,)
                            )
                    except Exception as e:
                        logger.warning(f"allocation_plan CANCEL 실패 tb_id={tb_id}: {e}")

                    # inventory 무게 복구
                    if tb_w > 0 and tb_d.get('lot_no'):
                        try:
                            self.db.execute(
                                """UPDATE inventory SET
                                   current_weight = current_weight + ?,
                                   picked_weight  = MAX(0, picked_weight - ?),
                                   updated_at     = ?
                                WHERE lot_no = ?""",
                                (tb_w, tb_w, now, tb_d['lot_no'])
                            )
                        except Exception as e:
                            logger.warning(f"inventory 무게복구 실패: {e}")

                    # stock_movement 이력
                    self.db.execute(
                        "INSERT INTO stock_movement "
                        "(lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_SOLD', ?, ?, ?)",
                        (tb_d.get('lot_no', ''), tb_w,
                         f"tonbag_id={tb_id}, OUTBOUND→AVAILABLE", now)
                    )

                    touched_lots.add(tb_d.get('lot_no', ''))
                    result["reverted"] += 1

                # LOT 상태 재계산
                for lot in touched_lots:
                    self.repo.recalc_lot_status(lot)

            result["success"] = True
            result["message"] = (
                f"출고 취소: {result['reverted']}건 → AVAILABLE 복귀"
            )

        except Exception as e:
            logger.error(f"revert_outbound_to_available 오류: {e}")
            result["errors"].append(str(e))

        return result

    # ================================================================
    # 취소 파이프라인 — RESERVED → CANCELLED
    # ================================================================

    def cancel_reservation(self, plan_ids: list, reason: str = '') -> Dict:
        """
        allocation_plan 취소 — RESERVED → CANCELLED
        [원본 이관] OutboundMixin.cancel_reservation() 일부
        ★ Transaction: with self.db.transaction("IMMEDIATE")
        """
        if not plan_ids:
            return {"ok": True, "cancelled": 0, "errors": []}
        try:
            with self.db.transaction("IMMEDIATE"):
                result = self.repo.cancel_allocation_plan(plan_ids, reason)
            return result
        except Exception as e:
            logger.error(f"cancel_reservation 예외: {e}")
            return {"ok": False, "cancelled": 0, "errors": [str(e)]}

    # ================================================================
    # 사전 검증
    # ================================================================

    def validate_before_confirm(self, lot_no: str = None) -> Dict:
        """confirm_outbound 실행 전 사전 검증 (트랜잭션 없음 — 조회만)"""
        result = {"ok": True, "errors": [], "warnings": []}
        try:
            tonbags = self.query.load_picked_tonbags(lot_no)
            if not tonbags:
                result["ok"] = False
                result["errors"].append("PICKED 톤백이 없습니다.")
                return result

            tb_list  = [self._normalize_tonbag(tb) for tb in tonbags]
            already  = self.query.guard_against_double_outbound(tb_list)
            if already:
                result["ok"] = False
                result["errors"].append(f"이중 출고 위험: {already}")

            cv = self.query.validate_customer_sale_ref(tb_list)
            if not cv["ok"]:
                result["warnings"].extend(cv["conflicts"])

            reserved = self.query.load_reserved_plans(lot_no)
            stale    = self.query.warn_stale_plans(reserved)
            if stale:
                result["warnings"].append(f"만료 예약 {len(stale)}건 존재")

        except Exception as e:
            result["ok"] = False
            result["errors"].append(str(e))
        return result

    # ================================================================
    # 대시보드
    # ================================================================

    def get_dashboard(self, lot_no: str = None) -> Dict:
        """대시보드용 상태별 집계 (조회만 — 트랜잭션 없음)"""
        try:
            reserved = self.query.load_reserved_plans(lot_no)
            picked   = self.query.load_picked_tonbags(lot_no)
            events   = self.query.get_outbound_event_log(limit=10)
            stale    = self.query.warn_stale_plans(reserved)
            return {
                "reserved_count": len(reserved),
                "picked_count":   len(picked),
                "stale_count":    len(stale),
                "recent_events":  events,
                "error": None
            }
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # 내부 헬퍼
    # ================================================================

    @staticmethod
    def _normalize_plan(plan) -> dict:
        """allocation_plan row → dict 정규화"""
        if hasattr(plan, 'keys'):
            return dict(plan)
        return {
            "id": plan[0], "lot_no": plan[1], "tonbag_id": plan[2],
            "sub_lt": plan[3], "customer": plan[4],
            "sale_ref": plan[5], "outbound_date": plan[6]
        }

    @staticmethod
    def _normalize_tonbag(tb) -> dict:
        """inventory_tonbag row → dict 정규화"""
        if hasattr(tb, 'keys'):
            return dict(tb)
        keys = ["id", "lot_no", "sub_lt", "weight", "tonbag_uid",
                "status", "is_sample", "customer", "sale_ref"]
        return {k: (tb[i] if i < len(tb) else None) for i, k in enumerate(keys)}
