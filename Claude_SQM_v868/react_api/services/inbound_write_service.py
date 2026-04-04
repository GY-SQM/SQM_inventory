# -*- coding: utf-8 -*-
"""입고 쓰기 서비스 — engine_modules.InboundMixin.process_inbound() 래퍼."""
import logging
from typing import Dict

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
from react_api.schemas.write_models import InboundCreateRequest

logger = logging.getLogger(__name__)


def create_inbound(engine: SQMInventoryEngineV3, req: InboundCreateRequest) -> Dict:
    """
    POST /api/inbound/create 핸들러.
    SQMInventoryEngineV3.process_inbound()를 호출한다.
    engine이 자체 트랜잭션을 관리하므로 여기서는 감싸지 않는다.
    """
    # packing_data 구성 (process_inbound이 기대하는 형식)
    packing_data = {
        'lot_no': req.lot_no,
        'product_name': req.product_name,
        'sap_no': req.sap_no or '',
        'bl_no': req.bl_no,
        'total_weight': req.total_weight_kg,
        'bag_count': req.bag_count,
        'location': req.location or '',
        'container_no': req.container_no or '',
        'mxbg_pallet': req.bag_count,
    }

    # 톤백 개별 중량이 있으면 추가
    if req.tonbags:
        packing_data['tonbags'] = [
            {'weight': t.weight, 'is_sample': t.is_sample}
            for t in req.tonbags
        ]

    invoice_data = {}
    if req.invoice_no:
        invoice_data['invoice_no'] = req.invoice_no
    if req.ship_date:
        invoice_data['ship_date'] = req.ship_date
    if req.arrival_date:
        invoice_data['arrival_date'] = req.arrival_date
    if req.warehouse:
        invoice_data['warehouse'] = req.warehouse

    bl_data = {'bl_no': req.bl_no} if req.bl_no else None

    try:
        result = engine.process_inbound(
            packing_data=packing_data,
            invoice_data=invoice_data if invoice_data else None,
            bl_data=bl_data,
            source_type=req.source_type,
            source_file=req.source_file or '',
        )
        return {
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'data': {
                'lot_no': result.get('lot_no', ''),
                'created_lots': result.get('created_lots', []),
                'created_tonbags': result.get('created_tonbags', 0),
                'warnings': result.get('warnings', []),
                'errors': result.get('errors', []),
            }
        }
    except Exception as e:
        logger.exception("입고 처리 실패")
        return {
            'success': False,
            'message': f"입고 처리 실패: {str(e)}",
            'data': {}
        }
