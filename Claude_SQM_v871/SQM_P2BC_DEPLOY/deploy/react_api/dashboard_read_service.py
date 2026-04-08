# -*- coding: utf-8 -*-
"""
DashboardReadService — get_summary에 con_return_critical 추가
배치: react_api/dashboard_read_service.py (기존 덮어쓰기)
★ 변경: get_summary() 반환값에 con_return_critical/warning 카운트 + 목록 추가
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from engine_modules.database import SQMDatabase
from react_api.utils.status_normalizer import normalize_display_status

logger = logging.getLogger(__name__)

CORE_DISPLAY_STATUSES = [
    "AVAILABLE", "RESERVED", "PICKED", "OUTBOUND", "PARTIAL", "DEPLETED"
]

CON_RETURN_CRIT_DAYS = 3
CON_RETURN_WARN_DAYS = 7


class DashboardReadService:

    def __init__(self, db: Optional[SQMDatabase] = None) -> None:
        self.db = db

    @staticmethod
    def _now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return round(float(value or 0), 3)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _fetch_status_rows(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT
                CASE
                    WHEN t.status IN ('OUTBOUND','SOLD') THEN 'OUTBOUND'
                    ELSE COALESCE(t.status, 'OTHER')
                END AS display_status,
                COUNT(*)                          AS bag_count,
                COALESCE(SUM(t.weight), 0)        AS weight_kg,
                COUNT(CASE WHEN t.is_sample = 1 THEN 1 END) AS sample_bag_count
            FROM inventory_tonbag t
            GROUP BY display_status
        """
        return self.db.fetchall(sql) or []

    # ================================================================
    # ★ con_return 임박 LOT 조회
    # ================================================================
    def _fetch_con_return_alerts(self) -> Dict[str, Any]:
        today   = datetime.now().date()
        today_s = today.strftime('%Y-%m-%d')
        warn_s  = (today + timedelta(days=CON_RETURN_WARN_DAYS)).strftime('%Y-%m-%d')
        crit_s  = (today + timedelta(days=CON_RETURN_CRIT_DAYS)).strftime('%Y-%m-%d')

        try:
            rows = self.db.fetchall(
                """SELECT lot_no, con_return,
                          COALESCE(container_no,'') AS container_no,
                          COALESCE(warehouse,'') AS warehouse
                   FROM inventory
                   WHERE con_return IS NOT NULL
                     AND con_return != ''
                     AND con_return >= ?
                     AND con_return <= ?
                     AND status NOT IN ('OUTBOUND','SOLD','DEPLETED')
                   ORDER BY con_return""",
                (today_s, warn_s)
            ) or []
        except Exception as e:
            logger.warning(f"con_return 조회 실패: {e}")
            return {"critical": 0, "warning": 0, "alerts": []}

        alerts = []
        critical_count = 0
        warning_count  = 0

        for r in rows:
            lot_no  = r.get('lot_no')  if hasattr(r,'keys') else r[0]
            cr      = r.get('con_return') if hasattr(r,'keys') else r[1]
            cnt     = r.get('container_no') if hasattr(r,'keys') else r[2]
            wh      = r.get('warehouse') if hasattr(r,'keys') else r[3]

            try:
                days_left = (datetime.strptime(cr, '%Y-%m-%d').date() - today).days
            except Exception:
                continue

            is_crit = cr <= crit_s
            if is_crit:
                critical_count += 1
            else:
                warning_count += 1

            alerts.append({
                "lot_no":       lot_no or "",
                "con_return":   cr,
                "days_left":    days_left,
                "container_no": cnt or "",
                "warehouse":    wh  or "",
                "is_critical":  is_crit,
            })

        return {
            "critical": critical_count,
            "warning":  warning_count,
            "alerts":   alerts[:20],  # 최대 20건
        }

    # ================================================================
    # get_summary — ★ con_return 필드 추가
    # ================================================================
    def get_summary(self) -> Dict[str, Any]:
        rows = self._fetch_status_rows()
        status_map = {
            s: {"status": s, "bag_count": 0, "weight_kg": 0.0,
                "weight_mt": 0.0, "sample_bag_count": 0}
            for s in CORE_DISPLAY_STATUSES
        }
        other_bucket = {
            "status": "OTHER", "bag_count": 0, "weight_kg": 0.0,
            "weight_mt": 0.0, "sample_bag_count": 0,
        }

        for row in rows:
            status = str(row.get("display_status") if hasattr(row,'keys') else row[0] or "OTHER")
            target = status_map.get(status, other_bucket)
            target["bag_count"]       += self._safe_int(row.get("bag_count") if hasattr(row,'keys') else row[1])
            target["weight_kg"]       += self._safe_float(row.get("weight_kg") if hasattr(row,'keys') else row[2])
            target["sample_bag_count"]+= self._safe_int(row.get("sample_bag_count") if hasattr(row,'keys') else row[3])

        for payload in list(status_map.values()) + [other_bucket]:
            payload["weight_mt"] = round(payload["weight_kg"] / 1000.0, 3)

        items = [status_map[s] for s in CORE_DISPLAY_STATUSES]
        if other_bucket["bag_count"] > 0 or other_bucket["weight_kg"] > 0:
            items.append(other_bucket)

        totals = {
            "bag_count":       sum(self._safe_int(x["bag_count"]) for x in items),
            "weight_kg":       round(sum(self._safe_float(x["weight_kg"]) for x in items), 3),
            "weight_mt":       round(sum(self._safe_float(x["weight_mt"]) for x in items), 3),
            "sample_bag_count":sum(self._safe_int(x["sample_bag_count"]) for x in items),
        }

        # ★ Q3: con_return 임박 데이터 추가
        cr_data = self._fetch_con_return_alerts()

        return {
            "items":                     items,
            "totals":                    totals,
            "generated_at":              self._now_str(),
            "con_return_critical_count": cr_data["critical"],
            "con_return_warning_count":  cr_data["warning"],
            "con_return_alerts":         cr_data["alerts"],
        }

    def get_by_product(self) -> Dict[str, Any]:
        sql = """
            SELECT
                COALESCE(i.product, '(Unknown)') AS product_name,
                COUNT(DISTINCT i.lot_no) AS lot_count,
                COUNT(t.id) AS tonbag_count,
                COALESCE(SUM(CASE WHEN t.status='AVAILABLE' THEN t.weight ELSE 0 END),0) AS available_kg,
                COALESCE(SUM(CASE WHEN t.status='RESERVED'  THEN t.weight ELSE 0 END),0) AS reserved_kg,
                COALESCE(SUM(CASE WHEN t.status='PICKED'    THEN t.weight ELSE 0 END),0) AS picked_kg,
                COALESCE(SUM(CASE WHEN t.status IN ('OUTBOUND','SOLD') THEN t.weight ELSE 0 END),0) AS outbound_kg
            FROM inventory i
            LEFT JOIN inventory_tonbag t ON t.lot_no = i.lot_no
            GROUP BY i.product
            ORDER BY available_kg DESC
        """
        rows = self.db.fetchall(sql) or []

        def _row(r):
            def _g(i, k): return r.get(k) if hasattr(r,'keys') else r[i]
            avail = self._safe_float(_g(3,'available_kg'))
            resv  = self._safe_float(_g(4,'reserved_kg'))
            pick  = self._safe_float(_g(5,'picked_kg'))
            outb  = self._safe_float(_g(6,'outbound_kg'))
            total = avail + resv + pick + outb
            return {
                "product_name": _g(0,'product_name') or "(Unknown)",
                "lot_count":    self._safe_int(_g(1,'lot_count')),
                "tonbag_count": self._safe_int(_g(2,'tonbag_count')),
                "available_kg": avail, "reserved_kg": resv,
                "picked_kg":    pick,  "outbound_kg": outb,
                "available_mt": round(avail/1000,3), "reserved_mt": round(resv/1000,3),
                "picked_mt":    round(pick/1000,3),  "outbound_mt": round(outb/1000,3),
                "total_mt":     round(total/1000,3),
            }

        return {"rows": [_row(r) for r in rows], "generated_at": self._now_str()}

    def get_location_summary(self) -> Dict[str, Any]:
        sql = """
            SELECT
                COALESCE(NULLIF(TRIM(location),''), '(미지정)') AS location,
                COUNT(*)              AS bag_count,
                COALESCE(SUM(weight), 0) AS weight_kg
            FROM inventory_tonbag
            WHERE status NOT IN ('OUTBOUND','SOLD','DEPLETED')
            GROUP BY location
            ORDER BY bag_count DESC
        """
        rows = self.db.fetchall(sql) or []

        def _row(r):
            wk = self._safe_float(r.get('weight_kg') if hasattr(r,'keys') else r[2])
            return {
                "location":  r.get('location') if hasattr(r,'keys') else r[0],
                "bag_count": self._safe_int(r.get('bag_count') if hasattr(r,'keys') else r[1]),
                "weight_kg": wk,
                "weight_mt": round(wk/1000, 3),
            }

        return {"rows": [_row(r) for r in rows], "generated_at": self._now_str()}
