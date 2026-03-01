import logging
# -*- coding: utf-8 -*-
"""
판매 가능(재고) vs 판매 배정(Allocation) LOT 규칙 검증.

- 규칙: 판매 배정 파일에 나오는 모든 LOT는 판매 가능(재고) 파일에 존재해야 함.
- LOT 정규화: "1125110452.0" -> "1125110452" (비교 시 동일 값으로 인식).
- 선택: LOT별 배정 수량(MT) 요약 (다음 단계: 재고 Available MT와 비교 가능).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from utils.common import normalize_lot

INVENTORY_PATH = ROOT.parent / "SQM-Inventory-2026_02_21.xlsx"
ALLOC_DIR = ROOT.parent / "generated_allocation"
ALLOC_FILES = [
    "Allocation - GY - PT LBM 300MT (2)-1.xlsx",
    "Allocation - GY - PT LBM 300MT (2)-2.xlsx",
    "Allocation - GY - PT LBM 300MT (2)-3.xlsx",
]


def get_inventory_lot_set(excel_path: Path) -> set:
    """SQM-Inventory(재고) 엑셀에서 LOT NO 목록 추출 (create_allocation_3files_from_inventory와 동일 로직)."""
    if not excel_path.exists():
        return set()
    xl = pd.ExcelFile(excel_path)
    sheet = "재고리스트" if "재고리스트" in xl.sheet_names else xl.sheet_names[0]
    df_raw = pd.read_excel(excel_path, sheet_name=sheet, header=None)

    def _norm(s):
        return str(s).strip().upper().replace(" ", "") if pd.notna(s) else ""

    header_row = 0
    for i in range(min(5, len(df_raw))):
        row = df_raw.iloc[i]
        if any("LOT" in _norm(v) for v in row):
            header_row = i
            break

    df = pd.read_excel(excel_path, sheet_name=sheet, header=header_row)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]

    lot_col = next((c for c in df.columns if "LOT" in c.upper() and "NO" in c.upper()), None)
    if lot_col is None:
        lot_col = next((c for c in df.columns if c.upper().startswith("LOT")), None)
    if lot_col is None:
        return set()

    lots = set()
    for _, r in df.iterrows():
        raw = r.get(lot_col, "")
        if pd.isna(raw):
            continue
        lot_no = normalize_lot(raw)
        if not lot_no:
            continue
        if lot_no.upper().startswith("LOT") and len(lot_no) < 15:
            continue
        if lot_no.isdigit() and 8 <= len(lot_no) <= 11:
            lots.add(lot_no)
        elif len(lot_no) >= 8:
            lots.add(lot_no)
    return lots


def get_allocation_lot_set(excel_path: Path) -> set:
    """Allocation 엑셀에서 LOT NO 목록 추출 (AllocationParser 사용)."""
    if not excel_path.exists():
        return set()
    try:
        from parsers.allocation_parser import AllocationParser
        parser = AllocationParser()
        result = parser.parse(str(excel_path))
        if not result or not result.rows:
            return set()
        out = set()
        for r in result.rows:
            lot = getattr(r, "lot_no", None) or (r.get("lot_no") if isinstance(r, dict) else None)
            if lot and str(lot).strip():
                out.add(str(lot).strip())
        return out
    except Exception as e:
        print(f"  [경고] {excel_path.name} 파싱 실패: {e}")
        return set()


def get_allocation_lot_qty_mt(allocation_paths: list) -> dict:
    """Allocation 파일들에서 LOT별 배정 수량(MT) 합계. {lot_no: total_qty_mt}"""
    from parsers.allocation_parser import AllocationParser
    parser = AllocationParser()
    lot_qty = {}
    for path in allocation_paths:
        if not path.exists():
            continue
        try:
            result = parser.parse(str(path))
            if not result or not result.rows:
                continue
            for r in result.rows:
                lot = getattr(r, "lot_no", None) or (r.get("lot_no") if isinstance(r, dict) else None)
                qty = float(getattr(r, "qty_mt", 0) or r.get("qty_mt", 0) or 0)
                if lot and str(lot).strip():
                    lot = str(lot).strip()
                    lot_qty[lot] = lot_qty.get(lot, 0) + qty
        except Exception as _pe:
            logging.getLogger(__name__).debug(f"[검증] 파일 파싱 오류: {_pe}")
    return lot_qty


def main():
    print("=" * 60)
    print("1) 판매 가능 파일 (재고) - SQM-Inventory-2026_02_21.xlsx")
    print("=" * 60)
    if not INVENTORY_PATH.exists():
        print(f"파일 없음: {INVENTORY_PATH}")
        return
    inv_lots = get_inventory_lot_set(INVENTORY_PATH)
    print(f"  재고 LOT 수: {len(inv_lots)}")
    if inv_lots:
        sample = sorted(inv_lots)[:8]
        print(f"  샘플 LOT: {sample}")

    print()
    print("2) 판매 배정 파일 (Allocation 3개)")
    print("=" * 60)
    alloc_lots = set()
    per_file = {}
    for fname in ALLOC_FILES:
        path = ALLOC_DIR / fname
        if not path.exists():
            print(f"  건너뜀 (없음): {fname}")
            continue
        lots = get_allocation_lot_set(path)
        per_file[fname] = lots
        alloc_lots |= lots
        print(f"  {fname}: LOT {len(lots)}개")
    print(f"  배정 쪽 총 LOT(중복 제거): {len(alloc_lots)}")

    print()
    print("3) 규칙 검사: 배정의 모든 LOT가 재고(판매 가능)에 있는가?")
    print("=" * 60)
    missing = alloc_lots - inv_lots
    if not missing:
        print("  결과: 규칙 준수 - 배정에 있는 모든 LOT가 재고에 존재합니다.")
    else:
        print(f"  결과: 미준수 - 재고에 없는 LOT가 {len(missing)}개 있습니다.")
        print("  (프로그램에서 '가용 톤백 없음'으로 뜨는 LOT와 일치합니다.)")
        for lot in sorted(missing)[:50]:
            print(f"    가용 톤백 없음: {lot}")
        if len(missing) > 50:
            print(f"    ... 외 {len(missing) - 50}개")

    only_in_inv = inv_lots - alloc_lots
    if only_in_inv and len(only_in_inv) <= 20:
        print()
        print("  참고: 재고에만 있고 배정에 없는 LOT (일부):", sorted(only_in_inv)[:20])

    print()
    print("4) LOT별 배정 수량(MT) - Allocation 합계")
    print("=" * 60)
    paths = [ALLOC_DIR / f for f in ALLOC_FILES]
    lot_qty = get_allocation_lot_qty_mt(paths)
    if lot_qty:
        total_mt = sum(lot_qty.values())
        print(f"  LOT 수: {len(lot_qty)}, 배정 총 MT: {total_mt:.4f}")
        for lot in sorted(lot_qty.keys())[:15]:
            print(f"    {lot}: {lot_qty[lot]:.4f} MT")
        if len(lot_qty) > 15:
            print(f"    ... 외 {len(lot_qty) - 15}개 LOT")
        print("  [다음 단계] 재고(DB) Available MT/KG와 비교 시, LOT별 수량 불일치를 바로 잡을 수 있습니다.")


if __name__ == "__main__":
    main()
