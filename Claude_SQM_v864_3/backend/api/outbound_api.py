# -*- coding: utf-8 -*-
"""
SQM v864.3 — Outbound API (Phase 4-B)
POST /api/outbound/quick : 즉시 출고 (원스톱) — F015
engine.quick_outbound(lot_no, count, customer, reason, operator) 직접 호출
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/outbound", tags=["outbound"])


class QuickOutboundRequest(BaseModel):
    lot_no: str = Field(..., min_length=1, description="LOT 번호")
    count: int = Field(..., gt=0, description="출고 톤백 개수")
    customer: str = Field(..., min_length=1, description="고객명")
    reason: str = Field("", description="사유 (선택)")
    operator: str = Field("", description="작업자 (선택)")


@router.post("/quick", summary="🚀 즉시 출고 — 원스톱 (F015)")
def quick_outbound(req: QuickOutboundRequest):
    """
    Allocation 없이 소량 즉시 출고 (AVAILABLE → PICKED 직접 전환).
    engine.quick_outbound() 트랜잭션 호출.
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")
    if not hasattr(engine, "quick_outbound"):
        raise HTTPException(500, "엔진에 quick_outbound 메서드 없음")

    try:
        result = engine.quick_outbound(
            lot_no=req.lot_no.strip(),
            count=req.count,
            customer=req.customer.strip(),
            reason=req.reason or "",
            operator=req.operator or "",
        )
    except Exception as e:
        logger.exception(f"[quick-outbound] engine 에러: {e}")
        raise HTTPException(500, f"Engine error: {e}")

    if result.get("success"):
        picked = int(result.get("picked_count", 0))
        total_weight_kg = float(result.get("total_weight_kg", 0))
        logger.info(
            f"[quick-outbound] OK: LOT={req.lot_no}, picked={picked}, "
            f"total_weight={total_weight_kg}kg, customer={req.customer}"
        )
        return {
            "ok": True,
            "data": {
                "lot_no": req.lot_no,
                "picked_count": picked,
                "total_weight_kg": total_weight_kg,
                "total_weight_mt": round(total_weight_kg / 1000.0, 3),
                "customer": req.customer,
            },
            "message": f"{picked}개 톤백 출고 완료 ({round(total_weight_kg/1000.0, 2)} MT)",
        }
    else:
        # 실패: 엔진 errors 배열 그대로 사용자에게 반환
        errors = result.get("errors", [])
        return {
            "ok": False,
            "data": {
                "lot_no": req.lot_no,
                "picked_count": int(result.get("picked_count", 0)),
                "errors": errors,
            },
            "error": "즉시 출고 실패",
            "detail": {"code": "QUICK_OUTBOUND_FAILED", "errors": errors},
            "message": "; ".join(errors) if errors else "즉시 출고 실패",
        }


@router.get("/quick/info", summary="즉시 출고 — LOT 가용 정보 (F015 보조)")
def quick_outbound_info(lot_no: str):
    """
    특정 LOT 의 가용 톤백 개수와 총 중량 반환.
    프론트 폼에서 '최대 가능 개수' 표시용.
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    lot_no = (lot_no or "").strip()
    if not lot_no:
        raise HTTPException(400, "lot_no required")

    try:
        rows = engine.db.fetchall(
            """SELECT COUNT(*) AS cnt, COALESCE(SUM(weight), 0) AS total_kg
               FROM inventory_tonbag
               WHERE lot_no = ? AND status = 'AVAILABLE' AND COALESCE(is_sample,0) = 0""",
            (lot_no,),
        )
        if rows:
            r = rows[0]
            cnt = int(r["cnt"] if hasattr(r, "__getitem__") else r[0])
            total_kg = float(r["total_kg"] if hasattr(r, "__getitem__") else r[1])
        else:
            cnt, total_kg = 0, 0.0
    except Exception as e:
        logger.warning(f"[quick-info] 조회 실패: {e}")
        raise HTTPException(500, f"조회 실패: {e}")

    try:
        from engine_modules.constants import QUICK_OUTBOUND_MAX_TONBAGS
        max_count = int(QUICK_OUTBOUND_MAX_TONBAGS)
    except Exception:
        max_count = 50  # fallback

    return {
        "ok": True,
        "data": {
            "lot_no": lot_no,
            "available_count": cnt,
            "total_weight_kg": total_kg,
            "total_weight_mt": round(total_kg / 1000.0, 3),
            "max_count": max_count,
        },
    }
