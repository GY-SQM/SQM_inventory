# UI 개선 단계별 실행 계획

> **목적**: UI_DESIGN_MASTER_PLAN.md의 7가지 항목을 **실행 순서**와 **단계**로 나누어, 리스크를 줄이고 체감 효과를 빠르게 내기 위한 가이드.

---

## 단계 나누는 원칙

| 원칙 | 설명 |
|------|------|
| **퀵윈 먼저** | 변경 범위가 작고, 사용자가 바로 체감하는 작업을 앞에 둔다. |
| **기반 먼저** | 나중 단계에서 같은 파일을 다시 손대지 않도록, “기반”(색상)을 퀵윈 직후에 둔다. |
| **같은 파일 묶기** | 한 단계 안에서 같은 파일을 여러 번 수정하는 것보다, 한 번 열었을 때 색상+간격+폰트를 같이 정리하면 효율적이다. |
| **독립 작업 뒤로** | 다이얼로그 크기·툴바처럼 독립적인/코드량 많은 작업은 단계를 나누어 뒤에 둔다. |

---

## 권장 5단계 요약

| 단계 | 내용 | 예상 시간 | 수정 파일 수 | 효과 |
|------|------|-----------|--------------|------|
| **1** | 퀵윈: 기본 컬럼 7~8개 + 트리뷰 행간·제브라 | 1~2시간 | 3~4개 | 첫인상·가독성 즉시 개선 |
| **2** | 색상 팔레트 통일 (ThemeColors) | 2~3시간 | 약 15개 | 다크/라이트 테마 완전 대응 |
| **3** | 간격(Spacing) + 폰트 3단계 통일 | 2시간 내외 | 20개 내외 | 시각적 정돈·위계 명확 |
| **4** | 다이얼로그 크기 표준화 (DialogSize) | 1~2시간 | 30개 내외 | 창 크기 일관성 |
| **5** | 툴바 미니멀화 (밑줄 기반) | 2~3시간 | 1개(대형) | 코드 약 200줄 감소, UI 통일 |

---

## Phase 1 — 퀵윈 (우선순위 3 + 4)

**목표**: 수정 범위 작고, 사용자 체감 큰 것만 먼저 적용.

### 1.1 기본 표시 컬럼 7~8개 (우선순위 3)

| 작업 | 파일 | 내용 |
|------|------|------|
| 재고 리스트 | `gui_app_modular/tabs/inventory_tab.py` | `INVENTORY_COLUMNS` 5번째 값 `default_visible`: 핵심 7~8개만 `True`, 나머지 `False`. (예: row_num, lot_no, sap_no, bl_no, product, status, current_weight, net_weight) |
| 톤백 리스트 | `gui_app_modular/tabs/tonbag_tab.py` | 컬럼 정의에 `default_visible` 추가(5번째 값), 7~8개만 `True`. 초기 `tree_sublot.configure(displaycolumns=...)`로 기본 표시 컬럼 적용. |

**검증**: 앱 실행 → 재고/톤백 탭 열었을 때 기본 7~8개만 보이고, “표시 컬럼” 체크로 나머지 표시 가능한지 확인.

### 1.2 트리뷰 행간 36px + 제브라 (우선순위 4)

| 작업 | 파일 | 내용 |
|------|------|------|
| 행 높이 | `gui_app_modular/utils/ui_constants.py` | `ReadableStyle.ROW_HEIGHT = 36` (현 38이면 36으로 조정). |
| 제브라 | `gui_app_modular/utils/table_styler.py`, `tree_enhancements.py` | zebra(stripe) 태그가 재고/톤백 트리뷰에 모두 적용되는지 확인. 미적용 구간 있으면 `ThemeColors.get('tree_stripe', is_dark)` 등으로 적용. |

**검증**: 재고·톤백 리스트에서 행 높이와 짝/홀 행 배경이 구분되는지 확인.

---

## Phase 2 — 색상 팔레트 통일 (우선순위 1)

**목표**: 하드코딩 색상을 `ThemeColors.get(key, is_dark)`로 교체해 다크/라이트 전환 시 UI가 깨지지 않게 함.

### 2.1 is_dark 소스 일원화

- `theme_mixin.py` 등에서 `current_theme` 기준 `ThemeColors.is_dark_theme(current_theme)` 사용하는지 확인.
- 다이얼로그/탭에서 색상을 쓸 때 `is_dark`를 인자로 넘기거나, 앱에서 `getattr(self, 'current_theme', 'flatly')`로 조회해 일관되게 사용.

### 2.2 파일별 색상 교체 (우선 적용할 파일)

아래 순서로 `bg=`/`fg=`/`#hex` 리터럴을 `ThemeColors.get('...', is_dark)`로 교체.

| 순서 | 파일 | 비고 |
|------|------|------|
| 1 | `toolbar_mixin.py` | 버튼·배경 색상 다수. |
| 2 | `inventory_tab.py`, `tonbag_tab.py` | 탭·필터바·트리 주변. |
| 3 | `custom_menubar.py`, `statusbar_mixin.py` | 메뉴·상태바. |
| 4 | `onestop_inbound.py`, `settings_dialog.py`, `help_dialogs.py` | 다이얼로그. |
| 5 | `lot_detail_dialog.py`, `do_update_dialog.py`, `table_styler.py` | 상세/테이블. |
| 6 | `drag_drop_mixin.py`, `context_menu_mixin.py`, `backup_handlers.py`, `location_upload_preview.py` | 나머지. |

**매핑 예**: `bg='white'` → `ThemeColors.get('bg_primary', is_dark)` 또는 `bg_card`, `fg='#333'` → `ThemeColors.get('text_primary', is_dark)`.

**검증**: 라이트/다크 테마 전환 후 각 탭·다이얼로그에서 글씨·배경이 모두 보이는지 확인.

---

## Phase 3 — 간격 + 폰트 (우선순위 2 + 5)

**목표**: 8px 그리드와 폰트 3단계를 적용해 시각적 정돈과 위계를 맞춤. Phase 2에서 연 파일이 많으므로 같은 영역을 한 번 더 열 때 간격·폰트까지 정리.

### 3.1 8px 그리드 (Spacing)

- `gui_app_modular/utils/ui_constants.py`의 `Spacing` import 후 사용.
- `padx=`/`pady=`/`padding=` 리터럴을 `Spacing.XS(4)`/`SM(8)`/`MD(16)`/`LG(24)`/`XL(32)`로 치환. (예: 5→XS, 10→SM, 15→MD, 20→MD 또는 LG)
- **우선 적용**: `column_toggle.py`, `toolbar_mixin.py`, 각 다이얼로그, `inventory_tab.py`, `tonbag_tab.py`.

### 3.2 폰트 3단계 통일 (10/12/16pt 또는 FontScale)

- `font=('')` / `font=()` 34곳 검색 후 제거.
- 기본: `맑은 고딕`, 크기는 본문 10pt·소제목 12pt·제목 16pt 또는 `FontScale().body()/heading()/title()` 사용.
- `get_font_scale()` 초기화 여부 확인 후, 공통으로 쓰는 다이얼로그/탭에서 한 곳에서 참조하도록 연결.

**검증**: 전체 화면에서 패딩이 8의 배수로 통일되고, 폰트가 맑은 고딕·3단계로 보이는지 확인.

### Phase 3 적용 현황 (v5.8.7)

- **3.1 8px 그리드**: `column_toggle.py`, `toolbar_mixin.py`, `inventory_tab.py`, `tonbag_tab.py`, `help_dialogs.py`(팁 오버레이), `settings_dialog.py`(API 설정) — `padx`/`pady`/`padding` → `Spacing.XS`/`SM`/`MD`/`LG` 적용.
- **3.2 폰트 3단계**: `column_toggle.py`(FontScale.small + FontStyle), `toolbar_mixin.py`(메뉴/탭/검색 팝업/툴팁 — `get_font_scale()`·`FontScale.heading()`/`body()`/`subtitle()`/`small()` 적용).

---

## Phase 4 — 다이얼로그 크기 표준화 (우선순위 6)

**목표**: `geometry("WxH")` 하드코딩 제거, small/medium/large 3단계로 통일.

### 4.1 적용 방식

- 새로 여는 다이얼로그: `setup_dialog_defaults(dialog, parent, title, size_type)` 사용 (이미 크기·중앙·grab·ESC 처리).
- 기존에 `geometry("...")`만 쓰는 곳: `DialogSize.get_geometry(parent, 'small'|'medium'|'large')` + `dialog.geometry(...)` + `center_dialog(dialog, parent)`.

### 4.2 파일별 size_type 제안

| 크기 | 용도 예 | 적용 파일 예 |
|------|---------|--------------|
| small | 단순 확인/알림 | keybindings_mixin 팝업, statusbar_mixin 400x300, drag_drop 350x220 등 |
| medium | 설정·폼 | settings_dialog 520x420, do_update_dialog 750x520, column_mapper 750x550, backup 600x400 등 |
| large | 상세·미리보기 | onestop_inbound 1200x700, lot_detail 950x720, help_dialogs 750x700, allocation_preview 950x720 등 |

**검증**: 자주 쓰는 다이얼로그 5~10개 열어서 크기·비율이 비슷한지 확인.

### Phase 4 적용 현황 (v5.8.7)

- **DialogSize.get_geometry(parent, 'small'|'medium'|'large')** + **center_dialog(dialog, parent)** 적용.
- 적용 파일: `settings_dialog`, `do_update_dialog`, `lot_detail_dialog`, `onestop_inbound`(메인·날짜입력·파싱결과·액션팝업), `toolbar_mixin`(검색 팝업), `help_dialogs`(가이드·환영·피드백·팁), `inventory_tab`(톤백상세·LOT이력), `tonbag_tab`(일괄출고·수동출고), `backup_handlers`, `context_menu_mixin`, `drag_drop_mixin`, `statusbar_mixin`, `keybindings_mixin`, `location_upload_preview`, `allocation_preview`, `column_mapper_dialog`, `auto_backup`, `outbound_preview_dialog`, `theme_mixin`, `test_runner_dialog`, `diagnostics_mixin`.

---

## Phase 5 — 툴바 미니멀화 (우선순위 7)

**목표**: `toolbar_mixin.py` 하드코딩 색상 제거, 밑줄 기반 미니멀 스타일로 리팩터, 약 200줄 감소.

- 메가 버튼 46곳 색상 → ttk + `ThemeColors.get_palette(is_dark)` 또는 style.colors 기반으로 통일.
- 밑줄/아이콘만 강조하는 구조로 변경해 코드 단순화.
- **검증**: 라이트/다크 전환, 입고·출고·보고서 버튼 동작 및 툴팁 정상 여부 확인.

### Phase 5 적용 현황

- **메뉴 헬퍼**: `_add_menu_items(menu, items)` 추가 — `(label, command)` 또는 `None`(구분선) 리스트로 일괄 구성.
- **리팩터**: 입고/출고/재고/고객보고서/도움말 메뉴를 `_add_menu_items` 사용으로 통일, 불필요한 `f = self._toolbar_font` 제거.
- **색상**: 이미 ThemeColors 단일 소스(_load_toolbar_colors). 밑줄·아이콘 강조 구조 유지.

---

## 실행 순서 요약 (한 줄)

1. **Phase 1**: 컬럼 기본 7~8개 + 트리뷰 36px·제브라 → 퀵윈.
2. **Phase 2**: 색상 팔레트 통일 → 다크 테마 기반.
3. **Phase 3**: Spacing + 폰트 3단계 → 간격·위계 일관.
4. **Phase 4**: 다이얼로그 크기 표준화 → 창 경험 통일.
5. **Phase 5**: 툴바 미니멀화 → 코드 정리 + UI 통일.

원하시면 **Phase 1만** 먼저 적용할 수 있도록, 수정할 위치(라인 근처·함수명)까지 구체적으로 짚어 드리겠습니다.

---

*문서 버전: 1.0 | 2026-02-17*
