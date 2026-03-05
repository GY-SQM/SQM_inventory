# -*- coding: utf-8 -*-
"""
SQM 크로스 체크 엔진 단위 테스트
v6.2.1 — 2026-02-27
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.cross_check_engine import (
    CrossCheckResult, CheckLevel,
    _normalize_vessel, _normalize_container, _normalize_bl,
    _vessel_fuzzy_match, _weight_diff_pct, cross_check_documents,
)
from parsers.document_models import (
    InvoiceData, PackingListData, BLData, DOData, LOTInfo, ContainerInfo,
)


def test_normalize_vessel():
    assert _normalize_vessel("CHARLOTTE MAERSK 535W") == "CHARLOTTE MAERSK 535W"
    assert _normalize_vessel("charlotte maersk") == "CHARLOTTE MAERSK"
    assert _normalize_vessel("") == ""


def test_normalize_container():
    assert _normalize_container("FFAU535500-6") == "FFAU5355006"
    assert _normalize_container("FFAU5355006") == "FFAU5355006"
    assert _normalize_container("") == ""


def test_normalize_bl():
    assert _normalize_bl("MAEU258468669") == "258468669"
    assert _normalize_bl("258468669") == "258468669"
    assert _normalize_bl("") == ""


def test_vessel_fuzzy_match():
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK 535W", "CHARLOTTE MAERSK") is True
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK", "CHARLOTTE MAERSK 535W") is True
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK", "CHARLOTTE MAERSK") is True
    assert _vessel_fuzzy_match("CHARLOTTE MAERSK", "EVER GIVEN") is False
    assert _vessel_fuzzy_match("", "CHARLOTTE MAERSK") is True


def test_weight_diff_pct():
    assert _weight_diff_pct(100000, 100000) == 0.0
    assert abs(_weight_diff_pct(100000, 99000) - 1.0) < 0.01
    assert _weight_diff_pct(0, 0) == 0.0


def test_all_match():
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
    assert result.is_clean


def test_sap_no_mismatch():
    inv = InvoiceData(sap_no="2200033057")
    pl = PackingListData(sap_no="2200033058")
    result = cross_check_documents(inv, pl)
    assert result.has_critical


def test_weight_warning():
    inv = InvoiceData(net_weight_kg=100020, gross_weight_kg=102625)
    bl = BLData(net_weight_kg=98500, gross_weight_kg=101000)
    result = cross_check_documents(inv, None, bl)
    nw_items = [i for i in result.items if i.field_name == "Net Weight"]
    assert len(nw_items) == 1
    assert nw_items[0].level == CheckLevel.WARNING


def test_weight_critical():
    inv = InvoiceData(net_weight_kg=100000)
    bl = BLData(net_weight_kg=90000)
    result = cross_check_documents(inv, None, bl)
    nw_items = [i for i in result.items if i.field_name == "Net Weight"]
    assert len(nw_items) == 1
    assert nw_items[0].level == CheckLevel.CRITICAL


def test_lot_numbers_mismatch():
    inv = InvoiceData(lot_numbers=["1125081447", "1125081448", "1125081999"])
    pl = PackingListData(
        lots=[
            LOTInfo(lot_no="1125081447"),
            LOTInfo(lot_no="1125081448"),
            LOTInfo(lot_no="1125081450"),
        ]
    )
    result = cross_check_documents(inv, pl)
    inv_only = [i for i in result.items if "Invoice Only" in i.field_name]
    pl_only = [i for i in result.items if "PL Only" in i.field_name]
    assert len(inv_only) >= 1
    assert len(pl_only) >= 1


def test_duplicate_lots():
    pl = PackingListData(
        lots=[
            LOTInfo(lot_no="1125081447"),
            LOTInfo(lot_no="1125081448"),
            LOTInfo(lot_no="1125081447"),
        ]
    )
    inv = InvoiceData(sap_no="TEST")
    result = cross_check_documents(inv, pl)
    dup_items = [i for i in result.items if "중복 LOT" in i.field_name]
    assert len(dup_items) == 1
    assert dup_items[0].level == CheckLevel.CRITICAL


def test_bl_no_normalized_match():
    inv = InvoiceData(bl_no="258468669")
    do = DOData(bl_no="MAEU258468669")
    result = cross_check_documents(inv, None, None, do)
    bl_items = [i for i in result.items if "B/L No" in i.field_name]
    assert len(bl_items) == 0


def test_row_tag_global():
    inv = InvoiceData(sap_no="2200033057")
    pl = PackingListData(sap_no="2200033058")
    result = cross_check_documents(inv, pl)
    assert result.global_level == CheckLevel.CRITICAL
    assert result.get_row_tag("1125081447") == "xc_critical"
