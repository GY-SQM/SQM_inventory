# SQM v5.7.7 — 릴리스 노트

## 개요

v5.7.6 출고 API 디버깅과 v5.7.7 코드 품질·통일 작업을 반영한 릴리스입니다.  
**DB 스키마/마이그레이션 변경 없음.**

---

## 버전 요약

| 버전 | 요약 |
|------|------|
| 5.7.6 | 출고 API 디버깅 — import_handlers `process_outbound(allocation_data)` 시그니처 통일, LOT 전량 출고 시 current_weight 조회 |
| 5.7.7 | 릴리스 태그 + 두 검토안 총괄 디버깅(버전 fallback, safe_int/safe_date, 메시지박스 통일, except+pass 정리, DO 메뉴 추가 등) |

---

## v5.7.6 — 출고 API 디버깅

- **문제**: `import_handlers.py`가 `process_outbound(lot_no, destination)` 2인자로 호출. 엔진은 `process_outbound(allocation_data)` 1인자만 지원.
- **수정**: Excel 출고 시 해당 LOT의 `current_weight`를 DB에서 조회한 뒤 `allocation_data = [{'lot_no', 'weight_kg', 'customer'}]` 형태로 구성하여 `process_outbound(allocation_data)` 호출.
- **파일**: `gui_app_modular/handlers/import_handlers.py`

---

## v5.7.7 — 코드 품질·통일 (DB 미접촉)

### 1. DO 후속 연결 메뉴 추가
- **도구 메뉴**에 "📋 D/O 후속 연결" 항목 추가.
- **파일**: `gui_app_modular/mixins/custom_menubar.py`, `gui_app_modular/mixins/menu_mixin.py`
- **결과**: 파일 → 입고, **도구** 두 경로에서 접근 가능.

### 2. 버전 fallback 단일화
- **version.py** 단일 소스. import 실패 시 fallback을 `__version__ = "0.0.0"`, `APP_NAME = "SQM 재고관리 시스템"`으로 통일.
- **수정 파일**: `run_app.py`, `gui_app_modular/utils/constants.py`, `config.py`, `parsers/document_parser_modular/__init__.py`, `engine_modules/inventory_modular/__init__.py`, `engine_modules/inventory.py`

### 3. safe_int 중복 제거
- `gui_app_modular/utils/helpers.py`에서 로컬 `safe_int` 구현 제거, `utils.common.safe_int` re-export로 통일.

### 4. safe_date 용도별 정리
- **helpers**: `safe_date` → date 객체 반환. 별칭 `safe_date_to_date` 추가, docstring에 "문자열 필요 시 safe_utils.safe_date_str" 명시.
- **safe_utils**: `safe_date` → 문자열 반환. 별칭 `safe_date_str` 추가, docstring에 "날짜 객체 필요 시 helpers.safe_date_to_date" 명시.

### 5. 메시지박스 통일 (CustomMessageBox)
- `messagebox` 직접 호출 → `CustomMessageBox`로 교체.
- **수정 파일**: `onestop_inbound.py`(1), `auto_backup.py`(3), `gemini_chat_gui.py`(1), `ui_ops_helper.py`(1), `mac_guard.py`(2).

### 6. except + pass → logger.debug (AGENTS.md 준수)
- **수정 파일**: `onestop_inbound.py`, `column_toggle.py`, `tree_enhancements.py`, `theme_mixin.py`, `mac_guard.py`
- 예외 시 `logger.debug(f"Suppressed: {e}")` 사용.

### 7. Unused import 제거
- `engine_modules/db_migration_mixin.py`: 미사용 `import configparser` 제거.

### 8. 문서
- `docs/CODE_QUALITY_AND_IMPROVEMENTS.md`: §1.3 두 검토안 총괄 디버깅 내역 추가.
- `docs/DEBUGGING_RISK_OVERVIEW.md`: 적용 완료 항목 갱신(safe_int, 버전, safe_date, 메시지박스).

---

## 변경된 파일 요약 (v5.7.6 + v5.7.7)

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.7.7, VERSION_HISTORY |
| gui_app_modular/handlers/import_handlers.py | process_outbound(allocation_data) 시그니처 통일 |
| gui_app_modular/mixins/custom_menubar.py | 도구 메뉴 D/O 후속 연결 추가 |
| gui_app_modular/mixins/menu_mixin.py | 도구 메뉴 D/O 후속 연결 추가 |
| run_app.py, config.py, gui_app_modular/utils/constants.py | 버전 fallback 0.0.0·APP_NAME 통일 |
| parsers/document_parser_modular/__init__.py | version.py 참조 |
| engine_modules/inventory_modular/__init__.py, engine_modules/inventory.py | version.py 참조 |
| gui_app_modular/utils/helpers.py | safe_int 제거·re-export, safe_date docstring·safe_date_to_date 별칭 |
| gui_app_modular/utils/safe_utils.py | safe_date docstring·safe_date_str 별칭 |
| gui_app_modular/dialogs/onestop_inbound.py | except+pass→logger, messagebox→CustomMessageBox |
| gui_app_modular/dialogs/auto_backup.py | messagebox→CustomMessageBox |
| gui_app_modular/utils/column_toggle.py | except→logger.debug |
| gui_app_modular/utils/tree_enhancements.py | except→logger.debug |
| gui_app_modular/mixins/theme_mixin.py | except→logger.debug |
| security/mac_guard.py | except→logger.debug, messagebox→CustomMessageBox |
| features/ai/gemini_chat_gui.py | messagebox→CustomMessageBox |
| ui_ops_helper.py | messagebox→CustomMessageBox |
| engine_modules/db_migration_mixin.py | unused configparser 제거 |
| docs/CODE_QUALITY_AND_IMPROVEMENTS.md | §1.3 총괄 디버깅 반영 |
| docs/DEBUGGING_RISK_OVERVIEW.md | 적용 완료 항목 갱신 |

---

*작성일: 2026-02-16 | SQM v5.7.7*
