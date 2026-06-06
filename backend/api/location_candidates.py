"""Helpers for displaying location-map import data as rack location candidates.

The helpers are read-only. They never update inventory_tonbag.location.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return bool(row)


def load_latest_candidates(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """Return {lot_no: [{location, tonbag_count}, ...]} for latest import batch."""
    if not _table_exists(con, "lot_location_import_batch") or not _table_exists(con, "lot_location_map"):
        return {}
    batch = con.execute("SELECT MAX(id) AS id FROM lot_location_import_batch").fetchone()
    batch_id = batch["id"] if batch and batch["id"] is not None else None
    if not batch_id:
        return {}

    out: dict[str, list[dict]] = {}
    rows = con.execute(
        """
        SELECT lot_no, location, tonbag_count
          FROM lot_location_map
         WHERE batch_id=?
         ORDER BY lot_no, dong, rack, col, level, location
        """,
        (batch_id,),
    ).fetchall()
    for r in rows:
        lot_no = str(r["lot_no"] or "").strip()
        if not lot_no:
            continue
        out.setdefault(lot_no, []).append({
            "location": str(r["location"] or "").strip(),
            "tonbag_count": int(r["tonbag_count"] or 0),
        })
    return out


def summarize_candidates(candidates: Iterable[dict]) -> str:
    """Return a LOT-level candidate summary like 'G6-... [2], G6-... [1]'."""
    parts = []
    for c in candidates or []:
        loc = str(c.get("location") or "").strip()
        cnt = int(c.get("tonbag_count") or 0)
        if loc and cnt > 0:
            parts.append(f"{loc} [{cnt}]")
    return ", ".join(parts)


def expand_candidates_for_sublots(candidates: Iterable[dict], sub_lts: Iterable) -> dict[int, str]:
    """
    Assign rack candidates to Sub LT rows by current operating rule:
    sort Sub LT ascending, then consume each location tonbag_count times.
    """
    ordered_subs = sorted(int(s) for s in sub_lts if s is not None)
    expanded_locations: list[str] = []
    for c in candidates or []:
        loc = str(c.get("location") or "").strip()
        cnt = int(c.get("tonbag_count") or 0)
        if loc and cnt > 0:
            expanded_locations.extend([loc] * cnt)
    return {
        sub_lt: expanded_locations[idx]
        for idx, sub_lt in enumerate(ordered_subs)
        if idx < len(expanded_locations)
    }
