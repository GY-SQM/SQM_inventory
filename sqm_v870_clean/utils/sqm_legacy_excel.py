"""SQM legacy workbook column mapping helpers.

The legacy workbook uses the same physical 16th column for different
business meanings:

- IN:     "Salar Invoice no." duplicate / unused for sale reference
- UNSOLD: "SALE REF"
- SOLD:   "SALE REF"

Use these helpers whenever reading or writing the legacy IN/UNSOLD/SOLD
workbook so a Sales Order reference is never written into the IN duplicate
invoice column.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


def normalize_excel_header(value: Any) -> str:
    """Normalize an Excel header for alias matching."""
    text = "" if value is None else str(value)
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def normalize_sheet_name(value: Any) -> str:
    return str(value or "").strip().upper()


_ALIASES = {
    "lot_no": {"lot no", "lot_no", "lot", "lot번호", "로트", "로트번호"},
    "sap_no": {"sap no", "sap_no", "sap", "sap번호"},
    "bl_no": {"m b/l", "bl no", "bl_no", "b/l", "bl", "선하증권"},
    "container_no": {"cont's no", "container no", "container_no", "container", "컨테이너", "컨테이너번호"},
    "product": {"품명", "product", "product name", "product_name", "제품", "품목", "상품"},
    "salar_invoice_no": {"salar invoice no.", "salar invoice no", "salar invoice", "invoice", "인보이스"},
    "stock_date": {"입고일", "stock_date", "stock date", "inbound_date", "inbound date", "재고일"},
    "warehouse": {"위치", "warehouse", "warehouse_name", "wh", "창고"},
    "remark": {"remark", "remarks", "비고"},
}


def resolve_legacy_inventory_key(
    header: Any,
    *,
    sheet_name: str | None = None,
    column_index_1based: int | None = None,
) -> str | None:
    """Return the standard key for a legacy inventory workbook column.

    The special 16th-column rule is intentionally checked before generic
    aliases. It prevents IN column 16 from being interpreted as sale_ref.
    """
    sheet = normalize_sheet_name(sheet_name)
    header_norm = normalize_excel_header(header)

    if column_index_1based == 16:
        if sheet == "IN":
            if header_norm in _ALIASES["salar_invoice_no"]:
                return "salar_invoice_no_duplicate"
            return None
        if sheet in {"UNSOLD", "SOLD"}:
            if header_norm in {"sale ref", "sale_ref", "saleref", "sales ref", "sales_ref"}:
                return "sale_ref"

    if header_norm in {"sale ref", "sale_ref", "saleref", "sales ref", "sales_ref"}:
        return "sale_ref"

    for key, aliases in _ALIASES.items():
        if header_norm in aliases:
            return key
    return None


def build_inventory_column_map(
    columns: Iterable[Any],
    *,
    sheet_name: str | None = None,
    include_sale_ref: bool = True,
    include_duplicate_invoice: bool = False,
) -> dict[str, Any]:
    """Build {standard_key: original_column} for legacy inventory headers."""
    result: dict[str, Any] = {}
    for idx, col in enumerate(columns, start=1):
        key = resolve_legacy_inventory_key(
            col,
            sheet_name=sheet_name,
            column_index_1based=idx,
        )
        if not key:
            continue
        if key == "sale_ref" and not include_sale_ref:
            continue
        if key == "salar_invoice_no_duplicate" and not include_duplicate_invoice:
            continue
        result.setdefault(key, col)
    return result
