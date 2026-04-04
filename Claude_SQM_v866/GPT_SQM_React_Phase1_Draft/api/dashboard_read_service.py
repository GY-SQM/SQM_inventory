# -*- coding: utf-8 -*-
"""
SQM React Phase 1 - Dashboard Read Service (Draft)
---------------------------------------------------
조회 전용 대시보드 집계 서비스.

설계 원칙:
1) DB schema 변경 금지
2) business policy 변경 금지
3) read-only 조회 전용
4) React 표시 기준 상태명은 OUTBOUND로 통일
5) legacy SOLD 데이터는 OUTBOUND로 매핑해서 표시

주의:
- 현재 프로젝트는 OUTBOUND가 기준 상태명이나, 기존 데이터/조회 일부에는 SOLD가 남아있을 수 있다.
- 이 서비스는 UI 표시용으로만 SOLD -> OUTBOUND 매핑을 적용한다.
- write-path나 기존 테이블 의미는 변경하지 않는다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine_modules.database import SQMDatabase

logger = logging.getLogger(__name__)


CORE_DISPLAY_STATUSES = ("AVAILABLE", "RESERVED", "PICKED", "OUTBOUND")


class DashboardReadService:
    """SQM 조회 전용 대시보드 서비스 초안."""

    def __init__(self, db: Optional[SQMDatabase] = None) -> None:
        self.db = db or SQMDatabase()

    @staticmethod
    def _now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _fetch_status_rows(self) -> List[Dict[str, Any]]:
        """
        inventory_tonbag 기준 상태별 톤백 수량/중량 조회.

        표시 규칙:
        - SOLD는 legacy 데이터로 간주하고 OUTBOUND로 표시 통합.
        - SHIPPED/DEPLETED 등은 이번 1단계 대시보드 핵심 상태에서 제외.
        """
        sql = """
            SELECT
                CASE
                    WHEN t.status IN ('OUTBOUND', 'SOLD') THEN 'OUTBOUND'
                    WHEN t.status IN ('AVAILABLE', 'RESERVED', 'PICKED') THEN t.status
                    ELSE 'OTHER'
                END AS display_status,
                COUNT(*) AS bag_count,
                COALESCE(SUM(COALESCE(t.weight, 0)), 0) AS weight_kg,
                COALESCE(SUM(CASE WHEN COALESCE(t.is_sample, 0) = 1 THEN 1 ELSE 0 END), 0) AS sample_bag_count
            FROM inventory_tonbag t
            GROUP BY display_status
            ORDER BY display_status
        """
        try:
            rows = self.db.fetchall(sql)
            return rows or []
        except Exception as exc:
            logger.error("_fetch_status_rows 쿼리 실패: %s", exc, exc_info=True)
            return []

    def get_summary(self) -> Dict[str, Any]:
        """상태별 KPI 요약 반환."""
        rows = self._fetch_status_rows()
        status_map: Dict[str, Dict[str, Any]] = {
            status: {
                "status": status,
                "bag_count": 0,
                "weight_kg": 0.0,
                "weight_mt": 0.0,
                "sample_bag_count": 0,
            }
            for status in CORE_DISPLAY_STATUSES
        }

        other_bucket = {
            "status": "OTHER",
            "bag_count": 0,
            "weight_kg": 0.0,
            "weight_mt": 0.0,
            "sample_bag_count": 0,
        }

        for row in rows:
            status = str(row.get("display_status") or "OTHER")
            target = status_map.get(status, other_bucket)
            target["bag_count"] += self._safe_int(row.get("bag_count"))
            target["weight_kg"] += self._safe_float(row.get("weight_kg"))
            target["sample_bag_count"] += self._safe_int(row.get("sample_bag_count"))

        for payload in list(status_map.values()) + [other_bucket]:
            payload["weight_mt"] = round(payload["weight_kg"] / 1000.0, 3)

        items = [status_map[s] for s in CORE_DISPLAY_STATUSES]
        if other_bucket["bag_count"] > 0 or other_bucket["weight_kg"] > 0:
            items.append(other_bucket)

        totals = {
            "bag_count": sum(self._safe_int(x["bag_count"]) for x in items),
            "weight_kg": round(sum(self._safe_float(x["weight_kg"]) for x in items), 3),
            "weight_mt": round(sum(self._safe_float(x["weight_mt"]) for x in items), 3),
            "sample_bag_count": sum(self._safe_int(x["sample_bag_count"]) for x in items),
        }

        return {
            "items": items,
            "totals": totals,
            "generated_at": self._now_str(),
        }

    def get_by_product(self) -> Dict[str, Any]:
        """제품별 상태 요약 반환."""
        sql = """
            SELECT
                COALESCE(NULLIF(TRIM(i.product), ''), 'UNKNOWN') AS product_name,
                SUM(CASE WHEN t.status = 'AVAILABLE' THEN COALESCE(t.weight, 0) ELSE 0 END) AS available_kg,
                SUM(CASE WHEN t.status = 'RESERVED' THEN COALESCE(t.weight, 0) ELSE 0 END) AS reserved_kg,
                SUM(CASE WHEN t.status = 'PICKED' THEN COALESCE(t.weight, 0) ELSE 0 END) AS picked_kg,
                SUM(CASE WHEN t.status IN ('OUTBOUND', 'SOLD') THEN COALESCE(t.weight, 0) ELSE 0 END) AS outbound_kg,
                COUNT(DISTINCT i.lot_no) AS lot_count,
                COUNT(t.id) AS tonbag_count
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON i.lot_no = t.lot_no
            GROUP BY COALESCE(NULLIF(TRIM(i.product), ''), 'UNKNOWN')
            ORDER BY product_name
        """
        try:
            rows = self.db.fetchall(sql) or []
        except Exception as exc:
            logger.error("get_by_product 쿼리 실패: %s", exc, exc_info=True)
            return {"rows": [], "generated_at": self._now_str()}

        normalized: List[Dict[str, Any]] = []
        for row in rows:
            available_kg = self._safe_float(row.get("available_kg"))
            reserved_kg = self._safe_float(row.get("reserved_kg"))
            picked_kg = self._safe_float(row.get("picked_kg"))
            outbound_kg = self._safe_float(row.get("outbound_kg"))
            total_kg = available_kg + reserved_kg + picked_kg + outbound_kg
            normalized.append(
                {
                    "product_name": row.get("product_name") or "UNKNOWN",
                    "lot_count": self._safe_int(row.get("lot_count")),
                    "tonbag_count": self._safe_int(row.get("tonbag_count")),
                    "available_kg": round(available_kg, 3),
                    "reserved_kg": round(reserved_kg, 3),
                    "picked_kg": round(picked_kg, 3),
                    "outbound_kg": round(outbound_kg, 3),
                    "available_mt": round(available_kg / 1000.0, 3),
                    "reserved_mt": round(reserved_kg / 1000.0, 3),
                    "picked_mt": round(picked_kg / 1000.0, 3),
                    "outbound_mt": round(outbound_kg / 1000.0, 3),
                    "total_mt": round(total_kg / 1000.0, 3),
                }
            )

        return {
            "rows": normalized,
            "generated_at": self._now_str(),
        }

    def get_location_summary(self) -> Dict[str, Any]:
        """위치별 간단 요약 반환."""
        sql = """
            SELECT
                COALESCE(NULLIF(TRIM(location), ''), 'UNASSIGNED') AS location,
                COUNT(*) AS bag_count,
                COALESCE(SUM(COALESCE(weight, 0)), 0) AS weight_kg
            FROM inventory_tonbag
            WHERE status IN ('AVAILABLE', 'RESERVED', 'PICKED', 'OUTBOUND', 'SOLD')
            GROUP BY COALESCE(NULLIF(TRIM(location), ''), 'UNASSIGNED')
            ORDER BY location
        """
        try:
            rows = self.db.fetchall(sql) or []
        except Exception as exc:
            logger.error("get_location_summary 쿼리 실패: %s", exc, exc_info=True)
            return {"rows": [], "generated_at": self._now_str()}

        normalized = []
        for row in rows:
            weight_kg = self._safe_float(row.get("weight_kg"))
            normalized.append(
                {
                    "location": row.get("location") or "UNASSIGNED",
                    "bag_count": self._safe_int(row.get("bag_count")),
                    "weight_kg": round(weight_kg, 3),
                    "weight_mt": round(weight_kg / 1000.0, 3),
                }
            )
        return {
            "rows": normalized,
            "generated_at": self._now_str(),
        }
