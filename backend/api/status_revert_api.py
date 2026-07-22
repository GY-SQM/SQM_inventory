"""
Common status revert API.

All status reverts use the same flow:
scope selection -> preview -> execute.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from core.db_allowed import ALLOWED_SCOPES, REVERT_MAP  # v9.0.0 central allowlist


router = APIRouter(prefix="/api/status-revert", tags=["status-revert"])

# REVERT_MAP / ALLOWED_SCOPES 는 v9.0.0 부터 core.db_allowed 에서 import (위 import 참조)


def _db_path() -> str:
    env_path = os.environ.get("SQM_TEST_DB_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    try:
        from config import DB_PATH

        return str(DB_PATH)
    except Exception:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root, "data", "db", "sqm_inventory.db")


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path(), timeout=10, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    return con


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(con, table):
        return set()
    return {str(r[1]) for r in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [v.strip() for v in text.replace("\n", ",").split(",") if v.strip()]


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    from_status = str(payload.get("from_status") or "").upper().strip()
    to_status = str(payload.get("to_status") or "").upper().strip()
    if not to_status and from_status in REVERT_MAP:
        to_status = REVERT_MAP[from_status]
    if REVERT_MAP.get(from_status) != to_status and not (from_status == "RETURN" and to_status in {"AVAILABLE", "SOLD"}):
        raise ValueError(f"허용되지 않은 되돌리기 단계: {from_status} → {to_status}")

    scope_type = str(payload.get("scope_type") or "").strip()
    if scope_type not in ALLOWED_SCOPES:
        raise ValueError(f"scope_type은 {sorted(ALLOWED_SCOPES)} 중 하나여야 합니다")

    filters = payload.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("filters는 object여야 합니다")

    return {
        "from_status": from_status,
        "to_status": to_status,
        "scope_type": scope_type,
        "scope_value": payload.get("scope_value"),
        "filters": filters,
        "actor": str(payload.get("actor") or "user").strip() or "user",
    }


def _add_eq_clause(parts: list[str], params: list[Any], exprs: list[str], value: Any) -> None:
    val = str(value or "").strip()
    if not val:
        return
    parts.append("(" + " OR ".join(f"{expr}=?" for expr in exprs) + ")")
    params.extend([val] * len(exprs))


def _add_date_clause(parts: list[str], params: list[Any], exprs: list[str], value: Any) -> None:
    val = str(value or "").strip()
    if not val:
        return
    parts.append("(" + " OR ".join(f"date({expr})=date(?)" for expr in exprs) + ")")
    params.extend([val] * len(exprs))


def _add_in_clause(parts: list[str], params: list[Any], expr: str, values: Any) -> None:
    vals = _as_list(values)
    if not vals:
        return
    parts.append(f"{expr} IN ({','.join('?' for _ in vals)})")
    params.extend(vals)


def _scope_filters(payload: dict[str, Any]) -> tuple[list[str], list[Any]]:
    scope_type = payload["scope_type"]
    scope_value = payload["scope_value"]
    filters = payload["filters"]
    parts: list[str] = []
    params: list[Any] = []

    def apply_one(key: str, value: Any) -> None:
        if key == "container_no":
            _add_eq_clause(parts, params, ["i.container_no"], value)
        elif key == "bl_no":
            _add_eq_clause(parts, params, ["i.bl_no", "t.bl_no", "ap.bl_no", "s.bl_no"], value)
        elif key in {"lot_no", "lot_nos", "selected_lots"}:
            _add_in_clause(parts, params, "i.lot_no", value)
        elif key == "inbound_date":
            _add_date_clause(parts, params, ["i.inbound_date", "t.inbound_date"], value)
        elif key == "sale_ref":
            _add_eq_clause(parts, params, ["i.sale_ref", "t.sale_ref", "ap.sale_ref", "s.sales_order_no"], value)
        elif key == "customer":
            _add_eq_clause(parts, params, ["i.sold_to", "t.picked_to", "ap.customer", "s.customer"], value)
        elif key == "picking_no":
            _add_eq_clause(parts, params, ["t.pick_ref", "ap.picking_no", "s.picking_no"], value)
        elif key == "outbound_date":
            _add_date_clause(parts, params, ["s.sold_date"], value)
        elif key == "return_reason":
            _add_eq_clause(parts, params, ["rh.reason"], value)

    if scope_type == "all_status":
        pass
    elif scope_type == "current_filter":
        for key, value in filters.items():
            apply_one(key, value)
    else:
        apply_one(scope_type, scope_value)

    for key, value in filters.items():
        apply_one(key, value)

    return parts, params


def _base_query(con: sqlite3.Connection) -> str:
    ap_cols = _columns(con, "allocation_plan")
    s_cols = _columns(con, "sold_table")

    def ap_expr(col: str) -> str:
        return col if col in ap_cols else f"NULL AS {col}"

    def s_expr(col: str) -> str:
        return col if col in s_cols else f"NULL AS {col}"

    joins = ["FROM inventory i"]
    joins.append("LEFT JOIN inventory_tonbag t ON t.lot_no = i.lot_no")
    if _table_exists(con, "allocation_plan"):
        joins.append(
            "LEFT JOIN (SELECT lot_no, "
            + ", ".join(ap_expr(c) for c in ["status", "bl_no", "customer", "sale_ref", "picking_no"])
            + " FROM allocation_plan) ap ON ap.lot_no = i.lot_no"
        )
    else:
        joins.append("LEFT JOIN (SELECT NULL AS lot_no, NULL AS status, NULL AS bl_no, NULL AS customer, NULL AS sale_ref, NULL AS picking_no) ap ON 1=0")
    if _table_exists(con, "sold_table"):
        joins.append(
            "LEFT JOIN (SELECT lot_no, "
            + ", ".join(s_expr(c) for c in ["status", "bl_no", "customer", "sales_order_no", "picking_no", "sold_date"])
            + " FROM sold_table) s ON s.lot_no = i.lot_no"
        )
    else:
        joins.append("LEFT JOIN (SELECT NULL AS lot_no, NULL AS status, NULL AS bl_no, NULL AS customer, NULL AS sales_order_no, NULL AS picking_no, NULL AS sold_date) s ON 1=0")
    joins.append("LEFT JOIN return_history rh ON rh.lot_no = i.lot_no" if _table_exists(con, "return_history") else "LEFT JOIN (SELECT NULL AS lot_no, NULL AS reason) rh ON 1=0")
    return "\n".join(joins)


def resolve_revert_targets(con: sqlite3.Connection, raw_payload: dict[str, Any]) -> list[str]:
    payload = _normalize_payload(raw_payload)
    from_status = payload["from_status"]
    where = [
        "(UPPER(COALESCE(i.status,''))=? OR UPPER(COALESCE(t.status,''))=? OR UPPER(COALESCE(ap.status,''))=? OR UPPER(COALESCE(s.status,''))=?)"
    ]
    params: list[Any] = [from_status, from_status, from_status, from_status]
    scope_parts, scope_params = _scope_filters(payload)
    where.extend(scope_parts)
    params.extend(scope_params)
    if payload["scope_type"] != "all_status" and not scope_parts:
        raise ValueError("되돌릴 범위를 선택해야 합니다")

    rows = con.execute(
        "SELECT DISTINCT i.lot_no\n"
        + _base_query(con)
        + "\nWHERE "
        + " AND ".join(where)
        + "\nORDER BY i.lot_no",
        params,
    ).fetchall()
    return [str(r["lot_no"]) for r in rows if r["lot_no"]]


def _summarize(con: sqlite3.Connection, lots: list[str], from_status: str) -> dict[str, Any]:
    if not lots:
        return {"target_lot_count": 0, "target_tonbag_count": 0, "target_weight_mt": 0.0}
    ph = ",".join("?" for _ in lots)
    row = con.execute(
        f"""
        SELECT COUNT(*) AS cnt, COALESCE(SUM(weight), 0) AS kg
        FROM inventory_tonbag
        WHERE lot_no IN ({ph}) AND UPPER(COALESCE(status,''))=?
        """,
        lots + [from_status],
    ).fetchone()
    return {
        "target_lot_count": len(lots),
        "target_tonbag_count": int(row["cnt"] or 0),
        "target_weight_mt": round(float(row["kg"] or 0) / 1000.0, 4),
    }


def _blocked(con: sqlite3.Connection, lots: list[str], from_status: str, to_status: str) -> list[dict[str, Any]]:
    if from_status != "AVAILABLE" or to_status != "PENDING" or not lots:
        return []
    ph = ",".join("?" for _ in lots)
    rows = con.execute(
        f"""
        SELECT lot_no, status, COUNT(*) AS cnt
        FROM inventory_tonbag
        WHERE lot_no IN ({ph}) AND UPPER(COALESCE(status,'')) IN ('RESERVED','PICKED','SOLD')
        GROUP BY lot_no, status
        ORDER BY lot_no, status
        """,
        lots,
    ).fetchall()
    return [{"lot_no": r["lot_no"], "status": r["status"], "count": int(r["cnt"] or 0)} for r in rows]


def preview_status_revert(con: sqlite3.Connection, raw_payload: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_payload(raw_payload)
    lots = resolve_revert_targets(con, raw_payload)
    summary = _summarize(con, lots, payload["from_status"])
    blocked = _blocked(con, lots, payload["from_status"], payload["to_status"])
    return {
        "ok": True,
        "from_status": payload["from_status"],
        "to_status": payload["to_status"],
        **summary,
        "lots": lots,
        "blocked": blocked,
        "warning": ["차단 대상이 있어 실행할 수 없습니다"] if blocked else [],
    }


def _update_inventory(con: sqlite3.Connection, lots: list[str], from_status: str, to_status: str) -> int:
    if not lots:
        return 0
    ph = ",".join("?" for _ in lots)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if to_status == "PENDING":
        cur = con.execute(
            f"UPDATE inventory SET status='PENDING', inbound_date=NULL, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [now] + lots + [from_status],
        )
    elif to_status == "AVAILABLE":
        cur = con.execute(
            f"UPDATE inventory SET status='AVAILABLE', sold_to=NULL, sale_ref=NULL, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [now] + lots + [from_status],
        )
    else:
        cur = con.execute(
            f"UPDATE inventory SET status=?, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [to_status, now] + lots + [from_status],
        )
    return int(cur.rowcount or 0)


def _update_tonbags(con: sqlite3.Connection, lots: list[str], from_status: str, to_status: str) -> int:
    if not lots:
        return 0
    ph = ",".join("?" for _ in lots)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if to_status == "PENDING":
        cur = con.execute(
            f"UPDATE inventory_tonbag SET status='PENDING', updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [now] + lots + [from_status],
        )
    elif to_status == "AVAILABLE":
        cur = con.execute(
            f"UPDATE inventory_tonbag SET status='AVAILABLE', sale_ref=NULL, picked_to=NULL, pick_ref=NULL, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [now] + lots + [from_status],
        )
    elif to_status == "RESERVED":
        cur = con.execute(
            f"UPDATE inventory_tonbag SET status='RESERVED', picked_to=NULL, pick_ref=NULL, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [now] + lots + [from_status],
        )
    else:
        cur = con.execute(
            f"UPDATE inventory_tonbag SET status=?, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [to_status, now] + lots + [from_status],
        )
    return int(cur.rowcount or 0)


def _update_allocation(con: sqlite3.Connection, lots: list[str], from_status: str, to_status: str) -> int:
    if not lots or not _table_exists(con, "allocation_plan"):
        return 0
    ph = ",".join("?" for _ in lots)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if to_status == "AVAILABLE":
        cur = con.execute(
            f"UPDATE allocation_plan SET status='CANCELLED', cancelled_at=? WHERE lot_no IN ({ph}) AND status=?",
            [now] + lots + [from_status],
        )
    else:
        cur = con.execute(
            f"UPDATE allocation_plan SET status=?, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
            [to_status, now] + lots + [from_status],
        )
    return int(cur.rowcount or 0)


def _update_sold_table(con: sqlite3.Connection, lots: list[str], from_status: str, to_status: str) -> int:
    if from_status != "SOLD" or to_status != "PICKED" or not lots or not _table_exists(con, "sold_table"):
        return 0
    ph = ",".join("?" for _ in lots)
    cur = con.execute(
        f"UPDATE sold_table SET status='REVERTED' WHERE lot_no IN ({ph}) AND status IN ('SOLD','CONFIRMED')",
        lots,
    )
    return int(cur.rowcount or 0)


def _recalc_lot_weights(con: sqlite3.Connection, lots: list[str]) -> int:
    """D2/D4: 상태복원 후 inventory 무게를 tonbag 상태 기준으로 재계산한다."""
    if not lots:
        return 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = 0
    for lot_no in lots:
        row = con.execute(
            """
            SELECT
                COALESCE(SUM(CASE
                    WHEN UPPER(COALESCE(status,'')) IN ('AVAILABLE','RESERVED','RETURN','SAMPLE')
                    THEN weight ELSE 0 END), 0) AS current_weight,
                COALESCE(SUM(CASE
                    WHEN UPPER(COALESCE(status,'')) IN ('PICKED','CONFIRMED','SHIPPED','SOLD')
                    THEN weight ELSE 0 END), 0) AS picked_weight
            FROM inventory_tonbag
            WHERE lot_no=?
            """,
            (lot_no,),
        ).fetchone()
        cur = con.execute(
            """
            UPDATE inventory
            SET current_weight=?, picked_weight=?, updated_at=?
            WHERE lot_no=?
            """,
            (
                float(row["current_weight"] or 0) if row else 0.0,
                float(row["picked_weight"] or 0) if row else 0.0,
                now,
                lot_no,
            ),
        )
        updated += int(cur.rowcount or 0)
    return updated


def _write_audit(con: sqlite3.Connection, payload: dict[str, Any], lots: list[str], counts: dict[str, int]) -> None:
    if not _table_exists(con, "audit_log"):
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "from_status": payload["from_status"],
        "to_status": payload["to_status"],
        "scope_type": payload["scope_type"],
        "scope_value": payload["scope_value"],
        "filters": payload["filters"],
        "lots": lots,
        "counts": counts,
    }
    con.execute(
        "INSERT INTO audit_log(event_type, event_data, user_note, created_by, created_at) VALUES (?,?,?,?,?)",
        (
            "STATUS_REVERT",
            json.dumps(data, ensure_ascii=False),
            f"{payload['from_status']} -> {payload['to_status']} ({len(lots)} LOT)",
            payload["actor"],
            now,
        ),
    )


def execute_status_revert(con: sqlite3.Connection, raw_payload: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_payload(raw_payload)
    preview = preview_status_revert(con, raw_payload)
    if preview["blocked"]:
        return {**preview, "ok": False, "message": "차단 대상이 있어 실행하지 않았습니다"}
    lots = preview["lots"]
    counts = {
        "inventory": _update_inventory(con, lots, payload["from_status"], payload["to_status"]),
        "tonbags": _update_tonbags(con, lots, payload["from_status"], payload["to_status"]),
        "allocation": _update_allocation(con, lots, payload["from_status"], payload["to_status"]),
        "sold_table": _update_sold_table(con, lots, payload["from_status"], payload["to_status"]),
    }
    counts["recalculated_lots"] = _recalc_lot_weights(con, lots)
    _write_audit(con, payload, lots, counts)
    con.commit()
    return {
        "ok": True,
        "message": f"{payload['from_status']} → {payload['to_status']}: {len(lots)} LOT 되돌리기 완료",
        "data": {
            "from": payload["from_status"],
            "to": payload["to_status"],
            "lots": lots,
            "counts": counts,
        },
    }


@router.get("/options", summary="되돌리기 대상 선택 옵션")
def get_revert_options(from_status: str = Query(...), limit: int = Query(300, ge=1, le=1000)):
    status = from_status.upper().strip()
    if status not in REVERT_MAP:
        raise HTTPException(400, "지원하지 않는 from_status")
    con = _db()
    try:
        def distinct(expr: str) -> list[str]:
            rows = con.execute(
                f"""
                SELECT DISTINCT {expr} AS v
                {_base_query(con)}
                WHERE (UPPER(COALESCE(i.status,''))=? OR UPPER(COALESCE(t.status,''))=? OR UPPER(COALESCE(ap.status,''))=? OR UPPER(COALESCE(s.status,''))=?)
                  AND {expr} IS NOT NULL AND TRIM(CAST({expr} AS TEXT)) != ''
                ORDER BY v
                LIMIT ?
                """,
                (status, status, status, status, limit),
            ).fetchall()
            return [str(r["v"]) for r in rows if r["v"]]

        return {
            "ok": True,
            "from_status": status,
            "to_status": REVERT_MAP[status],
            "options": {
                "container_no": distinct("i.container_no"),
                "bl_no": distinct("COALESCE(i.bl_no, t.bl_no, ap.bl_no, s.bl_no)"),
                "lot_no": distinct("i.lot_no"),
                "inbound_date": distinct("date(COALESCE(i.inbound_date, t.inbound_date))"),
                "sale_ref": distinct("COALESCE(i.sale_ref, t.sale_ref, ap.sale_ref, s.sales_order_no)"),
                "customer": distinct("COALESCE(i.sold_to, t.picked_to, ap.customer, s.customer)"),
                "picking_no": distinct("COALESCE(t.pick_ref, ap.picking_no, s.picking_no)"),
                "outbound_date": distinct("date(s.sold_date)"),
                "return_reason": distinct("rh.reason"),
            },
        }
    finally:
        con.close()


@router.post("/preview", summary="되돌리기 미리보기")
def preview_endpoint(payload: dict = Body(...)):
    con = _db()
    try:
        return preview_status_revert(con, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        con.close()


@router.post("/execute", summary="되돌리기 실행")
def execute_endpoint(payload: dict = Body(...)):
    con = _db()
    try:
        return execute_status_revert(con, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
