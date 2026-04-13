# -*- coding: utf-8 -*-
"""D/O 후속 연결 서비스 — inventory 테이블 D/O 정보 업데이트."""
import json
import logging
from typing import Dict, Optional

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)


def apply_do_update(
    lot_no: str,
    do_no: Optional[str] = None,
    ship_date: Optional[str] = None,
    arrival_date: Optional[str] = None,
    con_return: Optional[str] = None,
    free_time: Optional[int] = None,
) -> Dict:
    """D/O 후속 연결 — inventory 테이블 UPDATE + audit_log 기록."""
    with get_db() as db:
        existing = db.fetchone(
            "SELECT lot_no, bl_no FROM inventory WHERE lot_no = ?", (lot_no,)
        )
        if not existing:
            return {"success": False, "message": f"LOT을 찾을 수 없습니다: {lot_no}", "data": {}}

        updates = []
        params = []
        if do_no is not None:
            updates.append("bl_no = ?")
            params.append(do_no)
        if ship_date is not None:
            updates.append("ship_date = ?")
            params.append(ship_date)
        if arrival_date is not None:
            updates.append("arrival_date = ?")
            params.append(arrival_date)
        if con_return is not None:
            updates.append("con_return = ?")
            params.append(con_return)
        if free_time is not None:
            updates.append("free_time = ?")
            params.append(free_time)

        if not updates:
            return {"success": False, "message": "업데이트할 항목이 없습니다.", "data": {}}

        updates.append("updated_at = ?")
        params.append(now_str())
        params.append(lot_no)

        try:
            db.execute(
                f"UPDATE inventory SET {', '.join(updates)} WHERE lot_no = ?",
                tuple(params),
            )
            db.execute(
                "INSERT INTO audit_log (event_type, event_data, created_at) VALUES (?, ?, ?)",
                (
                    "DO_UPDATE",
                    json.dumps({
                        "lot_no": lot_no, "do_no": do_no,
                        "ship_date": ship_date, "arrival_date": arrival_date,
                        "con_return": con_return, "free_time": free_time,
                    }, ensure_ascii=False),
                    now_str(),
                ),
            )
            db.conn.commit()
            return {
                "success": True,
                "message": f"D/O 연결 완료: {lot_no}",
                "data": {"lot_no": lot_no},
            }
        except Exception as e:
            try:
                db.conn.rollback()
            except Exception:
                pass
            logger.exception("D/O 업데이트 실패: lot=%s", lot_no)
            return {"success": False, "message": f"D/O 업데이트 실패: {str(e)}", "data": {}}
