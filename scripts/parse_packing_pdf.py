"""Packing List PDF 파싱 테스트 스크립트"""
import sys
from pathlib import Path

# 프로젝트 루트
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from parsers.pdf_parser import PDFParser


def main():
    # PDF 경로: 워크스페이스 상위 폴더
    pdf_path = root.parent / "2200033057_PackingList1.pdf"
    if not pdf_path.exists():
        print(f"파일 없음: {pdf_path}")
        return 1

    parser = PDFParser()
    result = parser.parse_packing_list(str(pdf_path))

    if result is None:
        print("파싱 실패")
        if parser.errors:
            print("에러:", parser.errors)
        return 1

    print("=== Packing List 파싱 결과 ===")
    print("파일:", result.source_file)
    print("Folio:", result.folio)
    print("제품:", result.product)
    print("제품코드:", result.product_code)
    print("포장:", result.packing)
    print("선박:", result.vessel)
    print("고객:", result.customer)
    print("목적지:", result.destination)
    print("총 LOT 수:", result.total_lots)
    print("총 Net 중량(kg):", result.total_net_weight)
    print("총 Gross 중량(kg):", result.total_gross_weight)
    print()
    print("--- LOT 목록 ---")
    for i, lot in enumerate(result.lots, 1):
        print(f"  {i}. LOT: {lot.get('lot_no')}  Container: {lot.get('container_no')}  Net: {lot.get('net_weight')} kg")
    return 0

if __name__ == "__main__":
    sys.exit(main())
