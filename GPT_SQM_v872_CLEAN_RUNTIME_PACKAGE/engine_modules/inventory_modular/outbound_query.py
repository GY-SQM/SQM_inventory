# -*- coding: utf-8 -*-
"""
P2 Batch B — OutboundQueryRepository
출고 관련 조회(SELECT) 전용 레포지토리.
outbound_mixin.py에서 분리한 DB 읽기 로직.
"""
import logging
from typing import Dict, List, Optional

from features.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class OutboundQueryRepository(BaseRepository):
    """출고 관련 조회 전용 레포지토리."""

    def table_exists(self, table_name: str) -> bool:
        """테이블 존재 확인."""
        try:
            row = self.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            return bool(row)
        except Exception as exc:
            logger.debug("table_exists(%s) 조회 실패: %s", table_name, exc)
            return False

    def get_outbound_event_log(self, limit: int = 50) -> List[Dict]:
        """출고 이벤트 로그 최근 N건 조회."""
        try:
            rows = self.fetchall(
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

    def get_outbound_status(self, outbound_no: str) -> str:
        """출고번호별 상태 문자열 반환."""
        if not outbound_no:
            return ""
        try:
            row = self.fetchone(
                "SELECT status FROM outbound WHERE outbound_no = ? LIMIT 1",
                (outbound_no,),
            )
            if row:
                return (row.get("status") if isinstance(row, dict) else row[0]) or ""
        except Exception:
            logger.debug("[SUPPRESSED] exception in outbound_query.py")
        return ""

    def has_source_fingerprint_column(self) -> bool:
        """allocation_plan.source_fingerprint 컬럼 존재 여부."""
        try:
            cols = self.get_alloc_plan_cols()
            return "source_fingerprint" in cols
        except Exception as e:
            logger.debug(f"source_fingerprint 컬럼 확인 스킵: {e}")
            return False

    def get_alloc_plan_cols(self) -> set:
        """allocation_plan 테이블 컬럼 집합 조회."""
        try:
            rows = self.fetchall("PRAGMA table_info(allocation_plan)")
            result = set()
            for r in (rows or []):
                if isinstance(r, dict):
                    name = str(r.get("name", "")).strip().lower()
                else:
                    name = str(r[1]).strip().lower() if len(r) > 1 else ""
                if name:
                    result.add(name)
            return result
        except Exception as e:
            logger.debug(f"get_alloc_plan_cols 컬럼 조회 스킵: {e}")
            return set()

    def load_reserved_plans(self, lot_no: str = None, target_date: str = None) -> list:
        """RESERVED 상태 allocation_plan 조회."""
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
        return self.fetchall(query, tuple(params))

    def load_picked_tonbags(self, lot_no: str = None) -> list:
        """PICKED 상태 톤백 조회."""
        from engine_modules.constants import STATUS_PICKED
        query = """SELECT id, lot_no, sub_lt, weight, tonbag_uid FROM inventory_tonbag
                   WHERE status = ?"""
        params = [STATUS_PICKED]
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        return self.fetchall(query, tuple(params))

    def preflight_alloc_cols(self) -> dict:
        """allocation_plan 테이블 컬럼 존재 여부 사전 검사."""
        try:
            cols = self.get_alloc_plan_cols()
            return {
                'cols': cols,
                'has_source': 'source' in cols,
                'has_line_no': 'line_no' in cols,
                'has_export_type': 'export_type' in cols,
                'has_workflow_status': 'workflow_status' in cols,
                'has_fail_code': 'fail_code' in cols,
            }
        except Exception as e:
            logger.debug(f"preflight_alloc_cols 오류: {e}")
            return {
                'cols': set(),
                'has_source': False, 'has_line_no': False,
                'has_export_type': False, 'has_workflow_status': False,
                'has_fail_code': False,
            }

    def get_tonbag_status_counts(self, lot_no: str) -> dict:
        """LOT별 톤백 상태 COUNT 집계."""
        try:
            rows = self.fetchall(
                "SELECT status, COUNT(*) AS cnt "
                "FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
                (lot_no,)
            )
            cnt_map = {}
            for r in (rows or []):
                st = str(r.get('status', '') if isinstance(r, dict) else r[0]).strip().upper()
                c = int(r.get('cnt', 0) if isinstance(r, dict) else r[1])
                cnt_map[st] = c
            return cnt_map
        except Exception as exc:
            logger.warning("톤백 상태 카운트 조회 실패: %s", exc)
            return {}

    def lot_exists_in_db(self, lot_no: str) -> bool:
        """inventory_tonbag에 LOT 존재 여부."""
        row = self.fetchone(
            "SELECT 1 FROM inventory_tonbag WHERE lot_no = ? LIMIT 1",
            (lot_no,)
        )
        return bool(row)
