# -*- coding: utf-8 -*-
"""
SQM v4.0.0 — 코딩 스타일 가이드
=================================

Q5: 변수명 생성 규칙 (PEP 8 + SQM 커스텀)
"""

# ═══════════════════════════════════════════════════
# 1. 변수명 규칙
# ═══════════════════════════════════════════════════
#
# 종류            | 규칙              | 예시
# --------------- | ----------------- | ----------------------------
# 변수            | snake_case        | lot_no, current_weight
# 함수/메서드     | snake_case        | get_inventory(), _refresh_tab()
# 프라이빗 메서드 | _접두어           | _log(), _set_status()
# 클래스          | PascalCase        | SQMDatabase, InventoryTabMixin
# 상수            | UPPER_SNAKE       | MAX_BACKUPS, DEFAULT_THEME
# 모듈/파일       | snake_case        | inventory_tab.py, export_mixin.py
# DB 컬럼         | snake_case        | lot_no, sap_no, current_weight
# GUI 헤더        | Title Case/UPPER  | 'LOT NO', 'Balance(Kg)'
#
# ═══════════════════════════════════════════════════
# 2. SQM 전용 명명 규칙
# ═══════════════════════════════════════════════════
#
# 접두어           | 의미              | 예시
# --------------- | ----------------- | ----------------------------
# _refresh_       | UI 갱신           | _refresh_inventory()
# _on_            | 이벤트 핸들러     | _on_drop(), _on_save()
# _setup_         | 초기화            | _setup_toolbar()
# _process_       | 처리 로직         | _process_inbound()
# _validate_      | 검증              | _validate_lot_no()
# _migrate_       | DB 마이그레이션   | _migrate_v396_search_indexes()
# _show_          | 다이얼로그 표시   | _show_lot_history()
# _generate_      | 파일 생성         | _generate_daily_pdf()
# _export_        | 내보내기          | _export_to_excel()
# _import_        | 가져오기          | _import_outbound_excel()
#
# ═══════════════════════════════════════════════════
# 3. 금지 사항
# ═══════════════════════════════════════════════════
#
# ❌ camelCase 변수: self.lotNo → self.lot_no
# ❌ 한글 변수명: 잔량 = 100 → balance = 100
# ❌ 단일 문자 변수: x, y, n (루프 카운터 제외)
# ❌ 축약어 남발: inv_proc → inventory_processor
# ❌ 동사 없는 함수명: lot_detail() → get_lot_detail()
#
# ═══════════════════════════════════════════════════
# 4. DB 컬럼 ↔ GUI 헤더 매핑 표준
# ═══════════════════════════════════════════════════
#
# DB 컬럼 (snake_case)   → GUI 헤더 (Title/UPPER)
# ---------------------- | -----------------------
# lot_no                 → LOT NO
# sap_no                 → SAP NO
# bl_no                  → BL NO
# container_no           → CONTAINER
# product                → PRODUCT
# net_weight             → NET(Kg)
# current_weight         → Balance(Kg)
# initial_weight         → Inbound(Kg)
# outbound_weight (가상) → Outbound(Kg)
# salar_invoice_no       → INVOICE NO
# ship_date              → SHIP DATE
# arrival_date           → ARRIVAL
# status                 → STATUS
"""
