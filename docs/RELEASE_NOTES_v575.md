# SQM v5.7.5 — UI·원스톱 입고 개선 (폰트 위계, 캘린더, 진행 팝업, UID 표시)

## 개요
상단 메뉴/탭 글자 크기 위계 정리, 기간 필터 캘린더 선택, 표시 모드(행 높이) 제거, 원스톱 입고 진행 팝업·라벨·버튼·파싱 결과 확인 흐름, 스탯바 None 포맷 오류 수정, 톤백 UID 조회·폴백 표시를 반영한 버전입니다.

---

## 주요 변경 사항

### 1. UI 글자 크기 위계
- **상단 메뉴**(파일, 입고, 출고, 재고, 보고서, 설정/도움말): **14pt bold** — 가장 크게
- **탭**(재고리스트, 톤백리스트, 통계, 로그): **11pt** — 상단 메뉴보다 작게
- *파일: `gui_app_modular/mixins/toolbar_mixin.py`*

### 2. 기간 필터 — 캘린더 선택
- 필터 바 **기간(시작일~종료일)** 입력란 **클릭** 또는 **📅 버튼** 클릭 시 **캘린더 팝업** 표시
- 년/월 이동(◀ ▶) 후 날짜 클릭 시 `YYYY-MM-DD` 자동 입력 및 필터 적용
- *파일: `gui_app_modular/utils/tree_enhancements.py` — `show_date_calendar()`*

### 3. 표시 모드(컬럼/본문/날짜) 제거
- 재고 리스트·톤백 리스트에서 **표시 모드** 라디오 버튼 제거
- 행 높이는 기본(normal) 고정, **표시 컬럼** 체크박스만 유지
- *파일: `gui_app_modular/utils/column_toggle.py`, `table_styler.py`, `inventory_tab.py`, `tonbag_tab.py`*

### 4. 원스톱 입고 — 진행·라벨·버튼·흐름

| 항목 | 내용 |
|------|------|
| **진행 팝업** | 평소 숨김 → **파싱/업로드 시작 시** 화면 중앙 **큰 창**(880×380)으로 진행률·현재 작업 표시. 폰트 18pt(메시지)·16pt(%). |
| **서류 라벨** | ② **Invoice, FA** / ③ **Bill of Lading** / ④ **Delivery Order** 로 통일 |
| **파싱 메시지** | `현재 파싱 중: {서류명} — {파일명}` 형식으로 표시 |
| **미리보기** | TONBAG 열 삭제. 전 컬럼 **가운데 정렬**. SHIP DATE/ARRIVAL/FREE TIME/WH는 BL·D/O 파싱·계산으로 채움, FREE TIME 일수(storage_free_days) 폴백 추가. |
| **하단 버튼** | [엑셀 내보내기][DB 업로드] 파란색·폰트 15, [취소] 빨간색·폰트 15. **합계** 문구는 버튼과 **같은 한 줄 가운데** 배치. |
| **파싱 완료 흐름** | 파싱 끝 → **파싱 결과 확인** 큰 창(900×520) → 사용자 **맞음** 클릭 → **다음 작업 선택** 팝업(Excel/DB 업로드/취소) 표시 |
| **상수 조정** | `PROGRESS_POPUP_WIDTH/HEIGHT`, `PROGRESS_POPUP_CLOSE_DELAY_MS` 로 팝업 크기·자동 닫힘 시간 조정 가능 |

- *파일: `gui_app_modular/dialogs/onestop_inbound.py`*

### 5. 스탯바·재고 통계 — None 포맷 오류 수정
- DB 빈 상태 또는 톤백 집계 NULL 시 `tb_avail`/`tb_total` 등이 None이 되어 `:,` 포맷 시 **TypeError** 발생하던 문제 수정
- `lots`, `weight_mt`, `tb_total`, `tb_avail` 등을 **0**으로 안전 치환
- *파일: `gui_app_modular/mixins/statusbar_mixin.py`, `gui_app_modular/tabs/inventory_tab.py`*

### 6. 톤백 리스트 — UID 표시
- **UID**: 톤백 고유 식별자 (`LOT_NO-S0` / `LOT_NO-1` 등). 복사·관리용.
- **공란 원인**: 톤백 JOIN 조회 쿼리에 `tonbag_uid` 컬럼이 포함되지 않아 화면에 안 나오던 문제.
- **수정**: `get_tonbags_with_inventory()` SELECT에 **t.tonbag_uid** 추가. UID가 DB에 없을 때 **lot_no-S0** / **lot_no-sub_lt** 로 계산해 표시하는 폴백 추가.
- *파일: `engine_modules/inventory_modular/query_mixin.py`, `gui_app_modular/tabs/tonbag_tab.py`*

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.7.5, VERSION_HISTORY 5.7.5 |
| gui_app_modular/mixins/toolbar_mixin.py | 상단 메뉴 14pt, 탭 11pt |
| gui_app_modular/utils/tree_enhancements.py | 기간 캘린더 팝업, show_date_calendar() |
| gui_app_modular/utils/column_toggle.py | 표시 모드 UI 제거 |
| gui_app_modular/utils/table_styler.py | 표시 모드 블록 제거 |
| gui_app_modular/dialogs/onestop_inbound.py | 진행 팝업·라벨·버튼·합계·파싱 확인·버튼 팝업·미리보기 정렬·TONBAG 열 삭제·FREE TIME 폴백 등 |
| gui_app_modular/mixins/statusbar_mixin.py | 스탯바 None → 0 처리 |
| gui_app_modular/tabs/inventory_tab.py | _refresh_inv_stats None 방지 |
| engine_modules/inventory_modular/query_mixin.py | get_tonbags_with_inventory 에 tonbag_uid 추가 |
| gui_app_modular/tabs/tonbag_tab.py | UID 공란 시 lot_no-S0 / lot_no-sub_lt 폴백 |

---

*작성일: 2026-02-16 | SQM v5.7.5*
