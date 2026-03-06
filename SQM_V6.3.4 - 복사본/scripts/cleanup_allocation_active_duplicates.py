# -*- coding: utf-8 -*-
"""
allocation_plan 활성 중복 정리 스크립트.

정책:
- 같은 LOT의 활성 배정(STAGED/RESERVED)이 여러 건이면 최신 1건만 유지
- 나머지는 상태 전환으로 비활성화(삭제하지 않음)
- 기본은 dry-run이며, --apply 지정 시 실제 반영
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return bool(row)


def _col_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(r[1]).strip().lower() for r in rows}


def _fetch_active_duplicate_groups_by_lot(conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT lot_no, COUNT(*) AS cnt
        FROM allocation_plan
        WHERE COALESCE(TRIM(lot_no), '') != ''
          AND status IN ('STAGED', 'RESERVED')
        GROUP BY lot_no
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, lot_no ASC
        """
    ).fetchall()
    return [{"lot_no": str(r[0] or ""), "cnt": int(r[1] or 0)} for r in rows]


def _fetch_active_rows_for_lot(conn: sqlite3.Connection, lot_no: str) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT id, lot_no, status,
               COALESCE(workflow_status, '') AS workflow_status,
               COALESCE(created_at, '') AS created_at
        FROM allocation_plan
        WHERE lot_no = ?
          AND status IN ('STAGED', 'RESERVED')
        ORDER BY
            CASE WHEN COALESCE(created_at, '') = '' THEN 1 ELSE 0 END,
            created_at DESC,
            id DESC
        """,
        (lot_no,),
    ).fetchall()
    return [
        {
            "id": int(r[0]),
            "lot_no": str(r[1] or ""),
            "status": str(r[2] or ""),
            "workflow_status": str(r[3] or ""),
            "created_at": str(r[4] or ""),
        }
        for r in rows
    ]


def _fetch_active_duplicate_groups_exact(conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT
            lot_no,
            COALESCE(customer, '') AS customer,
            COALESCE(sale_ref, '') AS sale_ref,
            COALESCE(outbound_date, '') AS outbound_date,
            COALESCE(qty_mt, 0) AS qty_mt,
            COALESCE(status, '') AS status,
            COALESCE(workflow_status, '') AS workflow_status,
            COALESCE(tonbag_id, -1) AS tonbag_id,
            COALESCE(sub_lt, -1) AS sub_lt,
            COUNT(*) AS cnt
        FROM allocation_plan
        WHERE COALESCE(TRIM(lot_no), '') != ''
          AND status IN ('STAGED', 'RESERVED')
        GROUP BY
            lot_no, customer, sale_ref, outbound_date,
            qty_mt, status, workflow_status, tonbag_id, sub_lt
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, lot_no ASC
        """
    ).fetchall()
    out: List[Dict] = []
    for r in rows:
        out.append(
            {
                "lot_no": str(r[0] or ""),
                "customer": str(r[1] or ""),
                "sale_ref": str(r[2] or ""),
                "outbound_date": str(r[3] or ""),
                "qty_mt": float(r[4] or 0),
                "status": str(r[5] or ""),
                "workflow_status": str(r[6] or ""),
                "tonbag_id": int(r[7] or -1),
                "sub_lt": int(r[8] or -1),
                "cnt": int(r[9] or 0),
            }
        )
    return out


def _fetch_active_rows_for_exact_group(conn: sqlite3.Connection, g: Dict) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT id, lot_no, status,
               COALESCE(workflow_status, '') AS workflow_status,
               COALESCE(created_at, '') AS created_at
        FROM allocation_plan
        WHERE lot_no = ?
          AND COALESCE(customer, '') = ?
          AND COALESCE(sale_ref, '') = ?
          AND COALESCE(outbound_date, '') = ?
          AND COALESCE(qty_mt, 0) = ?
          AND COALESCE(status, '') = ?
          AND COALESCE(workflow_status, '') = ?
          AND COALESCE(tonbag_id, -1) = ?
          AND COALESCE(sub_lt, -1) = ?
          AND status IN ('STAGED', 'RESERVED')
        ORDER BY
            CASE WHEN COALESCE(created_at, '') = '' THEN 1 ELSE 0 END,
            created_at DESC,
            id DESC
        """,
        (
            g["lot_no"],
            g["customer"],
            g["sale_ref"],
            g["outbound_date"],
            g["qty_mt"],
            g["status"],
            g["workflow_status"],
            g["tonbag_id"],
            g["sub_lt"],
        ),
    ).fetchall()
    return [
        {
            "id": int(r[0]),
            "lot_no": str(r[1] or ""),
            "status": str(r[2] or ""),
            "workflow_status": str(r[3] or ""),
            "created_at": str(r[4] or ""),
        }
        for r in rows
    ]


def _update_deactivate_row(
    conn: sqlite3.Connection,
    row_id: int,
    has_workflow: bool,
    has_rejected_reason: bool,
    has_approved_by: bool,
    has_approved_at: bool,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sets = ["status = 'CANCELLED'"]
    params: List = []
    if has_workflow:
        sets.append("workflow_status = 'REJECTED'")
    if has_rejected_reason:
        sets.append("rejected_reason = COALESCE(NULLIF(rejected_reason, ''), 'DUPLICATE_CLEANUP')")
    if has_approved_by:
        sets.append("approved_by = COALESCE(NULLIF(approved_by, ''), ?)")
        params.append("duplicate_cleanup")
    if has_approved_at:
        sets.append("approved_at = COALESCE(approved_at, ?)")
        params.append(now)

    sql = f"UPDATE allocation_plan SET {', '.join(sets)} WHERE id = ?"
    params.append(row_id)
    conn.execute(sql, tuple(params))


def run(db_path: Path, apply: bool, mode: str) -> int:
    if not db_path.exists():
        print(f"[오류] DB 파일 없음: {db_path}")
        return 2

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "allocation_plan"):
            print("[안내] allocation_plan 테이블이 없어 종료합니다.")
            return 0

        cols = _col_names(conn, "allocation_plan")
        has_workflow = "workflow_status" in cols
        has_rejected_reason = "rejected_reason" in cols
        has_approved_by = "approved_by" in cols
        has_approved_at = "approved_at" in cols

        if mode == "lot":
            dup_groups = _fetch_active_duplicate_groups_by_lot(conn)
        else:
            dup_groups = _fetch_active_duplicate_groups_exact(conn)
        if not dup_groups:
            print("[완료] 활성 중복 LOT가 없습니다.")
            return 0

        print(f"[진단] 활성 중복 그룹: {len(dup_groups)}건 (mode={mode})")

        actions: List[Dict] = []
        for g in dup_groups:
            lot_no = g["lot_no"]
            if mode == "lot":
                rows = _fetch_active_rows_for_lot(conn, lot_no)
            else:
                rows = _fetch_active_rows_for_exact_group(conn, g)
            if len(rows) <= 1:
                continue
            keep_row = rows[0]
            drop_rows = rows[1:]
            actions.append(
                {
                    "lot_no": lot_no,
                    "keep_id": keep_row["id"],
                    "drop_ids": [r["id"] for r in drop_rows],
                }
            )

        total_drop = sum(len(a["drop_ids"]) for a in actions)
        print(f"[계획] 유지 {len(actions)}건 / 비활성화 {total_drop}행")
        for a in actions[:20]:
            print(f" - LOT {a['lot_no']}: keep id={a['keep_id']} / drop={a['drop_ids']}")
        if len(actions) > 20:
            print(f" ... 외 {len(actions) - 20} LOT")

        if not apply:
            print("\n[dry-run] 실제 반영 없음. --apply 옵션으로 실행하면 적용됩니다.")
            return 0

        backup_path = db_path.with_suffix(db_path.suffix + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(db_path, backup_path)
        print(f"[백업] {backup_path}")

        with conn:
            for a in actions:
                for row_id in a["drop_ids"]:
                    _update_deactivate_row(
                        conn,
                        row_id,
                        has_workflow=has_workflow,
                        has_rejected_reason=has_rejected_reason,
                        has_approved_by=has_approved_by,
                        has_approved_at=has_approved_at,
                    )

        print(f"[적용 완료] 비활성화 {total_drop}행 처리됨")
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="allocation_plan 활성 중복 정리")
    parser.add_argument(
        "--db",
        type=str,
        default="data/db/sqm_inventory.db",
        help="SQLite DB 경로",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제 반영(기본은 dry-run)",
    )
    parser.add_argument(
        "--mode",
        choices=["exact", "lot"],
        default="exact",
        help="중복 판정 모드: exact(권장) | lot(LOT당 1건만 유지)",
    )
    args = parser.parse_args()
    return run(Path(args.db).resolve(), apply=bool(args.apply), mode=str(args.mode))


if __name__ == "__main__":
    raise SystemExit(main())
