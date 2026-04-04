# -*- coding: utf-8 -*-
"""출고 쓰기 서비스 — engine_modules 출고/취소 래퍼."""
import logging
from typing import Dict

from engine_modules.database import SQMDatabase
from react_api.schemas.write_models import (
    OutboundExecuteRequest,
    OutboundCancelRequest,
    LocationUpdateRequest,
)

logger = logging.getLogger(__name__)


def execute_outbound(db: SQMDatabase, req: OutboundExecuteRequest) -> Dict:
    """
    POST /api/outbound/execute
    process_outbound()를 호출하여 톤백 출고 처리.
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
        result = db.process_outbound(
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


def cancel_outbound(db: SQMDatabase, req: OutboundCancelRequest) -> Dict:
    """
    PUT /api/outbound/cancel
    cancel_outbound_tonbag()를 호출하여 톤백 출고 취소.
    """
    try:
        result = db.cancel_outbound_tonbag(
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


def update_location(db: SQMDatabase, req: LocationUpdateRequest) -> Dict:
    """
    PUT /api/location/update
    톤백 위치 변경.
    """
    try:
        with db.transaction("IMMEDIATE"):
            tonbag = db.fetchone(
                "SELECT id, location FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                (req.lot_no, req.sub_lt),
            )
            if not tonbag:
                return {
                    'success': False,
                    'message': f"톤백 없음: {req.lot_no}-{req.sub_lt}",
                    'data': {}
                }

            old_location = tonbag.get('location', '') if isinstance(tonbag, dict) else (tonbag[1] if len(tonbag) > 1 else '')
            db.execute(
                "UPDATE inventory_tonbag SET location = ? WHERE lot_no = ? AND sub_lt = ?",
                (req.new_location, req.lot_no, req.sub_lt),
            )
            # 감사 로그
            db.execute(
                """INSERT INTO audit_log (event_type, event_data, created_at)
                   VALUES (?, ?, datetime('now'))""",
                ('LOCATION_UPDATE', f'{req.lot_no}-{req.sub_lt}: {old_location} → {req.new_location}'),
            )

        return {
            'success': True,
            'message': f"위치 변경 완료: {req.lot_no}-{req.sub_lt} → {req.new_location}",
            'data': {
                'lot_no': req.lot_no,
                'sub_lt': req.sub_lt,
                'old_location': old_location,
                'new_location': req.new_location,
            }
        }
    except Exception as e:
        logger.exception("위치 변경 실패")
        return {
            'success': False,
            'message': f"위치 변경 실패: {str(e)}",
            'data': {}
        }
