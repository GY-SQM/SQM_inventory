# -*- coding: utf-8 -*-
"""
SQM 피킹리스트 PDF 파서 (v6.1.0 출고 로직)
==========================================
파일 위치: parsers/document_parser_modular/picking_mixin.py

실데이터 기반 (LBM-LC20250901):
  - 5페이지 PDF, 역순 저장
  - 60 LOT, 300 MT 톤백 + 60 kg 샘플
  - KG(샘플)/MT(톤백) 각 60개 — 1:1 완전 매칭
  - 중복 등장: 전 LOT 2회 (KG/MT 각 섹션에서 1회씩)
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

UNIT_WEIGHT_KG = 500  # 기본 단위: 500kg 톤백


@dataclass
class PickingListMeta:
    picking_no:        str = ''   # LBM-LC20250901
    sales_order:       str = ''   # 3073
    outbound_id:       str = ''   # 80007418
    creation_date:     str = ''   # 15.01.2026
    delivery_terms:    str = ''   # CIF-Semarang Port
    containers:        str = '1'
    cutoff_date:       str = ''   # 29.01.2026
    plan_loading_date: str = ''
    contact_person:    str = ''   # HyunChae Woo
    contact_email:     str = ''   # Hyun.Chae.Woo@sqm.com
    port_loading:      str = ''   # Gwangyang
    port_discharge:    str = ''   # Semarang
    total_nw_kg:       str = ''   # 300,000.00  KG
    total_gw_kg:       str = ''


@dataclass
class PickingLotItem:
    lot_no:    str
    weight_kg: float
    unit:      str   # 'MT' | 'KG'
    storage:   str = ''


@dataclass
class PickingListResult:
    meta:    PickingListMeta           = field(default_factory=PickingListMeta)
    tonbag:  List[PickingLotItem]      = field(default_factory=list)
    sample:  List[PickingLotItem]      = field(default_factory=list)
    summary: Dict                      = field(default_factory=dict)
    errors:  List[str]                 = field(default_factory=list)
    success: bool                      = False


class PickingListParserMixin:
    """
    피킹리스트 PDF 파서 Mixin.

    사용법:
        result = parser.parse_picking_list('LBM_AP_SO_3073_Picking_list1.pdf')
        if result.success:
            for item in result.tonbag:
                print(item.lot_no, item.weight_kg)
    """

    def parse_picking_list(self, pdf_path: str) -> PickingListResult:
        """피킹리스트 PDF를 파싱하여 LOT/톤백/샘플/메타 데이터를 반환."""
        result = PickingListResult()
        try:
            blocks = self._extract_pdf_blocks(pdf_path)
            if not blocks:
                result.errors.append('PDF 텍스트 추출 실패')
                return result

            # 데이터 파싱
            all_items = self._parse_quantity_blocks(blocks)
            result.tonbag = self._dedup(all_items, 'MT')
            result.sample = self._dedup(all_items, 'KG')

            # 메타데이터 파싱 (Page1 = 마지막 페이지 헤더 기준)
            result.meta = self._parse_meta(blocks)

            # 검증
            tb_set = {r.lot_no for r in result.tonbag}
            sp_set = {r.lot_no for r in result.sample}

            if tb_set - sp_set:
                result.errors.append(
                    f'샘플 없는 톤백 LOT {len(tb_set - sp_set)}개: {sorted(tb_set - sp_set)[:5]}...'
                )
            if sp_set - tb_set:
                result.errors.append(
                    f'톤백 없는 샘플 LOT {len(sp_set - tb_set)}개: {sorted(sp_set - tb_set)[:5]}...'
                )

            total_mt  = sum(r.weight_kg for r in result.tonbag) / 1000
            total_spkg = sum(r.weight_kg for r in result.sample)

            result.summary = {
                'total_lots':       len(tb_set),
                'total_mt':         total_mt,
                'total_sample_kg':  total_spkg,
                'lot_integrity':    tb_set == sp_set,
                'tonbag_count':     len(result.tonbag),
                'sample_count':     len(result.sample),
            }

            result.success = len(result.errors) == 0
            logger.info(
                f'[PickingParser] 파싱 완료: {len(tb_set)} LOT / '
                f'{total_mt:.1f} MT / 샘플 {total_spkg:.0f} kg'
            )

        except (OSError, ValueError, TypeError) as e:
            result.errors.append(f'파싱 예외: {e}')
            logger.debug(f'Suppressed: {e}')

        return result

    def _extract_pdf_blocks(self, pdf_path: str) -> List[str]:
        """PDF 원시 바이트에서 텍스트 블록 추출 (Tj 연산자 기반)."""
        try:
            with open(pdf_path, 'rb') as f:
                raw = f.read().decode('latin-1', errors='replace')
            return re.findall(r'\(([^)]+)\)Tj', raw)
        except OSError as e:
            logger.error(f'PDF 읽기 실패: {e}')
            return []

    def _parse_quantity_blocks(self, blocks: List[str]) -> List[PickingLotItem]:
        """전체 블록에서 Quantity → Batch → Storage 패턴 순차 추출."""
        items = []
        i = 0
        while i < len(blocks):
            qty_m = re.match(
                r'^Quantity:\s*([\d.]+)\s*(MT|KG)$', blocks[i].strip()
            )
            if qty_m:
                qty_val   = float(qty_m.group(1))
                unit      = qty_m.group(2)
                weight_kg = qty_val * 1000 if unit == 'MT' else qty_val
                lot_no    = ''
                storage   = ''

                if i + 1 < len(blocks) and 'Batch number' in blocks[i + 1]:
                    lot_no = blocks[i + 1].replace('Batch number: ', '').strip()
                    i += 1
                if i + 1 < len(blocks) and 'Storage location' in blocks[i + 1]:
                    storage = blocks[i + 1].replace('Storage location: ', '').strip()
                    i += 1

                if lot_no:
                    items.append(PickingLotItem(
                        lot_no=lot_no, weight_kg=weight_kg,
                        unit=unit, storage=storage
                    ))
            i += 1
        return items

    def _dedup(self, items: List[PickingLotItem], unit: str) -> List[PickingLotItem]:
        """동일 lot_no + unit 쌍의 첫 번째만 유지 (중복 제거)."""
        seen: Dict = {}
        for it in items:
            if it.unit == unit and it.lot_no not in seen:
                seen[it.lot_no] = it
        return list(seen.values())

    def _parse_meta(self, blocks: List[str]) -> PickingListMeta:
        """Page1 블록(마지막 페이지)에서 메타데이터 추출."""
        meta = PickingListMeta()
        pl_positions = [i for i, b in enumerate(blocks) if 'PICKING LIST' in b]
        if not pl_positions:
            return meta

        p1_start = pl_positions[-1] + 1
        p1 = blocks[p1_start: p1_start + 45]

        def get(idx: int) -> str:
            return p1[idx].strip() if idx < len(p1) else ''

        meta.picking_no        = get(0)
        meta.sales_order       = get(1)
        meta.outbound_id       = get(2)
        meta.creation_date     = get(9)
        meta.delivery_terms    = get(10)
        meta.containers        = get(12)
        meta.cutoff_date       = get(15)
        meta.plan_loading_date = get(15)
        meta.contact_email     = get(22)
        meta.contact_person    = get(25)
        meta.port_discharge    = get(34)
        meta.port_loading      = get(36)

        for b in blocks:
            if re.search(r'[\d,]+\.\d+\s+KG', b):
                val = float(re.sub(r'[,\s]', '', b.replace('KG', '').strip()))
                if val > 200000:
                    if not meta.total_nw_kg:
                        meta.total_nw_kg = b.strip()
                    elif not meta.total_gw_kg:
                        meta.total_gw_kg = b.strip()

        return meta

    def expand_tonbags(
        self, result: PickingListResult, unit_weight: int = UNIT_WEIGHT_KG
    ) -> List[Dict]:
        """LOT 단위 톤백을 개별 행으로 분해."""
        rows = []
        for item in result.tonbag:
            count = max(1, round(item.weight_kg / unit_weight))
            for sub in range(1, count + 1):
                rows.append({
                    'type':      'TONBAG',
                    'lot_no':    item.lot_no,
                    'sub_lt':    sub,
                    'weight_kg': unit_weight,
                    'storage':   item.storage,
                    'status':    'PICKED',
                })
        sp_lots = {s.lot_no for s in result.sample}
        for item in result.tonbag:
            if item.lot_no in sp_lots:
                rows.append({
                    'type':      'SAMPLE',
                    'lot_no':    item.lot_no,
                    'sub_lt':    0,
                    'weight_kg': 1,
                    'storage':   item.storage,
                    'status':    'PICKED',
                })
        return rows
