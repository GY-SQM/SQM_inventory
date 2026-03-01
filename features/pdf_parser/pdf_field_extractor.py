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

# v6.12 Addon-G: 문서 파싱 시 500/1000 두 가지 모두 고려
UNIT_WEIGHT_KG = 500  # 기본값 (500kg net 문서)
VALID_UNIT_WEIGHTS = (500, 1000)  # 유효한 톤백 단가

# 파서가 기대하는 라벨 패턴
RE_QUANTITY = re.compile(
    r'^Quantity:\s*([\d,.]+)\s*(MT|KG)\s*$',
    re.IGNORECASE
)
RE_BATCH_NUMBER = re.compile(r'Batch number:\s*(.+)', re.IGNORECASE)
RE_STORAGE_LOCATION = re.compile(r'Storage location:\s*(.+)', re.IGNORECASE)
RE_LARGE_KG = re.compile(r'([\d,]+\.?\d*)\s*KG\b', re.IGNORECASE)


def _normalize_num(s: str) -> float:
    """천단위 구분자 제거 후 float. 유럽식(점=천단위, 콤마=소수) 자동 감지.
    
    예시:
        '300.000,00' → 300000.0  (유럽식)
        '1.234,56'   → 1234.56   (유럽식)
        '5,000.00'   → 5000.0    (미국/한국식)
        '5.00'       → 5.0       (소수점)
        ''           → 0.0
    """
    if not s or not isinstance(s, str):
        return 0.0
    s = s.strip()
    try:
        # ★ S4-4: 유럽식 감지 — 콤마가 마지막 구분자이고 점이 그 앞에 있으면 유럽식
        # 패턴: 숫자.숫자.숫자,숫자  또는  숫자.숫자,숫자
        if re.search(r'\d\.\d{3}[,]', s):
            # 유럽식: 점=천단위 제거, 콤마→점
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s and '.' in s:
            # 미국식: 콤마=천단위 제거 (점이 소수점)
            last_comma = s.rfind(',')
            last_dot = s.rfind('.')
            if last_dot > last_comma:
                # 미국식: 5,000.00
                s = s.replace(',', '')
            else:
                # 유럽식: 5.000,00
                s = s.replace('.', '').replace(',', '.')
        elif ',' in s and '.' not in s:
            # 콤마만 있음: 천단위 또는 소수점 판단
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # 소수점 가능성: 1234,56 → 1234.56
                s = s.replace(',', '.')
            else:
                # 천단위: 1,234,567 → 1234567
                s = s.replace(',', '')
        else:
            # 콤마 없음: 점만 또는 순수 숫자
            pass
        # 공백/기타 제거
        s = re.sub(r'[\s]', '', s)
        return float(s)
    except (ValueError, TypeError):
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
        # v6.12 Addon-G: 5MT(500kg×10) 또는 10MT(1000kg×10) 두 가지 확인
        if tb:
            expected_per_lot = sum_tonbag_kg / len(tb) if len(tb) else 0
            # 5MT(500kg×10) 또는 10MT(1000kg×10) 어느 쪽에도 맞지 않으면 경고
            near_5mt = abs(expected_per_lot - 5000.0) <= 100.0
            near_10mt = abs(expected_per_lot - 10000.0) <= 100.0
            if expected_per_lot > 0 and not near_5mt and not near_10mt:
                result.errors.append(
                    f'본품 배치당 중량 이상: 합계 {sum_tonbag_kg:.0f} kg, {len(tb)} LOT '
                    f'(기대: 5 MT 또는 10 MT/LOT, 실제: {expected_per_lot/1000:.1f} MT/LOT)'
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
        # v6.12 Addon-G: 500/1000 두 가지 단가로 Big bag 수 검증
        expected_bags_500 = round(sum_tonbag_kg / 500) if sum_tonbag_kg > 0 else 0
        expected_bags_1000 = round(sum_tonbag_kg / 1000) if sum_tonbag_kg > 0 else 0
        if tb:
            actual_bags = len(tb)
            # 500kg 또는 1000kg 어느 쪽으로도 맞지 않으면 경고
            match_500 = actual_bags > 0 and abs(expected_bags_500 - actual_bags * 10) <= actual_bags
            match_1000 = actual_bags > 0 and abs(expected_bags_1000 - actual_bags * 10) <= actual_bags
            if not match_500 and not match_1000 and actual_bags > 0:
                result.errors.append(
                    f'Big bag 수 불일치: 배치합 {sum_tonbag_kg:.0f}kg '
                    f'→ 500kg기준 {expected_bags_500}ea / 1000kg기준 {expected_bags_1000}ea vs 실제 {actual_bags}ea'
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
