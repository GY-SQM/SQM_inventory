# SQM v6.0.7 Release Notes

**Release Date:** 2026-02-21  
**Phase:** UI 메뉴 menu_registry 기반 정리 (3단계)

---

## 변경 요약

### 1. 입고 메뉴 단일 소스 (menu_registry)

- **FILE_MENU_INBOUND_ITEMS**에 다음 항목 추가 (optional=True):
  - **📍 톤백 위치 매핑** (`_on_tonbag_location_upload`)
  - **📋 입고현황 불러오기** (`_bulk_import_inventory`)
- 입고 메뉴 순서: PDF 스캔 입고 → 엑셀 수동 입고 → D/O 후속 연결 → 톤백 위치 매핑(opt) → 입고현황 불러오기(opt) → 반품 입고 (Excel) → 반품 (재입고).
- 커스텀 메뉴바·네이티브 메뉴·툴바가 동일한 목록을 사용하도록 정리.

### 2. 툴바 입고 메뉴 — menu_registry 적용

- **toolbar_mixin._build_inbound_menu**를 하드코딩 목록에서 **FILE_MENU_INBOUND_ITEMS** 기반으로 변경.
- optional 항목은 해당 메서드가 있을 때만 표시.
- 반품 (재입고)는 기존처럼 서브메뉴(소량 반품 / 다량 반품) 유지.
- ImportError 시 기존과 유사한 폴백 유지.

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.7, VERSION_HISTORY 추가 |
| `gui_app_modular/menu_registry.py` | FILE_MENU_INBOUND_ITEMS에 톤백 위치·입고현황 불러오기(optional) 추가 |
| `gui_app_modular/mixins/toolbar_mixin.py` | _build_inbound_menu를 menu_registry 기반으로 변경 |
| `docs/RELEASE_NOTES_v607.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 21일**
