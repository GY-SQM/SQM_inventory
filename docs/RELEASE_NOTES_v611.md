# SQM v6.1.1 — 테마 가시성 개선

**릴리즈 일자:** 2026-02-23  
**기준 버전:** v6.1.0  
**참고:** SQM_v701_patch_only 검토 반영 (테마 전환 시 글자 안 보이는 문제 완화)

---

## 1. 요약

- **테마 전환 시 글자 가시성** 개선: 라이트↔다크 전환 후 Treeview·네이티브 위젯에서 글자가 배경과 구분되도록 수정
- **ReadableStyle**: Treeview/Heading에 `foreground`·`background`·`fieldbackground` 명시, `style.map`에 `!selected` 추가
- **탭별 style.map**: Inv/Tb/Cargo Treeview에 `tree_select_bg`/`tree_select_fg` 정확 적용 + `!selected` foreground
- **전체 위젯 스캔**: `theme_refresh.py` 신규 — 테마 변경 시 루트 기준 모든 Treeview·tk.Text·tk.Label·tk.Listbox 일괄 갱신
- **2차 적용**: 테마 변경 후 50ms 뒤 `_update_theme_colors()` 재호출로 간헐적 타이밍 이슈 완화
- **Fallback**: `theme_refresh` import 실패 시 기존 방식(tree_inventory·tree_sublot만) + 전역 스타일 4종 일괄 갱신

---

## 2. 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `fixes/global_tree_style.py` | `import tkinter as tk` 추가 (tk.TclError 사용) |
| `gui_app_modular/utils/ui_constants.py` | ReadableStyle.apply() — Treeview/Heading에 foreground·background·fieldbackground, style.map에 !selected |
| `gui_app_modular/utils/theme_refresh.py` | **신규** — _walk_widgets, get_theme_colors_from_style, _refresh_single_treeview, _refresh_native_widget, refresh_all_widgets_for_theme, debug_dump_widget_theme_status |
| `gui_app_modular/tabs/inventory_tab.py` | Inv.Treeview style.map 중복 제거, tree_select_bg/fg + !selected(_tv_fg) |
| `gui_app_modular/tabs/tonbag_tab.py` | Tb.Treeview style.map — tree_select_bg(배경)/tree_select_fg(글자) + !selected(_tb_fg) |
| `gui_app_modular/tabs/cargo_overview_tab.py` | Cargo.Treeview style.map — tree_select_bg/fg + !selected(_tv_fg) |
| `gui_app_modular/mixins/theme_mixin.py` | _change_theme에 after(50, _update_theme_colors); _update_theme_colors → refresh_all_widgets_for_theme + _update_theme_colors_fallback 추가 |
| `version.py` | __version__ = 6.1.1, VERSION_HISTORY 6.1.1 항목 |

---

## 3. 동작 요약

- **테마 변경 시**: ReadableStyle 재적용 → refresh_all_widgets_for_theme()로 전체 Treeview·네이티브 위젯 색상 갱신 → 메뉴바·탭 리프레시 → 50ms 후 _update_theme_colors() 한 번 더 실행
- **theme_refresh 실패 시**: _update_theme_colors_fallback()으로 Treeview 4종(기본·Inv·Tb·Cargo) configure/map + tree_inventory·tree_sublot 태그·그리드 + 툴바만 갱신

---

## 4. 테스트 제안

1. flatly → darkly 전환 후 재고/톤백/총괄 탭에서 행 글자 보이는지 확인  
2. darkly → flatly 전환 후 동일 확인  
3. 테마 전환 후 행 선택/해제 시 글자 유지 확인  
4. theme_refresh 모듈 제거 또는 import 오류 시 fallback으로 동작하는지 확인  

---

*v6.1.0 + SQM_v701_patch_only 검토 반영.*
