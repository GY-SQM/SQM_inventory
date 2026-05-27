# -*- coding: utf-8 -*-
"""
features/parsers/location_inventory_parser.py — SQM v8.7.0
============================================================
위치재고조회 엑셀 파서 + 검증

대상 파일: 위치재고조회_YYYYMMDD_HHMMSS.xlsx
  헤더: 품명 | 화주 | 위치 | BAG | LOT | SAP | 단위 | 재고
        (품목/구분/수량 등 다른 표기도 _COL_ALIASES 로 흡수 — 컬럼 매칭 참고)
  1행 = 1 LOT
  '위치' 셀 = 멀티라인 — 각 줄 'G{동}-{칸}-{열}-{층} [N]'
    예) G6-08-13-01 [2]
    [N] = 그 랙 셀에 적재된 톤백 수 ([2]=2개, [1]=1개)

검증 항목 (DB 불필요 — 파일 자체 검증):
  - 위치 형식: warehouse_cell_logic.validate_cell_location (신형식 G{동}-{칸}-{열}-{층})
  - 셀 중복: 파일 내 같은 셀을 2개 LOT이 점유 → error
  - LOT 중복: 파일 내 같은 LOT번호가 2번 → error
  - [N] 누락: 괄호 없는 줄 → error
  - 수량 컬럼 vs [N] 합 불일치 → warning

입고 10개 검증은 "신규 LOT 여부"(DB 비교)가 필요하므로 이 파서에서는
tonbag_sum 만 계산하고, 판정은 backend/api/location_map_api.py 가 수행한다.

[수정이력]
  2026-05-19  Ruby  v8.7.0 신규 — 위치재고조회 엑셀 import 기능
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List

from engine_modules.warehouse_cell_logic import validate_cell_location

logger = logging.getLogger(__name__)

# 한 LOT(탄산리튬)의 정상 톤백 수 — 입고 검증 기준값
EXPECTED_TONBAGS_PER_LOT = 10

# 세로 채움 한 랙 셀의 정상 톤백 수 (1+1 2-pack) — '누락 셀' 판정용
NORMAL_CELL_TONBAGS = 2

# '위치' 셀 한 줄: 'G6-08-13-01 [2]' — 위치 + 선택적 [N]
_LINE_RE = re.compile(r'^\s*(.+?)\s*(?:\[\s*(\d+)\s*\])?\s*$')

# 컬럼 별칭 (소문자·공백제거 후 비교)
_COL_ALIASES = {
    'product':  ['품목', '품명', 'product', 'item'],
    'shipper':  ['화주', 'shipper', 'owner'],
    'location': ['위치', 'location', '로케이션', 'loc'],
    'bag':      ['bag', '백'],
    'lot_no':   ['lot', 'lotno', 'lot_no', 'lot no', '로트', '롯트'],
    'sap_no':   ['sap', 'sapno', 'sap_no', 'sap no'],
    'category': ['구분', '단위', 'category', 'type', 'gubun', 'unit'],
    'qty':      ['수량', '재고', 'qty', 'quantity', 'count', 'stock'],
}


def _norm(v: Any) -> str:
    return str(v if v is not None else '').strip()


def _match_columns(header_cells: list) -> Dict[str, int]:
    """헤더 행 셀 리스트 → {표준키: 컬럼인덱스}"""
    result: Dict[str, int] = {}
    for ci, cell in enumerate(header_cells):
        low = _norm(cell).lower()
        if not low:
            continue
        for std, aliases in _COL_ALIASES.items():
            if std in result:
                continue
            if low in aliases:
                result[std] = ci
                break
    return result


def _empty_doc(source_file: str) -> Dict[str, Any]:
    return {
        'ok': False,
        'source_file': source_file,
        'lots': [],
        'errors': [],
        'warnings': [],
        'stats': {},
    }


def parse_location_inventory_excel(xlsx_path: str) -> Dict[str, Any]:
    """
    위치재고조회 엑셀 → 구조화 doc + 파일 검증.

    반환 doc:
      ok          : bool — 치명적 에러(errors) 없음
      source_file : str
      lots[]      : LOT별 dict
        lot_no, product, shipper, sap_no, category, qty(int|None),
        row_num, tonbag_sum(int), short_count(int — 10 미만 부족분),
        cells[]: {location, dong, rack, col, level, tonbag_count,
                  valid(bool), reason}
      errors[]    : 치명적 — 형식오류 / 셀중복 / LOT중복 / [N]누락
      warnings[]  : 비치명 — 수량 불일치 / 빈 위치 등
      stats       : 집계
    """
    doc = _empty_doc(os.path.basename(xlsx_path))

    try:
        import openpyxl
    except ImportError:
        doc['errors'].append('openpyxl 미설치')
        return doc

    try:
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001
        doc['errors'].append(f'Excel 열기 실패: {exc}')
        return doc

    grid: List[list] = []
    try:
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            grid.append(list(row))
    finally:
        wb.close()

    # ── 헤더 행 탐색 (위치 + LOT 동시 포함) ──
    hdr_idx = None
    col: Dict[str, int] = {}
    for ri, row in enumerate(grid[:12]):
        cmap = _match_columns(row)
        if 'location' in cmap and 'lot_no' in cmap:
            hdr_idx = ri
            col = cmap
            break

    if hdr_idx is None:
        doc['errors'].append('헤더 인식 실패 — "위치" + "LOT" 컬럼이 필요합니다')
        return doc

    seen_lots: Dict[str, int] = {}            # lot_no -> 최초 발견 행번호(1-based)
    seen_cells: Dict[str, tuple] = {}         # location -> (lot_no, 행번호)

    for ri in range(hdr_idx + 1, len(grid)):
        row = grid[ri]
        row_num = ri + 1  # 엑셀 1-based 행번호

        def _cell(key: str):
            ci = col.get(key)
            if ci is None or ci >= len(row):
                return None
            return row[ci]

        lot_raw = _norm(_cell('lot_no'))
        if not lot_raw:
            continue  # 빈 LOT 행은 조용히 건너뜀
        # '1126030122.0' 같은 float 문자열 정규화
        lot_no = lot_raw
        if lot_raw.replace('.', '', 1).isdigit() and lot_raw.endswith('.0'):
            lot_no = lot_raw[:-2]

        loc_raw = _cell('location')
        if loc_raw is None or not _norm(loc_raw):
            doc['warnings'].append(f'행 {row_num}: LOT {lot_no} — 위치 비어있음 (건너뜀)')
            continue

        # ── 위치 셀 멀티라인 분해 ──
        cells: List[Dict[str, Any]] = []
        for line in str(loc_raw).split('\n'):
            line = line.strip()
            if not line:
                continue
            m = _LINE_RE.match(line)
            loc_str = (m.group(1).strip() if m else line).upper()
            n_str = m.group(2) if (m and m.group(2)) else None

            v = validate_cell_location(loc_str)
            entry = {
                'location': loc_str,
                'dong':  v.get('dong'),
                'rack':  v.get('rack'),
                'col':   v.get('col'),
                'level': v.get('level'),
                'tonbag_count': int(n_str) if n_str else 0,
                'valid': bool(v.get('ok')),
                'reason': '' if v.get('ok') else (v.get('reason') or '위치 형식 오류'),
            }
            if n_str is None:
                entry['valid'] = False
                entry['reason'] = '[N] 톤백수 누락 (예: G6-08-13-01 [2])'
            cells.append(entry)

        # ── LOT 중복 검사 ──
        if lot_no in seen_lots:
            doc['errors'].append(
                f'LOT 중복: {lot_no} — 행 {seen_lots[lot_no]} & 행 {row_num}')
        else:
            seen_lots[lot_no] = row_num

        # ── 셀 중복 검사 + 형식 오류 수집 ──
        for c in cells:
            if not c['valid']:
                doc['errors'].append(
                    f"행 {row_num} LOT {lot_no}: '{c['location']}' — {c['reason']}")
                continue
            loc = c['location']
            if loc in seen_cells:
                p_lot, p_row = seen_cells[loc]
                doc['errors'].append(
                    f'셀 중복: {loc} — LOT {p_lot}(행{p_row}) & LOT {lot_no}(행{row_num})')
            else:
                seen_cells[loc] = (lot_no, row_num)

        tonbag_sum = sum(c['tonbag_count'] for c in cells)

        # ── 수량 컬럼 정합성 (비치명) ──
        qty_raw = _cell('qty')
        try:
            qty_int = int(float(qty_raw)) if qty_raw not in (None, '') else None
        except (ValueError, TypeError):
            qty_int = None
        if qty_int is not None and qty_int != tonbag_sum:
            doc['warnings'].append(
                f'행 {row_num} LOT {lot_no}: 수량컬럼({qty_int}) ≠ [N]합({tonbag_sum})')

        doc['lots'].append({
            'lot_no':      lot_no,
            'product':     _norm(_cell('product')),
            'shipper':     _norm(_cell('shipper')),
            'sap_no':      _norm(_cell('sap_no')),
            'category':    _norm(_cell('category')),
            'qty':         qty_int,
            'row_num':     row_num,
            'tonbag_sum':  tonbag_sum,
            'short_count': max(0, EXPECTED_TONBAGS_PER_LOT - tonbag_sum),
            'cells':       cells,
        })

    # ── 집계 ──
    total_cells = sum(len(l['cells']) for l in doc['lots'])
    total_tonbags = sum(l['tonbag_sum'] for l in doc['lots'])
    doc['stats'] = {
        'total_lots':    len(doc['lots']),
        'total_cells':   total_cells,
        'total_tonbags': total_tonbags,
        'error_count':   len(doc['errors']),
        'warning_count': len(doc['warnings']),
    }
    doc['ok'] = (len(doc['errors']) == 0 and len(doc['lots']) > 0)
    if not doc['lots']:
        doc['errors'].append('유효한 LOT 데이터 행이 없습니다')

    logger.info(
        '[LocationInventoryParser] %s — LOT %d / 셀 %d / 톤백 %d / 에러 %d / 경고 %d',
        doc['source_file'], doc['stats']['total_lots'], total_cells,
        total_tonbags, len(doc['errors']), len(doc['warnings']),
    )
    return doc


def find_missing_cells(lot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    한 LOT에서 톤백수가 정상(2개)에 못 미치는 셀 목록 반환.
    입고 누락(바코드 스캔 누락) 셀을 지목하는 데 사용.
    (6·7층 가로 채움 로직 확정 전까지는 세로 채움 capacity=2 기준)
    """
    return [
        {
            'location':     c['location'],
            'tonbag_count': c['tonbag_count'],
            'shortage':     NORMAL_CELL_TONBAGS - c['tonbag_count'],
        }
        for c in lot.get('cells', [])
        if c.get('valid') and c['tonbag_count'] < NORMAL_CELL_TONBAGS
    ]
