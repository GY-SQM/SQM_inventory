"""
Repair truncated B/L numbers in SQLite.

Use dry-run by default:
  python scripts/fix_truncated_bl_numbers.py

Apply updates:
  python scripts/fix_truncated_bl_numbers.py --apply
"""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

try:
    import fitz  # PyMuPDF
except ImportError as e:  # pragma: no cover
    raise SystemExit("PyMuPDF is required: pip install pymupdf") from e

# Reuse project BL parser (same logic as app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from parsers.document_parser_modular.parser import DocumentParserV3


SAP_RE = re.compile(r"\b22\d{8}\b")
ALNUM_BL_RE = re.compile(r"\b[A-Z]{4,8}\d{6,12}\b")
NUM_BL_RE = re.compile(r"\b\d{6,12}\b")


def _extract_sap_from_text(text: str) -> Optional[str]:
    m = SAP_RE.search(text or "")
    return m.group(0) if m else None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().upper()


def _extract_bl_candidate(text: str) -> Optional[str]:
    t = _normalize_text(text)
    if not t:
        return None
    # Prefer anchors near B/L labels
    anchor = re.search(
        r"(B\s*/?\s*L\s*NO\.?|BILL\s+OF\s+LADING\s*NO\.?)[:\s]{1,20}([A-Z0-9\- ]{6,40})",
        t,
        re.IGNORECASE,
    )
    if anchor:
        block = anchor.group(2)
        m = ALNUM_BL_RE.search(block)
        if m:
            return m.group(0)
    # Fallback: best alnum candidate globally
    candidates = ALNUM_BL_RE.findall(t)
    if candidates:
        # longest first, then earliest occurrence
        candidates = sorted(set(candidates), key=lambda x: (-len(x), t.find(x)))
        return candidates[0]
    return None


def _read_pdf_text(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    try:
        chunks = []
        for page in doc:
            chunks.append(page.get_text("text") or "")
        return "\n".join(chunks)
    finally:
        doc.close()


def _iter_bl_files(source_roots: Iterable[Path]) -> Iterable[Path]:
    for root in source_roots:
        if not root.exists():
            continue
        for p in root.rglob("*.pdf"):
            name = p.name.upper()
            if "BL" in name or "BILL" in name:
                yield p


def discover_sap_bl_map(source_roots: Iterable[Path]) -> Dict[str, str]:
    sap_to_bl: Dict[str, str] = {}
    parser = DocumentParserV3(gemini_api_key="")
    for pdf in _iter_bl_files(source_roots):
        text = _read_pdf_text(pdf)
        sap = _extract_sap_from_text(str(pdf)) or _extract_sap_from_text(text)
        if not sap:
            continue
        bl = None
        try:
            bl_result = parser.parse_bl(str(pdf))
            bl = str(getattr(bl_result, "bl_no", "") or "").strip().upper()
        except Exception:
            bl = None
        if not bl:
            bl = _extract_bl_candidate(text)
        if not bl:
            continue
        if re.search(r"[A-Z]", bl) and re.search(r"\d", bl):
            sap_to_bl[sap] = bl
    return sap_to_bl


def _backup_db(db_path: Path) -> Path:
    backup = db_path.with_suffix(f".backup_blfix{db_path.suffix}")
    shutil.copy2(db_path, backup)
    return backup


def run(db_path: Path, source_roots: Iterable[Path], apply: bool) -> int:
    sap_to_bl = discover_sap_bl_map(source_roots)
    if not sap_to_bl:
        print("No recoverable SAP->BL mapping found.")
        return 1

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute(
        """
        SELECT sap_no, bl_no, COUNT(*) AS cnt
        FROM inventory
        WHERE COALESCE(sap_no, '') <> ''
        GROUP BY sap_no, bl_no
        ORDER BY sap_no
        """
    ).fetchall()

    plan = []
    for r in rows:
        sap = str(r["sap_no"] or "").strip()
        current_bl = str(r["bl_no"] or "").strip()
        full_bl = sap_to_bl.get(sap, "")
        if not full_bl:
            continue
        digits = "".join(NUM_BL_RE.findall(full_bl))
        digits = digits if digits else re.sub(r"\D", "", full_bl)
        if not current_bl:
            plan.append((sap, current_bl, full_bl))
            continue
        if re.fullmatch(r"\d{6,12}", current_bl):
            if current_bl == digits or digits.endswith(current_bl):
                plan.append((sap, current_bl, full_bl))

    print(f"Mappings discovered: {len(sap_to_bl)}")
    print(f"Planned SAP fixes: {len(plan)}")
    for sap, old_bl, new_bl in plan:
        print(f"- SAP {sap}: {old_bl} -> {new_bl}")

    if not apply:
        print("Dry-run only. Use --apply to update DB.")
        con.close()
        return 0

    backup = _backup_db(db_path)
    print(f"Backup created: {backup}")

    inv_updated = 0
    tb_updated = 0
    with con:
        for sap, old_bl, new_bl in plan:
            digits = re.sub(r"\D", "", new_bl)
            inv_updated += cur.execute(
                """
                UPDATE inventory
                SET bl_no = ?
                WHERE sap_no = ?
                  AND (
                        COALESCE(bl_no,'') = ''
                        OR bl_no = ?
                        OR bl_no = ?
                      )
                """,
                (new_bl, sap, old_bl, digits),
            ).rowcount
            tb_updated += cur.execute(
                """
                UPDATE inventory_tonbag
                SET bl_no = ?
                WHERE sap_no = ?
                  AND (
                        COALESCE(bl_no,'') = ''
                        OR bl_no = ?
                        OR bl_no = ?
                      )
                """,
                (new_bl, sap, old_bl, digits),
            ).rowcount

    con.close()
    print(f"Updated inventory rows: {inv_updated}")
    print(f"Updated inventory_tonbag rows: {tb_updated}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix truncated BL numbers.")
    parser.add_argument(
        "--db",
        default=r"d:\프로그램\Sqm 재고관리\SQM V6.3.2\data\db\sqm_inventory.db",
        help="SQLite DB path",
    )
    parser.add_argument(
        "--source-root",
        action="append",
        default=[
            r"d:\프로그램\Sqm 재고관리\sample inbound data",
            r"d:\프로그램\Sqm 재고관리\SQM V6.3.2\data\proof_docs",
        ],
        help="Root directory containing BL pdf files (repeatable)",
    )
    parser.add_argument("--apply", action="store_true", help="Apply DB updates")
    args = parser.parse_args()

    db_path = Path(args.db)
    roots = [Path(p) for p in args.source_root]
    return run(db_path, roots, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
