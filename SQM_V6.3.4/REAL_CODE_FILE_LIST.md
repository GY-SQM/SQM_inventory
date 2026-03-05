# 실제 코드 파일 목록

아래 목록은 현재 워크스페이스에서 **실제 존재**하고, 최근 반영한 승인/피킹/Gate-1 흐름에 직접 연결된 파일입니다.

## 1) Allocation 승인 워크플로우

- `gui_app_modular/dialogs/allocation_approval_dialog.py`
- `gui_app_modular/dialogs/allocation_dialog.py`
- `gui_app_modular/handlers/outbound_handlers.py`
- `gui_app_modular/menu_registry.py`
- `engine_modules/inventory_modular/outbound_mixin.py`
- `engine_modules/db_migration_mixin.py`

## 2) Gate-1 승인 연계 / 감사 기록

- `gui_app_modular/handlers/outbound_handlers.py`
- `engine_modules/inventory_modular/outbound_mixin.py`

## 3) Picking 파서 경고/완화 로직

- `parsers/document_parser_modular/picking_mixin.py`

## 4) 참고

- 이 목록은 현재 앱 소스 기준입니다.
- `all_patches`, `SQM_v701_*`, `_tmp_*` 같은 보조/아카이브 폴더는 제외했습니다.
