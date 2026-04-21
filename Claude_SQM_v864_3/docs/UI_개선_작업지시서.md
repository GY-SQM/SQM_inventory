# SQM Inventory — UI 개선 작업 지시서

> 작성일: 2026-04-20  
> 기준 버전: v8.6.4  
> 목표: 전체 메뉴·탭·다이얼로그 시각적 완성도 향상 (폰트·정렬·여백·컬럼 폭 전수 정비)

---

## ⚠️ 절대 불변 원칙

- **기존 메뉴·탭·버튼·다이얼로그는 단 하나도 삭제하거나 숨기지 않는다**
- 메뉴바 항목 수·순서 변경 금지
- 버튼 기능 변경 금지 — 위치·크기·색상만 수정 가능
- `grid_remove`, `pack_forget` 추가 금지

---

## 컬럼 정렬 표준 (전체 공통 적용)

| 컬럼 유형 | anchor | 예시 |
|-----------|--------|------|
| 숫자·수량·금액·중량 | `'e'` (우측) | 중량, 수량, 금액 |
| 텍스트·고객사·품명 | `'w'` (좌측) | 고객사명, 품명 |
| ID·코드·상태·날짜 | `'center'` (중앙) | LOT번호, 상태 |
| 헤더(heading) | `'center'` | 항상 center |

---

## 1단계 — 글로벌 스타일 (전체에 즉시 반영)

### `fixes/global_tree_style.py`
- rowheight: **26 → 32**
- Heading font: `('맑은 고딕', 10, 'bold')` 명시 추가
- 색상 하드코딩 30개 → `tc()` 전환

### `fixes/theme_colorful_override.py`
- TNotebook.Tab padding: `(10,4)` → `(14, 6)` — 탭 글씨 잘림 방지
- TButton padding: `(8,4)` → `(10, 6)`
- Heading font 명시

### `gui_app_modular/utils/ui_constants.py`
추가 상수:
```python
FONT_FAMILY = '맑은 고딕'
FONT_BODY   = (FONT_FAMILY, 10)
FONT_SMALL  = (FONT_FAMILY, 9)
FONT_HEADER = (FONT_FAMILY, 11, 'bold')
FONT_TITLE  = (FONT_FAMILY, 13, 'bold')
FONT_MONO   = ('Consolas', 10)
TREE_ROW_HEIGHT = 32
PAD_XS=4; PAD_SM=8; PAD_MD=12; PAD_LG=16; PAD_XL=24
BTN_PAD_X=12; BTN_PAD_Y=6
```

---

## 2단계 — 탭 전수 정비

### `tabs/dashboard_tab.py`
- 색상 `ACCENT='#2563eb'` 등 4개 → `tc()` 전환
- 폰트 13/11/10 혼재 → FONT_TITLE/FONT_HEADER/FONT_BODY
- rowheight=34 → 32
- 컬럼 width=175/72/68/52: Product→220, 숫자컬럼→80 이상
- 숫자 컬럼 anchor → `'e'`

### `tabs/inventory_tab.py`
- 24개 컬럼 전수 anchor 재설정 (숫자→`'e'`, 텍스트→`'w'`)
- 컬럼 width stretch=YES 미설정 컬럼 보완
- rowheight 통일 32

### `tabs/allocation_tab.py`
- 폰트 9/10 → FONT_BODY(10)
- rowheight=36 → 32
- 수치 컬럼 anchor → `'e'`
- 버튼 레이블 font 9pt → 10pt

### `tabs/cargo_overview_tab.py`
- 20개 컬럼 anchor 전수 재설정
- 고객사·품명→`'w'`, 수량·중량→`'e'`, 상태·코드→`'center'`
- rowheight 통일 32

### `tabs/scan_tab.py`
- 폰트 13/11 → FONT_HEADER/FONT_BODY
- 버튼 색상 5개 하드코딩(`#3b82f6` 등) → `tc()` 전환
- Entry width=32 → 35 (스캔 바코드 길이 감안)
- 컬럼 width(120,160,140,90,260) anchor 재설정

### `tabs/move_tab.py`
- 폰트 `('Consolas', 11)` → FONT_BODY
- 버튼 `bg='#22c55e'` → `tc('success')`
- Entry width=28 → 32
- 컬럼 7개 anchor 재설정

### `tabs/outbound_scheduled_tab.py`
- 15개 컬럼 anchor 전수 재설정
- 날짜·코드→`'center'`, 수량·중량→`'e'`, 고객사→`'w'`
- rowheight 32 통일

### `tabs/picked_tab.py`
- PICKED_LOT_COLUMNS, PICKED_DETAIL_COLUMNS anchor 재설정
- 수량·중량 컬럼 → `'e'`
- rowheight 32 통일

### `tabs/sold_tab.py`
- SOLD_LOT_COLUMNS, SOLD_DETAIL_COLUMNS anchor 재설정
- rowheight 32 통일

### `tabs/log_tab.py`
- 모노폰트 → FONT_MONO = ('Consolas', 10)
- tag_configure 색상 하드코딩 → tc() 전환
- wrap='word' 확인

### `tabs/tonbag_tab.py`
- 폰트 `('맑은 고딕', 11)` → FONT_BODY
- 21개 컬럼 anchor 전수 재설정
  - 텍스트(고객사·품명·위치)→`'w'`
  - 수량·중량·금액→`'e'`
  - 코드·상태·날짜→`'center'`
- rowheight 계산식 → 고정 32

### `tabs/summary_tab.py`
- 폰트 표준화 FONT_BODY/FONT_HEADER
- 행 색상 태그('odd','even') → tc() 기반

---

## 3단계 — 다이얼로그 전수 정비

### `dialogs/allocation_template_dialog.py` ★최우선
- 색상 C_BG·C_BG2 등 18개 하드코딩 → `tc()` 전환
- `C_BG2='#283593'` (다크 전용) → 라이트 모드 깨짐 수정
- 폰트 `'Malgun Gothic', 9/11` → FONT_BODY/FONT_HEADER
- rowheight=24 → 32
- padx 0/10/12/18 난립 → PAD_SM/PAD_MD
- geometry 없음 → DIALOG_LG + center_dialog()

### `dialogs/allocation_dialog.py` ★최우선
- 폰트 9/10 → FONT_BODY
- padx=1, pady=1 → PAD_SM
- 필터 Entry width=22/16 → 25/18
- 날짜 Entry width=12 → 16 (YYYY-MM-DD)
- height=18 Treeview → expand=YES 동적
- 색상 `_bg,_fg` 폴백 → tc() 전환

### `dialogs/allocation_approval_dialog.py`
- geometry 없음 → DIALOG_LG + center_dialog()
- Treeview height=18 → expand=YES
- 컬럼 width=120/280/180 → stretch=YES + 비율 기반
- anchor 미설정 → 숫자`'e'`, 텍스트`'w'`

### `dialogs/dn_cross_check_dialog.py`
- **Listbox 스크롤바 없음 → Scrollbar 추가** (높음)
- padx 16/20 → PAD_MD=12 통일
- geometry 없음 → DIALOG_MD + center_dialog()
- Excel 경로 Entry width=55 → width=60 + expand

### `dialogs/auto_backup.py`
- font `'Consolas',9` → FONT_MONO
- Text 위젯 스크롤바 연결 확인
- width=12/20/25/50 혼재 → 역할별 표준화
- resizable 미설정 → resizable(True,True)

### `dialogs/integrity_v760_dialog.py`
- 색상 `'#E74C3C','#F39C12','#27AE60'` → tc('danger'), tc('warning'), tc('success')
- rowheight=24 → 32
- font `('Consolas',9)` → FONT_MONO

### `dialogs/email_config_dialog.py`
- 폰트 `('맑은 고딕',9)` → FONT_BODY
- geometry="480x480" → center_dialog() 추가
- Entry/Label sticky 확인

### `dialogs/help_dialogs.py`
- 폰트 `('맑은 고딕',16,'bold')` → FONT_TITLE
- 색상 `'white'` 등 하드코딩 → tc() 전환

### `dialogs/inbound_history_dialog.py`
- rowheight=16 → **32** (가장 작음, 심각)
- 컬럼 width(45,115,115,120,135,95,95,120,90,105,85) anchor 재설정
  - 날짜·코드→`'center'`, 수량·중량→`'e'`, 텍스트→`'w'`

### `dialogs/inbound_preview_dialog.py`
- 폰트 `('맑은 고딕',10)` → FONT_BODY
- Treeview height=18 → expand=YES
- padx=10 → PAD_MD

### `dialogs/inbound_template_dialog.py`
- Listbox font `('맑은 고딕',10)` → FONT_BODY
- Notebook 탭 레이블 잘림 확인 → 패딩 (14,6)
- Entry width 고정값 → 적정값 조정

### `dialogs/lot_detail_dialog.py`
- FONT_TITLE/FONT_SUBTITLE 내부 정의 → 전역 FONT_* 사용
- Button padding 하드코딩 → BTN_PAD_X/Y
- geometry constraint 없음 → minsize + center_dialog()

### `dialogs/lot_status_dialog.py`
- Notebook 4개 탭 레이블 잘림 확인
- 컬럼 minwidth=40 → 적정값
- 폰트 표준화

### `dialogs/onestop_inbound.py`
- 색상 `'#6366f1','#d97706'` 등 → tc() 전환
- PREVIEW_COLUMNS 18개 컬럼 anchor 재설정
- Button padding 하드코딩 → BTN_PAD_X/Y

### `dialogs/onestop_outbound.py`
- Custom notebook style 색상 `'#6366f1','#d97706'` → tc()
- Button padding padx=18, pady=10 → BTN_PAD_X/Y
- geometry constraint → center_dialog()

### `dialogs/parse_error_recovery_dialog.py`
- 색상 `'#0f172a','#e2e8f0','#22d3ee'` → tc() 전환
- 폰트 `'Segoe UI', 9/10/14` → FONT_BODY/FONT_TITLE
- Entry width=30 → 35

### `dialogs/parse_preview_confirm_dialog.py`
- rowheight=28 → 32
- anchor='center' 전체 → 컬럼 유형별 재설정
- 컬럼 width 표준화

### `dialogs/picking_template_dialog.py`
- 폰트 `('맑은 고딕',10)` → FONT_BODY
- Listbox width 표준화
- Notebook 탭 패딩 (14,6)

### `dialogs/preparse_select_dialog.py`
- Canvas 기반 스크롤 다이얼로그 → minsize(480,520) 유지
- 폰트 표준화
- Canvas window 계산 정확성 확인

### `dialogs/product_inventory_report.py`
- 컬럼 width(60,220,120,60,60,110,100,100,100) anchor 재설정
  - 품명→`'w'`, 수량·중량→`'e'`, 코드→`'center'`

### `dialogs/product_master_dialog.py`
- 컬럼 width(60,280,160,70,70) anchor 재설정
- 품명→`'w'`, 코드·유형→`'center'`
- Scrollbar 연결 확인

### `dialogs/return_dialog.py`
- 폰트 `('맑은 고딕',10)` → FONT_BODY
- DISPLAY_COLS 7개 컬럼 anchor 재설정
- geometry → center_dialog()

### `dialogs/return_statistics_dialog.py`
- geometry="900x600" → center_dialog() + 유지
- 탭 4개 컬럼 anchor 재설정

### `dialogs/review_center.py`
- geometry="1200x760" → center_dialog() + 유지
- minsize(900,600) 유지

### `dialogs/settings_dialog.py`
- 폰트 혼재 → FONT_BODY/FONT_HEADER
- Entry width=55 → expand 처리
- LabelFrame padding → PAD_MD

### `dialogs/test_runner_dialog.py`
- 폰트 `('Consolas',9)` → FONT_MONO
- Text height=20 → expand=YES
- Scrollbar 확인

### `dialogs/picking_list_preview_dialog.py`
- anchor='center' 전체 → 숫자`'e'`, 텍스트`'w'`

### `dialogs/location_upload_preview.py`
- 컬럼 width(60,150,120,180,120,110,110,110,95) anchor 재설정
- Scrollbar 확인

### `dialogs/outbound_preview_dialog.py`
- Button padding 표준화 BTN_PAD_X/Y
- Scrollbar 구성 확인

### `dialogs/column_mapper_dialog.py`
- width=25/30 고정 → expand=YES
- 폰트 → FONT_BODY

### `dialogs/do_update_dialog.py`
- 컬럼 width(130,120,120,90,80,100) anchor 재설정
- 날짜→`'center'`, 수량→`'e'`, 텍스트→`'w'`

### `dialogs/allocation_preview.py`
- 폰트 `('맑은 고딕',9)` → FONT_BODY
- 컬럼 width(35,55,110,130,200) anchor 재설정
- height=20 Treeview → expand=YES

---

## 4단계 (선택) — 고급화

### 옵션 C: ttkbootstrap vapor/cyborg 테마 (권장)
- 현재 코드 유지, 테마 이름만 변경
- vapor: 다크 네온 고급감
- cyborg: 다크 블루 비즈니스

---

## 전체 체크리스트

**글로벌**
- [ ] 모든 Treeview rowheight = 32px
- [ ] TNotebook.Tab padding = (14, 6) — 탭 글씨 잘림 없음
- [ ] TButton padding = (10, 6)
- [ ] Treeview Heading font = ('맑은 고딕', 10, 'bold')

**컬럼 정렬**
- [ ] 숫자·수량·중량 컬럼 anchor = 'e'
- [ ] 텍스트·고객사·품명 컬럼 anchor = 'w'
- [ ] 코드·상태·날짜 컬럼 anchor = 'center'

**폰트**
- [ ] 9pt 사용 없음 (최소 10pt)
- [ ] '맑은 고딕'/'Malgun Gothic' 혼재 없음
- [ ] Consolas 9pt → 10pt

**색상**
- [ ] 하드코딩 #XXXXXX → tc() 전환
- [ ] 라이트/다크 모드 전환 시 깨짐 없음

**다이얼로그**
- [ ] 모든 다이얼로그 center_dialog() 적용
- [ ] minsize(400, 300) 설정
- [ ] 스크롤바 누락 없음
- [ ] Listbox 스크롤바 (dn_cross_check)

**기능 보존**
- [ ] 모든 메뉴 항목 존재 확인
- [ ] 모든 탭 존재 확인
- [ ] 모든 버튼 기능 정상
