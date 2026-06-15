# -*- coding: utf-8 -*-
"""
SQM Inventory Engine - Shipment Mixin
=====================================

v2.9.91 - Extracted from inventory.py

Shipment document processing (parse, preview, process)
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ShipmentMixin:
    """
    Shipment processing mixin

    Methods for PDF document parsing and shipment inbound
    """

    def get_shipment_list(self) -> List[Dict]:
        """
        Get shipment list

        Returns:
            List of shipment records
        """
        query = """
            SELECT
                id, sap_no, bl_no, folio, product,
                total_net_weight, total_gross_weight, ship_date, arrival_date,
                status, created_at
            FROM shipment
            ORDER BY created_at DESC
        """
        return self.db.fetchall(query)

    def get_shipment_integrity_summary(self, sap_no: str) -> Dict[str, Any]:
        """
        C10: 선적(SAP) 기준 선적↔재고 최소 정합성 요약.

        Shipment 테이블의 total_net_weight와 같은 sap_no로 입고된 inventory
        initial_weight 합계를 비교해 선적-재고 흐름의 공백을 API/테스트에서
        확인할 수 있게 한다. 이 메서드는 데이터를 변경하지 않는다.
        """
        sap_no = str(sap_no or "").strip()
        result: Dict[str, Any] = {
            "ok": False,
            "valid": False,
            "shipment": None,
            "inventory": {
                "lot_count": 0,
                "inventory_net_weight": 0.0,
                "inventory_current_weight": 0.0,
                "lots": [],
            },
            "errors": [],
            "warnings": [],
        }
        if not sap_no:
            result["errors"].append("SAP 번호 없음")
            return result

        shipment = self.db.fetchone(
            """
            SELECT id, sap_no, bl_no, folio, product,
                   total_net_weight, total_gross_weight, ship_date, arrival_date,
                   status, created_at
            FROM shipment
            WHERE sap_no = ?
            """,
            (sap_no,),
        )
        if not shipment:
            result["errors"].append(f"선적 없음: {sap_no}")
            return result

        summary = self.db.fetchone(
            """
            SELECT COUNT(*) AS lot_count,
                   COALESCE(SUM(initial_weight), 0) AS inventory_net_weight,
                   COALESCE(SUM(current_weight), 0) AS inventory_current_weight
            FROM inventory
            WHERE sap_no = ?
            """,
            (sap_no,),
        ) or {}
        lots = self.db.fetchall(
            """
            SELECT lot_no, sap_no, bl_no, initial_weight, current_weight,
                   picked_weight, status
            FROM inventory
            WHERE sap_no = ?
            ORDER BY lot_no
            """,
            (sap_no,),
        )

        shipment_net = float(shipment.get("total_net_weight") or 0)
        inventory_net = float(summary.get("inventory_net_weight") or 0)
        lot_count = int(summary.get("lot_count") or 0)

        result.update({
            "ok": True,
            "valid": True,
            "shipment": dict(shipment),
            "inventory": {
                "lot_count": lot_count,
                "inventory_net_weight": inventory_net,
                "inventory_current_weight": float(summary.get("inventory_current_weight") or 0),
                "lots": [dict(row) for row in lots],
            },
        })

        if lot_count == 0:
            result["warnings"].append(f"선적 {sap_no}에 연결된 재고 LOT 없음")

        diff = abs(shipment_net - inventory_net)
        if diff > 1.0:
            result["valid"] = False
            result["errors"].append(
                f"선적-재고 중량 불일치: shipment({shipment_net:.1f}kg) ≠ "
                f"inventory({inventory_net:.1f}kg), 차이={diff:.1f}kg"
            )

        logger.info(
            "[C10] shipment integrity sap_no=%s valid=%s lots=%s diff=%.1fkg",
            sap_no,
            result["valid"],
            lot_count,
            diff,
        )
        return result

    # NOTE: get_shipment_detail → 미호출로 삭제 (v3.8.4 데드코드 정리)
