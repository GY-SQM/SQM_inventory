# SQM UI 디자인 마스터 플랜

> **세계 최고 수준 데스크탑 UI 전문가 관점** 정리  
> 기존 인프라(ThemeColors, Spacing, FontScale, UICalculator)를 실제로 연결하는 것이 핵심.  
> 새 설계가 아니라 **32개 파일의 하드코딩을 인프라 참조로 단계적 교체**.

---

## 1. 가장 큰 문제 3가지

### 1.1 색상 하드코딩 → 다크 테마 시 UI 붕괴

| 항목 | 현황 |
|------|------|
| 색상 하드코딩 | **169곳** (32개 파일) |
| 비-ttk 위젯 | **485곳** |
| 대표 패턴 | `bg='white'`, `fg='#333'`, `#000`, `#fff` 등 |
| 결과 | 다크 테마 전환 시 글씨가 안 보이는 구간 다수 |

**해결 방향**  
- **단일 색상 팔레트**에서 전체 제어.  
- 이미 **ThemeColors**, **ui_constants.py**에 LIGHT/DARK 팔레트가 정의되어 있으나 **실제 사용률 약 2.7%**.

**조치**  
- 32개 파일 내 `bg=`/`fg=`/배경·전경 리터럴을 `ThemeColors.get(key, is_dark)` 참조로 교체.  
- 비-ttk 위젯은 가능한 범위에서 ttk 전환, 불가 시 최소한 색상만 팔레트 참조로 통일.

---

### 1.2 간격·정렬 규칙 부재 → 시각적 혼란

| 항목 | 현황 |
|------|------|
| 패딩 | 5, 10, 15, 20px 등 **제각각** |
| 버튼 width | 8, 10, 12 등 **혼용** |
| 폰트 크기 | 8pt ~ 20pt **12가지 이상** 혼재 |

**해결 방향**  
- **8px 그리드**: 모든 간격을 8의 배수(8, 16, 24, 32)로 통일.  
- **Spacing** 클래스가 이미 정의돼 있으나 **거의 미적용**.

**조치**  
- `padx`/`pady`/`padding` 리터럴을 `Spacing.XS`/`Spacing.SM`/`Spacing.MD`/`Spacing.LG` 등으로 교체.  
- 버튼·라벨 등 폰트는 **FontScale** 3단계(10/12/16pt 또는 BODY/HEADING/TITLE)로 통일.

---

### 1.3 정보 밀도 과다 → 첫인상 과부하

| 항목 | 현황 |
|------|------|
| 재고 리스트 | **19컬럼** 전부 기본 표시 |
| 톤백 리스트 | **20컬럼** 전부 기본 표시 |
| 컬럼 토글 | 있으나 **기본값 = 전부 표시** |

**해결 방향**  
- 기본 표시 **7~8개**, 나머지는 **숨김(토글로 표시 가능**.  
- 전문 디자이너는 “처음 열면 핵심만 보이고, 필요 시 펼쳐보기”를 선호.

**조치**  
- **재고**: `INVENTORY_COLUMNS` 5번째 값 `default_visible`을 핵심 7~8개만 `True`, 나머지 `False`로 변경.  
- **톤백**: 컬럼 정의에 `default_visible` 추가 후 동일하게 7~8개만 기본 표시, 초기 `displaycolumns` 적용.

---

## 2. 그다음 문제들

### 2.1 다이얼로그 크기 불일치

- **현황**: 750×550, 400×500, 600×400, 950×720 등 **창마다 상이**.  
- **해결**: **small / medium / large** 3단계 표준화.  
- **인프라**: **UICalculator**, **DialogSize**, **setup_dialog_defaults()**가 이미 **ui_constants.py**에 있으나 **미적용**.  
- **조치**: 각 다이얼로그에서 `geometry("WxH")` 호출을 `setup_dialog_defaults(dialog, parent, title, size_type)` 또는 `DialogSize.get_geometry(parent, 'medium')` 등으로 교체.

### 2.2 툴바 과다

- **현황**: `toolbar_mixin.py` **1,034줄**, 메가 버튼에 **하드코딩 색상 46곳**.  
- **해결**: 밑줄 기반 **미니멀 디자인**으로 전환 → 약 **200줄 삭제** + 시각적 통일.  
- **조치**: 버튼 스타일을 ttk + ThemeColors로 통일, 불필요한 커스텀 그리드/색상 제거.

### 2.3 트리뷰 행간·가독성

- **현황**: 기본 행 높이 30px + 10pt 폰트, 숫자 밀집으로 **눈 피로**.  
- **해결**: 행 높이 **36px** + **짝수/홀수 행 배경 교대(zebra striping)**.  
- **인프라**: **ReadableStyle.ROW_HEIGHT**, **ThemeColors** `tree_stripe` 등 이미 존재. **table_styler**, **tree_enhancements**에서 stripe 적용 가능.  
- **조치**: Treeview 스타일에서 `rowheight=36`, zebra 태그 일괄 적용 확인·보강.

### 2.4 폰트 불일치

- **현황**: 빈 폰트 `''` **34곳** → OS마다 다른 시스템 폰트로 표시.  
- **해결**: **맑은 고딕** 통일 + **10/12/16pt** 3단계(또는 FontScale BODY/HEADING/TITLE).  
- **인프라**: **FontScale**, **ReadableStyle.FONT_FAMILY** 존재하나 활용률 낮음.  
- **조치**: `font=('')` 또는 `font=()` 제거 후 `FontScale().body()/heading()/title()` 또는 상수 튜플로 통일.

---

## 3. 전문 디자이너 우선순위

| 순위 | 항목 | 효과 | 난이도 |
|------|------|------|--------|
| 1 | 색상 팔레트 통일 (하드코딩 제거) | 다크/라이트 완전 대응 | 중 (2~3시간) |
| 2 | 8px 그리드 간격 통일 (Spacing) | 시각적 정돈감 | 중 |
| 3 | 기본 표시 컬럼 축소 (19→8, 20→8) | 첫인상 개선 | 쉬움 |
| 4 | 트리뷰 행간 36px + 제브라 스트라이핑 | 데이터 가독성 | 쉬움 |
| 5 | 폰트 3단계 통일 (10/12/16pt) | 시각 위계 명확 | 쉬움 |
| 6 | 다이얼로그 크기 표준화 (DialogSize) | 일관된 경험 | 쉬움 |
| 7 | 툴바 미니멀화 (밑줄 기반) | 코드 200줄 삭제 + 깔끔 | 중 |

---

## 4. 인프라 요약 (이미 있음 → 연결만 하면 됨)

| 인프라 | 파일 | 용도 |
|--------|------|------|
| **ThemeColors** | gui_app_modular/utils/ui_constants.py | LIGHT/DARK 팔레트, `get(key, is_dark)` |
| **Spacing** | 동일 | XS=4, SM=8, MD=16, LG=24, XL=32, XXL=48 (8px 그리드) |
| **FontScale** | 동일 | DPI 기반, FontStyle.TITLE/BODY/SMALL 등 |
| **UICalculator** | 동일 | DPI·해상도 스케일, get_main_window_size() |
| **DialogSize** | 동일 | small/medium/large/full, get_geometry(parent, size_type) |
| **setup_dialog_defaults()** | 동일 | 제목·크기·중앙·grab·ESC 닫기 일괄 적용 |
| **ReadableStyle** | 동일 | Treeview rowheight, 폰트, Notebook, LabelFrame 등 |
| **ColumnWidth** | 동일 | 필드별 너비·앵커, configure_column() |

---

## 5. 마이그레이션 체크리스트

### 5.1 색상 (우선순위 1)

- [ ] `gui_app_modular` 하위에서 `bg=['"]white|fg=['"]#|bg=['"]#|fg=['"]black` 검색 후 파일별 교체.
- [ ] 아래 **색상 하드코딩 파일 목록**부터 `ThemeColors.get(..., is_dark)` 적용.

**색상 하드코딩이 발견된 파일 (bg=/fg= 리터럴)**  
onestop_inbound, inventory_tab, toolbar_mixin, tonbag_tab, custom_menubar, settings_dialog, lot_detail_dialog, do_update_dialog, help_dialogs, table_styler, ui_constants (내부 참조용 제외), drag_drop_mixin, context_menu_mixin, backup_handlers, location_upload_preview.
- [ ] theme_mixin에서 `is_dark` 소스 일원화 후, 모든 다크 의존 위젯이 해당 값 참조하도록 정리.

### 5.2 간격 (우선순위 2)

- [ ] `padx=`/`pady=`/`padding=` 리터럴을 Spacing 상수로 교체 (예: 5→Spacing.XS, 10→Spacing.SM, 15→Spacing.MD, 20→Spacing.MD 또는 LG).
- [ ] column_toggle, toolbar_mixin, dialogs, tabs 등 **padx/pady 다수 사용 파일**부터 적용.

### 5.3 기본 표시 컬럼 (우선순위 3)

- [ ] **inventory_tab.py**: `INVENTORY_COLUMNS`에서 기본 표시할 7~8개만 `True`, 나머지 `False`. (예: row_num, lot_no, sap_no, bl_no, product, status, current_weight, net_weight 등)
- [ ] **tonbag_tab.py**: `_tonbag_columns`에 `default_visible` 추가 후 동일 정책, 초기 `displaycolumns` 설정.

### 5.4 트리뷰 (우선순위 4)

- [ ] **ReadableStyle.ROW_HEIGHT** 36으로 설정 확인 (현 38이면 36으로 조정 검토).
- [ ] **table_styler** / **tree_enhancements**에서 zebra(stripe) 태그가 모든 리스트에 적용되는지 확인.

### 5.5 폰트 (우선순위 5)

- [ ] `font=('')` 또는 `font=()` 34곳 검색 후 맑은 고딕 + 10/12/16pt 또는 FontScale BODY/HEADING/TITLE로 통일.
- [ ] **get_font_scale()** 초기화 여부 확인 후, 다이얼로그·탭에서 공통 사용하도록 연결.

### 5.6 다이얼로그 크기 (우선순위 6)

- [ ] 아래 목록의 `geometry("...")` 호출을 `setup_dialog_defaults(dialog, parent, title, 'small'|'medium'|'large')` 또는 `DialogSize.get_geometry(parent, size_type)` + `center_dialog()`로 교체.

**geometry 하드코딩 사용 파일 (일부)**  
- onestop_inbound.py (1200x700, 520x460, 900x520, 420x80)  
- inventory_tab.py (700x400, 600x350)  
- toolbar_mixin.py (520x420)  
- tonbag_tab.py (400x300 등)  
- settings_dialog.py (520x420)  
- lot_detail_dialog.py (950x720)  
- do_update_dialog.py (750x520)  
- help_dialogs.py (750x700, 550x400, 500x400)  
- pdf_handlers.py, validation_mixin.py, context_menu_mixin.py, backup_handlers.py, advanced_dialogs_mixin.py, product_handlers.py, column_mapper_dialog.py, upload_error_dialog.py, auto_backup.py, drag_drop_mixin.py, statusbar_mixin.py, diagnostics_mixin.py, test_runner_dialog.py, custom_menubar.py, outbound_handlers.py, ui_ops_helper.py, features_v2_mixin.py, allocation_preview.py, location_upload_preview.py, simple_excel_outbound.py 등

### 5.7 툴바 (우선순위 7)

- [ ] toolbar_mixin.py에서 메가 버튼용 하드코딩 색상 46곳 제거.
- [ ] ttk + ThemeColors(style.colors 또는 get_palette) 기반 밑줄 미니멀 스타일로 리팩터.
- [ ] 목표: 약 200줄 삭제 + 시각적 통일.

---

## 6. 요약 (Ruby 의견 반영)

- **새로 만드는 것이 아님.**  
- **ThemeColors, FontScale, Spacing, UICalculator, DialogSize, ReadableStyle** 등 **이미 설계된 인프라를 실제로 쓰면 됨.**  
- **32개 파일의 하드코딩을 하나씩 인프라 참조로 바꾸는 작업**이 전부.  
- 순서: **색상 → 간격 → 컬럼 기본값 → 트리뷰·폰트 → 다이얼로그 크기 → 툴바** 로 진행하면 리스크 적고 효과 즉시 나타남.

---

*문서 버전: 1.0 | SQM v587 | 2026-02-17*
