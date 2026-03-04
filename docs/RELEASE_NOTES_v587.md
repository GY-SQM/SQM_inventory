# SQM v5.8.7 — UI 마스터 플랜·Phase1/2 적용

## ※ 버전 표기 안내
**이전에 푸시된 v8.7.0 태그는 버전 표기 오류입니다. 정식 버전은 v5.8.7 입니다.**

---

## 개요
- **UI 디자인 마스터 플랜** 문서 추가 및 **Phase1(퀵윈)·Phase2(색상 팔레트)** 적용.
- 재고/톤백 기본 표시 컬럼 8개, 트리뷰 행간 36px·제브라, ThemeColors 단일 소스 적용.
- 톤백 리스트 SAP NO 컬럼: `-` 및 접미사 제거 후 표시 (예: `1125072729-S0` → `1125072729`).

---

## v5.8.7에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **문서** | docs/UI_DESIGN_MASTER_PLAN.md, docs/UI_IMPLEMENTATION_PHASES.md |
| **Phase1** | 기본 표시 컬럼 8개(재고 19열·톤백 20열 중), 트리뷰 행간 36px·제브라, ColumnToggleBar 3-tuple(default_visible) |
| **Phase2** | toolbar_mixin·inventory_tab·tonbag_tab·custom_menubar·statusbar_mixin·settings_dialog 색상 → ThemeColors.get(key, is_dark) |
| **톤백 SAP NO** | 톤백 리스트에서 SAP NO 표시 시 `-` 및 접미사 제거 (표시만, DB 저장값은 유지) |
| **버전** | version.py — __version__ = 5.8.7 |

---

## 변경된 파일 요약

| 구분 | 파일 |
|------|------|
| **버전** | version.py |
| **문서** | docs/UI_DESIGN_MASTER_PLAN.md, docs/UI_IMPLEMENTATION_PHASES.md, docs/RELEASE_NOTES_v587.md |
| **GUI 탭** | gui_app_modular/tabs/inventory_tab.py, tonbag_tab.py |
| **GUI 유틸** | gui_app_modular/utils/ui_constants.py, column_toggle.py, table_styler.py |
| **GUI 믹스인** | gui_app_modular/mixins/toolbar_mixin.py, custom_menubar.py, statusbar_mixin.py |
| **다이얼로그** | gui_app_modular/dialogs/settings_dialog.py |
| **기타** | (이전 커밋 대비 추가 변경분 포함) |

---

*작성일: 2026-02-17 | SQM v5.8.7*
