# -*- coding: utf-8 -*-
"""
SQM 재고관리 - 메뉴 항목 단일 정의 (Menu Registry)
=================================================

custom_menubar.py 와 menu_mixin.py 의 네이티브 메뉴가 동일한 항목을 표시하도록
'파일' 메뉴 내 입고/출고 항목을 여기서만 정의합니다.
새 메뉴 항목은 이 파일에만 추가하면 두 메뉴에 모두 반영됩니다.

각 항목: (라벨, app 메서드명, optional?)
- optional=True 이면 app에 해당 메서드가 있을 때만 메뉴에 추가됩니다.
"""

# 입고 서브메뉴에 들어갈 항목 (순서 유지, v6.0.6 3단계: 단일 소스)
# optional=True 이면 app에 해당 메서드가 있을 때만 메뉴에 추가
FILE_MENU_INBOUND_ITEMS = [
    ("📄 PDF 스캔 입고", "_on_pdf_inbound"),
    ("📊 엑셀 파일 수동 입고", "_bulk_import_inventory_simple"),
    ("📋 D/O 후속 연결", "_on_do_update"),
    ("📍 톤백 위치 매핑", "_on_tonbag_location_upload", True),
    ("📋 입고현황 불러오기", "_bulk_import_inventory", True),
    ("📂 반품 입고 (Excel)", "_on_return_inbound_upload"),
    ("🔄 반품 (재입고)", "_show_return_dialog"),  # 소량/다량 반품 다이얼로그
    ("📊 반품 사유 통계", "_show_return_statistics"),
    ("📧 반품 경고 이메일", "_send_return_alert_email"),
    ("⚙️ 이메일 설정", "_show_email_config"),
    ("📋 정합성 검증 리포트", "_on_integrity_report", True),  # v7.0.1
]

# 출고 서브메뉴에 들어갈 항목 (순서 유지)
FILE_MENU_OUTBOUND_ITEMS = [
    ("📋 Allocation 입력 (파일/붙여넣기)", "_on_allocation_input_unified"),
    ("📋 Picking List 업로드 (PDF)", "_on_picking_list_upload"),
    ("📊 바코드 스캔 업로드 (CSV/Excel)", "_on_barcode_scan_upload"),
    ("📊 Sales Order 업로드 (Excel)", "_on_sales_order_upload", True),  # optional
]
