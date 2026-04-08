# -*- coding: utf-8 -*-
"""Return 쓰기 서비스 — engine_modules ReturnMixin 래퍼."""
import logging
from typing import Dict

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3

logger = logging.getLogger(__name__)

VALID_REASON_CODES = {"품질불량", "수량오류", "고객요청", "파손", "기타"}


def execute_single_return(
    engine: SQMInventoryEngineV3,
    lot_no: str,
    sub_lt: int,
    reason_code: str,
    note: str = "",
) -> Dict:
    """소량반품 단건 처리.

    engine.return_single_tonbag()을 호출한다.
    engine이 자체 트랜잭션(IMMEDIATE)을 관리하며 실패 시 자동 rollback.
    """
    if reason_code not in VALID_REASON_CODES:
        return {
            "success": False,
            "message": f"허용되지 않은 사유코드: {reason_code}. "
                       f"허용: {', '.join(sorted(VALID_REASON_CODES))}",
            "data": {},
        }

    try:
        result = engine.return_single_tonbag(
            lot_no=lot_no,
            sub_lt=sub_lt,
            reason=reason_code,
            remark=note,
        )
        success = result.get("success", False)
        return {
            "success": success,
            "message": result.get("message", "반품 처리 완료" if success else "반품 처리 실패"),
            "data": {
                "lot_no": lot_no,
                "sub_lt": sub_lt,
                "reason": reason_code,
                "processed": result.get("processed", 0),
                "warnings": result.get("warnings", []),
                "errors": result.get("errors", []),
            },
        }
    except Exception as e:
        logger.exception("소량반품 처리 실패: lot=%s sub=%s", lot_no, sub_lt)
        return {
            "success": False,
            "message": f"반품 처리 실패: {str(e)}",
            "data": {},
        }
