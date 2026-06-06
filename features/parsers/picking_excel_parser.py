# -*- coding: utf-8 -*-
"""
SQM — Picking List Excel 파서
=============================
Picking List Excel(.xlsx/.xls) → picking_list_parser.parse_picking_list_pdf()
와 동일한 doc dict 반환. backend/api/outbound_api.py 의 picking-import-excel
엔드포인트에서 사용하며, 결과는 기존 picking_engine.apply_picking_list_to_db()
로 그대로 넘어간다 (PDF 경로와 엔진 공유).

Excel 형식:
  상단 키-값 : Outbound ID / Sales Order / Customer reference / Customer /
               Creation Date / Plan Loading Date
  데이터 헤더: Lot No | Quantity | Unit | Storage location
  데이터 행  : LOT별 본품(MT) 1행 + 샘플(KG) 1행

doc 구조: outbound_id, sales_order_no, picking_no, customer,
  creation_date, plan_loading_date, source_file, items[],
  total_normal_mt, total_sample_kg, total_lots, parse_method, parse_ok,
  warnings, bag_weight_kg
  items[]: {lot_no, qty_mt, qty_kg, unit, is_sample, storage_location}
"""
import logging
import os

logger = logging.getLogger(__name__)

# 상단 키-값 라벨 → doc 키 매핑 (소문자, 콜론 제거 후 비교)
_KV_LABELS = {
    'outbound id': 'outbound_id',
    'sales order': 'sales_order_no',
    'sales order no': 'sales_order_no',
    'customer reference': 'picking_no',
    'picking no': 'picking_no',
    'picking no.': 'picking_no',
    'customer': 'customer',
    'invoice account': 'customer',
    'creation date': 'creation_date',
    'plan loading date': 'plan_loading_date',
    'plan loading': 'plan_loading_date',
}


def _empty_doc(source_file: str = '') -> dict:
    return {
        'outbound_id': None,
        'sales_order_no': None,
        'picking_no': None,
        'customer': None,
        'creation_date': None,
        'plan_loading_date': None,
        'source_file': source_file,
        'items': [],
        'total_normal_mt': 0.0,
        'total_sample_kg': 0.0,
        'total_lots': 0,
        'parse_method': 'excel',
        'parse_ok': False,
        'warnings': [],
        'bag_weight_kg': 0,
    }


def parse_picking_list_excel(xlsx_path: str) -> dict:
    """Picking List Excel → doc dict (picking_engine 호환)."""
    doc = _empty_doc(os.path.basename(xlsx_path))

    try:
        import openpyxl
    except ImportError:
        doc['warnings'].append('openpyxl 미설치')
        return doc

    try:
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    except Exception as exc:
        doc['warnings'].append(f'Excel 열기 실패: {exc}')
        return doc

    grid = []
    try:
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            grid.append(list(row))
    finally:
        wb.close()

    # ── 상단 키-값 헤더 + 데이터 헤더 행 탐색 ──
    hdr_idx = None
    col = {}
    for ri, row in enumerate(grid):
        cells = [('' if c is None else str(c)).strip() for c in row]
        if not any(cells):
            continue
        low = [c.lower() for c in cells]
        joined = ' '.join(low)

        # 키-값 (A열 라벨 / B열 값)
        if len(cells) >= 2 and cells[0]:
            key = low[0].rstrip(':').strip()
            if key in _KV_LABELS and cells[1]:
                doc[_KV_LABELS[key]] = cells[1].strip()

        # 데이터 헤더 행 (Lot + Quantity 동시 포함)
        if hdr_idx is None and 'lot' in joined and ('quantity' in joined or 'qty' in joined):
            hdr_idx = ri
            for ci, c in enumerate(low):
                if 'lot' in c and 'lot' not in col:
                    col['lot'] = ci
                elif ('quantity' in c or c in ('qty', 'qty(mt)', 'qty (mt)')) and 'qty' not in col:
                    col['qty'] = ci
                elif c == 'unit' and 'unit' not in col:
                    col['unit'] = ci
                elif 'storage' in c and 'storage' not in col:
                    col['storage'] = ci

    if hdr_idx is None or 'lot' not in col or 'qty' not in col:
        doc['warnings'].append('헤더 인식 실패 — Lot No / Quantity 컬럼 필요')
        return doc

    # ── 데이터 행 파싱 ──
    seen = set()
    for row in grid[hdr_idx + 1:]:
        cells = list(row)

        def cell(key):
            ci = col.get(key)
            if ci is None or ci >= len(cells):
                return None
            return cells[ci]

        lot_raw = cell('lot')
        if lot_raw is None or str(lot_raw).strip() == '':
            continue
        lot_no = str(lot_raw).strip().split('.')[0]
        if not lot_no.isdigit() or len(lot_no) < 8:
            continue

        qty_raw = cell('qty')
        try:
            qty = float(str(qty_raw).replace(',', '').strip())
        except (ValueError, TypeError, AttributeError):
            continue
        if qty <= 0:
            continue

        unit = (str(cell('unit') or '').strip().upper() or 'MT')
        if unit not in ('MT', 'KG'):
            unit = 'MT'
        storage = str(cell('storage') or '').strip()

        key = (lot_no, unit)
        if key in seen:
            continue
        seen.add(key)

        if unit == 'MT':
            qty_kg = qty * 1000.0
            qty_mt = qty
            is_sample = False
        else:
            qty_kg = qty
            qty_mt = qty / 1000.0
            is_sample = qty <= 1.0

        doc['items'].append({
            'lot_no': lot_no,
            'qty_mt': round(qty_mt, 4),
            'qty_kg': round(qty_kg, 4),
            'unit': unit,
            'is_sample': is_sample,
            'storage_location': storage,
        })

    normal = [i for i in doc['items'] if not i['is_sample']]
    sample = [i for i in doc['items'] if i['is_sample']]
    doc['total_normal_mt'] = round(sum(i['qty_mt'] for i in normal), 3)
    doc['total_sample_kg'] = round(sum(i['qty_kg'] for i in sample), 3)
    doc['total_lots'] = len(normal)
    doc['parse_ok'] = bool(doc['items'])
    if not doc['items']:
        doc['warnings'].append('유효한 데이터 행 0건')
    else:
        logger.info(
            '[PickingExcelParser] 파싱 완료: LOT %d개 / 본품 %.3f MT / 샘플 %.1f KG',
            doc['total_lots'], doc['total_normal_mt'], doc['total_sample_kg'],
        )
    return doc
