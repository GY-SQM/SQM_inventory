# SQM MASTER FINAL v868 (Claude Code Execution Standard)
생성일: 2026-04-04 (루비 세션 업데이트)
최종수정: 2026-04-04 (전수검사 + P0~P3 로드맵 반영)
기준: Claude_SQM_v868 실제 구현 상태 100% 반영

---

## ⚠️ 전수검사 결과 요약 (2026-04-04)

### 현재 완성도
| 구분 | 완성도 | 비고 |
|---|---|---|
| 백엔드 API | 85% | Return API만 없음 |
| React 페이지 (조회) | 55% | 컬럼 누락 多 |
| React 페이지 (기능) | 20% | D/O연결, 위치매핑 등 누락 |
| Return 기능 | 0% | 백엔드+프론트 전무 |
| 다크/라이트 테마 | 0% | 미구현 |
| 열 토글 | 0% | 미구현 |
| **종합** | **≈ 45%** | tkinter 대체 불가 현재 상태 |

### 확정 방향
- **목표**: tkinter 완전 대체 (병행 운영 아님)
- **Return 탭**: 소량반품(직접입력) + Excel 다량반품 **둘 다** 구현
- **컬럼 토글**: 테이블 상단 가로 체크박스 줄 형태 (v864 스타일)
- **반품 사유 코드**: v864 동일 5개 고정 (품질불량/수량오류/고객요청/파손/기타)
- **실행 방식**: Claude Code 자율 실행
- **ARRIVAL, CON RETURN, FREE TIME**: 매일 확인 → 기본 ON 컬럼

### 누락 확인 항목
| 항목 | v864 | v868 | 우선순위 |
|---|---|---|---|
| Return 탭 (반품) | ✅ | ❌ 전무 | P0 |
| ARRIVAL/CON RETURN/FREE TIME 컬럼 | ✅ | ❌ | P0 |
| 컬럼 토글 바 | ✅ | ❌ | P0 |
| D/O 후속 연결 | ✅ | ❌ | P1 |
| 톤백 위치 매핑 | ✅ | ❌ | P1 |
| 다크/라이트 테마 | ✅ | ❌ | P2 |

---

## 0. 절대 실행 규칙

### 자율 실행 규칙
- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기 / 삭제는 자동 승인된 것으로 간주할 것
- 테스트 실패 시 자동 수정 후 재시도할 것
- 작업 완료 후 다음 단계 자동 진행
- 중단 없이 끝까지 수행할 것

### 강제 테스트 규칙
```text
Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```
테스트 실패 상태에서 다음 단계 진행 금지.

---

## 1. 기준 원본

기준 원본은 `Claude_SQM_v868` 이다.

### 확인된 상위 구조
```text
core/
  pdf_engine.py              ← PC/Android 공통 PDF 엔진 ✅
data/
  db/sqm_inventory.db
engine_modules/
  inventory_modular/
    inbound_mixin.py
    outbound_mixin.py
    query_mixin.py
features/
gui_app_modular/
parsers/
react_api/
  middleware/
    security.py              ← Phase 5 보안 미들웨어 ✅
  routes/
    dashboard.py             ✅
    inventory.py             ✅
    tabs.py                  ✅
    inbound.py               ← Phase 4 쓰기 API ✅
    outbound_write.py        ← Phase 4 쓰기 API ✅
    location.py              ← Phase 4 쓰기 API ✅
    files.py                 ← Phase 4 쓰기 API ✅
    search.py                ← Phase 6 검색 ✅
    tools.py                 ← Phase 6 도구 ✅
    advanced.py              ← Phase 6 Advanced ✅
    ai_dashboard.py          ← Phase 7 AI ✅
  services/
    inbound_write_service.py ← Phase 3 ✅
    outbound_write_service.py← Phase 3 ✅
  schemas/
    write_models.py          ← Phase 1 ✅
scripts/
  telegram_bridge.py         ← Phase 8 ✅
  telegram_notify.py         ← Phase 8 ✅
tests/
  stage_gates/               ← 기존 12개 + 신규 1개 ✅
web/src/
  components/
    MenuBar.jsx              ← Phase 4 메뉴바 ✅
    LotDetailModal.jsx       ← Phase 4 모달 ✅
    InboundModal.jsx         ← Phase 4 모달 ✅
    OutboundModal.jsx        ← Phase 4 모달 ✅
    SearchModal.jsx          ← Phase 4 검색 모달 ✅
    Modal.jsx                ← 공통 모달 ✅
  pages/                     ← 7개 페이지 ✅
docs/
  RECON_V867_WEB_MIGRATION_MAP.md ← Recon 완료 ✅
```

---

## 2. 현재 구현 완료 현황

### Phase 완료 현황
```text
Recon Phase : ✅ 완료
Phase 1     : ✅ 완료 (공통 응답 스키마, write_models)
Phase 2     : ✅ 완료 (테스트 13개)
Phase 3     : ✅ 완료 (서비스 레이어 2개)
Phase 4     : ✅ 완료 (메뉴바 + 모달 4종 + 쓰기 API 5종)
Phase 5     : ✅ 완료 (security 미들웨어)
Phase 6     : ✅ 완료 (search + tools + advanced)
Phase 7     : ✅ 완료 (ai_dashboard)
Phase 8     : 🔄 진행 중 (telegram_bridge + telegram_notify 있음)
P0~P3       : 🔄 신규 로드맵 수립 완료 (18개 스텝 — 섹션 9 참조)
```

### API 현황 (전체)
```text
GET  /api/dashboard/summary
GET  /api/dashboard/by-product
GET  /api/dashboard/location-summary
GET  /api/inventory/filters
GET  /api/inventory/search
GET  /api/inventory/lot/{lot_no}
GET  /api/tabs/tonbag
GET  /api/tabs/allocation
GET  /api/tabs/picked
GET  /api/tabs/sold
GET  /api/tabs/outbound
GET  /api/tabs/move-log          ← tabs.py 구현 완료 (프론트 연결됨)
GET  /api/tabs/audit-log         ← tabs.py 구현 완료 (프론트 연결됨)
GET  /api/tabs/stock-movement    ← tabs.py 구현 완료 (프론트 연결됨)
POST /api/inbound/create          ← 쓰기 API
POST /api/outbound/execute        ← 쓰기 API
PUT  /api/outbound/cancel         ← 쓰기 API
PUT  /api/location/update         ← 쓰기 API
POST /api/files/upload            ← 쓰기 API
GET  /api/search/unified
GET  /api/tools/export/csv
GET  /api/tools/integrity-check
GET  /api/advanced/outbound-history

[P0 신규 추가 예정]
GET  /api/return/list             ← P0-3 신규
GET  /api/return/statistics       ← P0-3 신규
POST /api/return/single           ← P0-4 신규 (소량반품)
POST /api/return/bulk-excel       ← P0-5 신규 (Excel 다량반품 preview)
POST /api/return/bulk-confirm     ← P0-5 신규 (최종 실행)

[P1 신규 추가 예정]
POST /api/do-update/apply         ← P1-1 신규
POST /api/location/bulk-update    ← P1-2 신규
POST /api/location/single-update  ← P1-2 신규
POST /api/allocation/create       ← P1-3 확인/보완
```

### React 컴포넌트 현황
```text
[기존 완료]
MenuBar.jsx        ← 검색/도구/입고/출고 드롭다운 ✅
LotDetailModal.jsx ← LOT 상세 팝업 ✅
InboundModal.jsx   ← 입고 파싱 모달 ✅
OutboundModal.jsx  ← 출고 처리 모달 ✅
SearchModal.jsx    ← 통합 검색 모달 ✅
DataTable.jsx      ← 공통 테이블 컴포넌트 ✅

[페이지 — 기존]
DashboardPage.jsx      ✅ (161줄, 실구현)
InventoryPage.jsx      ✅ (182줄, 실구현) ← P0-1에서 토글바 추가 예정
CargoOverviewPage.jsx  ✅ (106줄, 실구현)
ScanPage.jsx           ✅ (85줄, 실구현)
TonbagPage.jsx         ⚠️ (34줄, 기본구현)
AllocationPage.jsx     ⚠️ (29줄, 기본구현)
MovePage.jsx           ⚠️ (23줄, 기본구현)
SummaryPage.jsx        ⚠️ (21줄, 기본구현)
SoldPage.jsx           ⚠️ (20줄, 기본구현)
PickedPage.jsx         ⚠️ (20줄, 기본구현)
OutboundPage.jsx       ⚠️ (19줄, 기본구현)
LogPage.jsx            ⚠️ (17줄, 기본구현)

[P0 신규 추가 예정]
ReturnPage.jsx         ← P0-6 신규 (소량반품탭 + Excel탭 + 이력탭)
web/src/api/returnApi.js ← P0-6 신규

[P1 신규 추가 예정]
DoUpdateModal.jsx        ← P1-1 신규
LocationMappingModal.jsx ← P1-2 신규
AllocationInputModal.jsx ← P1-3 신규
OutboundHistoryPage.jsx  ← P1-4 신규

[P2 신규 추가 예정]
ProductMasterModal.jsx   ← P2-2 신규
IntegrityPage.jsx        ← P2-3 신규
```

---

## 3. 작업 전략

### 절대 금지
- 예전 가정 구조만 믿고 수정하지 말 것
- 실제 v868 구조 조사 없이 패치 먼저 적용하지 말 것
- FastAPI에서 완전 신규 업무 로직 작성 금지
- rollback 없는 쓰기 API 구현 금지
- fitz 직접 import 금지 → core/pdf_engine 경유
- engine_modules 직접 수정 금지

### 필수 원칙
1. 기존 engine_modules 로직 재사용
2. 단계별 테스트 게이트 통과 후만 다음 단계 진행
3. 모든 쓰기 API 트랜잭션 보호
4. core/pdf_engine.py 통해서만 PDF 처리

---

## 4. 남은 작업

### Phase 8: 통합 실행 완료 기준

#### 8-1. Telegram Bridge 완성
```text
파일: scripts/telegram_bridge.py (존재 ✅)
확인 필요:
  - y/n/1/2/3 응답 처리 동작 확인
  - idle timeout 감지 동작 확인
  - Claude Code 출력 300~500자 전송 확인
```

#### 8-2. run_master.bat 완성
```text
파일: run_master.bat (존재 ✅)
확인 필요:
  - .env 존재 확인
  - pytest 통과 확인
  - FastAPI 정상 기동 확인
  - web/dist 빌드 확인
  - Telegram bridge 연결 확인
```

#### 8-3. run_master.ps1 완성
```text
파일: run_master.ps1 (존재 ✅)
확인 필요:
  - run_master.bat 과 동일 기능 PowerShell 버전
```

#### 8-4. pytest 전체 통과 확인
```text
cd F:\프로그램\Sqm 재고관리\Claude_SQM_v868
pytest tests/ -v
→ 전체 통과 확인
```

---

> ⚠️ Phase 8의 "누락 탭 5개 구현" 항목은 전수검사 결과 이미 구현 완료 확인됨.
> MovePage / ScanPage / LogPage / SummaryPage / CargoOverviewPage 모두 존재.
> 해당 항목 삭제, 아래 P0~P3 로드맵으로 대체.

---

## 5. 실행 방법

### PC 실행
```cmd
F:
cd "프로그램\Sqm 재고관리\Claude_SQM_v868"
python -m uvicorn react_api.main:app --host 127.0.0.1 --port 8000
```
```cmd
F:
cd "프로그램\Sqm 재고관리\Claude_SQM_v868\web"
npm run dev
```

### Android Termux 실행
```bash
cd ~/sqm
uvicorn react_api.main:app --host 0.0.0.0 --port 8000
```

### 브라우저 접속
```
http://127.0.0.1:8000/docs  ← FastAPI
http://localhost:5173        ← React
```

---

## 6. 다음 세션 Claude Code 실행 프롬프트

> ⚠️ 오늘 밤 실행 범위: P0-1~P0-4 (4개 스텝 확실 완료 목표)
> P0-5~P0-6는 다음 세션에서 진행

```
현재 작업 기준 원본은 Claude_SQM_v868 이다.
MASTER_FINAL_v868_통합완성본.md 를 기준으로 작업한다.

[절대 실행 규칙]
- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기/삭제는 자동 승인된 것으로 간주할 것
- 테스트 실패 시 자동 수정 후 재시도할 것
- 중단 없이 끝까지 수행할 것
- 부분 완료 상태에서 절대 멈추지 말 것

[강제 테스트 규칙]
Pre-Test → 구현 → Post-Test → 실패시 수정 → Re-Test → 통과 → 다음 스텝
테스트 실패 상태에서 다음 스텝 진행 금지.

[현재 상태]
- Phase 1~7: 완료
- Phase 8: 진행 중 (telegram_bridge, run_master.bat 존재)
- P0~P3 로드맵: 수립 완료 (18개 스텝, 섹션 9 참조)

[이번 실행 목표 — P0-1 ~ P0-4 확실 완료]

STEP 1 (P0-2 먼저): inventory_read_service.py 누락 컬럼 확인
  작업:
    - SELECT 절에 아래 필드 포함 여부 확인
      arrival_date, con_return, free_time, warehouse,
      customs, initial_weight, outbound_weight
    - 누락 필드 있으면 JOIN inventory i 활용하여 추가
  완료 확인:
    python -c "from react_api.services.inventory_read_service import search_inventory; print('OK')"
    → OK 출력 확인

STEP 2 (P0-1): web/src/pages/InventoryPage.jsx 컬럼 토글 바
  작업:
    - 파일 상단에 COLUMN_DEFS 배열 정의
      { key, label, defaultVisible, align } 구조
    - useState로 visibleCols 상태 관리
    - 테이블 위에 가로 체크박스 줄 토글 바 UI 추가 (v864 스타일)
      스타일: 배경 #f8fafc, 패딩 8px, 체크박스+라벨 인라인 나열
    - <th>/<td> 렌더링 시 visibleCols[col.key] 조건부 적용
    - 기본 ON 컬럼:
        LOT NO, SAP NO, BL NO, PRODUCT, STATUS,
        Balance(Kg), NET(Kg), CONTAINER, MXBG,
        LOCATION, INVOICE NO, SHIP DATE,
        ARRIVAL, CON RETURN, FREE TIME
    - 기본 OFF 컬럼:
        WH, CUSTOMS, Inbound(Kg), Outbound(Kg),
        TONBAG UID, TONBAG NO, Weight(Kg), SAMPLE
  완료 확인:
    cd web && npm run build
    → 빌드 성공 확인

STEP 3 (P0-3): Return 조회 API
  신규 생성: react_api/routes/return_tab.py
    GET /api/return/list
      파라미터: lot_no(optional), page(default=1), page_size(default=50)
      소스: return_log 테이블 조회
      반환: { total, page, rows, generated_at }
    GET /api/return/statistics
      파라미터: start_date(optional), end_date(optional)
      반환: { total_count, this_month, by_reason, by_customer }
  신규 생성: react_api/services/return_read_service.py
    - engine_modules/inventory_modular/return_mixin.py의
      get_return_history(), get_return_statistics() 로직 포팅
    - engine_modules 직접 수정 금지 — 로직만 참조하여 새로 작성
  react_api/main.py 수정:
    - from react_api.routes.return_tab import router as return_router 추가
    - app.include_router(return_router) 추가
  완료 확인:
    python -m py_compile react_api/routes/return_tab.py && echo OK
    python -m py_compile react_api/services/return_read_service.py && echo OK
    python -c "from react_api.main import app; print('라우터 등록 OK')"

STEP 4 (P0-4): Return 소량반품 쓰기 API
  신규 생성: react_api/routes/return_write.py
    POST /api/return/single
      요청 바디: { lot_no, sub_lt, reason_code, note(optional) }
      사유코드 허용값: 품질불량, 수량오류, 고객요청, 파손, 기타 (고정 5개)
      응답: { success, message, return_id, data }
  신규 생성: react_api/services/return_write_service.py
    - engine_modules/inventory_modular/return_mixin.py의
      return_single_tonbag() 로직 래퍼로 작성
    - SQMInventoryEngineV3 인스턴스 경유 (inbound_write_service.py 패턴 참조)
    - 트랜잭션 보호 필수 (rollback 보장)
    - 반환: ReturnResult 성공/실패 표준 응답
  react_api/main.py 수정:
    - from react_api.routes.return_write import router as return_write_router 추가
    - app.include_router(return_write_router) 추가
  완료 확인:
    python -m py_compile react_api/routes/return_write.py && echo OK
    python -m py_compile react_api/services/return_write_service.py && echo OK
    python -c "from react_api.main import app; print('라우터 등록 OK')"

STEP 5: 전체 최종 검증
  pytest tests/ -v
  → 전체 통과 확인
  → 실패 항목 있으면 자동 수정 후 재실행
  → 전체 통과 후 종료

[절대 금지]
- rollback 없는 쓰기 API 구현
- fitz 직접 import (core/pdf_engine 경유)
- engine_modules 직접 수정
- 테스트 생략
- 중간에 멈춤
- P0-5, P0-6 진행 (오늘 범위 아님)
```

---

## 7. 금지 사항
- 테스트 생략
- 사용자 질문 발생
- 부분 완료 상태 종료
- rollback 없는 쓰기 API 구현
- fitz 직접 import
- engine_modules 직접 수정
- 예전 가정 구조만 믿고 수정 (반드시 실제 파일 확인 후 작업)
- 스텝 간 테스트 건너뜀

---

## 8. 최종 목표
```text
1. Phase 8 완전 완료
2. P0~P3 18개 스텝 완료 → tkinter 완전 대체
3. pytest 전체 통과
4. Telegram 원격 제어 가능
5. 무중단 밤샘 실행 가능
6. PC/Android 동일 코드 실행 가능
7. Return(반품) 탭 완전 구현
8. 다크/라이트 테마 전환
```

---

## 9. P0~P3 tkinter 완전 대체 로드맵 (18개 스텝)

> **실행 원칙:** Pre-Test → 구현 → Post-Test → 통과 → 다음 스텝
> **완료 기준:** 각 스텝은 브라우저에서 눈으로 확인 가능한 수준

### 🔴 P0 — 운영 필수 (지금 당장 없으면 업무 불가) | 예상 2~3세션

#### P0-1: Inventory 컬럼 토글 바 추가
```text
대상: web/src/pages/InventoryPage.jsx
작업:
  - COLUMN_DEFS 배열 정의 (key, label, defaultVisible, align)
  - useState로 visibleCols 상태 관리
  - 상단 가로 체크박스 줄 형태 토글 바 UI (v864 스타일)
  - 토글 상태에 따라 <th>/<td> 조건부 렌더링
기본 OFF: ARRIVAL, CON RETURN, FREE TIME, WH, CUSTOMS,
          Inbound(Kg), Outbound(Kg), ↓Avail개, ↓Resv개
기본 ON: LOT NO, SAP NO, BL NO, PRODUCT, STATUS, Balance(Kg),
         NET(Kg), CONTAINER, MXBG, LOCATION, INVOICE NO, SHIP DATE
완료 기준: 체크박스 ON/OFF → 컬럼 즉시 show/hide 확인
```

#### P0-2: Inventory 누락 컬럼 데이터 연결 확인
```text
대상: react_api/services/inventory_read_service.py
작업:
  - SELECT 절에 arrival_date, con_return, free_time, warehouse,
    customs, initial_weight, outbound_weight 포함 여부 확인
  - 누락 시 SELECT에 추가 (JOIN inventory i 이미 있음)
완료 기준: /api/inventory/search 응답 JSON에 해당 필드 존재 확인
```

#### P0-3: Return 백엔드 — DB 조회 API
```text
신규: react_api/routes/return_tab.py
  GET /api/return/list
  GET /api/return/statistics
신규: react_api/services/return_read_service.py
  - ReturnMixin.get_return_history() 로직 포팅
  - ReturnMixin.get_return_statistics() 로직 포팅
main.py에 return_router 등록
완료 기준: GET /api/return/list → 200 OK + rows 확인
```

#### P0-4: Return 백엔드 — 소량반품 쓰기 API
```text
신규: react_api/routes/return_write.py
  POST /api/return/single
신규: react_api/services/return_write_service.py
  - ReturnMixin.return_single_tonbag() 래퍼
  - 트랜잭션 보호 필수
  - 사유코드: 품질불량/수량오류/고객요청/파손/기타 (고정 5개)
완료 기준: 테스트 LOT POST → DB return_log 레코드 생성 확인
```

#### P0-5: Return 백엔드 — Excel 다량반품 쓰기 API
```text
대상: react_api/routes/return_write.py (P0-4에 추가)
  POST /api/return/bulk-excel  (preview 반환)
  POST /api/return/bulk-confirm (최종 실행)
  - features/parsers/return_inbound_parser.py 직접 재사용
완료 기준: 샘플 Excel 업로드 → preview JSON → confirm → DB 확인
```

#### P0-6: ReturnPage.jsx — 프론트 구현
```text
신규: web/src/pages/ReturnPage.jsx
  [상단] 요약 카드 4개: 총반품건수 / 이번달 / 처리완료 / 대기중
  [탭1] 반품 이력 테이블
  [탭2] 소량반품 입력 폼 (LOT 검색 → 톤백 선택 → 사유 → 실행)
  [탭3] Excel 다량반품 (업로드 → preview → 확인 → 실행결과)
신규: web/src/api/returnApi.js
App.jsx /return 라우트 추가
MenuBar.jsx 입고 메뉴 "반품(재입고)" 항목 추가
완료 기준: 3개 탭 전환, 소량반품 실행, Excel 업로드 흐름 확인
```

---

### 🟡 P1 — 핵심 기능 (1~2주 내 필요) | 예상 2세션

#### P1-1: D/O 후속 연결 API + UI
```text
신규: react_api/routes/do_update.py
  POST /api/do-update/apply
신규: web/src/components/DoUpdateModal.jsx
MenuBar 입고 메뉴 "D/O 후속 연결" 연결
```

#### P1-2: 톤백 위치 매핑 API + UI
```text
신규: react_api/routes/location_bulk.py
  POST /api/location/bulk-update
  POST /api/location/single-update
신규: web/src/components/LocationMappingModal.jsx
  탭1: 단건 입력 / 탭2: Excel 업로드
```

#### P1-3: Allocation 입력 Modal 강화
```text
신규: web/src/components/AllocationInputModal.jsx
  Excel 업로드 → 파싱 → preview → 예약 적용
MenuBar 출고 메뉴 "Allocation 입력" 연결
```

#### P1-4: 출고 이력 조회 페이지
```text
신규: web/src/pages/OutboundHistoryPage.jsx
  기간/고객사/LOT 필터 + 결과 테이블 + CSV 내보내기
  /api/advanced/outbound-history 연결 (백엔드 이미 있음)
App.jsx /outbound-history 라우트 추가
```

---

### 🟠 P2 — UX 완성도 | 예상 2세션

#### P2-1: 다크/라이트 테마 토글
```text
대상: web/src/App.jsx, web/src/index.css
  CSS variables 방식
  dark: #0b1322 배경 + #38bdf8 액센트
  light: #f0f5fc + #162040
  MenuBar 우측 🌙/☀️ 토글 버튼
```

#### P2-2: 제품 마스터 관리 Modal
```text
신규: react_api/routes/product_master.py
신규: web/src/components/ProductMasterModal.jsx
```

#### P2-3: 정합성 검증 결과 UI 강화
```text
신규: web/src/pages/IntegrityPage.jsx
  이슈 항목별 테이블 + 자동수복 버튼 + 내보내기
```

#### P2-4: LOT 상세 모달 컬럼 완성
```text
대상: web/src/components/LotDetailModal.jsx
  무게 보존 법칙 시각화
  이동 이력 탭 + 반품 이력 탭 + D/O 정보 섹션
```

---

### 🟢 P3 — 고급 기능 (완전 대체 마무리) | 예상 2~3세션

#### P3-1: 파싱 템플릿 관리 UI
```text
신규: react_api/routes/template_mgmt.py
신규: web/src/pages/TemplatePage.jsx
```

#### P3-2: 이메일 / Telegram 알림 설정 UI
```text
신규: react_api/routes/notification.py
신규: web/src/pages/SettingsPage.jsx
  탭1: Gmail SMTP / 탭2: Telegram / 탭3: 자동백업
```

#### P3-3: 반품 통계 대시보드
```text
신규: web/src/pages/ReturnStatsPage.jsx
  월별 트렌드 차트 (recharts) + 고객사별 파이차트 + Excel 내보내기
```

#### P3-4: 전체 통합 테스트 + pytest 검증
```text
신규 테스트:
  tests/stage_gates/test_return_api.py
  tests/stage_gates/test_do_update.py
  tests/stage_gates/test_location_bulk.py
최종: pytest tests/ -v 전체 통과 + npm run build 성공
```

---

### 📊 로드맵 일정 요약
| Phase | 스텝 수 | 예상 세션 | 완료 후 상태 |
|---|---|---|---|
| P0 | 6개 | 2~3세션 | 일상 업무 90% 가능 |
| P1 | 4개 | 2세션 | tkinter 대체 가능 수준 |
| P2 | 4개 | 2세션 | UX tkinter 동등 |
| P3 | 4개 | 2~3세션 | 완전 대체 완료 |
| **합계** | **18개** | **8~11세션** | 🎯 tkinter 완전 종료 |
