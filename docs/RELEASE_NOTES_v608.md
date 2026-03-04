# SQM v6.0.8 Release Notes

**Release Date:** 2026-02-21  
**Phase:** 4단계 탭 구조 · LOT 리스트 명칭 통일

---

## 변경 요약

### 1. 4단계 메인 탭 구조

- **탭 순서:** 📦 AVAILABLE → 📋 ALLOCATION → 🚛 PICKED → ✅ SOLD → 📊 대시보드 → 📝 로그
- **main_app.py:** 노트북 탭 추가 순서 변경, `idx_to_key` 매핑 갱신(0=inventory, 1=cargo_overview, 2=outbound_scheduled, 3=tonbag, 4=dashboard, 5=log), 시작 탭 0번(AVAILABLE)
- **toolbar_mixin.py:** `_tab_index_map` 및 탭 버튼 라벨을 AVAILABLE/ALLOCATION/PICKED/SOLD/대시보드/로그로 변경, 툴팁 보강

### 2. 명칭 변경: 재고 리스트 → LOT 리스트

- **inventory_tab.py:** 라디오 "📦 재고 보기" → "📦 LOT 리스트", "🎒 톤백 보기" → "🎒 톤백 리스트", Excel 내보내기 툴팁 "LOT 리스트를 Excel..."
- **outbound_handlers.py:** Add Selected 툴팁 "LOT 리스트에서 선택한 LOT를..."
- **toolbar_mixin.py:** 메뉴 "재고리스트 Excel" → "LOT 리스트 Excel", 검색/필터 관련 주석·문자열 "LOT 리스트"
- **help_dialogs.py:** 단축키 안내 "📦 AVAILABLE (LOT 리스트)", "📋 ALLOCATION", "🚛 PICKED", "✅ SOLD (톤백 리스트)", "📊 대시보드", "📝 로그"(Ctrl+6 추가)

### 3. 탭 전환·새로고침 연동

- 탭 인덱스와 `inventory`/`cargo_overview`/`outbound_scheduled`/`tonbag`/`dashboard`/`log` 키 매핑 유지, 각 탭 `_refresh_*` 동작 기존대로 유지

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.8, VERSION_HISTORY 추가 |
| `gui_app_modular/main_app.py` | 탭 4+2 구성·순서·idx_to_key·시작 탭 0 |
| `gui_app_modular/mixins/toolbar_mixin.py` | 탭 버튼 4개 메인+대시보드/로그, _tab_index_map, LOT 리스트 문구 |
| `gui_app_modular/tabs/inventory_tab.py` | LOT 리스트·톤백 리스트 라벨·툴팁 |
| `gui_app_modular/handlers/outbound_handlers.py` | LOT 리스트 툴팁 |
| `gui_app_modular/dialogs/help_dialogs.py` | 단축키 탭 이동 문구(AVAILABLE/ALLOCATION/PICKED/SOLD, Ctrl+6) |
| `docs/RELEASE_NOTES_v608.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 21일**
