# SQM v5.9.1 Release Notes

**Release Date**: 2026-02-18  
**Type**: Bugfix + UI Improvement  
**변경 파일**: 44개 (112 추가, 6,048 삭제)

---

## 🐛 P0 — 크래시 버그 수정 (9건)

| # | 파일 | 수정 내용 |
|---|------|----------|
| P0-1 | `engine_modules/inventory_modular/engine.py` | `import sqlite3` 누락 → 추가 |
| P0-2 | `gui_app_modular/mixins/database_mixin.py` | `import sqlite3` 누락 → 추가 |
| P0-3 | `engine_modules/inventory_modular/return_mixin.py` | `from datetime import date` → `date, datetime` |
| P0-4 | `utils/backup.py`, `parsers/pdf_parser.py` | `except ValueError:` → `except ValueError as e:` (4곳) |
| P0-5 | `gui_app_modular/dialogs/onestop_inbound.py` | `msgbox` 미정의 → `from tkinter import messagebox as msgbox` |
| P0-6 | `gui_app_modular/mixins/custom_menubar.py`, `tabs/inventory_tab.py`, `main_app.py` | `tk`/`ttk` import 누락 → 추가 |
| P0-7 | `engine_modules/database.py` | `transaction()` 중복 정의 제거 — HardStopException 보호 누락된 버전 삭제 |
| P0-8 | `engine_modules/db_migration_mixin.py` | `_migrate_v423_tonbag_location()` 중복 정의 제거 |
| P0-9 | `gui_app_modular/utils/ui_ops_helper.py` | `self.root` → `parent` (staticmethod 내 참조 오류) |

## 🧹 P1 — 릴리스 위생

- **버전 통일**: `version.py`, `VERSION.txt`, `updates/latest.json` → 동일 버전
- **빌드 스크립트**: `build_exe.bat` 하드코딩 버전 제거, `sqm_inventory.spec` 동적 버전 적용
- **데드 코드 삭제**: `SQM_v587_FINAL_PATCH/`, `PATCH/`, `docs_v531/`, `gui_processors/`, `__init__.py`(루트), `scripts/migrate_v563_tonbag_weight.py`
- **배치 통일**: 중복 `.bat` 파일 제거 → `SQM_실행.bat` 단일 유지
- **문서 정리**: `README_PATCH_*.md` → `docs/archive/` 이동
- **.gitignore**: `backup/`, `.pytest_cache/`, 런타임 설정 파일 추가

## 🎨 UI 개선

- **샘플 UID**: `S0` → `0` 으로 표시 변경 (6곳: `tonbag_compat.py`, `tonbag_tab.py`, `lot_detail_dialog.py`)
- **트리뷰 폰트 축소**: 재고/톤백 리스트 14pt → 11pt (가독성 개선)
- **컨테이너 구분 버튼 이동**: 설정/도구 메뉴 → 필터바 초기화 옆 체크박스로 이동 (접근성 향상)

## 🔧 Excel Round-trip 수정

- **`bulk_import_mixin.py`**: 컬럼명 정규화 추가 (`LOT NO` → `lot_no` 매칭)
- **`tonbag_location_uploader.py`**: 동일 정규화 적용 (공백/하이픈 → 밑줄)
- 프로그램이 내보낸 Excel 파일을 다시 읽을 때 컬럼 매칭 실패 문제 해결

---

## 영향 범위

- **엔진**: `database.py`, `engine.py`, `return_mixin.py`, `db_migration_mixin.py`, `tonbag_compat.py`
- **GUI**: `inventory_tab.py`, `tonbag_tab.py`, `toolbar_mixin.py`, `custom_menubar.py`, `menu_mixin.py`, `tree_enhancements.py`
- **파서**: `pdf_parser.py`, `onestop_inbound.py`
- **유틸**: `backup.py`, `ui_ops_helper.py`, `bulk_import_mixin.py`, `tonbag_location_uploader.py`
- **빌드**: `build_exe.bat`, `sqm_inventory.spec`, `.gitignore`

---

**(주) 지와이로지스 2026년 2월 18일**
