# -*- coding: utf-8 -*-
"""
Allocation 출고 경로 검증
- AllocationParser 호환성: 파서가 Allocation 형식 Excel을 정상 파싱하는지
- 경로 ③ Excel 출고: process_outbound에 sale_ref/sold_to/qty_mt 전달 여부는 import_handlers 수정으로 반영됨
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def minimal_allocation_excel():
    """AllocationParser가 기대하는 최소 형식 Excel 생성 (1행 타이틀, 2행 빈행, 3행 헤더, 4행 데이터)."""
    try:
        import pandas as pd
    except ImportError:
        pytest.skip("pandas required")
    title = "Allocation - PT LBM - September / CIF Semarang - 300MT of MIc9000"
    headers = [
        "Product", "SAP NO", "ETA BUSAN", "Date in stock", "QTY (MT)", "LOT NO",
        "WH", "Customs", "SOLD TO", "GW", "SALE REF", "OUTBOUND DATE"
    ]
    row1 = [
        "LITHIUM CARBONATE", "1234567890", "2026-02-20", "2026-02-18", 11.5,
        "1125072729", "GY", "", "PT LBM", 23000, "SR-001", "2026-02-20"
    ]
    df = pd.DataFrame(
        [ [title] + [""] * (len(headers) - 1),
          [""] * len(headers),
          headers,
          row1 ]
    )
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    df.to_excel(path, index=False, header=False)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_allocation_parser_parse(minimal_allocation_excel):
    """AllocationParser.parse()가 Allocation 형식 Excel을 파싱하면 AllocationData를 반환한다."""
    from parsers.allocation_parser import AllocationParser

    parser = AllocationParser()
    result = parser.parse(minimal_allocation_excel)
    assert result is not None
    assert result.header is not None
    assert "PT LBM" in result.header.customer or "LBM" in result.header.title.upper()
    assert len(result.rows) >= 1
    row = result.rows[0]
    assert len(row.lot_no) == 10 and row.lot_no.isdigit()
    assert row.qty_mt >= 0
    assert row.sold_to or result.header.customer


def test_allocation_parser_column_mapping():
    """헤더 행에서 LOT NO, QTY (MT), SOLD TO 등 컬럼 매핑이 동작하는지."""
    from parsers.allocation_parser import AllocationParser

    parser = AllocationParser()
    headers = ["LOT NO", "QTY (MT)", "SOLD TO", "SALE REF", "PRODUCT"]
    col_map = parser._map_columns(headers)
    assert "lot_no" in col_map
    assert "qty_mt" in col_map
    assert "sold_to" in col_map or "customer" in col_map
