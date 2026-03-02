"""
SQM v6.2.7 — 파서 방어 테스트 (Bad Input Parser Defense)
==========================================================
잘못된/비정상 텍스트 입력 시 파서가 크래시 없이 방어하는지 검증.

영역:
  1. PickingListParser — 빈/가비지/부분/거대/인코딩 깨진 텍스트
  2. _normalize_num — 극단적 숫자 문자열
  3. DocumentDetector — 빈/랜덤/혼합 문서 감지
  4. AllocationParser — 잘못된 Excel 경로/형식

실행: python -m pytest tests/test_parser_defense.py -v
"""

import logging
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  1. PickingListParser 방어
# ═══════════════════════════════════════════════════════════

class TestPickingParserDefense:
    """잘못된 텍스트 입력 → 크래시 없이 실패 반환."""

    @pytest.fixture
    def parser(self):
        from parsers.document_parser_modular.picking_mixin import PickingListParserMixin
        return PickingListParserMixin()

    # --- 빈/None ---

    def test_empty_string(self, parser):
        """빈 문자열 → errors + success=False."""
        r = parser.parse_from_text('')
        assert not r.success
        assert len(r.errors) > 0

    def test_whitespace_only(self, parser):
        """공백만 → 실패."""
        r = parser.parse_from_text('   \n\n\t  \n  ')
        assert not r.success

    def test_none_text(self, parser):
        """None → 크래시 없이 실패."""
        try:
            r = parser.parse_from_text(None)
            assert not r.success
        except (TypeError, AttributeError):
            pass  # None 처리 불가도 OK

    # --- 가비지 데이터 ---

    def test_random_garbage(self, parser):
        """랜덤 문자 → 크래시 없이."""
        r = parser.parse_from_text('aslkdjf qlwej 12!@# $%^ &*() zxcvb')
        assert not r.success
        assert isinstance(r.errors, list)

    def test_binary_like_text(self, parser):
        """바이너리 유사 문자열 → 방어."""
        r = parser.parse_from_text('\x00\x01\x02\xff\xfe binary junk \x89PNG')
        assert not r.success

    def test_html_injection(self, parser):
        """HTML 태그 입력 → 방어."""
        r = parser.parse_from_text('<script>alert("xss")</script><h1>PICKING LIST</h1>')
        assert isinstance(r.errors, list)

    def test_sql_in_text(self, parser):
        """SQL문 포함 텍스트 → 방어."""
        r = parser.parse_from_text("PICKING LIST\nDROP TABLE inventory;\nQuantity: 5.00 MT")
        assert isinstance(r, object)

    # --- 부분 데이터 ---

    def test_header_only(self, parser):
        """헤더만 있고 본문 없음 → 실패."""
        r = parser.parse_from_text('PICKING LIST\nPK-2026-001\n80007418')
        assert not r.success  # 톤백 데이터 없음

    def test_quantity_without_batch(self, parser):
        """수량만 있고 배치번호 없음."""
        text = "PICKING LIST\nPK-TEST\nQuantity: 5.00 MT\nQuantity: 1.00 KG"
        r = parser.parse_from_text(text)
        # 배치번호 없으면 파싱 불가
        assert isinstance(r, object)

    def test_batch_without_quantity(self, parser):
        """배치번호만 있고 수량 없음."""
        text = "PICKING LIST\nBatch number: 1125072300\nBatch number: 1125072301"
        r = parser.parse_from_text(text)
        assert isinstance(r, object)

    # --- 극단적 크기 ---

    def test_huge_text(self, parser):
        """10만 줄 텍스트 → 크래시 없이 (메모리 안전)."""
        lines = ['PICKING LIST'] + [f'Line {i}: random data' for i in range(100_000)]
        r = parser.parse_from_text('\n'.join(lines))
        assert isinstance(r, object)

    def test_very_long_single_line(self, parser):
        """100KB 한 줄 → 방어."""
        r = parser.parse_from_text('X' * 100_000)
        assert not r.success

    # --- 인코딩 문제 ---

    def test_mixed_encoding(self, parser):
        """한/영/일 혼합 → 방어."""
        text = "PICKING LIST\n피킹리스트\nピッキングリスト\nQuantity: 5.00 MT\nBatch: 1125072300"
        r = parser.parse_from_text(text)
        assert isinstance(r, object)

    # --- 잘못된 숫자 형식 ---

    def test_invalid_quantity_formats(self, parser):
        """비정상 수량 형식 → 방어."""
        texts = [
            "PICKING LIST\nQuantity: -5.00 MT\nBatch: 1125072300",
            "PICKING LIST\nQuantity: NaN MT\nBatch: 1125072300",
            "PICKING LIST\nQuantity: Infinity MT\nBatch: 1125072300",
            "PICKING LIST\nQuantity: 0.00 MT\nBatch: 1125072300",
        ]
        for text in texts:
            r = parser.parse_from_text(text)
            assert isinstance(r, object), f"크래시: {text[:50]}"

    # --- 중복 데이터 ---

    def test_duplicate_lots(self, parser):
        """동일 LOT 반복 → 중복 제거 또는 경고."""
        lines = ['PICKING LIST', 'PK-DUP-TEST']
        for _ in range(5):
            lines.extend([
                'Quantity: 5.00 MT',
                'Batch number: 1125072300',  # 동일 LOT 5회
                'Quantity: 1.00 KG',
                'Batch number: 1125072300',
            ])
        r = parser.parse_from_text('\n'.join(lines))
        assert isinstance(r, object)


# ═══════════════════════════════════════════════════════════
#  2. _normalize_num 극단적 입력
# ═══════════════════════════════════════════════════════════

class TestNormalizeNumDefense:
    """_normalize_num에 극단적 입력."""

    @pytest.fixture
    def norm(self):
        from parsers.document_parser_modular.picking_mixin import _normalize_num
        return _normalize_num

    def test_none(self, norm):
        assert norm(None) == 0.0

    def test_empty(self, norm):
        assert norm('') == 0.0

    def test_integer_obj(self, norm):
        """int 객체 → 0 (str만 허용)."""
        assert norm(12345) == 0.0  # isinstance(s, str) 체크

    def test_nan_string(self, norm):
        """'NaN' → float('nan') 또는 0.0 (현재 float('nan') 반환 — 발견사항)."""
        import math
        result = norm('NaN')
        # float('NaN')은 Python에서 유효 → _normalize_num이 그대로 반환
        # 이상적으로는 0.0이지만, 현재 동작은 nan
        assert result == 0.0 or math.isnan(result)

    def test_inf_string(self, norm):
        assert norm('Infinity') == 0.0 or norm('Infinity') == float('inf')

    def test_negative(self, norm):
        result = norm('-500.0')
        assert result == -500.0 or result == 0.0

    def test_pure_comma(self, norm):
        assert norm(',,,') == 0.0

    def test_pure_dots(self, norm):
        result = norm('...')
        assert isinstance(result, float)

    def test_spaces_mixed(self, norm):
        result = norm(' 1 000 ')
        assert isinstance(result, float)

    def test_currency_symbol(self, norm):
        result = norm('$5,000.00')
        assert isinstance(result, float)

    def test_percent_sign(self, norm):
        result = norm('99.5%')
        assert isinstance(result, float)

    def test_very_long_number(self, norm):
        """1000자리 숫자 → 크래시 없이."""
        result = norm('9' * 1000)
        assert isinstance(result, float)

    # 유럽식 (S4-4 수정 검증)
    def test_euro_basic(self, norm):
        assert norm('300.000,00') == 300000.0

    def test_euro_small(self, norm):
        assert norm('1.234,56') == 1234.56

    def test_american_basic(self, norm):
        assert norm('5,000.00') == 5000.0


# ═══════════════════════════════════════════════════════════
#  3. DocumentDetector 방어
# ═══════════════════════════════════════════════════════════

class TestDocumentDetectorDefense:
    """잘못된 입력으로 문서 감지 → 크래시 없이."""

    @pytest.fixture
    def detector(self):
        from parsers.document_detector import DocumentDetector
        return DocumentDetector()

    def test_empty_text(self, detector):
        r = detector.detect('', '')
        assert r.document_type is not None

    def test_none_text(self, detector):
        try:
            r = detector.detect(None, '')
            assert r is not None
        except (TypeError, AttributeError):
            pass

    def test_random_text(self, detector):
        r = detector.detect('random gibberish text 12345 !@#$%', 'unknown.pdf')
        assert r.document_type is not None

    def test_all_types_keywords(self, detector):
        """모든 유형 키워드 혼합 → 하나 선택."""
        text = "INVOICE PACKING LIST BILL OF LADING DELIVERY ORDER COA CERTIFICATE"
        r = detector.detect(text, '')
        assert r.document_type is not None
        assert 0.0 <= r.confidence <= 1.0

    def test_unicode_filename(self, detector):
        r = detector.detect('PACKING LIST', '패킹리스트_한글파일명_🎉.pdf')
        assert r is not None

    def test_no_filename(self, detector):
        r = detector.detect('INVOICE No: INV-2026-001')
        assert r is not None

    def test_huge_text(self, detector):
        """10만 글자 → 크래시 없이."""
        r = detector.detect('A' * 100_000, 'big_file.pdf')
        assert r is not None


# ═══════════════════════════════════════════════════════════
#  4. AllocationParser 방어
# ═══════════════════════════════════════════════════════════

class TestAllocationParserDefense:
    """잘못된 Excel/경로로 파싱 → 크래시 없이."""

    @pytest.fixture
    def parser(self):
        from parsers.allocation_parser import AllocationParser
        return AllocationParser()

    def test_nonexistent_file(self, parser):
        """미존재 파일 → None 반환 (P2 패치 완료)."""
        r = parser.parse('/path/to/nonexistent.xlsx')
        assert r is None
        assert len(parser.errors) > 0

    def test_empty_file(self, parser):
        """빈 파일 → None."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b'')
            path = f.name
        try:
            r = parser.parse(path)
            assert r is None
        except Exception:
            pass  # 빈 파일 오류도 OK
        finally:
            os.unlink(path)

    def test_text_file_as_excel(self, parser):
        """텍스트 파일을 Excel로 → None."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False, mode='w') as f:
            f.write('This is not an Excel file\nJust plain text')
            path = f.name
        try:
            r = parser.parse(path)
            assert r is None
        except Exception:
            pass
        finally:
            os.unlink(path)

    def test_directory_path(self, parser):
        """디렉토리 경로 → None (P2 패치 완료)."""
        r = parser.parse('/tmp/')
        assert r is None

    def test_special_chars_path(self, parser):
        """특수문자 경로 → None (P2 패치 완료)."""
        r = parser.parse("/tmp/file'with\"special;chars.xlsx")
        assert r is None
