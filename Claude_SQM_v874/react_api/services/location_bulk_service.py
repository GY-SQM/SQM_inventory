# -*- coding: utf-8 -*-
"""위치 일괄 변경 서비스 — Excel 업로드 기반 톤백 위치 매핑."""
import json
import logging
import os
import tempfile
from typing import Any, Dict, List

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)


def update_single_location(lot_no: str, sub_lt: int, location: str, operator: str = "web_user") -> Dict:
    """단건 위치 변경 — inventory_tonbag.location UPDATE + tonbag_move_log 기록."""
    with get_db() as db:
        row = db.fetchone(
            "SELECT id, location FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
            (lot_no, sub_lt),
        )
        if not row:
            return {"success": False, "message": f"톤백을 찾을 수 없습니다: {lot_no}-{sub_lt}", "data": {}}

        from_location = row.get("location") or ""
        if from_location == location:
            return {"success": True, "message": "이미 동일한 위치입니다.", "data": {"lot_no": lot_no, "sub_lt": sub_lt}}

        try:
            db.execute(
                "UPDATE inventory_tonbag SET location = ? WHERE lot_no = ? AND sub_lt = ?",
                (location, lot_no, sub_lt),
            )
            db.execute(
                "INSERT INTO tonbag_move_log "
                "(lot_no, sub_lt, from_location, to_location, move_date, operator, source_type, created_at) "
                "VALUES (?, ?, ?, ?, date('now'), ?, 'WEB', ?)",
                (lot_no, sub_lt, from_location, location, operator, now_str()),
            )
            db.conn.commit()
            return {
                "success": True,
                "message": f"위치 변경: {lot_no}-{sub_lt} {from_location} → {location}",
                "data": {"lot_no": lot_no, "sub_lt": sub_lt, "from": from_location, "to": location},
            }
        except Exception as e:
            try:
                db.conn.rollback()
            except Exception:
                pass
            logger.exception("위치 변경 실패: %s-%s", lot_no, sub_lt)
            return {"success": False, "message": f"위치 변경 실패: {str(e)}", "data": {}}


def bulk_update_locations(items: List[Dict[str, Any]], operator: str = "web_user") -> Dict:
    """일괄 위치 변경 — 전체 성공 or 전체 rollback."""
    with get_db() as db:
        success_count = 0
        errors = []

        try:
            for idx, item in enumerate(items):
                lot_no = item.get("lot_no", "")
                sub_lt = item.get("sub_lt")
                location = item.get("location", "")
                if not lot_no or sub_lt is None or not location:
                    errors.append(f"행 {idx+1}: 필수 필드 누락")
                    continue

                row = db.fetchone(
                    "SELECT location FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                    (lot_no, int(sub_lt)),
                )
                if not row:
                    errors.append(f"행 {idx+1}: 톤백 없음 {lot_no}-{sub_lt}")
                    continue

                from_loc = row.get("location") or ""
                db.execute(
                    "UPDATE inventory_tonbag SET location = ? WHERE lot_no = ? AND sub_lt = ?",
                    (location, lot_no, int(sub_lt)),
                )
                db.execute(
                    "INSERT INTO tonbag_move_log "
                    "(lot_no, sub_lt, from_location, to_location, move_date, operator, source_type, created_at) "
                    "VALUES (?, ?, ?, ?, date('now'), ?, 'WEB_BULK', ?)",
                    (lot_no, int(sub_lt), from_loc, location, operator, now_str()),
                )
                success_count += 1

            if errors and success_count == 0:
                db.conn.rollback()
                return {"success": False, "message": f"전체 실패: {len(errors)}건 오류", "data": {"errors": errors}}

            db.conn.commit()
            return {
                "success": True,
                "message": f"위치 일괄 변경: 성공 {success_count}건, 오류 {len(errors)}건",
                "data": {"success_count": success_count, "errors": errors},
            }
        except Exception as e:
            try:
                db.conn.rollback()
            except Exception:
                pass
            logger.exception("위치 일괄 변경 실패")
            return {"success": False, "message": f"위치 일괄 변경 실패: {str(e)}", "data": {}}


def parse_location_excel(file_path: str) -> Dict:
    """위치 매핑 Excel 파싱 — preview 용."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows_data = []
        headers = []

        for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
            if row_idx == 0:
                headers = [str(c or "").strip().lower() for c in row]
                continue
            if not any(row):
                continue
            row_dict = dict(zip(headers, row))
            lot_no = str(row_dict.get("lot_no", row_dict.get("lot no", "")) or "").strip()
            sub_lt = row_dict.get("sub_lt", row_dict.get("sub lt", row_dict.get("sub", "")))
            location = str(row_dict.get("location", row_dict.get("위치", "")) or "").strip()

            if lot_no and location:
                rows_data.append({
                    "lot_no": lot_no,
                    "sub_lt": int(sub_lt) if sub_lt else 0,
                    "location": location,
                })
        wb.close()
        return {"parse_ok": True, "rows": rows_data, "errors": [], "total": len(rows_data)}
    except ImportError:
        return {"parse_ok": False, "rows": [], "errors": ["openpyxl 미설치"], "total": 0}
    except Exception as e:
        return {"parse_ok": False, "rows": [], "errors": [str(e)], "total": 0}
