# RECON v867 Web Migration Map
Generated: 2026-04-04

---

## 1. 메뉴 대응표 (tkinter → React)

| tkinter 메뉴 | tkinter 파일 | React 대응 | 구현 상태 |
|---|---|---|---|
| 📤 출고 (Top-level) | custom_menubar.py:136 | **없음 → 신규 드롭다운** | ❌ |
| 📁 파일 (입고/백업/내보내기) | custom_menubar.py:163 | **없음 → 신규 드롭다운** | ❌ |
| 📝 보고서 | custom_menubar.py:238 | **없음 → 신규 드롭다운** | ❌ |
| 🔧 도구 | custom_menubar.py:261 | **없음 → 신규 드롭다운** | ❌ |
| 👁️ 뷰 (탭 이동) | custom_menubar.py:370 | NavLink 존재 (App.jsx:23-35) | ✅ 부분 |
| 도움말 | menu_mixin.py:342 | **없음** | ❌ |

### React 상단 메뉴바 구현 계획
```
검색 | 도구 | 입고 | 출고 | [현재 탭 표시]
```
→ 기존 NavLink 바를 드롭다운 메뉴 포함 Navigation으로 확장

---

## 2. 다이얼로그 대응표 (tkinter → React 모달)

| tkinter 다이얼로그 | 파일 | React 모달 | 우선순위 |
|---|---|---|---|
| OneStopInboundDialog | dialogs/onestop_inbound.py:122 | 입고 파싱 모달 | P1 |
| S1OneStopOutboundDialog | dialogs/onestop_outbound.py | 출고 처리 모달 | P1 |
| LotDetailDialogMixin | dialogs/lot_detail_dialog.py | LOT 상세 모달 | P1 |
| AllocationDialog | dialogs/allocation_dialog.py | Allocation 모달 | P2 |
| ProductMasterDialog | dialogs/product_master_dialog.py | 제품 마스터 | P2 |
| IntegrityV760Dialog | dialogs/integrity_v760_dialog.py | 정합성 검사 | P3 |
| InboundHistoryDialog | dialogs/inbound_history_dialog.py | 입고 이력 | P3 |

---

## 3. 쓰기 API 연결 후보 함수 표

| 신규 API | engine_modules 함수 | 파일 | 비고 |
|---|---|---|---|
| POST /api/inbound/create | `InboundMixin.process_inbound()` | inbound_mixin.py:124 | packing_data, invoice_data, bl_data 필요 |
| POST /api/outbound/execute | `OutboundMixin` 관련 함수 | outbound_mixin.py | 4-step outbound workflow |
| PUT /api/outbound/cancel | `OutboundMixin` 관련 함수 | outbound_mixin.py | status 변경 + rollback |
| PUT /api/location/update | location 관련 (tonbag_location) | query_mixin.py / DB 직접 | inventory_tonbag.location 업데이트 |
| POST /api/files/upload | parsers/ 모듈 | parsers/ | PDF/Excel 파싱 후 결과 반환 |

---

## 4. 기존 API 엔드포인트 현황 (ALL GET)

| Method | Path | 서비스 |
|---|---|---|
| GET | /api/health | main.py |
| GET | /api/dashboard/summary | dashboard_read_service |
| GET | /api/dashboard/by-product | dashboard_read_service |
| GET | /api/dashboard/location-summary | dashboard_read_service |
| GET | /api/inventory/filters | inventory_read_service |
| GET | /api/inventory/search | inventory_read_service |
| GET | /api/inventory/lot/{lot_no} | inventory_read_service |
| GET | /api/tabs/tonbag | tabs.py |
| GET | /api/tabs/allocation | tabs.py |
| GET | /api/tabs/picked | tabs.py |
| GET | /api/tabs/sold | tabs.py |
| GET | /api/tabs/outbound | tabs.py |

---

## 5. 실제 수정 파일 목록

### Backend (react_api/)
| 파일 | 작업 | 유형 |
|---|---|---|
| react_api/main.py | 신규 라우터 등록 | 수정 |
| react_api/routes/inbound.py | POST /inbound/create | 신규 |
| react_api/routes/outbound_write.py | POST /outbound/execute, PUT /outbound/cancel | 신규 |
| react_api/routes/location.py | PUT /location/update | 신규 |
| react_api/routes/files.py | POST /files/upload | 신규 |
| react_api/schemas/write_models.py | 요청/응답 모델 | 신규 |
| react_api/services/inbound_write_service.py | process_inbound 래퍼 | 신규 |
| react_api/services/outbound_write_service.py | outbound 래퍼 | 신규 |

### Frontend (web/src/)
| 파일 | 작업 | 유형 |
|---|---|---|
| web/src/App.jsx | 메뉴바 교체 | 수정 |
| web/src/components/MenuBar.jsx | 드롭다운 메뉴바 | 신규 |
| web/src/components/LotDetailModal.jsx | LOT 상세 팝업 | 신규 |
| web/src/components/InboundModal.jsx | 입고 파싱 모달 | 신규 |
| web/src/components/OutboundModal.jsx | 출고 처리 모달 | 신규 |
| web/src/api/writeApi.js | 쓰기 API 클라이언트 | 신규 |

---

## 6. 핵심 연결 흐름

```
React MenuBar → 입고 클릭 → InboundModal 열림
  → 파일 업로드 → POST /api/files/upload → parsers/ 호출
  → 파싱 결과 미리보기
  → 생성 확인 → POST /api/inbound/create → InboundMixin.process_inbound()
  → 결과 표시 (LOT NO, 톤백 수, 경고)

React MenuBar → 출고 클릭 → OutboundModal 열림
  → 톤백 선택 → 수량/출고처 입력
  → 실행 → POST /api/outbound/execute → OutboundMixin 관련 함수
  → 결과 표시 (성공/실패)

InventoryPage → LOT 클릭 → LotDetailModal 열림
  → GET /api/inventory/lot/{lot_no} (기존)
  → 기본정보 + 톤백 목록 + 이력 + 배정 상태
```
