# -*- coding: utf-8 -*-
"""
carrier_templates/msc.py — SQM v8.0.6 PATCH
=============================================
MSC(Mediterranean Shipping Company) 선사 템플릿 2 정의

설계 원칙:
  - 기존 bl_carrier_registry.py의 MSC CarrierTemplate 설정과 호환
  - BL = Sea Waybill 구조 (RIDER PAGE 주의)
  - DO는 샘플 미확보 상태 → generic 규칙 적용 후 수동 검수 권장

[수정이력]
  2026-03-17  Ruby  SQM v8.0.6 신규 생성
"""
from __future__ import annotations
from typing import Any, Dict, List


# ─────────────────────────────────────────────────────────────────
# BL 서브템플릿 목록 (우선순위 순)
# ─────────────────────────────────────────────────────────────────
_MSC_BL_SUBTEMPLATES: List[Dict[str, Any]] = [
    {
        "template_id": "MSC_BL_V1",
        "doc_type": "BL",
        "priority": 100,
        "title_keywords": [
            "MEDITERRANEAN SHIPPING COMPANY",
            "SEA WAYBILL No.",
            "MSC CHILE",
            "MSC ",
        ],
        "match_rules": {
            "required_any": [
                "MEDITERRANEAN SHIPPING COMPANY",
                "SEA WAYBILL No.",
            ],
            "exclude_any": [
                "MAERSK",
                "MAEU",
                "D/O 발급확인서",
                "DELIVERY ORDER",
            ],
        },
        "field_rules": {
            "bl_no": {
                # MSC: 1페이지 첫 줄 끝에 위치 (예: MEDUFP963996)
                "label_aliases": ["SEA WAYBILL No.", "B/L No.", "SEA WAYBILL NUMBER"],
                "type": "text",
                "required": True,
                # MSC는 BL No가 라벨 오른쪽이 아닌 같은 줄 끝에 있음
                "extract_rule": "same_line_end",
            },
            "booking_no": {
                "label_aliases": ["Booking No.", "Booking Number"],
                "type": "text",
            },
            "vessel": {
                "label_aliases": ["Vessel", "Ocean Vessel", "Vessel Name"],
                "type": "text",
            },
            "voyage_no": {
                "label_aliases": ["Voyage No.", "Voyage"],
                "type": "text",
            },
            "shipper": {
                "label_aliases": ["Shipper", "Shipper/Exporter"],
                "type": "block_text",
            },
            "consignee": {
                "label_aliases": ["Consignee"],
                "type": "block_text",
            },
            "notify_party": {
                "label_aliases": ["Notify Party", "Notify Address"],
                "type": "block_text",
            },
            "port_of_loading": {
                "label_aliases": ["Port of Loading", "Place of Receipt"],
                "type": "text",
            },
            "port_of_discharge": {
                "label_aliases": ["Port of Discharge", "Place of Delivery"],
                "type": "text",
            },
            "container_table": {
                # ★ MSC 주의: Rider Page(2~3페이지)의 컨테이너 번호가 BL No로 오탐될 수 있음
                "anchor_keywords": [
                    "Container No",
                    "Seal No",
                    "KGS",
                    "CBM",
                    "ML-CL",
                ],
                "type": "table",
                "page_scope": "page0",  # 1페이지만 사용 (Rider Page 제외)
            },
            "gross_weight_total": {
                "label_aliases": ["Total Gross Weight", "GROSS WEIGHT"],
                "type": "number",
            },
            "sap_no": {
                # MSC SAP는 Rider Page(2~3페이지)에 위치
                "label_aliases": ["SAP", "SAP NO", "SAP No."],
                "type": "text",
                "page_scope": "page1_to_2",
            },
        },
        "preview_fields": [
            "bl_no",
            "booking_no",
            "vessel",
            "voyage_no",
            "port_of_discharge",
            "shipper",
            "consignee",
            "first_container_no",
            "gross_weight_total",
            "sap_no",
        ],
        "normalizers": {
            "bl_no": "strip_upper",
            "booking_no": "strip",
            "vessel": "strip_upper",
            "voyage_no": "strip_upper",
            "port_of_discharge": "strip_upper",
            "first_container_no": "container_no_upper",
            "gross_weight_total": "number_only",
            "sap_no": "strip",
        },
        "gemini_hint": (
            "【MSC Sea Waybill 전용 규칙】\n"
            "BL No 위치: 1페이지 상단 맨 첫 번째 줄 끝에 있습니다.\n"
            "형식 예시: MEDUFP963996 (MEDU로 시작하는 알파벳+숫자 혼합)\n"
            "⚠️ 주의: Rider Page(2~3페이지)에 컨테이너 번호(MSNU..., TCLU...)가 있는데 "
            "이것은 BL No가 아닙니다. 절대 혼동하지 마세요.\n"
            "⚠️ SAP NO는 Rider Page(2~3페이지)에 있음\n"
            "⚠️ 'SEA WAYBILL No.'가 여러 번 등장하면 반드시 1페이지 것만 사용하세요."
        ),
        # 기존 bl_carrier_registry 호환 플래그
        "_bl_page_scope": "page0",
        "_sap_page_hint": "page1_to_2",
        "_bl_extract_pattern": (
            r"MEDITERRANEAN SHIPPING COMPANY.*?SEA WAYBILL No\.\s+(\w{6,20})"
        ),
        "_bl_format_hint": "MEDUFP963996",
    },
]

# ─────────────────────────────────────────────────────────────────
# DO 서브템플릿 목록 (MSC DO 샘플 미확보 → generic 기반)
# ─────────────────────────────────────────────────────────────────
_MSC_DO_SUBTEMPLATES: List[Dict[str, Any]] = [
    {
        "template_id": "MSC_DO_V1",
        "doc_type": "DO",
        "priority": 80,  # 샘플 미확보로 priority 낮춤
        "title_keywords": [
            "MSC",
            "D/O",
            "DELIVERY ORDER",
            "MEDITERRANEAN SHIPPING",
        ],
        "match_rules": {
            "required_any": [
                "MEDITERRANEAN SHIPPING",
                "MSC",
            ],
            "exclude_any": [
                "SEA WAYBILL No.",
                "MAERSK",
            ],
        },
        "field_rules": {
            "do_no": {
                "label_aliases": ["D/O No.", "DO No.", "Delivery Order No."],
                "type": "text",
                "required": True,
            },
            "bl_no": {
                "label_aliases": ["B/L No.", "Sea Waybill No.", "SEA WAYBILL No."],
                "type": "text",
                "required": True,
            },
            "ocean_vessel": {
                "label_aliases": ["Vessel", "Ocean Vessel"],
                "type": "text",
            },
            "voyage_no": {
                "label_aliases": ["Voyage No."],
                "type": "text",
            },
            "consignee": {
                "label_aliases": ["Consignee"],
                "type": "block_text",
            },
            "container_table": {
                "anchor_keywords": ["Container", "Seal", "Weight"],
                "type": "table",
            },
            "free_time_table": {
                "anchor_keywords": ["FREE TIME", "Free Time", "반납", "Return"],
                "type": "table",
            },
            "gross_weight_total": {
                "label_aliases": ["Gross Weight", "Total Weight"],
                "type": "number",
            },
        },
        "preview_fields": [
            "do_no",
            "bl_no",
            "ocean_vessel",
            "voyage_no",
            "consignee",
            "first_container_no",
            "gross_weight_total",
        ],
        "normalizers": {
            "do_no": "strip",
            "bl_no": "strip_upper",
            "ocean_vessel": "strip_upper",
            "voyage_no": "strip_upper",
            "first_container_no": "container_no_upper",
            "gross_weight_total": "number_only",
        },
        "gemini_hint": (
            "【MSC D/O 전용 (샘플 미확보 — 검수 필수)】\n"
            "D/O No: 상단 'D/O No.' 라벨 오른쪽\n"
            "B/L No: MSC Sea Waybill 번호 (MEDU로 시작)\n"
            "⚠️ MSC DO 실제 샘플 기반이 아닙니다. 파싱 후 반드시 수동 검수하세요."
        ),
    },
]

# ─────────────────────────────────────────────────────────────────
# MSC 템플릿 Family (Template 2)
# ─────────────────────────────────────────────────────────────────
MSC_TEMPLATE_FAMILY: Dict[str, Any] = {
    "family_id": "TEMPLATE_2_MSC",
    "carrier": "MSC",
    "carrier_name": "Mediterranean Shipping Company",
    "priority": 100,
    "aliases": [
        "MSC",
        "MEDITERRANEAN SHIPPING COMPANY",
        "MEDITERRANEAN SHIPPING",
        "MSC CHILE",
    ],
    "match_rules": {
        "required_any": [
            "MEDITERRANEAN SHIPPING COMPANY",
            "SEA WAYBILL No.",
            "MSC CHILE",
        ],
        "exclude_any": [
            "MAERSK",
            "MAEU",
            "MAERSK LINE",
            "CMA CGM",
            "HMM",
            "ONE",
        ],
        "score_rules": [
            {"contains": "MEDITERRANEAN SHIPPING COMPANY", "score": 40},
            {"contains": "SEA WAYBILL No.", "score": 30},
            {"contains": "MSC CHILE", "score": 20},
            {"contains": "MSC ", "score": 15},
            {"contains": "MEDUFP", "score": 25},
            {"contains": "MEDU", "score": 20},
            {"contains": "B/L NO.", "score": 10},
        ],
    },
    "subtemplates": {
        "BL": _MSC_BL_SUBTEMPLATES,
        "DO": _MSC_DO_SUBTEMPLATES,
    },
}


def get_msc_template_family() -> Dict[str, Any]:
    """MSC 템플릿 Family 반환 (template_registry 등록용)"""
    return MSC_TEMPLATE_FAMILY
