# -*- coding: utf-8 -*-
"""
SQM Inventory Engine - Shipment Mixin
=====================================

v2.9.91 - Extracted from inventory.py

Shipment document processing (parse, preview, process)
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class ShipmentMixin:
    """
    Shipment processing mixin
    
    Methods for PDF document parsing and shipment inbound
    """
    
    def _convert_packing_result(self, pl_result, pdf_path: str) -> dict:
        """Convert parser result to PackingListData format"""
        from parsers.pdf_parser import PackingListData
        
        packing_data = PackingListData()
        packing_data.source_file = pdf_path
        packing_data.folio = pl_result.folio
        packing_data.product = pl_result.product
        packing_data.product_code = getattr(pl_result, 'code', '')
        packing_data.vessel = pl_result.vessel
        packing_data.customer = pl_result.customer
        packing_data.destination = pl_result.destination
        
        packing_data.lots = []
        for lot in pl_result.lots:
            packing_data.lots.append({
                'lot_no': getattr(lot, 'lot_no', ''),
                'container_no': getattr(lot, 'container_no', ''),
                'net_weight': getattr(lot, 'net_weight_kg', 0) or getattr(lot, 'net_weight', 0),
                'gross_weight': getattr(lot, 'gross_weight_kg', 0) or getattr(lot, 'gross_weight', 0),
                'mxbg_pallet': getattr(lot, 'mxbg', 10) or 10,
                'plastic_jars': 1,
            })
        
        packing_data.total_lots = len(packing_data.lots)
        packing_data.total_net_weight = sum(lot['net_weight'] for lot in packing_data.lots)
        
        return packing_data
    
    def get_shipment_list(self) -> List[Dict]:
        """
        Get shipment list
        
        Returns:
            List of shipment records
        """
        query = """
            SELECT 
                id, sap_no, bl_no, folio, product,
                total_qty_mt, total_lots, ship_date, arrival_date,
                status, created_at
            FROM shipment
            ORDER BY created_at DESC
        """
        return self.db.fetchall(query)
    

    # NOTE: get_shipment_detail → 미호출로 삭제 (v3.8.4 데드코드 정리)
