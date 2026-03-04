# SQM v3.6.3 변경 리포트 — 1단계: 테마 색상 팔레트 통합

**작성일:** 2026-02-04  
**버전:** v3.6.2 → v3.6.3  
**목표:** 하드코딩 색상 169건 → ThemeColors 팔레트 참조 전환

---

## 📊 변경 전/후 비교

| 측정 항목 | v3.6.2 | v3.6.3 | 변화 |
|----------|--------|--------|------|
| 하드코딩 색상 (bg='#xxx') | 169건 | **12건** | ▼ 93% 감소 |
| ThemeColors 팔레트 키 | 35+35개 | **50+50개** | ▲ 30키 확장 |
| 다크모드 호환성 | 부분적 | **~90%** | ★ 대폭 개선 |
| 잔여 12건 구성 | — | fallback 2 + 의도적 분기 10 | 안전 |
| 문법 오류 | 0건 | 0건 | 유지 |

---

## 🔧 수정 파일 (8개)

### 1. `ui_constants.py` — ThemeColors 팔레트 확장
- LIGHT/DARK 각각 15키 추가 (총 30키)
- 신규: `search_bg/fg/border/placeholder/cursor`
- 신규: `statusbar_bg/fg/icon_ok/warn/err/progress/track`
- 신규: `badge_db/version/text`
- 신규: `arrow_separator`, `shortcut_text/dim`, `canvas_highlight`

### 2. `toolbar_mixin.py` — 검색바 + 상태바 팔레트화
- `_setup_toolbar()`: 검색 프레임 6색 → `_p['search_*']`
- 화살표 구분자 `fg='#bdc3c7'` → `_p['arrow_separator']`
- 단축키 텍스트 `fg='#cccccc'` → `_p['shortcut_text']`
- `_setup_statusbar()`: 전체 13색 → 팔레트 참조
- `_update_status()`: 아이콘 색상 → `_sb_colors` 딕셔너리
- `_update_progress()`: 프로그레스 색상 → 팔레트 참조
- 배지 (DB/버전) 색상 → `badge_*` 팔레트

### 3. `dashboard_tab.py` — 차트/카드 팔레트화
- Listbox `selectbackground` → `_p['tree_select_bg']`
- Canvas 배경 → `_p['chart_bg']`
- 범례 색상 → `_p['success']`, `_p['warning']`
- 카드 배경 → `_p['bg_card']`
- 카드 제목 → `_p['text_secondary']`
- 알림 색상 → `_p['danger']`, `_p['warning']`

### 4. `pivot_tab.py` — 제어판/필터/버튼 팔레트화
- 제어 패널 `bg='#ecf0f1'` 12건 → `_ctrl_bg` (팔레트)
- 필터 프레임 `bg='#d5dbdb'` → `_pp['bg_hover']`
- 상태바 영역 `bg='#2c3e50'` → `_pp['statusbar_bg']`
- 버튼 색상 6건 → `_pp['success/warning/info']`
- 텍스트 색상 → `_pp['text_primary/secondary']`
- 전체화면 바 → `_pp['statusbar_bg/fg']`
- **하드코딩 0건 달성**

### 5. `inventory_tab.py` — 액션바 팔레트화
- `bg='#ecf0f1'` 4건 → `ThemeColors.get('bg_secondary')`

### 6. `features_v2_mixin.py` — Treeview tag 팔레트화
- `background='#FFC7CE'` → `ThemeColors.get('picked')`
- `background='#FFEB9C'` → `ThemeColors.get('reserved')`

### 7. `refresh_mixin.py` — Treeview tag 팔레트화
- `ThemeColors.configure_tags()` 호출 + except fallback 유지

### 8. 버전 통일
- `version.py`, `constants.py`, `main_app.py` → v3.6.3

---

## 🔮 다음 단계 (v3.6.4 예정)

**2단계: tk 위젯 → ttk 위젯 마이그레이션**
- `tk.Label/Button/Frame` 485건 → `ttk.Label/Button/Frame` + bootstyle
- ttkbootstrap 테마가 모든 위젯에 자동 적용
- bootstyle 매핑: 녹색→success, 주황→warning, 파랑→info
