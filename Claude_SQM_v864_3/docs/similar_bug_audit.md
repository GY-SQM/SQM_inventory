# v864_1 유사 버그 전수검사 리포트 (Track D)

조사 일자: 2026-04-18
조사자: Claude (read-only audit)
대상 루트: `F:\program\SQM_inventory\Claude_SQM_v864_1`
조사 방법: Grep + Read + AST 분석 (코드 수정 없음)

---

## 0. 요약 — 발견 패턴 유형별 건수 / 심각도별 분포

| 섹션 | 패턴 | 발견 건수 | 비고 |
|------|------|-----------|------|
| A | 함수 시그니처 불일치 추가 발견 | 0 | 기존 `_dbg_log(4-arg)` 패턴은 이미 4개 파일 모두 통일 완료. AST 분석에서 추가 발견 없음 |
| B | Dead Code 추가 발견 | 4 (확정) + 3 (의도된 stub) | `_show_batch_outbound`, `_show_stock_alerts`, `_show_outbound_prediction`, `_show_search_popup` 등 |
| C | 메뉴/버튼 handler 미존재 추가 발견 | 0 (menu_registry 4건은 optional=True) / `_on_select_outbound_no` 1건 (bind) |
| D | dataclass 필드 오타 | 4 | `warehouse`, `free_time`, `free_time_date`(DOData), `free_time_until`(FreeTimeInfo), `net_weight`(LOTInfo) |
| E | 위젯 pack/grid 누락 | 0 | 모두 false positive (Notebook.add / PanedWindow.add 로 배치) |
| F | `__main__` 블록 오염 (main_app.py 외) | 0 | 다른 파일에서 추가 발견 없음 |
| G | hasattr fallback silent fail | 7 | `_refresh_tonbag_list`×5, `_setup_summary_tab_content`×1, `_reapply_dashboard_card_colors`×1 |
| H | 중복 tooltip 구현체 | 6 (3개 더 발견) | `apply_auto_tooltip`, `MenuTooltipManager`, `_apply_tooltip_safe`×2 |

**총 실제 버그 후보 건수: 약 15건 (CRITICAL 3, HIGH 4, MEDIUM 5, LOW 3)**

---

## A. 함수 시그니처 불일치 (추가 발견)

AST 기반 전수 분석 결과, **추가 발견 없음**.

### 검증된 기존 패턴 (이미 수정됨)
- `_dbg_log(tag, location, message, data=None)` 4-param 시그니처가 다음 4개 파일에서 모두 일관되게 정의됨:
  - `parsers/document_parser_modular/bl_mixin.py:23`
  - `gui_app_modular/dialogs/onestop_inbound.py:76`
  - `gui_app_modular/dialogs/parse_preview_confirm_dialog.py:24`
  - `features/parsers/onestop_inbound_candidate_patch.py:34`
  - 모든 호출부도 4-arg kwarg 형태.

### 유사 패턴 검사 (1-arg helper는 1-arg로만 호출되는지)
- `_log(msg)` / `_log_safe(msg)` / `_trace`, `_debug`, `_audit`, `_info`, `_warn` — 모두 정의와 호출부 일관.
- `gui_app_modular/tabs/log_tab.py:132 _log(message, level, where, what)`는 4-param 시그니처이며 `main_app.py`가 호출하는 `self._log(..., level=, where=, what=)` 형태도 모두 일치.

### AST 전체 스캔 결과
추가로 AST로 모든 클래스 메서드 및 모듈 함수의 인자 수 vs 호출 인자 수를 비교했을 때, `@staticmethod`/`@classmethod`/defaults/varargs 고려 후 **실제 불일치 0건**.

---

## B. Dead Code (추가 발견)

### B-1. 확정 dead (바로 제거/복구 필요) — HIGH

1. **`_show_stock_alerts`** — `gui_app_modular/mixins/features_v2_mixin.py:27`
   - v2.7 "재고 알림" 기능. 메뉴/툴바/버튼 어디서도 호출 안 함.
   - FeaturesV2Mixin 전체가 UI 엔트리 포인트 없이 떠있음.

2. **`_show_batch_outbound`** — `gui_app_modular/mixins/features_v2_mixin.py:82`
   - v2.7 "배치 출고" 기능. 호출 0회.
   - 주의: `gui_app_modular/mixins/drag_drop_mixin.py:265`에 동명의 nested `do_batch_outbound`가 있으나 다른 함수.

3. **`_show_outbound_prediction`** — `gui_app_modular/mixins/features_v2_mixin.py:221`
   - v2.7 "출고 예측" 기능. 호출 0회.

4. **`_show_search_popup`** — `gui_app_modular/mixins/toolbar_mixin.py:1145`
   - v3.8.9 검색 팝업. `gui_app_modular/` 전체에서 참조 0건.
   - 주석: "v3.8.9: 검색 팝업 — DB 데이터 로드 + LOT 리스트 필터링". `menu_audit_v864.md:403`에서는 `_paste_to_tree_placeholder` 내부 사용이라 기록돼 있으나 실제 grep에서 나오지 않음.

### B-2. 의도된 stub (유지 가능) — INFO

1. **`_show_progress_popup`** — `gui_app_modular/dialogs/onestop_inbound.py:1988`
   - 본문 docstring: "작업진행 전용 창 사용 안 함 — 기존 화면(인라인 진행 상태)만 사용"
   - 명시적 deprecation, 유지해도 무방.

2. **`_build_inbound_doc_frame` / `_build_inbound_progress_frame` / `_build_inbound_preview_frame` / `_build_inbound_button_frame`** — `gui_app_modular/dialogs/onestop_inbound.py:300-314`
   - 주석: "v7.0.0: _create_dialog 분리 — 4개 서브메서드 (테스트 가시성 확보)"
   - 실제 구현은 `_impl` 변형으로 모두 `pass`. 테스트 도입 대비 placeholder.

3. **`_show_gemini_api_guide`** — `gui_app_modular/dialogs/settings_dialog.py:220`
   - settings 다이얼로그 내부 가이드 팝업. 같은 다이얼로그 내 버튼이 참조했을 가능성 높음 — UI 미연결 상태.

### B-3. 기타 의심 (수동 검증 필요)

- `_refresh_after_action` (allocation_dialog.py:1595) — `_deferred_refresh_after_action`은 5회 호출되지만 `_refresh_after_action`은 0회. 다이얼로그 내부 도우미가 분리된 후 원본이 남은 듯.
- `_refresh_dashboard_chart` / `_refresh_dashboard_return_rate` — `dashboard_tab.py`와 `dashboard_data_mixin.py` 양쪽에 **중복 정의** (같은 이름). MRO에 따라 하나는 shadow됨.
  - `tabs/dashboard_tab.py:1022, 1118`
  - `tabs/dashboard_data_mixin.py:620, 1118`
- `_show_allocation_template_preview` (advanced_dialogs_mixin.py:1658) — 호출부 없음.
- `_show_return_export_history` (advanced_dialogs_mixin.py:1678) — 호출부 없음.
- `_show_from_tray` (window_mixin.py:272) — Tray 아이콘 메뉴에서 호출 예상 — 실제 미연결.
- `_show_simple_outbound_paste_dialog` (simple_excel_outbound.py:29) — 호출부 없음.
- `_refresh_inventory_async` (inventory_tab.py:1390) — `menu_audit_v864.md:280`은 "정상"이라 기록했지만 호출부 grep 0건.
- `_refresh_ttk_label` (theme_refresh.py) — 유틸 함수, 호출부 없음.
- `_bind_tk_tooltip` (ui_constants.py) — 다른 함수 내 nested (문제 없음).
- `_show_validation_result` (validation_mixin.py:31) — 호출부 없음.

---

## C. 메뉴/버튼 handler 미존재 (추가 발견)

### C-1. menu_registry.py 핸들러 미구현 (모두 optional=True → 자동 생략)
이미 `docs/menu_audit_v864.md:108-110, 187`에서 문서화된 4건:
- `_generate_customer_report`
- `_manage_report_templates`
- `_show_report_history`
- `_show_system_info`

모두 `optional=True` 플래그라 menu builder에서 자동 생략됨 → 실제 UX 영향 없음. 레지스트리 정리는 LOW 우선순위.

### C-2. Toolbar/menubar `_safe_call` 문자열 — **추가 발견 없음**
모든 핸들러 문자열이 실제 메서드 이름과 일치.

### C-3. bind() 이벤트 핸들러 참조 오류 — HIGH
- **`_on_select_outbound_no`** — `gui_app_modular/tabs/outbound_scheduled_tab.py:94`
  ```python
  self._ob_outbound_no_combo.bind('<<ComboboxSelected>>', lambda e: self._on_select_outbound_no())
  ```
  전 코드베이스에 `def _on_select_outbound_no` **정의 없음**. 콤보박스 선택 시 `AttributeError` → 조용히 실패 (lambda 예외 suppression 여부는 바인딩 환경 의존).

### C-4. Sidebar 폴백 체인 (이미 CRIT-3로 수정됨)
`gui_app_modular/mixins/toolbar_mixin.py:944-947, 965-970` — 주석에 "v8.7.0 [FIX CRIT-3]"로 명시. `_apply_theme`, `_show_settings_dialog` 부재를 fallback으로 흡수. 의도된 방어 코드이나 결국 silent fail이므로 섹션 G 참고.

---

## D. dataclass 필드 오타 / misuse

### D-1. 확정 버그 — CRITICAL (값이 항상 기본값으로 반환됨)

1. **`getattr(do, 'warehouse', ...)`** — `DOData`에 `warehouse` 필드 없음 (실제: `warehouse_name`, `warehouse_code`)
   - `gui_app_modular/dialogs/do_update_dialog.py:216`
     ```python
     warehouse = str(getattr(do, 'warehouse', DEFAULT_WAREHOUSE) or DEFAULT_WAREHOUSE)
     ```
     → 항상 `DEFAULT_WAREHOUSE` 반환. D/O 업데이트 다이얼로그에 실제 창고명 표시 안 됨.
   - `gui_app_modular/dialogs/onestop_inbound.py:2898` (1/2 — 첫 항의 `warehouse_name`은 맞지만 fallback `warehouse`는 dead) — 기능에 영향은 없으나 불필요 fallback.

2. **`getattr(do, 'free_time_date', '')`** — `DOData`에 `free_time_date` 필드 없음 (실제: `free_time_info: List[FreeTimeInfo]`)
   - `gui_app_modular/dialogs/do_update_dialog.py:230`
     ```python
     ft_date = str(getattr(do, 'free_time_date', '') or '')
     ```
     → 항상 빈 문자열. 위 줄(222-228)에서 `free_time_info`를 루프로 먼저 탐색하기 때문에 대부분 문제 없지만, **`free_time_info`가 비어있을 때의 fallback이 영원히 실패**.

3. **`getattr(do, 'free_time', '')`** / **`getattr(do, 'free_time', None)`** — DOData에 `free_time` 필드 없음
   - `gui_app_modular/dialogs/inbound_upload_mixin.py:492`
     ```python
     'free_time': str(getattr(do, 'free_time', '') or ''),
     ```
     → 항상 빈 문자열. 업로드 시 FREE TIME 컬럼 누락.
   - `gui_app_modular/dialogs/onestop_inbound.py:2932`
     ```python
     ft_single = getattr(do, 'free_time', None)
     if ft_single is not None:
         days_val = getattr(ft_single, 'storage_free_days', None) or ...
     ```
     → `ft_single`이 항상 None → 그 하위 블록 전체(`days_val`/`con_return` 계산)가 dead code.

4. **`getattr(ft, 'free_time_until', '')`** — `FreeTimeInfo`에 `free_time_until` 필드 없음 (실제: `free_time_date`)
   - `gui_app_modular/dialogs/onestop_inbound.py:2908`
     ```python
     ftd = (getattr(ft, 'free_time_date', '') or getattr(ft, 'free_time_until', ''))
     ```
     → 두 번째 fallback 영원히 빈값. 첫 번째가 성공하므로 실질적 영향은 없으나 dead fallback.

5. **`getattr(lot, 'net_weight', 0)`** — `LOTInfo`에 `net_weight` 필드 없음 (실제: `net_weight_kg`)
   - `engine_modules/inventory_modular/preflight_mixin.py:309`
     ```python
     lots_data.append({
         'lot_no': getattr(lot, 'lot_no', ''),
         'net_weight': getattr(lot, 'net_weight', 0),     # ← 항상 0
         'container_no': getattr(lot, 'container_no', '')
     })
     ```
     → **CRITICAL**: Preflight 검증에 전달되는 LOT 중량이 항상 0. 중량 기반 validation이 실질적으로 무력화됨. 특히 PreflightValidator에서 중량 검증 로직이 있다면 모든 LOT이 "0 kg"으로 취급됨.

### D-2. 불확실 — 수동 검증 필요

- `gui_app_modular/dialogs/onestop_inbound.py:2678` 주석: "`getattr(pl_result, 'success', False)`는 항상 False 반환" — 이미 인지되고 `lots` 길이로 우회. 유지 가능.
- `PackingListData`에는 `success` 필드가 없으나 `error_message`, `raw_response`, `pl_warnings`는 있음. 다른 유사 필드 misuse는 있는지 한 번 더 검증 권장.

---

## E. 위젯 pack/grid 누락

AST+regex 분석 결과 **실제 버그 없음**.

초기 탐지 결과 (10건)는 모두 false positive:
- `main_app.py`의 `tab_inventory, tab_allocation, ...` 등 9개 Notebook 탭: `self.notebook.add(self.tab_X, text=...)`로 배치. Notebook 방식은 pack 불필요.
- `onestop_outbound.py`의 `tab1~tab4`: Notebook 방식 동일.
- `utils/split_panel.py:46` `self._master_container`: `self._paned.add(self._master_container, ...)` — PanedWindow 방식.

기존 이슈 `_tree_frame` 생성 후 pack 누락 패턴은 **재현되지 않음** (이미 수정되었거나 영향 없음).

---

## F. `__main__` 블록 오염 (main_app.py 외)

전체 프로젝트 스캔 결과 **추가 발견 0건**.

`main_app.py`의 4개 dead method (`_on_run_v530_migration`, `_show_product_master`, `_show_product_inventory_report`, `_read_ui_settings`) 외에 `if __name__ == '__main__':` 블록 안에 잘못 들여쓰기된 클래스 메서드는 발견되지 않음.

검증 방법: 모든 `.py` 파일에서 `if __name__ == '__main__':` 행 이후 같거나 더 깊은 들여쓰기로 정의된 `def _xxx(self, ...)` 패턴 스캔.

---

## G. hasattr fallback silent fail

### G-1. 메서드가 어디에도 정의되지 않음 — 영구 silent fail

| # | 파일:라인 | 패턴 | 영향 |
|---|-----------|------|------|
| 1 | `gui_app_modular/main_app.py:440` | `if hasattr(self, '_setup_summary_tab_content'): self._setup_summary_tab_content()` | 요약 탭 초기화 항상 스킵 |
| 2 | `gui_app_modular/handlers/outbound_handlers.py:2297,2354,2438,2536,2548` (5회) | `if hasattr(self, '_refresh_tonbag_list'): self._refresh_tonbag_list()` | 출고 처리 후 톤백 리스트 리프레시 **5개 지점**에서 모두 스킵 — HIGH |
| 3 | `gui_app_modular/tabs/tonbag_tab.py:1336` | 동일 | 위와 동일 |
| 4 | `gui_app_modular/mixins/theme_mixin.py:214` | `if hasattr(self, '_reapply_dashboard_card_colors'): self._reapply_dashboard_card_colors()` | 테마 변경 시 대시보드 카드 색상 재적용 스킵 |

→ **모두 dead**: `def _setup_summary_tab_content`, `def _refresh_tonbag_list`, `def _reapply_dashboard_card_colors` 전 프로젝트에 정의 없음.

### G-2. 이미 CRIT-3로 알려진 패턴 (참고)
- `toolbar_mixin.py:944-947` `_apply_theme`/`apply_theme` fallback — `apply_theme` (underscore 없음)도 정의 안 됨.
- `toolbar_mixin.py:965-970` `_on_settings`/`_show_api_settings`/`_show_settings_dialog` — `_show_api_settings`만 실제 존재.
- `context_menu_mixin.py:150` `_on_paste_table` hasattr → 정의 없음.

### G-3. 검증된 true hasattr (OK)
- 위 검사는 instance variables (e.g., `_sidebar_frame`, `_toolbar_font`, `_step_labels`, `_dirty_tabs`, `_splash_window`, `_cust_combo`)를 제외. 이들은 런타임 생성 변수로 hasattr 검사가 올바름.

---

## H. 중복 Tooltip 구현체

### 발견된 구현체 목록 (6개, 기존 3개에서 추가 3개 발견)

| # | 구현 | 파일:라인 | 위치 정책 | 자동숨김 |
|---|------|-----------|-----------|----------|
| 1 | `apply_tooltip(widget, text, delay=250)` | `gui_app_modular/utils/ui_constants.py:1075` | 11시 방향 멀리 | 3초 / 클릭 |
| 2 | `_attach_tooltip(self, widget, text)` | `gui_app_modular/mixins/toolbar_mixin.py:1774` | (검증 필요) | (검증 필요) |
| 3 | `_attach_doc_tooltip(self, widget, text)` | `gui_app_modular/dialogs/onestop_inbound.py:219` | (검증 필요) | (검증 필요) |
| 4 | `apply_auto_tooltip(widget, label)` | `gui_app_modular/utils/auto_tooltip.py:66` | (검증 필요) | (검증 필요) |
| 5 | `MenuTooltipManager` 클래스 | `gui_app_modular/utils/auto_tooltip.py:103` | 메뉴 특화 | (검증 필요) |
| 6 | `_apply_tooltip_safe(self, widget, text)` ×2 | `gui_app_modular/utils/column_toggle.py:72`, `tree_enhancements.py:455` | 트리 컬럼 | (검증 필요) |

기존에 "3개 통일 완료"라고 언급된 것은 1/2/3번(apply/attach 계열)으로 추정. **4/5/6번은 별도 계보** (auto-tooltip, 컬럼 툴팁) — 위치/타이머 정책 일관성 재확인 필요.

### 권장
- `apply_auto_tooltip`과 `MenuTooltipManager`는 메뉴 라벨 기반 자동 tooltip이라 별도 유지 타당.
- `_apply_tooltip_safe` ×2 — `column_toggle.py`, `tree_enhancements.py`에 거의 동일한 private 구현. 하나로 병합 권장 (LOW).

---

## I. 심각도별 정렬

### CRITICAL (데이터 무결성 영향)
1. **D-1.5 `getattr(lot, 'net_weight', 0)` → 항상 0** [preflight_mixin.py:309]
   - LOT Preflight 검증에서 **모든 LOT 중량이 0으로 취급**. 중량 초과/부족 validation이 무력화될 가능성.
2. **D-1.3 `getattr(do, 'free_time', '')` → 항상 빈값** [inbound_upload_mixin.py:492]
   - 입고 업로드 시 FREE TIME 컬럼이 항상 공란. 컨테이너 반납일 추적 불가.
3. **G-1.2 `_refresh_tonbag_list` 5회 silent skip** [outbound_handlers.py 5지점, tonbag_tab.py 1지점]
   - 출고 처리 완료 후 톤백 리스트 refresh가 **6개 지점에서 모두 skip** → UI 비동기 불일치.

### HIGH (UX / 기능 가용성 영향)
4. **D-1.1 `getattr(do, 'warehouse', ...)` → DEFAULT 반환** [do_update_dialog.py:216]
   - D/O 업데이트 다이얼로그에 실제 창고명 미표시.
5. **D-1.2 `getattr(do, 'free_time_date', '')` fallback dead** [do_update_dialog.py:230]
   - free_time_info 비어있을 때 대체 경로 실패.
6. **D-1.4 `getattr(do, 'free_time', None)` 블록 dead** [onestop_inbound.py:2932-2944]
   - `storage_free_days`로 FREE TIME 계산하는 대체 로직 전체가 dead code.
7. **C-3 `_on_select_outbound_no` bind target 부재** [outbound_scheduled_tab.py:94]
   - ComboboxSelected 이벤트가 AttributeError로 조용히 실패.

### MEDIUM
8. **B-1.1~4** features_v2_mixin 3개 dead method + toolbar search popup
9. **G-1.1** `_setup_summary_tab_content` 영구 skip
10. **G-1.4** `_reapply_dashboard_card_colors` 영구 skip (테마 변경 시 카드 색상 반영 불완전)
11. **B-3** dashboard_chart/return_rate 중복 정의 (shadow)
12. **C-1** menu_registry 4개 미구현 handler (optional=True라 영향 제한적)

### LOW
13. **H** `_apply_tooltip_safe` 중복 구현 병합
14. **D-1 fallback deads** (`warehouse` / `free_time_until`의 fallback은 primary 성공으로 실질 영향 없음)
15. **B-3** advanced_dialogs_mixin dead methods

---

## J. 권장 조치

### J-1. 자동 수정 가능 (단순 rename)
- `preflight_mixin.py:309`: `'net_weight'` → `'net_weight_kg'` (getattr 필드명)
- `do_update_dialog.py:216`: `'warehouse'` → `'warehouse_name'`
- `inbound_upload_mixin.py:492`: `getattr(do, 'free_time', '')` 제거 또는 `free_time_info[0].storage_free_days` 참조로 교체
- `onestop_inbound.py:2908`: `getattr(ft, 'free_time_until', '')` fallback 제거 (dead)
- `do_update_dialog.py:230`: `getattr(do, 'free_time_date', '')` 제거 (DOData 필드 아님)

### J-2. 수동 판단 필요
- `onestop_inbound.py:2932-2944` `ft_single = getattr(do, 'free_time', None)` 전체 블록 — 의도가 `free_time_info[0]`인지 `containers` 내부인지 재설계 필요. 단순 제거가 아니라 로직 재검토.
- `_refresh_tonbag_list` 정의 필요 — tonbag_tab에 실제 refresh 메서드 추가 or 6개 호출지점 모두 `_refresh_inventory` 등으로 교체.
- `_setup_summary_tab_content` — v3.8.8 주석("검색 탭 삭제")에 따라 완전히 제거할 것인지, 요약 탭 기능 신규 구현할지 결정.
- `_reapply_dashboard_card_colors` — theme_mixin이 호출하는 dashboard hook. Dashboard 측에 정의 추가 필요.
- `_on_select_outbound_no` — outbound_scheduled_tab에 실제 메서드 구현 또는 bind 제거.

### J-3. 리팩터링 권장 (LOW)
- features_v2_mixin 전체 UI 연결 재검토 — 3개 기능(stock alerts / batch outbound / outbound prediction)이 통째로 미노출 상태.
- dashboard_tab.py와 dashboard_data_mixin.py의 중복 메서드 정의(`_refresh_dashboard_chart`, `_refresh_dashboard_return_rate`) 하나로 병합.
- `_apply_tooltip_safe` 중복 구현 `utils/` 공통 모듈로 추출.
- `_bind_tk_tooltip` / `apply_tooltip` / `_attach_tooltip` / `_attach_doc_tooltip` 4종의 정책(위치·자동숨김) 통일 여부 재확인.

### J-4. 레지스트리 정리 (DOCUMENTATION 영향만)
- `menu_registry.py`의 4개 optional 핸들러(`_generate_customer_report` 등): stub 추가 또는 레지스트리에서 제거해 UX 혼란 방지.

---

## K. 불확실 — 수동 검증 필요

1. **B-3 list 내 `_refresh_inventory_async`**: `menu_audit_v864.md:280`은 "정상"으로 분류했으나 grep 결과 호출부 없음. 문서화 오류 가능성 or 파일 주석에서 언급만.
2. **D-1.4 onestop_inbound `ft_single` 블록**: 코드 구조상 `getattr(do, 'free_time_info', [])`의 오타 가능성 있음. 수동 리뷰 권장.
3. **H Tooltip** 4/5/6번 구현체의 **실제 위치·타이머 정책** — 코드 본문 상세 비교 필요 (본 audit은 존재 여부만 확인).
4. **`_show_from_tray`**: window_mixin.py:272 정의되어 있으나 호출 0회. Tray icon 기능 자체가 비활성인지, 외부 라이브러리 callback인지 불명.
5. **B-3 `_show_gemini_api_guide`, `_show_simple_outbound_paste_dialog`, `_refresh_after_action`**: 각 파일 다이얼로그/핸들러가 독자 UI에서 연결되어 호출될 가능성. 외부 이벤트 바인딩 체크 필요.

---

## 부록 — 조사 방법 상세

### 사용한 분석 도구
1. **Grep (ripgrep)**: 패턴 매칭, 인용부호/괄호 구분
2. **Read**: 컨텍스트 검증
3. **Python AST**: 함수/메서드 시그니처 vs 호출부 대조 (staticmethod/classmethod/varargs/defaults 고려)
4. **정규식 + os.walk**: 전체 프로젝트 grep + 정의/참조 dictionary 빌드

### 제외한 경로
- `__pycache__/`, `.git/`, `backup/` 디렉터리
- `docs/` (문서), 마크다운 파일
- 노트북/컴파일 산출물

### False positive 필터 정책
- 인스턴스 변수(runtime assignment)와 메서드 구분을 위해 `def` 패턴과 `self.xxx = ...` 할당을 별도 추적
- widget method 호출(`command=self.tree.yview`) 제외
- Notebook.add/PanedWindow.add 배치 케이스 pack 누락에서 제외
- 중복 정의 검사에서 `@property`/`@setter` 쌍 제외
- staticmethod/classmethod 시그니처 정규화

---

**검증 한계**:
이 리포트는 정적 분석 결과이며, 런타임 다이나믹 바인딩(e.g., Tk의 `command=callable_ref`, `.bind(... self.method)`)에서 silent ignore되는 AttributeError는 실제 에러 로그로만 최종 확인 가능합니다. CRIT 항목 수정 전에 해당 코드 경로에 대한 통합 테스트를 권장합니다.
