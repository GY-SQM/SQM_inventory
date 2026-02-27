# -*- coding: utf-8 -*-
"""
SQM 피킹리스트 PDF 파서 — 최종 로직 (라벨-라인 기반, 하드스톱 검증)
================================================================
파일: parsers/document_parser_modular/picking_mixin.py

문서 구조(고정 패턴):
  - Header: PICKING LIST, Customer reference(LBM-LC20250901), Requisition(3073),
    Sales order(80007418), Creation Date, Delivery terms, Ports, Containers(15 x40')
  - 본품: Quantity: 5.00 MT → Batch number: ... → Storage location: ...
  - 샘플: Quantity: 1.00 KG → Batch number: ... (동일 LOT)
  - 요약: Net 300,000.00 KG / Gross 307,800.00 KG, Big bag 500kg net 600ea

파이프라인: PDF/Text 추출 → 블록(줄) 목록 → Quantity/Batch/Storage 파싱 → 메타 파싱
            → 정규화(MT→kg, 콤마 제거) → 하드스톱 검증 → success/errors
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

UNIT_WEIGHT_KG = 500  # Big bag 500kg net (문서 기준)

# 파서가 기대하는 라벨 패턴
RE_QUANTITY = re.compile(
    r'^Quantity:\s*([\d,.]+)\s*(MT|KG)\s*$',
    re.IGNORECASE
)
RE_BATCH_NUMBER = re.compile(r'Batch number:\s*(.+)', re.IGNORECASE)
RE_STORAGE_LOCATION = re.compile(r'Storage location:\s*(.+)', re.IGNORECASE)
RE_LARGE_KG = re.compile(r'([\d,]+\.?\d*)\s*KG\b', re.IGNORECASE)


def _normalize_num(s: str) -> float:
    """천단위 콤마 제거 후 float. 빈 문자열/실패 시 0."""
    if not s or not isinstance(s, str):
        return 0.0
    try:
        return float(re.sub(r'[,\s]', '', s.strip()))
    except ValueError:
        return 0.0


@dataclass
class PickingListMeta:
    picking_no:        str = ''
    sales_order:       str = ''
    outbound_id:       str = ''
    creation_date:     str = ''
    delivery_terms:    str = ''
    containers:        str = '1'
    cutoff_date:       str = ''
    plan_loading_date: str = ''
    contact_person:    str = ''
    contact_email:     str = ''
    port_loading:      str = ''
    port_discharge:    str = ''
    total_nw_kg:       str = ''
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
    피킹리스트 파서 — 절대 예외로 죽지 않음. 실패 시 result.errors + success=False.

    진입점:
      - parse_picking_list(pdf_path)  : PDF 파일
      - parse_from_text(all_text)    : 이미 추출된 텍스트(OCR 등)
    """

    def parse_picking_list(self, pdf_path: str) -> PickingListResult:
        """PDF에서 텍스트 추출 후 파싱. 추출 실패 시 errors에 메시지."""
        result = PickingListResult()
        try:
            blocks = self._extract_pdf_blocks(pdf_path)
            if not blocks:
                result.errors.append('PDF 텍스트 추출 실패')
                return result
            return self._parse_blocks(blocks)
        except (OSError, ValueError, TypeError) as e:
            result.errors.append(f'파싱 예외: {e}')
            logger.debug(f'Suppressed: {e}')
            return result

    def parse_from_text(self, all_text: str) -> PickingListResult:
        """이미 추출된 전체 텍스트로 파싱(OCR/외부 추출 결과용)."""
        if not all_text or not all_text.strip():
            r = PickingListResult()
            r.errors.append('입력 텍스트가 비어 있습니다')
            return r
        blocks = [ln.strip() for ln in all_text.splitlines() if ln.strip()]
        return self._parse_blocks(blocks)

    def _parse_blocks(self, blocks: List[str]) -> PickingListResult:
        """공통: 블록(줄) 목록 → 파싱 → 정규화 → 하드스톱 검증 → Result."""
        result = PickingListResult()
        try:
            all_items = self._parse_quantity_blocks(blocks)
            result.tonbag = self._dedup(all_items, 'MT')
            result.sample = self._dedup(all_items, 'KG')
            result.meta = self._parse_meta(blocks)
            self._validate_hard_stops(result)
            total_mt = sum(r.weight_kg for r in result.tonbag) / 1000.0
            total_spkg = sum(r.weight_kg for r in result.sample)
            tb_set = {r.lot_no for r in result.tonbag}
            result.summary = {
                'total_lots':    len(tb_set),
                'total_mt':     total_mt,
                'total_sample_kg': total_spkg,
                'lot_integrity': tb_set == {s.lot_no for s in result.sample},
                'tonbag_count':  len(result.tonbag),
                'sample_count':  len(result.sample),
            }
            result.success = len(result.errors) == 0
            if result.success:
                logger.info(
                    f'[PickingParser] 파싱 완료: {len(tb_set)} LOT / '
                    f'{total_mt:.1f} MT / 샘플 {total_spkg:.0f} kg'
                )
        except (ValueError, TypeError) as e:
            result.errors.append(f'파싱 중 오류: {e}')
            logger.debug(f'Suppressed: {e}')
        return result

    def _validate_hard_stops(self, result: PickingListResult) -> None:
        """하드스톱 검증. 위반 시 result.errors에 추가."""
        tb = result.tonbag
        sp = result.sample
        tb_set = {r.lot_no for r in tb}
        sp_set = {s.lot_no for s in sp}

        if not tb:
            result.errors.append('본품(톤백) 배치가 없습니다. 문서 형식 또는 OCR을 확인하세요.')
        if not sp:
            result.errors.append('샘플 배치가 없습니다. 문서 형식 또는 OCR을 확인하세요.')

        if tb_set - sp_set:
            result.errors.append(
                f'샘플 없는 톤백 LOT {len(tb_set - sp_set)}개: {sorted(tb_set - sp_set)[:5]}...'
            )
        if sp_set - tb_set:
            result.errors.append(
                f'톤백 없는 샘플 LOT {len(sp_set - tb_set)}개: {sorted(sp_set - tb_set)[:5]}...'
            )

        sum_tonbag_kg = sum(r.weight_kg for r in tb)
        sum_sample_kg = sum(s.weight_kg for s in sp)
        if tb and abs(sum_tonbag_kg - len(tb) * 5000.0) > 1.0:
            expected_per_lot = sum_tonbag_kg / len(tb) if len(tb) else 0
            if expected_per_lot and abs(expected_per_lot - 5000.0) > 100.0:
                result.errors.append(
                    f'본품 배치당 중량 이상: 합계 {sum_tonbag_kg:.0f} kg, {len(tb)} LOT (기대: 5 MT/LOT)'
                )
        if sp and abs(sum_sample_kg - len(sp) * 1.0) > 0.01:
            result.errors.append(
                f'샘플 배치 합계 불일치: {sum_sample_kg:.2f} kg (기대: {len(sp)} kg, 1 kg/LOT)'
            )

        total_nw = result.meta.total_nw_kg
        if total_nw:
            nw_val = _normalize_num(RE_LARGE_KG.search(total_nw).group(1) if RE_LARGE_KG.search(total_nw) else total_nw)
            if nw_val > 100000 and abs(sum_tonbag_kg - nw_val) > 0.01 * nw_val:
                result.errors.append(
                    f'본품 총량 불일치: 배치 합 {sum_tonbag_kg:.0f} kg vs 문서 NW {total_nw.strip()}'
                )
        expected_bags = round(sum_tonbag_kg / UNIT_WEIGHT_KG)
        if tb and expected_bags > 0 and abs(expected_bags - len(tb) * 10) > len(tb):
            result.errors.append(
                f'Big bag 수 불일치: 예상 {expected_bags}ea (500kg net 기준) vs LOT당 10백 기대'
            )

    def _extract_pdf_blocks(self, pdf_path: str) -> List[str]:
        """PDF 텍스트 추출. (…)Tj 우선, 실패 시 PyMuPDF 줄 단위 폴백."""
        try:
            with open(pdf_path, 'rb') as f:
                raw = f.read().decode('latin-1', errors='replace')
            blocks = re.findall(r'\(([^)]+)\)Tj', raw)
            if blocks:
                return blocks
            try:
                import fitz
                doc = fitz.open(pdf_path)
                lines = []
                for page in doc:
                    lines.extend(page.get_text().splitlines())
                doc.close()
                blocks = [ln.strip() for ln in lines if ln.strip()]
                if blocks:
                    logger.debug(f'[PickingParser] PyMuPDF 폴백으로 {len(blocks)} 블록 추출')
                    return blocks
            except Exception as e:
                logger.debug(f'Suppressed: {e}')
            return []
        except OSError as e:
            logger.error(f'PDF 읽기 실패: {e}')
            return []

    def _parse_quantity_blocks(self, blocks: List[str]) -> List[PickingLotItem]:
        """라벨-라인 순차: Quantity: X MT/KG → Batch number: → Storage location:."""
        items: List[PickingLotItem] = []
        i = 0
        while i < len(blocks):
            line = blocks[i].strip()
            qty_m = RE_QUANTITY.match(line)
            if not qty_m:
                i += 1
                continue
            qty_val = _normalize_num(qty_m.group(1))
            unit = qty_m.group(2).upper()
            weight_kg = qty_val * 1000.0 if unit == 'MT' else qty_val
            lot_no = ''
            storage = ''
            if i + 1 < len(blocks):
                bn = RE_BATCH_NUMBER.match(blocks[i + 1].strip())
                if bn:
                    lot_no = bn.group(1).strip()
                    i += 1
            if i + 1 < len(blocks):
                sl = RE_STORAGE_LOCATION.match(blocks[i + 1].strip())
                if sl:
                    storage = sl.group(1).strip()
                    i += 1
            if lot_no:
                items.append(PickingLotItem(lot_no=lot_no, weight_kg=weight_kg, unit=unit, storage=storage))
            i += 1
        return items

    def _dedup(self, items: List[PickingLotItem], unit: str) -> List[PickingLotItem]:
        """동일 lot_no + unit 첫 번째만 유지."""
        seen: Dict[str, PickingLotItem] = {}
        for it in items:
            if it.unit == unit and it.lot_no not in seen:
                seen[it.lot_no] = it
        return list(seen.values())

    def _parse_meta(self, blocks: List[str]) -> PickingListMeta:
        """PICKING LIST 헤더 기준 메타 + 200,000 kg 이상 KG 라인으로 NW/GW."""
        meta = PickingListMeta()
        pl_positions = [i for i, b in enumerate(blocks) if 'PICKING LIST' in b]
        if pl_positions:
            p1_start = pl_positions[-1] + 1
            p1 = blocks[p1_start: p1_start + 45]

            def get(idx: int) -> str:
                return p1[idx].strip() if idx < len(p1) else ''

            meta.picking_no = get(0)
            meta.sales_order = get(1)
            meta.outbound_id = get(2)
            meta.creation_date = get(9)
            meta.delivery_terms = get(10)
            meta.containers = get(12)
            meta.cutoff_date = get(15)
            meta.plan_loading_date = get(15)
            meta.contact_email = get(22)
            meta.contact_person = get(25)
            meta.port_discharge = get(34)
            meta.port_loading = get(36)

        for b in blocks:
            m = RE_LARGE_KG.search(b)
            if m:
                val = _normalize_num(m.group(1))
                if val > 200000:
                    line = b.strip()
                    if not meta.total_nw_kg:
                        meta.total_nw_kg = line
                    elif not meta.total_gw_kg:
                        meta.total_gw_kg = line
        return meta

    def build_pick_plan(
        self,
        result: PickingListResult,
        bag_weight_kg: int = UNIT_WEIGHT_KG,
        container_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        피킹 결과 → 컨테이너별 배치/톤백/샘플 배분(결정론적 round-robin).
        result.summary, result.meta.containers 사용. 검증 실패 시 plan['errors']에만 추가.
        """
        plan: Dict[str, Any] = {
            'header': {
                'picking_no': result.meta.picking_no,
                'sales_order': result.meta.sales_order,
                'total_mt': result.summary.get('total_mt', 0),
                'total_sample_kg': result.summary.get('total_sample_kg', 0),
            },
            'containers': [],
            'errors': list(result.errors),
        }
        if not result.tonbag:
            plan['errors'].append('본품 톤백 없음 — 플랜 생성 불가')
            return plan
        n_containers = container_count
        if n_containers is None and result.meta.containers:
            num_match = re.search(r'(\d+)', result.meta.containers)
            n_containers = int(num_match.group(1)) if num_match else 15
        if n_containers is None or n_containers < 1:
            n_containers = 15
        plan['header']['container_count'] = n_containers
        plan['containers'] = [{'container_index': i + 1, 'batches': []} for i in range(n_containers)]
        for idx, item in enumerate(result.tonbag):
            c = plan['containers'][idx % n_containers]
            qty_kg = item.weight_kg
            tonbag_count = max(1, round(qty_kg / bag_weight_kg))
            c['batches'].append({
                'batch_no': item.lot_no,
                'main_qty_kg': qty_kg,
                'tonbag_weight_kg': bag_weight_kg,
                'tonbag_count': tonbag_count,
                'sample_kg': 1.0,
                'storage_location': item.storage,
            })
        return plan

    def expand_tonbags(
        self,
        result: PickingListResult,
        unit_weight: int = UNIT_WEIGHT_KG,
    ) -> List[Dict]:
        """LOT 단위 톤백/샘플을 개별 행으로 분해(기존 출고 실행 호환)."""
        rows: List[Dict] = []
        for item in result.tonbag:
            count = max(1, round(item.weight_kg / unit_weight))
            for sub in range(1, count + 1):
                rows.append({
                    'type': 'TONBAG',
                    'lot_no': item.lot_no,
                    'sub_lt': sub,
                    'weight_kg': unit_weight,
                    'storage': item.storage,
                    'status': 'PICKED',
                })
        sp_lots = {s.lot_no for s in result.sample}
        for item in result.tonbag:
            if item.lot_no in sp_lots:
                rows.append({
                    'type': 'SAMPLE',
                    'lot_no': item.lot_no,
                    'sub_lt': 0,
                    'weight_kg': 1,
                    'storage': item.storage,
                    'status': 'PICKED',
                })
        return rows
