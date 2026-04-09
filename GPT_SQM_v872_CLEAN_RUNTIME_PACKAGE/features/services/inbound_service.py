"""
P2 리팩토링 — InboundService
Parser → Validator → Repository 파이프라인 오케스트레이션.
onestop_inbound.py의 UI에서 이 Service를 통해 비즈니스 로직을 위임받음.
"""
import logging

from features.parsers.inbound_parser import InboundParser
from features.validators.inbound_validator import InboundValidator
from features.repositories.inbound_repository import InboundRepository

logger = logging.getLogger(__name__)


class InboundService:
    """입고 비즈니스 로직 파이프라인: 파싱 → 검증 → 저장."""

    def __init__(self, engine, parser: InboundParser = None,
                 validator: InboundValidator = None,
                 repository: InboundRepository = None):
        self.parser = parser or InboundParser()
        self.validator = validator or InboundValidator()
        self.repository = repository or InboundRepository(engine)
        self.engine = engine

    def validate_preview(self, rows: list) -> list:
        """미리보기 데이터 검증. 에러 리스트 반환."""
        return self.validator.preflight_validate(rows)

    def validate_date(self, date_str: str) -> bool:
        """날짜 형식 검증."""
        return self.validator.validate_date(date_str)

    def calc_dates(self, arrival: str, con_return: str, ft_raw: str):
        """날짜 상호 계산."""
        return self.validator.calc_dates(arrival, con_return, ft_raw)

    def check_required_docs(self, file_paths: dict, doc_types: list) -> bool:
        """필수 서류 확인."""
        return self.validator.has_required_docs(file_paths, doc_types)

    def save_single_lot(self, row: dict, pl, invoice, bl, do,
                        format_bl_fn=None, date_str_fn=None):
        """단일 LOT 저장 파이프라인: 데이터 변환 → 중복 확인 → 저장."""
        lot_no = str(row.get('lot_no', '') or '').strip()

        if lot_no and self.repository.lot_exists(lot_no):
            return {'success': False, 'skipped': True, 'lot_no': lot_no,
                    'message': f'LOT {lot_no} 이미 존재'}

        packing_dict = self.repository.build_packing_dict(
            row, pl, invoice, bl, do, format_bl_fn, date_str_fn
        )
        inv_dict, bl_dict, do_dict = self.repository.build_doc_dicts(
            invoice, bl, do, format_bl_fn, date_str_fn
        )

        result = self.repository.save_lot(packing_dict, inv_dict, bl_dict, do_dict)
        return result
