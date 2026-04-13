# -*- coding: utf-8 -*-
"""P2-5/12: Smart Inbound API — 스마트 입고 엔드포인트"""
import os
import json
import logging
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/smart-inbound", tags=["smart-inbound"])

DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "data" / "db" / "sqm_inventory.db")


@router.post("/parse")
async def smart_parse(
    file: UploadFile = File(...),
    doc_type: str = Form("BL"),
):
    """PDF 업로드 → 스마트 파싱 (템플릿 우선, AI 폴백)"""
    try:
        from features.ai.smart_document_parser import SmartDocumentParser
        from features.ai.confidence_scorer import ConfidenceScorer

        # 임시 파일 저장
        suffix = Path(file.filename).suffix or '.pdf'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # 파싱
        parser = SmartDocumentParser(db_path=DB_PATH)
        result = parser.parse_document(tmp_path, doc_type)

        # 신뢰도 평가
        scorer = ConfidenceScorer()
        confidence = scorer.score(result, result.get('parse_method', 'AI'))

        # 임시 파일 삭제
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        return {
            "success": True,
            "data": result,
            "confidence": confidence,
            "generated_at": now_str(),
        }

    except Exception as e:
        logger.error(f"스마트 파싱 실패: {e}")
        return JSONResponse(status_code=500, content={
            "success": False, "error": str(e)
        })


@router.post("/cross-validate")
async def cross_validate(
    bl_data: dict = None,
    pl_data: dict = None,
    fa_data: dict = None,
):
    """교차검증 실행"""
    try:
        from features.ai.cross_validator import CrossValidator
        validator = CrossValidator()
        result = validator.validate(bl_data or {}, pl_data, fa_data)
        return {"success": True, **result, "generated_at": now_str()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/save")
async def smart_save(data: dict):
    """파싱 결과 DB 저장 + 템플릿 학습"""
    try:
        parsed = data.get('parsed', {})
        user_corrected = data.get('corrected', parsed)
        save_template = data.get('save_template', False)

        # 입고 저장 — 기존 /api/inbound/create 로직 재활용
        with get_db() as db:
            lot_no = user_corrected.get('lot_no', '')
            bl_no = user_corrected.get('bl_no', '')
            product = user_corrected.get('product', user_corrected.get('product_name', ''))
            net_weight = float(user_corrected.get('net_weight', 0))
            bag_count = int(user_corrected.get('tonbag_count', user_corrected.get('bag_count', 0)))

            if not lot_no or not bl_no:
                return {"success": False, "message": "LOT NO와 BL NO는 필수입니다."}

            # inventory 저장
            db.execute("""
                INSERT OR IGNORE INTO inventory (lot_no, bl_no, product_name, net_weight, current_weight, status, inbound_date, source_type)
                VALUES (?, ?, ?, ?, ?, 'AVAILABLE', date('now'), 'SMART_INBOUND')
            """, (lot_no, bl_no, product, net_weight, net_weight))

            # 톤백 생성
            for i in range(1, bag_count + 1):
                weight = round(net_weight / bag_count, 2) if bag_count > 0 else 0
                db.execute("""
                    INSERT OR IGNORE INTO inventory_tonbag (lot_no, sub_lt, weight, status, inbound_date)
                    VALUES (?, ?, ?, 'AVAILABLE', date('now'))
                """, (lot_no, i, weight))

            db.commit()

        # 템플릿 학습
        if save_template and parsed.get('carrier'):
            try:
                from features.ai.template_learner import TemplateLearner
                learner = TemplateLearner(DB_PATH)
                learner.learn_from_correction(
                    parsed['carrier'],
                    parsed.get('doc_type', 'BL'),
                    parsed, user_corrected
                )
            except Exception as e:
                logger.warning(f"템플릿 학습 실패: {e}")

        return {
            "success": True,
            "message": f"LOT {lot_no} 입고 완료 ({bag_count}개 톤백)",
            "lot_no": lot_no,
            "created_tonbags": bag_count,
        }

    except Exception as e:
        logger.error(f"스마트 저장 실패: {e}")
        return {"success": False, "message": str(e)}


@router.get("/templates")
def list_templates():
    """저장된 템플릿 목록"""
    with get_db() as db:
        try:
            rows = db.fetchall("""
                SELECT id, carrier, doc_type, usage_count,
                       COALESCE(success_rate, 0) as success_rate,
                       created_at, updated_at
                FROM inbound_template
                WHERE is_active = 1
                ORDER BY usage_count DESC
            """)
            return {"success": True, "templates": rows, "total": len(rows)}
        except Exception:
            return {"success": True, "templates": [], "total": 0}
