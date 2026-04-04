# -*- coding: utf-8 -*-
"""출고 쓰기 서비스 — engine_modules 출고/취소/위치변경 래퍼."""
import logging
from typing import Dict

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
from react_api.schemas.write_models import (
    OutboundExecuteRequest,
    OutboundCancelRequest,
    LocationUpdateRequest,
)

logger = logging.getLogger(__name__)


def execute_outbound(engine: SQMInventoryEngineV3, req: OutboundExecuteRequest) -> Dict:
    """
    POST /api/outbound/execute
    engine.process_outbound()를 호출하여 톤백 출고 처리.
    engine이 자체 트랜잭션(IMMEDIATE)을 관리한다.
    """
    allocations = []
    for item in req.items:
        allocations.append({
            'lot_no': item.lot_no,
            'sub_lt': item.sub_lt,
            'customer': item.customer or req.customer,
            'qty_kg': item.qty_kg,
            'sale_ref': req.sale_ref or '',
            'destination': req.destination or '',
        })

    try:
        result = engine.process_outbound(
            allocation_data=allocations,
            source=req.source,
            stop_at_picked=req.stop_at_picked,
        )
        return {
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'data': {
                'processed': result.get('processed', 0),
                'lots_processed': result.get('lots_processed', 0),
                'total_weight_kg': result.get('total_weight_kg', 0),
                'total_picked': result.get('total_picked', 0),
                'warnings': result.get('warnings', []),
                'errors': result.get('errors', []),
            }
        }
    except Exception as e:
        logger.exception("출고 처리 실패")
        return {
            'success': False,
            'message': f"출고 처리 실패: {str(e)}",
            'data': {}
        }


def cancel_outbound(engine: SQMInventoryEngineV3, req: OutboundCancelRequest) -> Dict:
    """
    PUT /api/outbound/cancel
    engine.cancel_outbound_tonbag()를 호출하여 톤백 출고 취소.
    engine이 자체 트랜잭션(IMMEDIATE)을 관리한다.
    """
    try:
        result = engine.cancel_outbound_tonbag(
            lot_no=req.lot_no,
            sub_lt=req.sub_lt,
        )
        return {
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'data': {
                'errors': result.get('errors', []),
            }
        }
    except Exception as e:
        logger.exception("출고 취소 실패")
        return {
            'success': False,
            'message': f"출고 취소 실패: {str(e)}",
            'data': {}
        }


def update_location(engine: SQMInventoryEngineV3, req: LocationUpdateRequest) -> Dict:
    """
    PUT /api/location/update
    engine.update_tonbag_location()를 호출하여 톤백 위치 변경.
    engine이 자체 트랜잭션 + 7개 hard-stop 검증을 수행한다.
    """
    try:
        result = engine.update_tonbag_location(
            lot_no=req.lot_no,
            sub_lt=req.sub_lt,
            location=req.new_location,
            source='WEB',
            reason_code=req.reason_code or 'RELOCATE',
            operator=req.operator or 'web_user',
            note=req.note or '',
        )
        return {
            'success': result.get('success', False),
            'message': result.get('error', '') if not result.get('success') else
                       f"위치 변경 완료: {req.lot_no}-{req.sub_lt} "
                       f"{result.get('from_location', '')} → {result.get('to_location', '')}",
            'data': {
                'lot_no': req.lot_no,
                'sub_lt': req.sub_lt,
                'from_location': result.get('from_location', ''),
                'to_location': result.get('to_location', ''),
            }
        }
    except Exception as e:
        logger.exception("위치 변경 실패")
        return {
            'success': False,
            'message': f"위치 변경 실패: {str(e)}",
            'data': {}
        }
