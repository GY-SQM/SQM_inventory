# 운영 필수 파일 목록 (최소)

아래 파일만 있으면, 현재 반영된 핵심 운영 흐름(Allocation 승인 워크플로우 + Gate-1 승인 연계 + Picking 경고)이 동작합니다.

## 필수 파일

- `engine_modules/inventory_modular/outbound_mixin.py`
- `engine_modules/db_migration_mixin.py`
- `gui_app_modular/handlers/outbound_handlers.py`
- `gui_app_modular/dialogs/allocation_dialog.py`
- `gui_app_modular/dialogs/allocation_approval_dialog.py`
- `gui_app_modular/menu_registry.py`
- `parsers/document_parser_modular/picking_mixin.py`

## 용도 요약

- 승인 워크플로우 엔진/반영: `engine_modules/inventory_modular/outbound_mixin.py`
- 승인 관련 DB 컬럼/테이블 마이그레이션: `engine_modules/db_migration_mixin.py`
- 출고 핸들러(승인 코드/사유/Gate-1 실행 연계): `gui_app_modular/handlers/outbound_handlers.py`
- Allocation 입력/예약 + 승인대기 자동 이동: `gui_app_modular/dialogs/allocation_dialog.py`
- 승인대기/승인이력 UI: `gui_app_modular/dialogs/allocation_approval_dialog.py`
- 출고 메뉴 노출: `gui_app_modular/menu_registry.py`
- 피킹 파서 경고/완화: `parsers/document_parser_modular/picking_mixin.py`
