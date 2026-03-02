"""
SQM 크로스 체크 엔진 단위 테스트
v6.2.1 — 2026-02-27
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.cross_check_engine import (
    CheckLevel,
    CrossCheckResult,
    _normalize_bl,
    _normalize_container,
    _normalize_vessel,
    _vessel_fuzzy_match,
    _weight_diff_pct,
    cross_check_documents,
)
from parsers.document_models import (
    BLData,
    ContainerInfo,
    DOData,
    InvoiceData,
    LOTInfo,
    PackingListData,
)

# ═══════════════════════════════════════════════════════════
# 유틸리티 함수 테스트
# ═══════════════════════════════════════════════════════════

def test_normalize_vessel():
    assert _normalize_vessel("CHARLOTTE MAERSK 535W") == "CHARLOTTE MAERSK 535W"
    assert _normalize_vessel("charlotte maersk") == "CHARLOTTE MAERSK"
    assert _normalize_vessel("") == ""
    print("  ✅ _normalize_vessel 통과")


def test_normalize_container():
    assert _normalize_container("FFAU535500-6") == "FFAU5355006"
    assert _normalize_container("FFAU5355006") == "FFAU5355006"
    assert _normalize_container("") == ""
    print("  ✅ _normalize_container 통과")


def test_normalize_bl():
    assert _normalize_bl("MAEU258468669") == "258468669"
    assert _normalize_bl("258468669") == "258468669"
    assert _normalize_bl("") == ""
    print("  ✅ _normalize_bl 통과")


def test_vessel_fuzzy_match():
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK 535W", "CHARLOTTE MAERSK") is True
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK", "CHARLOTTE MAERSK 535W") is True
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK", "CHARLOTTE MAERSK") is True
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK", "EVER GIVEN") is False
    assert _vessel_fuzzy_match("", "CHARLOTTE MAERSK") is True  # 빈 값은 패스
    print("  ✅ _vessel_fuzzy_match 통과")


def test_weight_diff_pct():
    assert _weight_diff_pct(100000, 100000) == 0.0
    assert abs(_weight_diff_pct(100000, 99000) - 1.0) < 0.01
    assert _weight_diff_pct(0, 0) == 0.0
    print("  ✅ _weight_diff_pct 통과")


# ═══════════════════════════════════════════════════════════
# 크로스 체크 엔진 통합 테스트
# ═══════════════════════════════════════════════════════════

def test_all_match():
    """모든 항목이 일치하는 정상 케이스"""
    inv = InvoiceData(
        sap_no="2200033057", bl_no="258468669",
        vessel="CHARLOTTE MAERSK 535W",
        product_name="LITHIUM CARBONATE BATTERY GRADE",
        net_weight_kg=100020, gross_weight_kg=102625,
        package_count=220,
        lot_numbers=["1125081447", "1125081448", "1125081449"],
    )
    pl = PackingListData(
        sap_no="2200033057", vessel="CHARLOTTE MAERSK 535W",
        product="LITHIUM CARBONATE", code="MIC9000.00",
        total_net_weight_kg=100020, total_gross_weight_kg=102625,
        lots=[
            LOTInfo(lot_no="1125081447", container_no="FFAU5355006", net_weight_kg=5001),
            LOTInfo(lot_no="1125081448", container_no="FFAU5355007", net_weight_kg=5001),
            LOTInfo(lot_no="1125081449", container_no="FFAU5355008", net_weight_kg=5001),
        ],
        containers=["FFAU5355006", "FFAU5355007", "FFAU5355008"],
    )
    bl = BLData(
        bl_no="258468669", sap_no="2200033057",
        vessel="CHARLOTTE MAERSK", voyage="535W",
        product_name="LITHIUM CARBONATE BATTERY GRADE",
        net_weight_kg=100020, gross_weight_kg=102625,
        total_containers=3, total_packages=220,
        containers=[
            ContainerInfo(container_no="FFAU5355006"),
            ContainerInfo(container_no="FFAU5355007"),
            ContainerInfo(container_no="FFAU5355008"),
        ],
    )
    do = DOData(
        bl_no="MAEU258468669",
        vessel="CHARLOTTE MAERSK", voyage="535W",
        gross_weight_kg=102625, total_packages=220,
        containers=[
            ContainerInfo(container_no="FFAU5355006"),
            ContainerInfo(container_no="FFAU5355007"),
            ContainerInfo(container_no="FFAU5355008"),
        ],
    )

    result = cross_check_documents(inv, pl, bl, do)
    assert result.is_clean, f"예상: 불일치 없음, 실제: {result.detail_text}"
    print("  ✅ test_all_match 통과 (정상 케이스)")


def test_sap_no_mismatch():
    """SAP NO 불일치 → CRITICAL"""
    inv = InvoiceData(sap_no="2200033057")
    pl = PackingListData(sap_no="2200033058")  # 다른 SAP NO!

    result = cross_check_documents(inv, pl)
    assert result.has_critical, "SAP NO 불일치는 CRITICAL이어야 함"
    sap_items = [i for i in result.items if i.field_name == "SAP NO"]
    assert len(sap_items) == 1
    assert sap_items[0].level == CheckLevel.CRITICAL
    print("  ✅ test_sap_no_mismatch 통과 (SAP NO 불일치 → CRITICAL)")


def test_weight_warning():
    """중량 차이 1~5% → WARNING"""
    inv = InvoiceData(net_weight_kg=100020, gross_weight_kg=102625)
    bl = BLData(net_weight_kg=98500, gross_weight_kg=101000)  # ~1.5% 차이

    result = cross_check_documents(inv, None, bl)
    nw_items = [i for i in result.items if i.field_name == "Net Weight"]
    assert len(nw_items) == 1
    assert nw_items[0].level == CheckLevel.WARNING
    print("  ✅ test_weight_warning 통과 (중량 1.5% 차이 → WARNING)")


def test_weight_critical():
    """중량 차이 >5% → CRITICAL"""
    inv = InvoiceData(net_weight_kg=100000)
    bl = BLData(net_weight_kg=90000)  # 10% 차이

    result = cross_check_documents(inv, None, bl)
    nw_items = [i for i in result.items if i.field_name == "Net Weight"]
    assert len(nw_items) == 1
    assert nw_items[0].level == CheckLevel.CRITICAL
    print("  ✅ test_weight_critical 통과 (중량 10% 차이 → CRITICAL)")


def test_lot_count_mismatch():
    """LOT 개수 불일치"""
    inv = InvoiceData(lot_numbers=["1125081447", "1125081448", "1125081449"])
    pl = PackingListData(
        lots=[
            LOTInfo(lot_no="1125081447"),
            LOTInfo(lot_no="1125081448"),
        ]
    )

    result = cross_check_documents(inv, pl)
    lot_items = [i for i in result.items if "LOT 개수" in i.field_name]
    assert len(lot_items) >= 1
    print("  ✅ test_lot_count_mismatch 통과 (LOT 개수 불일치)")


def test_lot_numbers_mismatch():
    """LOT 번호 목록 불일치"""
    inv = InvoiceData(lot_numbers=["1125081447", "1125081448", "1125081999"])
    pl = PackingListData(
        lots=[
            LOTInfo(lot_no="1125081447"),
            LOTInfo(lot_no="1125081448"),
            LOTInfo(lot_no="1125081450"),  # Invoice에 없는 LOT
        ]
    )

    result = cross_check_documents(inv, pl)
    inv_only = [i for i in result.items if "Invoice Only" in i.field_name]
    pl_only = [i for i in result.items if "PL Only" in i.field_name]
    assert len(inv_only) >= 1, "Invoice에만 있는 LOT 감지 실패"
    assert len(pl_only) >= 1, "PL에만 있는 LOT 감지 실패"
    print("  ✅ test_lot_numbers_mismatch 통과 (LOT 번호 불일치)")


def test_duplicate_lots():
    """Packing List 내 중복 LOT 검출"""
    pl = PackingListData(
        lots=[
            LOTInfo(lot_no="1125081447"),
            LOTInfo(lot_no="1125081448"),
            LOTInfo(lot_no="1125081447"),  # 중복!
        ]
    )
    inv = InvoiceData(sap_no="TEST")  # 문서 2개 이상 필요

    result = cross_check_documents(inv, pl)
    dup_items = [i for i in result.items if "중복 LOT" in i.field_name]
    assert len(dup_items) == 1
    assert dup_items[0].level == CheckLevel.CRITICAL
    print("  ✅ test_duplicate_lots 통과 (중복 LOT → CRITICAL)")


def test_container_mismatch():
    """컨테이너 번호 불일치"""
    pl = PackingListData(
        lots=[
            LOTInfo(lot_no="1125081447", container_no="FFAU5355006"),
            LOTInfo(lot_no="1125081448", container_no="FFAU5355007"),
        ]
    )
    bl = BLData(
        containers=[
            ContainerInfo(container_no="FFAU5355006"),
            ContainerInfo(container_no="FFAU5355009"),  # PL에 없는 컨테이너
        ],
        total_containers=2,
    )

    result = cross_check_documents(None, pl, bl)
    cn_items = [i for i in result.items if "Container 번호" in i.field_name]
    assert len(cn_items) >= 1
    print("  ✅ test_container_mismatch 통과 (컨테이너 번호 불일치)")


def test_bl_no_normalized_match():
    """B/L 번호 정규화 후 일치 (MAEU prefix)"""
    inv = InvoiceData(bl_no="258468669")
    do = DOData(bl_no="MAEU258468669")

    result = cross_check_documents(inv, None, None, do)
    bl_items = [i for i in result.items if "B/L No" in i.field_name]
    # 정규화 후 같으면 불일치 없어야 함
    assert len(bl_items) == 0, f"B/L 정규화 후 일치해야 하는데: {bl_items}"
    print("  ✅ test_bl_no_normalized_match 통과 (B/L 정규화)")


def test_single_document_skip():
    """문서 1개만 있으면 크로스 체크 스킵"""
    inv = InvoiceData(sap_no="TEST")
    result = cross_check_documents(inv)
    assert result.is_clean
    print("  ✅ test_single_document_skip 통과 (단일 문서 스킵)")


def test_product_mismatch():
    """제품명 불일치 → CRITICAL"""
    inv = InvoiceData(product_name="LITHIUM CARBONATE BATTERY GRADE")
    bl = BLData(product_name="NICKEL SULFATE HEXAHYDRATE")  # 완전히 다른 제품

    result = cross_check_documents(inv, None, bl)
    prod_items = [i for i in result.items if "Product" in i.field_name]
    assert len(prod_items) == 1
    assert prod_items[0].level == CheckLevel.CRITICAL
    print("  ✅ test_product_mismatch 통과 (제품명 불일치 → CRITICAL)")


def test_result_summary():
    """결과 요약 문자열 테스트"""
    result = CrossCheckResult()
    assert "통과" in result.summary

    result.add("Test", CheckLevel.WARNING, "테스트 경고")
    assert "주의 1건" in result.summary

    result.add("Test2", CheckLevel.CRITICAL, "테스트 심각")
    assert "심각 1건" in result.summary
    assert result.has_critical is True
    print("  ✅ test_result_summary 통과")


def test_row_tag_global():
    """전체 문서 레벨 불일치 → 모든 행에 태그 적용"""
    inv = InvoiceData(sap_no="2200033057")
    pl = PackingListData(sap_no="2200033058")

    result = cross_check_documents(inv, pl)
    # SAP NO 불일치 = CRITICAL → global_level = CRITICAL
    assert result.global_level == CheckLevel.CRITICAL
    # 아무 LOT 번호에 대해서도 xc_critical 반환
    assert result.get_row_tag("1125081447") == "xc_critical"
    assert result.get_row_tag("ANY_LOT") == "xc_critical"
    print("  ✅ test_row_tag_global 통과 (전체 레벨 → 모든 행)")


def test_row_tag_lot_specific():
    """중복 LOT → 해당 LOT만 태그 적용"""
    pl = PackingListData(
        lots=[
            LOTInfo(lot_no="1125081447"),
            LOTInfo(lot_no="1125081448"),
            LOTInfo(lot_no="1125081447"),  # 중복
        ]
    )
    inv = InvoiceData()  # 빈 Invoice (2개 이상 문서 필요)

    result = cross_check_documents(inv, pl)
    lot_levels = result.get_lot_levels()
    assert "1125081447" in lot_levels
    assert lot_levels["1125081447"] == CheckLevel.CRITICAL
    assert "1125081448" not in lot_levels  # 정상 LOT는 매핑 없음
    print("  ✅ test_row_tag_lot_specific 통과 (중복 LOT만 하이라이트)")


def test_row_tag_clean():
    """불일치 없으면 태그 None"""
    result = CrossCheckResult()
    assert result.get_row_tag("ANY") is None
    assert result.global_level is None
    print("  ✅ test_row_tag_clean 통과 (정상 → 태그 없음)")


# ═══════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 SQM CrossCheckEngine 단위 테스트")
    print("=" * 60)

    print("\n[유틸리티 함수]")
    test_normalize_vessel()
    test_normalize_container()
    test_normalize_bl()
    test_vessel_fuzzy_match()
    test_weight_diff_pct()

    print("\n[크로스 체크 엔진 통합 테스트]")
    test_all_match()
    test_sap_no_mismatch()
    test_weight_warning()
    test_weight_critical()
    test_lot_count_mismatch()
    test_lot_numbers_mismatch()
    test_duplicate_lots()
    test_container_mismatch()
    test_bl_no_normalized_match()
    test_single_document_skip()
    test_product_mismatch()
    test_result_summary()
    test_row_tag_global()
    test_row_tag_lot_specific()
    test_row_tag_clean()

    print("\n" + "=" * 60)
    print("✅ 전체 테스트 통과!")
    print("=" * 60)
