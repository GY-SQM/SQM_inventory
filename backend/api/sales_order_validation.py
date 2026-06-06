import os
import sqlite3
from collections import defaultdict
from typing import Any


def _db_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    return os.path.join(root, "data", "db", "sqm_inventory.db")


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path(), timeout=5, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        (name,),
    ).fetchone()
    return bool(row)


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(r[1]) for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _allocation_rows(con: sqlite3.Connection) -> list[dict]:
    if not _table_exists(con, "allocation_plan"):
        return []
    cols = _columns(con, "allocation_plan")
    qty_expr = "qty_mt" if "qty_mt" in cols else ("qty" if "qty" in cols else "0")
    sale_expr = "sale_ref" if "sale_ref" in cols else "''"
    customer_expr = "customer" if "customer" in cols else "''"
    bl_expr = "bl_no" if "bl_no" in cols else "''"
    picking_expr = "picking_no" if "picking_no" in cols else "''"
    status_expr = "status" if "status" in cols else "''"
    rows = con.execute(
        f"""
        SELECT
            lot_no,
            COALESCE({sale_expr}, '') AS sale_ref,
            COALESCE({customer_expr}, '') AS customer,
            COALESCE({bl_expr}, '') AS bl_no,
            COALESCE({picking_expr}, '') AS picking_no,
            COALESCE({status_expr}, '') AS status,
            SUM(COALESCE({qty_expr}, 0)) AS qty_mt
        FROM allocation_plan
        WHERE TRIM(COALESCE(lot_no, '')) != ''
          AND COALESCE({status_expr}, '') NOT IN ('CANCELLED', 'REVERTED')
        GROUP BY lot_no, sale_ref, customer, bl_no, picking_no, status
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _allocation_by_lot(con: sqlite3.Connection) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in _allocation_rows(con):
        lot = str(r.get("lot_no") or "").strip()
        if not lot:
            continue
        cur = out.setdefault(lot, {
            "lot_no": lot,
            "qty_mt": 0.0,
            "sale_refs": set(),
            "customers": set(),
            "bl_nos": set(),
            "picking_nos": set(),
            "statuses": set(),
        })
        cur["qty_mt"] += _num(r.get("qty_mt"))
        for key, target in [
            ("sale_ref", "sale_refs"),
            ("customer", "customers"),
            ("bl_no", "bl_nos"),
            ("picking_no", "picking_nos"),
            ("status", "statuses"),
        ]:
            val = str(r.get(key) or "").strip()
            if val:
                cur[target].add(val)
    return out


def _finalize(issue_rows: list[dict], context: dict) -> dict:
    severity_rank = {"error": 3, "warning": 2, "info": 1, "ok": 0}
    level = "ok"
    for issue in issue_rows:
        if severity_rank.get(issue.get("severity"), 0) > severity_rank.get(level, 0):
            level = issue.get("severity") or level
    counts = defaultdict(int)
    for issue in issue_rows:
        counts[issue.get("severity") or "info"] += 1
    return {
        "level": level,
        "counts": dict(counts),
        "issues": issue_rows[:80],
        "context": context,
    }


def validate_picking_doc(parsed: dict) -> dict:
    con = _connect()
    try:
        alloc = _allocation_by_lot(con)
    finally:
        con.close()

    sales_order_no = str(parsed.get("sales_order_no") or "").strip()
    picking_no = str(parsed.get("picking_no") or "").strip()
    picked_by_lot: dict[str, float] = defaultdict(float)
    for item in parsed.get("items") or []:
        lot = str(item.get("lot_no") or "").strip()
        if not lot:
            continue
        picked_by_lot[lot] += _num(item.get("qty_kg")) / 1000.0

    issues: list[dict] = []
    sale_refs = set()
    for lot, picked_mt in sorted(picked_by_lot.items()):
        a = alloc.get(lot)
        if not a:
            issues.append({
                "severity": "warning",
                "code": "NO_ALLOCATION",
                "message": f"LOT {lot}: Allocation에 없는 LOT가 Picking List에 포함됨",
                "lot_no": lot,
                "picking_mt": round(picked_mt, 4),
                "allocation_mt": 0,
            })
            continue
        sale_refs.update(a["sale_refs"])
        allocation_mt = _num(a.get("qty_mt"))
        if picked_mt > allocation_mt + 0.001:
            issues.append({
                "severity": "error",
                "code": "OVER_PICK",
                "message": f"LOT {lot}: Picking 수량이 Allocation 예약 수량보다 큼",
                "lot_no": lot,
                "picking_mt": round(picked_mt, 4),
                "allocation_mt": round(allocation_mt, 4),
            })
        elif picked_mt < allocation_mt - 0.001:
            issues.append({
                "severity": "info",
                "code": "PARTIAL_PICK",
                "message": f"LOT {lot}: Allocation 예약 수량 중 일부만 Picking됨",
                "lot_no": lot,
                "picking_mt": round(picked_mt, 4),
                "allocation_mt": round(allocation_mt, 4),
            })

    if sales_order_no and not picked_by_lot:
        issues.append({
            "severity": "warning",
            "code": "NO_PICKING_ITEMS",
            "message": f"Sales Order No {sales_order_no}: Picking LOT 데이터가 없음",
        })
    if len({x for x in sale_refs if x}) > 1:
        issues.append({
            "severity": "warning",
            "code": "MIXED_ALLOCATION_REF",
            "message": "같은 Picking/Sales Order 안에 서로 다른 Allocation 참조가 섞여 있음",
            "sale_refs": sorted(sale_refs),
        })

    if not issues:
        issues.append({
            "severity": "ok",
            "code": "MATCHED",
            "message": "Allocation과 Picking List 매칭 완료",
        })

    return _finalize(issues, {
        "mode": "picking_upload",
        "sales_order_no": sales_order_no,
        "picking_no": picking_no,
        "lots": len(picked_by_lot),
        "picking_mt": round(sum(picked_by_lot.values()), 4),
    })


def validate_sales_order_no(sales_order_no: str = "", lot_no: str = "") -> dict:
    con = _connect()
    try:
        alloc = _allocation_by_lot(con)
        if not _table_exists(con, "sold_table"):
            return _finalize([{
                "severity": "warning",
                "code": "NO_SOLD_TABLE",
                "message": "sold_table이 없어 Sales Order No 누적 검증을 할 수 없음",
            }], {"mode": "sales_order_no", "sales_order_no": sales_order_no})
        clauses = ["COALESCE(status, '') IN ('SOLD', 'CONFIRMED')"]
        params: list[Any] = []
        if sales_order_no:
            clauses.append("sales_order_no = ?")
            params.append(sales_order_no)
        if lot_no:
            clauses.append("lot_no = ?")
            params.append(lot_no)
        where = " AND ".join(clauses)
        rows = con.execute(
            f"""
            SELECT lot_no,
                   COALESCE(sales_order_no, '') AS sales_order_no,
                   COALESCE(picking_no, '') AS picking_no,
                   SUM(COALESCE(sold_qty_kg, 0)) / 1000.0 AS sold_mt,
                   COUNT(*) AS row_count
            FROM sold_table
            WHERE {where}
            GROUP BY lot_no, sales_order_no, picking_no
            ORDER BY sales_order_no, lot_no
            """,
            params,
        ).fetchall()
    finally:
        con.close()

    sold_by_lot: dict[str, float] = defaultdict(float)
    so_set = set()
    picking_set = set()
    for r in rows:
        lot = str(r["lot_no"] or "").strip()
        if not lot:
            continue
        sold_by_lot[lot] += _num(r["sold_mt"])
        if r["sales_order_no"]:
            so_set.add(str(r["sales_order_no"]))
        if r["picking_no"]:
            picking_set.add(str(r["picking_no"]))

    issues: list[dict] = []
    sale_refs = set()
    for lot, sold_mt in sorted(sold_by_lot.items()):
        a = alloc.get(lot)
        if not a:
            issues.append({
                "severity": "warning",
                "code": "NO_ALLOCATION",
                "message": f"LOT {lot}: Sales Order에는 있으나 Allocation 근거가 없음",
                "lot_no": lot,
                "sales_order_mt": round(sold_mt, 4),
                "allocation_mt": 0,
            })
            continue
        sale_refs.update(a["sale_refs"])
        allocation_mt = _num(a.get("qty_mt"))
        if sold_mt > allocation_mt + 0.001:
            issues.append({
                "severity": "error",
                "code": "OVER_SOLD",
                "message": f"LOT {lot}: Sales Order 누적 수량이 Allocation 예약 수량보다 큼",
                "lot_no": lot,
                "sales_order_mt": round(sold_mt, 4),
                "allocation_mt": round(allocation_mt, 4),
            })
        elif sold_mt < allocation_mt - 0.001:
            issues.append({
                "severity": "info",
                "code": "PARTIAL_SOLD",
                "message": f"LOT {lot}: Allocation 예약 수량 중 일부만 Sales Order에 반영됨",
                "lot_no": lot,
                "sales_order_mt": round(sold_mt, 4),
                "allocation_mt": round(allocation_mt, 4),
            })

    if len({x for x in sale_refs if x}) > 1:
        issues.append({
            "severity": "warning",
            "code": "MIXED_ALLOCATION_REF",
            "message": "같은 Sales Order No 안에 서로 다른 Allocation 참조가 섞여 있음",
            "sale_refs": sorted(sale_refs),
        })
    if len(so_set) > 1 and not sales_order_no:
        issues.append({
            "severity": "warning",
            "code": "MULTIPLE_SALES_ORDERS",
            "message": "여러 Sales Order No가 함께 선택되어 개별 검증이 필요함",
            "sales_order_nos": sorted(so_set)[:20],
        })
    if not rows:
        issues.append({
            "severity": "warning",
            "code": "NO_SALES_ORDER_ROWS",
            "message": "Sales Order No 누적 데이터가 없음",
        })
    if not issues:
        issues.append({
            "severity": "ok",
            "code": "MATCHED",
            "message": "Sales Order No 누적 수량과 Allocation 매칭 완료",
        })

    return _finalize(issues, {
        "mode": "sales_order_no",
        "sales_order_no": sales_order_no,
        "lots": len(sold_by_lot),
        "sales_order_mt": round(sum(sold_by_lot.values()), 4),
        "picking_nos": sorted(picking_set)[:20],
    })
