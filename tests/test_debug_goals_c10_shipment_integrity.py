# -*- coding: utf-8 -*-
"""C10 회귀 테스트 — shipment_mixin 선적↔재고 정합 최소 흐름."""
from engine_modules.inventory_modular.shipment_mixin import ShipmentMixin


class FakeDB:
    def __init__(self):
        self.queries = []

    def fetchone(self, query, params=()):
        self.queries.append((query, params))
        if "FROM shipment" in query:
            return {
                "id": 1,
                "sap_no": "SAP-1",
                "bl_no": "BL-1",
                "folio": "F-1",
                "product": "LITHIUM CARBONATE",
                "total_net_weight": 1001.0,
                "total_gross_weight": 1020.0,
                "ship_date": "2026-06-01",
                "arrival_date": "2026-06-10",
                "status": "ARRIVED",
            }
        if "COUNT(*)" in query:
            return {"lot_count": 1, "inventory_net_weight": 900.0, "inventory_current_weight": 900.0}
        raise AssertionError(query)

    def fetchall(self, query, params=()):
        self.queries.append((query, params))
        return [
            {
                "lot_no": "LOT-1",
                "sap_no": "SAP-1",
                "bl_no": "BL-1",
                "initial_weight": 900.0,
                "current_weight": 900.0,
                "picked_weight": 0.0,
                "status": "AVAILABLE",
            }
        ]


class Engine(ShipmentMixin):
    def __init__(self):
        self.db = FakeDB()


def test_get_shipment_integrity_summary_reports_weight_mismatch():
    result = Engine().get_shipment_integrity_summary("SAP-1")

    assert result["ok"] is True
    assert result["shipment"]["sap_no"] == "SAP-1"
    assert result["inventory"]["lot_count"] == 1
    assert result["inventory"]["lots"][0]["lot_no"] == "LOT-1"
    assert result["valid"] is False
    assert result["errors"]
    assert "선적-재고 중량 불일치" in result["errors"][0]


def test_get_shipment_integrity_summary_missing_shipment_is_explicit():
    class EmptyDB(FakeDB):
        def fetchone(self, query, params=()):
            if "FROM shipment" in query:
                return None
            return super().fetchone(query, params)

    class EmptyEngine(ShipmentMixin):
        def __init__(self):
            self.db = EmptyDB()

    result = EmptyEngine().get_shipment_integrity_summary("NO-SAP")

    assert result["ok"] is False
    assert result["valid"] is False
    assert result["errors"] == ["선적 없음: NO-SAP"]
