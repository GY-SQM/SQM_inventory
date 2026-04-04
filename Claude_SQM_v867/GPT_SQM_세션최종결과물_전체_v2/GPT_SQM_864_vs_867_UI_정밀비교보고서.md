# GPT_SQM_864_vs_867_UI_정밀비교보고서
생성일시: 2026-04-04 14:41 (Asia/Seoul)
대상: `Claude_SQM_v864_20260329_FULL.zip` vs `Claude_SQM_v867.zip`

## 1. 한줄 결론
- **867의 React UI는 864의 Tkinter UI와 동일하지 않다.**
- **867 안의 Tkinter UI는 864 Tkinter UI와 매우 유사하며, 핵심 메인 탭 구조는 동일하다.**
- 따라서 867은 **기존 Tkinter 본체 유지 + 별도 React 조회 UI 추가** 상태로 보는 것이 정확하다.

## 2. 전수 비교 핵심 수치
- 864 전체 파일 수: **499**
- 867 전체 파일 수: **332**
- `gui_app_modular/**/*.py` 파일 수: 864 = **122**, 867 = **122**
- 동일 해시의 Tkinter GUI 파일 수: **106 / 122**
- 내용이 달라진 Tkinter GUI 파일 수: **16 / 122**
- 867 React UI 파일 수 (`web/src/**/*.*`): **19**
- 867 React API 파일 수 (`react_api/**/*.py`): **16**

### 2-1. 867에서 변경된 Tkinter GUI 파일 16개
- `gui_app_modular/dialogs/inbound_upload_mixin.py`
- `gui_app_modular/dialogs/lot_detail_dialog.py`
- `gui_app_modular/dialogs/onestop_inbound.py`
- `gui_app_modular/dialogs/onestop_outbound.py`
- `gui_app_modular/handlers/outbound_handlers.py`
- `gui_app_modular/main_app.py`
- `gui_app_modular/mixins/advanced_dialogs_mixin.py`
- `gui_app_modular/mixins/context_menu_mixin.py`
- `gui_app_modular/mixins/refresh_mixin.py`
- `gui_app_modular/mixins/validation_mixin.py`
- `gui_app_modular/tabs/dashboard_tab.py`
- `gui_app_modular/tabs/inventory_tab.py`
- `gui_app_modular/tabs/tonbag_tab.py`
- `gui_app_modular/utils/auto_tooltip.py`
- `gui_app_modular/utils/global_row_number_tree.py`
- `gui_app_modular/utils/pdf_report_gen.py`

## 3. 메인 화면 구조 비교

### 3-1. 864 Tkinter 메인 탭
- 📦 Inventory
- 📋 Allocation
- 🚛 Picked
- 📤 Outbound
- 🔄 Return
- 🔀 Move
- 📊 Dashboard
- 📝 Log
- 📷 Scan

### 3-2. 867 Tkinter 메인 탭
- 📦 Inventory
- 📋 Allocation
- 🚛 Picked
- 📤 Outbound
- 🔄 Return
- 🔀 Move
- 📊 Dashboard
- 📝 Log
- 📷 Scan

### 3-3. 867 React 상단 네비게이션
- Dashboard
- Inventory
- Tonbag
- Allocation
- Outbound
- Picked
- Sold

## 4. 동일성 판정표
| 항목 | 864 Tkinter | 867 Tkinter | 867 React | 판정 |
|---|---|---|---|---|
| 메인 탭 골격 | 9개 | 9개 | 7개 | React는 다름 |
| Inventory | 있음 | 있음 | 있음 | 부분 일치 |
| Allocation | 있음 | 있음 | 있음 | 부분 일치 |
| Picked | 있음 | 있음 | 있음 | 부분 일치 |
| Outbound | 있음 | 있음 | 있음 | 부분 일치 |
| Return | 있음 | 있음 | 없음 | React 누락 |
| Move | 있음 | 있음 | 없음 | React 누락 |
| Dashboard | 있음 | 있음 | 있음 | 부분 일치 |
| Log | 있음 | 있음 | 없음 | React 누락 |
| Scan | 있음 | 있음 | 없음 | React 누락 |
| Tonbag | 전용 메인탭 아님 | 전용 메인탭 아님 | 있음 | React 추가 항목 |
| Sold | 전용 메인탭 아님 | 전용 메인탭 아님 | 있음 | React 추가 항목 |

## 5. 메뉴 체계 비교
- `menu_registry.py` 동일 여부: **True**
- **FILE_MENU_INBOUND_ITEMS**: 14개
- **FILE_MENU_OUTBOUND_ITEMS**: 14개

### 5-1. 판정
- Tkinter는 드롭다운형 업무 메뉴 체계가 완성되어 있다.
- 867 React는 현재 `App.jsx` 기준 **단순 NavLink 상단바**이며, Tkinter 메뉴 체계를 동일하게 재현하지 못했다.

## 6. 다이얼로그/모달 비교
- 864 Tkinter 다이얼로그 파일 수: **39**
- 867 Tkinter 다이얼로그 파일 수: **39**
- 867 React `web/src`에서 `Modal`, `Dialog` 관련 구현 검색 결과: **없음**

### 6-1. Tkinter에 존재하는 대표 업무 다이얼로그
- `gui_app_modular/dialogs/allocation_approval_dialog.py`
- `gui_app_modular/dialogs/lot_detail_dialog.py`
- `gui_app_modular/dialogs/onestop_inbound.py`
- `gui_app_modular/dialogs/onestop_outbound.py`
- `gui_app_modular/dialogs/picking_list_preview_dialog.py`
- `gui_app_modular/dialogs/return_dialog.py`
- `gui_app_modular/dialogs/settings_dialog.py`
- `gui_app_modular/dialogs/tonbag_location_upload.py`

### 6-2. 판정
- LOT 상세, 입고 파싱, 출고 처리, 반품, 위치 이동 승인 등 Tkinter 핵심 업무 다이얼로그가 React에는 아직 대응 구현되지 않았다.

## 7. React API 비교
- 867 `react_api` 라우트는 **GET 중심 조회 API**로 구성되어 있다.
- `react_api/routes/dashboard.py`: GET /summary, GET /by-product, GET /location-summary
- `react_api/routes/inventory.py`: GET /filters, GET /search, GET /lot/{lot_no}
- `react_api/routes/tabs.py`: GET /tonbag, GET /allocation, GET /picked, GET /sold, GET /outbound
- `react_api/main.py`: GET /api/health
- 전체 `POST/PUT/DELETE` 개수: POST=0, PUT=0, DELETE=0
- 따라서 현재 React는 **조회형 대시보드/리스트 UI**이고, Tkinter의 실행형 업무 흐름(입고 생성, 출고 실행, 취소, 위치 변경)을 아직 완전히 대체하지 못한다.

## 8. 864 Tkinter ↔ 867 React 화면/기능 대응표
| 864 Tkinter 기준 기능 | 867 React 현재 상태 | 관련 파일 | 판정 |
|---|---|---|---|
| Dashboard 탭 | 있음 | `web/src/pages/DashboardPage.jsx, react_api/routes/dashboard.py` | 부분 일치 |
| Inventory 탭 | 있음 | `web/src/pages/InventoryPage.jsx, react_api/routes/inventory.py` | 부분 일치 |
| Allocation 탭 | 있음 | `web/src/pages/AllocationPage.jsx, react_api/routes/tabs.py` | 부분 일치 |
| Picked 탭 | 있음 | `web/src/pages/PickedPage.jsx, react_api/routes/tabs.py` | 부분 일치 |
| Outbound 탭 | 있음 | `web/src/pages/OutboundPage.jsx, react_api/routes/tabs.py` | 부분 일치 |
| Return 탭 | 없음 | `Tk: return 관련 대응 React 페이지 부재` | 누락 |
| Move 탭 | 없음 | `Tk: 이동/위치 관련 대응 React 페이지 부재` | 누락 |
| Log 탭 | 없음 | `로그/이력 페이지 부재` | 누락 |
| Scan 탭 | 없음 | `바코드/스캔 페이지 부재` | 누락 |
| LOT 상세 팝업 | API만 일부 존재, UI 없음 | `react_api/routes/inventory.py + web/src/api/inventoryApi.js` | 누락/반쪽 |
| 입고 파싱 모달 | 없음 | `gui_app_modular/dialogs/onestop_inbound.py` | 누락 |
| 출고 처리 모달 | 없음 | `gui_app_modular/dialogs/onestop_outbound.py` | 누락 |
| 반품 처리 | 없음 | `gui_app_modular/dialogs/return_dialog.py` | 누락 |
| 위치 변경/이동 승인 | 없음 | `gui_app_modular/dialogs/tonbag_location_upload.py` | 누락 |
| 드롭다운 업무 메뉴 | 없음 | `web/src/App.jsx` | 누락 |
| 쓰기 API | 없음 | `react_api/routes/*` | 누락 |

## 9. 빠진 핵심 10개 기능 (867 React 기준)
1. **Return 화면** — 반품/재입고 업무
2. **Move 화면** — 톤백 이동/위치 승인
3. **Log 화면** — 로그/이력 추적
4. **Scan 화면** — 스캔 중심 출고/검증
5. **상단 드롭다운 메뉴** — 입고/출고/도구/검색
6. **LOT 상세 모달** — LOT 클릭 상세정보, 톤백목록, 이력
7. **입고 파싱 모달** — PDF/Excel 업로드 후 파싱 확인
8. **출고 처리 모달** — 톤백 선택 후 출고 실행
9. **반품/위치 변경 모달** — 반품/재고 이동 실행
10. **쓰기 API** — create/execute/cancel/update/upload

## 10. P0 / P1 / P2 우선순위

### P0 (가장 먼저)
- **쓰기 API 추가**
  - `react_api/main.py`
  - `react_api/routes/*.py`
  - `engine_modules/inventory_modular/inbound_mixin.py`
  - `engine_modules/inventory_modular/outbound_mixin.py`
  - `engine_modules/inventory_modular/tonbag_mixin.py`
  - `engine_modules/inventory_modular/return_mixin.py`
- **상단 메뉴를 Tkinter 메뉴 구조에 맞게 확장**
  - `web/src/App.jsx`
  - `gui_app_modular/menu_registry.py`
- **LOT 상세 모달 구현**
  - `web/src/pages/InventoryPage.jsx`
  - `web/src/api/inventoryApi.js`
  - `react_api/routes/inventory.py`
  - `engine_modules/inventory_modular/query_mixin.py`
- **입고 파싱/출고 처리 모달 골격**
  - `web/src/components/*`
  - `web/src/pages/*`
  - `gui_app_modular/dialogs/onestop_inbound.py`
  - `gui_app_modular/dialogs/onestop_outbound.py`

### P1 (그 다음)
- **Return / Move / Scan 페이지 이식**
  - `web/src/pages/ReturnPage.jsx (신규)`
  - `web/src/pages/MovePage.jsx (신규)`
  - `web/src/pages/ScanPage.jsx (신규)`
  - `react_api/routes/tabs.py 또는 신규 routes`
- **반품/위치 변경 실행 로직 연결**
  - `engine_modules/inventory_modular/return_mixin.py`
  - `engine_modules/inventory_modular/tonbag_mixin.py`
- **로그/이력 조회 페이지 추가**
  - `web/src/pages/LogPage.jsx (신규)`
  - `react_api/routes/*`
  - `engine_modules/inventory_modular/outbound_mixin.py`

### P2 (마무리/고급화)
- **Tkinter 다이얼로그 세부 UX 이식**
  - `gui_app_modular/dialogs/lot_detail_dialog.py`
  - `gui_app_modular/dialogs/allocation_approval_dialog.py`
  - `gui_app_modular/dialogs/picking_list_preview_dialog.py`
  - `gui_app_modular/dialogs/inbound_template_dialog.py`
- **권한/검증/트랜잭션 공통화**
  - `react_api/schemas/*.py`
  - `react_api/utils/*.py`
  - `engine_modules/inventory_modular/integrity_mixin.py`
- **테마/스타일 정교화**
  - `web/src/App.css`
  - `web/src/index.css`
  - `신규 공통 컴포넌트`

## 11. 실제 엔진 연결 후보 함수
- **입고 생성** → `engine_modules/inventory_modular/inbound_mixin.py` : process_inbound
- **출고 실행** → `engine_modules/inventory_modular/outbound_mixin.py` : process_outbound, cancel_outbound_tonbag
- **LOT 상세** → `engine_modules/inventory_modular/query_mixin.py` : get_lot_detail, get_lot_items
- **반품** → `engine_modules/inventory_modular/return_mixin.py` : process_return, process_return_reinbound, finalize_return_to_available
- **위치 변경/이동 승인** → `engine_modules/inventory_modular/tonbag_mixin.py` : update_tonbag_location, submit_batch_move, approve_batch_move, reject_batch_move

## 12. 최종 판정
- **867 React UI = 864 Tkinter UI** 라고 말할 수 없다.
- **867 Tkinter UI ≈ 864 Tkinter UI** 는 성립한다.
- 867 React는 현시점에 **조회형 1차 이행본** 이고, Tkinter와의 기능 동등성은 아직 미완성이다.
