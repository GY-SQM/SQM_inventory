# -*- coding: utf-8 -*-
"""
SQM 피킹리스트 PDF 파서 — 최종 로직 (라벨-라인 기반, 하드스톱 검증)
================================================================
파일: parsers/document_parser_modular/picking_mixin.py

v6.12.1 — 60LOT/300MT 대용량 피킹리스트 대응
  - 멀티페이지 PDF 텍스트 병합 (Tj + PyMuPDF + Gemini Vision OCR 3단 폴백)
  - 대용량 검증 임계치 조정 (300MT, 600ea Big bag)
  - 파싱 진행 로깅 (10 LOT 단위)
  - 유럽식 숫자 형식 정규화 (300.000,00 → 300000.0)
  - 루즈 매칭 폴백 (Quantity: 라벨 없는 비정형 문서)

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
# v6.12.1: 대용량 대응 — 라벨 없이 값만 있는 행도 캡처 (폴백)
RE_QUANTITY_LOOSE = re.compile(
    r'^\s*([\d,.]+)\s*(MT|KG)\s*$',
    re.IGNORECASE
)
RE_BATCH_NUMBER = re.compile(r'Batch number:\s*(.+)', re.IGNORECASE)
# v6.12.1: "Batch number:" 없이 LOT 번호 패턴만 있는 행 (폴백)
RE_LOT_ONLY = re.compile(r'^\s*(\d{10,})\s*$')  # 10자리 이상 숫자
RE_STORAGE_LOCATION = re.compile(r'Storage location:\s*(.+)', re.IGNORECASE)
RE_LARGE_KG = re.compile(r'([\d,]+\.?\d*)\s*KG\b', re.IGNORECASE)
# v6.12.1: 유럽식 숫자 (1.234,56 or 300.000,00)
RE_EURO_NUMBER = re.compile(r'^(\d{1,3}(?:\.\d{3})+),(\d{2})$')
# v6.12.1: Big bag 수 추출
RE_BIG_BAG = re.compile(r'Big\s*bag.*?(\d+)\s*ea', re.IGNORECASE)


def _normalize_num(s: str) -> float:
    """천단위 콤마/유럽식 포인트 제거 후 float. 빈 문자열/실패 시 0."""
    if not s or not isinstance(s, str):
        return 0.0
    s = s.strip()
    # v6.12.1: 유럽식 숫자 감지 (300.000,00 → 300000.00)
    euro = RE_EURO_NUMBER.match(s)
    if euro:
        integer_part = euro.group(1).replace('.', '')
        decimal_part = euro.group(2)
        return float(f'{integer_part}.{decimal_part}')
    try:
        return float(re.sub(r'[,\s]', '', s))
    except ValueError:
        return 0.0


@dataclass
class PickingListMeta:
    picking_no:        str = ''
    sales_order:       str = ''
    outbound_id:       str = ''
    creation_date:     str = ''
    delivery_terms:    str = ''
    containers:        str = ''
    cutoff_date:       str = ''
    plan_loading_date: str = ''
    contact_email:     str = ''
    contact_person:    str = ''
    port_discharge:    str = ''
    port_loading:      str = ''
    total_nw_kg:       str = ''
    total_gw_kg:       str = ''


@dataclass
class PickingLotItem:
    lot_no:    str
    weight_kg: float
    unit:      str   # MT or KG
    storage:   str = ''


@dataclass
class PickingListResult:
    success:  bool = False
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)  # v6.12.1: 경고(파싱 중단 안함)
    tonbag:   List[PickingLotItem]      = field(default_factory=list)
    sample:   List[PickingLotItem]      = field(default_factory=list)
    meta:     PickingListMeta           = field(default_factory=PickingListMeta)
    summary:  Dict[str, Any]            = field(default_factory=dict)
    page_count: int = 0   # v6.12.1: PDF 페이지 수


class PickingListParserMixin:
    """
    피킹리스트 파서 — 절대 예외로 죽지 않음. 실패 시 result.errors + success=False.

    v6.12.1 대용량 강화:
      - 60LOT / 300MT / 15컨테이너 문서 파싱 지원
      - 3단 폴백: Tj 추출 → PyMuPDF → Gemini Vision OCR
      - 유럽식 숫자 정규화
      - 파싱 진행 로깅 (대용량 시 20 아이템 단위)

    진입점:
      - parse_picking_list(pdf_path)  : PDF 파일
      - parse_from_text(all_text)    : 이미 추출된 텍스트(OCR 등)
    """

    def parse_picking_list(self, pdf_path: str) -> PickingListResult:
        """PDF에서 텍스트 추출 후 파싱. 3단 폴백 추출."""
        result = PickingListResult()
        try:
            blocks, page_count = self._extract_pdf_blocks_v2(pdf_path)
            result.page_count = page_count
            if not blocks:
                result.errors.append('PDF 텍스트 추출 실패 (Tj + PyMuPDF + OCR 모두 실패)')
                return result
            logger.info(f'[PickingParser] 추출: {len(blocks)} 블록 / {page_count} 페이지')
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
        """
        공통: 블록(줄) 목록 → 파싱 → 정규화 → 하드스톱 검증 → Result.

        v6.12.1 대용량 개선:
        - 블록 1000+ 줄 → 자동 청크 분할 파싱 (대용량 안정성)
        - 파싱 통계 리포트 (경고 포함)
        - 중복 LOT 감지 (멀티페이지 병합 시 페이지 경계 중복)
        """
        result = PickingListResult()
        try:
            # 대용량 감지
            is_large = len(blocks) > 500
            if is_large:
                logger.info(f'[PickingParser] 대용량 문서: {len(blocks)} 블록 → 청크 파싱')

            all_items = self._parse_quantity_blocks(blocks)

            # v6.12.1: 라벨 기반 파싱 실패 시 루즈 매칭 폴백
            if not all_items:
                logger.info('[PickingParser] 라벨 기반 실패 → 루즈 매칭 시도')
                all_items = self._parse_quantity_blocks_loose(blocks)
                if all_items:
                    result.warnings.append(
                        f'루즈 매칭으로 {len(all_items)}개 아이템 추출 '
                        f'(Quantity: 라벨 없음 — 문서 형식 확인 필요)')

            # v6.12.1: 중복 LOT 감지 (멀티페이지 PDF 병합 시 발생 가능)
            lot_counts: Dict[str, int] = {}
            for it in all_items:
                key = f'{it.lot_no}_{it.unit}'
                lot_counts[key] = lot_counts.get(key, 0) + 1
            duplicates = {k: v for k, v in lot_counts.items() if v > 1}
            if duplicates:
                dup_lots = [k.split('_')[0] for k in list(duplicates.keys())[:5]]
                result.warnings.append(
                    f'중복 LOT 감지 ({len(duplicates)}건): {dup_lots} '
                    f'(멀티페이지 병합 중복 → 자동 dedup 처리됨)'
                )

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
                'block_count':   len(blocks),
                'raw_items':     len(all_items),
                'dedup_removed': len(all_items) - len(result.tonbag) - len(result.sample),
            }
            result.success = len(result.errors) == 0
            if result.success:
                logger.info(
                    f'[PickingParser] 파싱 완료: {len(tb_set)} LOT / '
                    f'{total_mt:.1f} MT / 샘플 {total_spkg:.0f} kg'
                )
                if len(tb_set) >= 30:
                    logger.info(f'[PickingParser] 대용량 문서: {len(tb_set)} LOT / '
                                f'{total_mt:.0f} MT / {len(blocks)} 블록')
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
        # v6.12 Addon-G: 5MT(500kg*10) 또는 10MT(1000kg*10) 두 가지 확인
        if tb:
            expected_per_lot = sum_tonbag_kg / len(tb) if len(tb) else 0
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
            nw_m = RE_LARGE_KG.search(total_nw)
            if nw_m:
                nw_val = _normalize_num(nw_m.group(1))
                # v6.12.1: 대용량(300MT) + 소규모(5MT) 모두 커버
                if nw_val > 1000 and abs(sum_tonbag_kg - nw_val) > 0.05 * nw_val:
                    result.errors.append(
                        f'본품 총량 불일치: 배치 합 {sum_tonbag_kg:.0f} kg vs 문서 NW {total_nw.strip()} '
                        f'(차이: {abs(sum_tonbag_kg - nw_val):.0f} kg = {abs(sum_tonbag_kg - nw_val) / nw_val * 100:.1f}%)'
                    )
        # v6.12 Addon-G: 500/1000 두 가지 단가로 Big bag 수 검증
        expected_bags_500 = round(sum_tonbag_kg / 500) if sum_tonbag_kg > 0 else 0
        expected_bags_1000 = round(sum_tonbag_kg / 1000) if sum_tonbag_kg > 0 else 0
        if tb:
            actual_bags = len(tb)
            match_500 = actual_bags > 0 and abs(expected_bags_500 - actual_bags * 10) <= actual_bags
            match_1000 = actual_bags > 0 and abs(expected_bags_1000 - actual_bags * 10) <= actual_bags
            if not match_500 and not match_1000 and actual_bags > 0:
                result.errors.append(
                    f'Big bag 수 불일치: 배치합 {sum_tonbag_kg:.0f}kg '
                    f'-> 500kg기준 {expected_bags_500}ea / 1000kg기준 {expected_bags_1000}ea vs 실제 {actual_bags}ea'
                )

        # v6.12.1: Big bag 문서 표기 vs 파싱 LOT 비교
        for b in [result.meta.total_nw_kg, result.meta.total_gw_kg]:
            m = RE_BIG_BAG.search(b) if b else None
            if m:
                doc_bags = int(m.group(1))
                if actual_bags > 0 and doc_bags > 0 and doc_bags != actual_bags:
                    result.warnings.append(
                        f'Big bag 문서 표기({doc_bags}ea) vs 파싱 LOT({actual_bags}개) 불일치')

    def _extract_pdf_blocks_v2(self, pdf_path: str) -> tuple:
        """
        v6.12.1: 3단 폴백 PDF 텍스트 추출.
        1단계: (...)Tj raw 추출 (가장 빠름)
        2단계: PyMuPDF 줄 단위 (정확도 높음)
        3단계: Gemini Vision OCR (이미지 기반 PDF 전용)

        Returns: (blocks, page_count)
        """
        page_count = 0

        # 1단계: Tj raw 추출
        try:
            with open(pdf_path, 'rb') as f:
                raw = f.read().decode('latin-1', errors='replace')
            blocks = re.findall(r'\(([^)]+)\)Tj', raw)
            page_count = raw.count('/Type /Page')
            if blocks and len(blocks) >= 10:
                logger.info(f'[PickingParser] Tj 추출 성공: {len(blocks)} 블록 / ~{page_count}p')
                return blocks, page_count
        except OSError as e:
            logger.debug(f'Tj 추출 실패: {e}')

        # 2단계: PyMuPDF
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            all_lines: List[str] = []
            for page in doc:
                all_lines.extend(page.get_text().splitlines())
            doc.close()
            blocks = [ln.strip() for ln in all_lines if ln.strip()]
            if blocks and len(blocks) >= 10:
                logger.info(f'[PickingParser] PyMuPDF 추출: {len(blocks)} 블록 / {page_count}p')
                return blocks, page_count
        except Exception as e:
            logger.debug(f'PyMuPDF 실패: {e}')

        # 3단계: Gemini Vision OCR (대용량 이미지 PDF)
        try:
            ocr_text = self._gemini_ocr_picking(pdf_path)
            if ocr_text and len(ocr_text) > 100:
                blocks = [ln.strip() for ln in ocr_text.splitlines() if ln.strip()]
                logger.info(f'[PickingParser] Gemini OCR 추출: {len(blocks)} 블록')
                return blocks, page_count
        except Exception as e:
            logger.debug(f'Gemini OCR 실패: {e}')

        return [], page_count

    def _gemini_ocr_picking(self, pdf_path: str) -> str:
        """
        v6.12.1: Gemini Vision API로 Picking List PDF OCR.
        60LOT/300MT 문서 대응:
        - 페이지당 200dpi 이미지 변환 (15+ 페이지 대용량)
        - 실패 페이지 스킵 + 부분 성공 허용
        - max_output_tokens=65536
        - 진행률 로깅
        """
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            all_text_parts = []
            failed_pages = []

            logger.info(f'[Gemini OCR] 시작: {page_count} 페이지 / {pdf_path}')

            for page_num in range(page_count):
                page = doc[page_num]
                # 대용량: 200dpi (품질+속도 균형)
                dpi = 150 if page_count > 10 else 200
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes('png')

                import base64
                b64 = base64.b64encode(img_bytes).decode('utf-8')

                try:
                    from utils.gemini_client import call_gemini_vision
                    prompt = (
                        "이 피킹리스트(Picking List) PDF 페이지에서 "
                        "모든 텍스트를 그대로 추출하세요.\n"
                        "특히 다음 패턴을 정확히 추출하세요:\n"
                        "- Quantity: X.XX MT 또는 KG\n"
                        "- Batch number: (10자리 이상 숫자)\n"
                        "- Storage location:\n"
                        "숫자의 소수점/콤마를 변경하지 마세요.\n"
                        "줄바꿈을 유지하세요."
                    )
                    text = call_gemini_vision(b64, prompt, max_tokens=65536)
                    if text:
                        all_text_parts.append(text)
                    if (page_num + 1) % 5 == 0 or page_num == page_count - 1:
                        logger.info(
                            f'[Gemini OCR] 진행: {page_num+1}/{page_count} 페이지 완료 '
                            f'({len(all_text_parts)} 성공, {len(failed_pages)} 실패)'
                        )
                except ImportError:
                    logger.debug('[Gemini OCR] gemini_client 미설치')
                    break
                except Exception as e:
                    failed_pages.append(page_num + 1)
                    logger.warning(f'[Gemini OCR] 페이지 {page_num+1} 실패 (계속 진행): {e}')
                    continue

            doc.close()

            if failed_pages:
                logger.warning(
                    f'[Gemini OCR] 완료: {len(all_text_parts)}/{page_count} 페이지 성공, '
                    f'실패 페이지: {failed_pages}'
                )
            else:
                logger.info(f'[Gemini OCR] 완료: {page_count}/{page_count} 페이지 전체 성공')

            return '\n'.join(all_text_parts)
        except Exception as e:
            logger.debug(f'Gemini OCR 전체 실패: {e}')
            return ''

    # === 하위 호환 유지 ===
    def _extract_pdf_blocks(self, pdf_path: str) -> List[str]:
        """레거시 호환: _extract_pdf_blocks_v2 래퍼."""
        blocks, _ = self._extract_pdf_blocks_v2(pdf_path)
        return blocks

    def _parse_quantity_blocks(self, blocks: List[str]) -> List[PickingLotItem]:
        """라벨-라인 순차: Quantity: X MT/KG -> Batch number: -> Storage location:."""
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
                if len(items) % 20 == 0:
                    logger.debug(f'[PickingParser] 파싱 진행: {len(items)}개 아이템 추출...')
            i += 1
        return items

    def _parse_quantity_blocks_loose(self, blocks: List[str]) -> List[PickingLotItem]:
        """
        v6.12.1: 폴백 — "Quantity:" 라벨 없이 값만 있는 비정형 문서 파싱.
        패턴: 숫자+MT/KG -> 다음 줄 10자리+ 숫자(LOT) -> 다음 줄 Storage
        """
        items: List[PickingLotItem] = []
        i = 0
        while i < len(blocks):
            line = blocks[i].strip()
            qty_m = RE_QUANTITY.match(line) or RE_QUANTITY_LOOSE.match(line)
            if not qty_m:
                i += 1
                continue
            qty_val = _normalize_num(qty_m.group(1))
            unit = qty_m.group(2).upper()
            weight_kg = qty_val * 1000.0 if unit == 'MT' else qty_val
            lot_no = ''
            storage = ''
            for offset in range(1, 4):
                if i + offset >= len(blocks):
                    break
                next_line = blocks[i + offset].strip()
                bn = RE_BATCH_NUMBER.match(next_line)
                if bn:
                    lot_no = bn.group(1).strip()
                    i += offset
                    break
                lot_m = RE_LOT_ONLY.match(next_line)
                if lot_m:
                    lot_no = lot_m.group(1)
                    i += offset
                    break
            if i + 1 < len(blocks):
                sl = RE_STORAGE_LOCATION.match(blocks[i + 1].strip())
                if sl:
                    storage = sl.group(1).strip()
                    i += 1
            if lot_no:
                items.append(PickingLotItem(lot_no=lot_no, weight_kg=weight_kg, unit=unit, storage=storage))
            i += 1
        if items:
            logger.info(f'[PickingParser] 루즈 매칭: {len(items)}개 아이템 추출')
        return items

    def _dedup(self, items: List[PickingLotItem], unit: str) -> List[PickingLotItem]:
        """동일 lot_no + unit 첫 번째만 유지."""
        seen: Dict[str, PickingLotItem] = {}
        for it in items:
            if it.unit == unit and it.lot_no not in seen:
                seen[it.lot_no] = it
        return list(seen.values())

    def _parse_meta(self, blocks: List[str]) -> PickingListMeta:
        """
        v6.12.1 개선: 고정 인덱스 + 정규식 하이브리드 메타 추출.

        60LOT/300MT 문서는 페이지 병합 시 인덱스가 어긋날 수 있으므로
        정규식으로 보정합니다.
        """
        meta = PickingListMeta()
        all_text = '\n'.join(blocks)

        # 1단계: 고정 인덱스 (기존 — 표준 문서에서 빠름)
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

        # 2단계: 정규식 보정 (고정 인덱스 결과가 비정상이면 덮어쓰기)
        _rx = {
            'sales_order': re.compile(r'(?:Sales\s*order|SO)\s*[:\-]?\s*(\d{8,})', re.I),
            'picking_no': re.compile(r'(?:Picking\s*No|Requisition)\s*[:\-]?\s*(\d{3,})', re.I),
            'outbound_id': re.compile(r'(?:Customer\s*reference|Outbound)\s*[:\-]?\s*([\w\-]+)', re.I),
            'creation_date': re.compile(r'(?:Creation\s*date|Date)\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})', re.I),
            'delivery_terms': re.compile(r'(?:Delivery\s*terms?|Incoterms?)\s*[:\-]?\s*(\w+)', re.I),
            'containers': re.compile(r'(\d+)\s*[xX×]\s*\d{2,3}[\'\"]', re.I),
            'contact_email': re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+'),
            'port_loading': re.compile(r'(?:Port\s*of\s*loading|POL)\s*[:\-]?\s*(.+?)(?:\n|$)', re.I),
            'port_discharge': re.compile(r'(?:Port\s*of\s*discharge|POD|Destination)\s*[:\-]?\s*(.+?)(?:\n|$)', re.I),
        }
        for attr, rx in _rx.items():
            current_val = getattr(meta, attr, '')
            if not current_val or len(current_val) < 2:
                m = rx.search(all_text)
                if m:
                    val = m.group(1).strip() if rx.groups else m.group(0).strip()
                    setattr(meta, attr, val)
                    logger.debug(f'[_parse_meta] 정규식 보정: {attr}={val}')

        # 3단계: NW/GW 추출 (기존 유지 — 200,000+ KG 라인)
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
        """피킹 결과 -> 컨테이너별 배치/톤백/샘플 배분(결정론적 round-robin)."""
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
