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
    ("📋 입고 현황 조회", "_bulk_import_inventory", True),
    ("📂 반품 입고 (Excel)", "_on_return_inbound_upload"),
    ("🔄 반품 (재입고)", "_show_return_dialog"),  # 소량/다량 반품 다이얼로그
    ("📊 반품 사유 통계", "_show_return_statistics"),
    ("📧 반품 경고 이메일", "_send_return_alert_email"),
    ("⚙️ 이메일 설정", "_show_email_config"),
    ("📋 정합성 검증 리포트", "_on_integrity_report", True),  # v7.0.1
]

# 입고 > 반품(재입고) 서브메뉴 항목 (toolbar/custom menubar 공용)
# 각 항목: (라벨, mode)
# - mode=0: 소량 반품(1~2건)
# - mode=1: 다량 반품(Excel)
FILE_MENU_INBOUND_RETURN_SUB_ITEMS = [
    ("📝 소량 반품 (1~2건)", 0),
    ("📂 다량 반품 (Excel)", 1),
]

# 출고 서브메뉴에 들어갈 항목 (순서 유지)
FILE_MENU_OUTBOUND_ITEMS = [
    ("📋 Allocation 입력 (파일/붙여넣기)", "_on_allocation_input_unified"),
    ("✅ Allocation 승인 대기", "_show_allocation_approval_queue", True),
    ("📜 승인 이력(조회)", "_show_allocation_approval_history", True),
    ("📌 예약 반영(승인분)", "_apply_approved_allocation", True),
    None,  # 구분선
    ("📋 Picking List 업로드 (PDF)", "_on_picking_list_upload"),
    ("📊 바코드 스캔 업로드 (CSV/Excel)", "_on_barcode_scan_upload"),
    ("🔁 Swap 리포트 (기간/필터)", "_show_swap_report_dialog", True),
    ("📊 Sales Order 업로드 (Excel)", "_on_sales_order_upload", True),  # optional
    ("📋 출고 현황 조회", "_show_outbound_history", True),
    None,  # 구분선
    ("📤 빠른 출고 (붙여넣기)", "_on_quick_outbound_paste"),
    None,  # 구분선
    ("📋 판매 배정 탭으로 이동 (취소 버튼은 탭에서 사용)", "_on_go_allocation_tab"),
]

# 파일 > 내보내기 공통 항목 (toolbar/custom/native 공용)
# 각 항목: (라벨, export_option)
FILE_MENU_EXPORT_ITEMS = [
    ("📋 통관요청 양식", 1),
    ("📊 루비리 양식", 2),
    ("🎒 톤백 현황", 4),
    ("⭐ 통합 현황", 6),
]

# 파일 > 백업 공통 항목 (toolbar/custom/native 공용)
# 각 항목: (라벨, app 메서드명)
FILE_MENU_BACKUP_ITEMS = [
    ("💾 백업 생성", "_on_backup_click"),
    ("🔄 복원", "_on_restore_click"),
    ("📋 백업 목록", "_show_backup_list"),
]
