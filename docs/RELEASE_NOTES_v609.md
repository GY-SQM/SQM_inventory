# SQM v6.0.9 Release Notes

**Release Date:** 2026-02-21  
**Phase:** 4단계 탭 한글 라벨 · 총괄 재고 리스트 복원

---

## 변경 요약

### 1. 4단계 탭·툴바 한글 라벨 (로직·흐름 동일)

- **탭/툴바 표시:** AVAILABLE → **판매가능**, RESERVED → **판매배정**, PICKED → **판매화물 결정**, SOLD → **출고**
- **main_app.py:** 노트북 탭 텍스트 한글 적용
- **toolbar_mixin.py:** 탭 버튼 라벨 한글 적용
- **inventory_tab.py / allocation_tab.py / picked_tab.py / sold_tab.py:** 각 탭 제목 한글 (판매가능 LOT 리스트 등)
- **help_dialogs.py:** 단축키 탭 이동 안내 한글
- DB 값(AVAILABLE, RESERVED, PICKED, SOLD) 및 업무 흐름·로직은 변경 없음

### 2. 총괄 재고 리스트 탭·메뉴 복원

- **노트북:** 7탭 구성 — 판매가능 / 판매배정 / 판매화물 결정 / 출고 / **총괄 재고 리스트** / 통계 / 로그
- **main_app.py:** `tab_cargo_overview` 노트북 재추가, `_setup_cargo_overview_tab` 호출, `idx_to_key`에 cargo_overview(4) 반영, 탭 전환 시 `_refresh_cargo_overview` 연동
- **toolbar_mixin.py:** 탭 버튼 "📋 총괄 재고 리스트" 추가, `_tab_index_map` 7탭 기준 갱신, 전체 새로고침에 `_refresh_cargo_overview` 포함
- **custom_menubar.py:** 보기 메뉴에 "📋 총괄 재고 리스트" 복원, 7탭 순서에 맞게 항목 정리
- **keybindings_mixin.py:** Ctrl+7 → 로그 탭
- **help_dialogs.py:** 탭 이동 단축키에 총괄 재고 리스트(Ctrl+5), Ctrl+6 대시보드, Ctrl+7 로그 반영

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.9, VERSION_HISTORY 추가 |
| `gui_app_modular/main_app.py` | 7탭(총괄 재고 리스트 포함), 한글 탭 라벨, idx_to_key·refresh 연동 |
| `gui_app_modular/mixins/toolbar_mixin.py` | 한글 탭 라벨, 총괄 재고 리스트 버튼, _tab_index_map 7탭 |
| `gui_app_modular/mixins/custom_menubar.py` | 보기 메뉴 7탭·총괄 재고 리스트 복원 |
| `gui_app_modular/mixins/keybindings_mixin.py` | Ctrl+7 로그 탭 |
| `gui_app_modular/tabs/inventory_tab.py` | 판매가능 제목·하단 통계 문구 |
| `gui_app_modular/tabs/allocation_tab.py` | 판매배정 제목 |
| `gui_app_modular/tabs/picked_tab.py` | 판매화물 결정 제목 |
| `gui_app_modular/tabs/sold_tab.py` | 출고 제목 |
| `gui_app_modular/dialogs/help_dialogs.py` | 단축키 탭 이동 한글·총괄·Ctrl+5~7 |
| `docs/RELEASE_NOTES_v609.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 21일**
