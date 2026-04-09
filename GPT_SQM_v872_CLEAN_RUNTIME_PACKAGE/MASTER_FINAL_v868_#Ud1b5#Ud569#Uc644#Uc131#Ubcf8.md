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
- **테스트**: 기동님(남기동)이 직접 수행 — Claude Code 자율 테스트 후 최종 확인은 기동님
- **v864 종료**: v868 완성 후 v864(tkinter) 완전 사용 중지 예정
- **전환 기준**: No.36 최종 통합 검증 통과 + 기동님 직접 테스트 통과 시점

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

## 📋 단계별 수정·디버깅 작업 상세표 (1~36번)

> 최종수정: 2026-04-04 | 전체 36개 항목 | 완료 8개 | 대기 28개

---

### 📊 전체 진행 현황 요약

| Phase | 목적 | 전체 | 완료 | 대기 | 진행률 | 완료 시 효과 |
|---|---|---|---|---|---|---|
| 🔴 P0 | 운영 필수 — 없으면 업무 불가 | 14개 | 0개 | 14개 | 0% | 일상 업무 90% 가능 |
| 🟡 P1 | 핵심 기능 — tkinter 대체 기준선 | 7개 | 0개 | 7개 | 0% | tkinter 대체 가능 수준 |
| 🟠 P2 | UX 완성 — 편의성 tkinter 동등 | 6개 | 0개 | 6개 | 0% | 운영 편의 완성 |
| 🟢 P3 | 고급 기능 — 완전 대체 마무리 | 9개 | 0개 | 9개 | 0% | tkinter 완전 종료 |
| **합계** | | **36개** | **0개** | **36개** | **0%** | 🎯 tkinter 완전 종료 |

---

## 🔴 P0 — 운영 필수 (14개 항목)

---

### No.1 — Inventory 누락 컬럼 SELECT 추가

| 항목 | 내용 |
|---|---|
| **순번** | 1 |
| **Phase/스텝** | P0-2 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `react_api/services/inventory_read_service.py` |
| **v864 대응 기능** | inventory_tab.py의 INVENTORY_COLUMNS 24개 컬럼 완전 표시 |
| **작업 목적** | 백엔드 SELECT에 누락된 7개 필드 추가 — 데이터는 DB에 있지만 API가 안 내려보내고 있음 |
| **구체적 작업** | SELECT 절에 `i.arrival_date`, `i.con_return`, `i.free_time`, `i.warehouse`, `i.customs`, `i.initial_weight`, `i.outbound_weight` 추가. JOIN inventory i 이미 존재하므로 SELECT 줄만 수정 |
| **주요 디버깅 포인트** | ① JOIN alias 불일치 (`i` vs `inv`) ② 필드명 오타 (`con_return` vs `container_return`) ③ NULL 처리 누락 시 프론트 렌더링 오류 |
| **완료 확인 명령** | `python -c "from react_api.services.inventory_read_service import search_inventory; print('OK')"` → OK 출력 확인 + `/api/inventory/search` 응답 JSON에 7개 필드 존재 확인 |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.2 — Inventory 컬럼 토글 바 UI

| 항목 | 내용 |
|---|---|
| **순번** | 2 |
| **Phase/스텝** | P0-1 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `web/src/pages/InventoryPage.jsx` |
| **v864 대응 기능** | inventory_tab.py의 ColumnToggleBar — 체크박스로 컬럼 숨기기/보이기 |
| **작업 목적** | 24개 컬럼 중 자주 쓰지 않는 컬럼을 숨겨 화면 가독성 향상. 매일 확인하는 ARRIVAL·CON RETURN·FREE TIME은 기본 ON |
| **구체적 작업** | ① 파일 상단 COLUMN_DEFS 배열 정의 `{key, label, defaultVisible, align}` ② `useState(초기값)` visibleCols 상태 생성 ③ 테이블 위 가로 체크박스 줄 UI 추가 (배경 #f8fafc, 패딩 8px) ④ `<th>/<td>` 렌더링 시 `visibleCols[col.key]` 조건 적용 |
| **기본 ON 컬럼** | LOT NO / SAP NO / BL NO / PRODUCT / STATUS / Balance(Kg) / NET(Kg) / CONTAINER / MXBG / LOCATION / INVOICE NO / SHIP DATE / ARRIVAL / CON RETURN / FREE TIME |
| **기본 OFF 컬럼** | WH / CUSTOMS / Inbound(Kg) / Outbound(Kg) / TONBAG UID / TONBAG NO / Weight(Kg) / SAMPLE |
| **주요 디버깅 포인트** | ① 체크박스 key 중복으로 React 경고 ② colSpan 숫자가 visibleCols 개수와 불일치 → "No results" 셀 레이아웃 깨짐 ③ useState 초기값에 모든 key 포함 안 하면 undefined 오류 |
| **완료 확인 명령** | `cd web && npm run build` 빌드 성공 + 브라우저에서 체크박스 ON/OFF 시 컬럼 즉시 show/hide 확인 |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.3 — Return 조회 API 라우터 생성

| 항목 | 내용 |
|---|---|
| **순번** | 3 |
| **Phase/스텝** | P0-3 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/routes/return_tab.py` |
| **v864 대응 기능** | return_mixin.py의 `get_return_history()` + return_statistics_dialog.py 조회 기능 |
| **작업 목적** | React 프론트에서 반품 이력·통계를 조회할 수 있도록 FastAPI 엔드포인트 제공 |
| **구체적 작업** | ① `GET /api/return/list` — return_history 테이블 페이지 조회 (lot_no 필터, page/page_size 파라미터) ② `GET /api/return/statistics` — 기간별 사유코드·고객사 집계 반환 ③ 응답 형식: `{total, page, rows, generated_at}` |
| **주요 디버깅 포인트** | ① return_history vs return_log 테이블명 확인 필수 ② fetchall 결과가 dict인지 tuple인지 확인 ③ page 계산 시 0페이지 요청 방지 (`ge=1` 강제) ④ SQL 인라인 주석 `--` 포함 금지 |
| **완료 확인 명령** | `python -m py_compile react_api/routes/return_tab.py && echo OK` + uvicorn 기동 후 `/api/return/list` → 200 OK 확인 |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.4 — Return 조회 서비스 레이어 생성

| 항목 | 내용 |
|---|---|
| **순번** | 4 |
| **Phase/스텝** | P0-3 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/services/return_read_service.py` |
| **v864 대응 기능** | return_mixin.py의 `get_return_history()` / `get_return_statistics()` |
| **작업 목적** | 라우터와 DB 로직 분리 — inbound_write_service.py 패턴과 동일하게 서비스 레이어 구성 |
| **구체적 작업** | ① `get_return_history(lot_no, page, page_size)` — return_history 테이블 SELECT + dict 변환 ② `get_return_statistics(start_date, end_date)` — 사유별/고객별/월별 GROUP BY 집계 ③ engine_modules 직접 수정 금지 — return_mixin.py 로직 참조하여 SQL 재작성 |
| **주요 디버깅 포인트** | ① return_mixin.py의 실제 테이블명·컬럼명과 일치 여부 ② SQL 인라인 주석 `--` 절대 금지 ③ 날짜 필터 빈 문자열 처리 (`''` vs `None`) ④ COALESCE 누락 시 None 값이 JSON 직렬화 오류 |
| **완료 확인 명령** | `python -m py_compile react_api/services/return_read_service.py && echo OK` |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.5 — main.py에 Return 조회 라우터 등록

| 항목 | 내용 |
|---|---|
| **순번** | 5 |
| **Phase/스텝** | P0-3 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `react_api/main.py` |
| **v864 대응 기능** | 없음 (신규 API 등록) |
| **작업 목적** | FastAPI 앱에 return_router 포함시켜 `/api/return/*` 경로 활성화 |
| **구체적 작업** | ① `from react_api.routes.return_tab import router as return_router` 추가 ② `app.include_router(return_router)` 추가 |
| **주요 디버깅 포인트** | ① import 경로 오타 (`return_tab` vs `return_tabs`) ② 기존 라우터와 prefix 충돌 여부 ③ 등록 순서 — 다른 include_router 아래에 추가 |
| **완료 확인 명령** | `python -c "from react_api.main import app; print([r.path for r in app.routes if 'return' in str(r.path)])"` → `/api/return/list` `/api/return/statistics` 출력 확인 |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.6 — Return 소량반품 쓰기 API 라우터 생성

| 항목 | 내용 |
|---|---|
| **순번** | 6 |
| **Phase/스텝** | P0-4 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/routes/return_write.py` |
| **v864 대응 기능** | ReturnReinboundDialog의 "반품 실행" 버튼 동작 + return_single_tonbag() 호출 |
| **작업 목적** | 창고 직원이 소량(1~2건) 반품 처리 시 LOT·sub_lt·사유코드 입력 후 DB에 반품 처리 |
| **구체적 작업** | ① `POST /api/return/single` 엔드포인트 정의 ② 요청 바디: `{lot_no, sub_lt, reason_code, note(optional)}` ③ 사유코드 허용값 검증: 품질불량·수량오류·고객요청·파손·기타 (이 외 값은 422 반환) ④ return_write_service.execute_single_return() 호출 ⑤ 응답: `{success, message, return_id, data}` |
| **주요 디버깅 포인트** | ① 사유코드 validation — Enum 또는 Literal 타입 사용 ② 트랜잭션 rollback 경로 누락 시 DB 반쪽 반영 ③ sub_lt 타입 — 정수인지 문자열인지 확인 ④ 존재하지 않는 LOT/sub_lt 요청 시 404 반환 |
| **완료 확인 명령** | `python -m py_compile react_api/routes/return_write.py && echo OK` |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.7 — Return 소량반품 쓰기 서비스 레이어 생성

| 항목 | 내용 |
|---|---|
| **순번** | 7 |
| **Phase/스텝** | P0-4 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/services/return_write_service.py` |
| **v864 대응 기능** | ReturnMixin.return_single_tonbag() + ReturnReinboundEngine.process() |
| **작업 목적** | 반품 처리 핵심 로직을 서비스 레이어로 분리 — engine_modules 직접 수정 없이 래퍼 패턴 적용 |
| **구체적 작업** | ① SQMInventoryEngineV3 인스턴스 생성 (inbound_write_service.py 패턴 참조) ② `engine.return_single_tonbag(lot_no, sub_lt, reason, note)` 호출 ③ 트랜잭션 보호 — try/except 로 rollback 보장 ④ ReturnResult 성공/실패 표준 응답 형식으로 변환 ⑤ 무게 보존 법칙 위반 시 RuntimeError 차단 |
| **주요 디버깅 포인트** | ① SQMInventoryEngineV3 생성자 파라미터 — DB 경로 `core/config.DB_PATH` 사용 ② rollback 누락 — except 블록에 `conn.rollback()` 필수 ③ ReturnResult 속성명 확인 (`.success` vs `.ok`) ④ 이미 반품된 tonbag 재반품 시 중복 방지 로직 |
| **완료 확인 명령** | `python -m py_compile react_api/services/return_write_service.py && echo OK` |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.8 — main.py에 Return 쓰기 라우터 등록

| 항목 | 내용 |
|---|---|
| **순번** | 8 |
| **Phase/스텝** | P0-4 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `react_api/main.py` |
| **v864 대응 기능** | 없음 (신규 API 등록) |
| **작업 목적** | `POST /api/return/single` 경로 활성화 |
| **구체적 작업** | ① `from react_api.routes.return_write import router as return_write_router` 추가 ② `app.include_router(return_write_router)` 추가 ③ No.5에서 등록한 return_router와 prefix 충돌 없는지 확인 (`/api/return` 공유 가능) |
| **주요 디버깅 포인트** | ① return_router(조회)와 return_write_router(쓰기) prefix 동일 `/api/return` — FastAPI는 경로별로 분리되므로 충돌 없음 ② 두 라우터 모두 같은 태그 `return` 사용 시 Swagger 문서 그룹화됨 |
| **완료 확인 명령** | `python -c "from react_api.main import app; print('OK')"` → OK 출력 + uvicorn 기동 후 `/api/docs`에서 POST /api/return/single 확인 |
| **상태** | ⬜ 미시작 |
| **완료 예정** | Claude Code 실행 후 |

---

### No.9 — Return Excel 다량반품 API 추가

| 항목 | 내용 |
|---|---|
| **순번** | 9 |
| **Phase/스텝** | P0-5 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `react_api/routes/return_write.py` (No.6 파일에 추가) |
| **v864 대응 기능** | `_on_return_inbound_upload()` + ReturnInboundParser + bulk_return_by_lot() |
| **작업 목적** | 월 3회 발생하는 다량 반품을 Excel 파일 업로드로 일괄 처리 — 2단계 (preview → confirm) |
| **구체적 작업** | ① `POST /api/return/bulk-excel` — Excel 파일 UploadFile 수신 → `features/parsers/return_inbound_parser.py` 호출 → 파싱 결과만 반환 (DB 저장 없음) → `{rows:[...], warnings:[...], total:N}` ② `POST /api/return/bulk-confirm` — bulk-excel preview 결과 rows를 받아 실제 DB 반품 처리 → 전체 성공 or 전체 rollback → `{success_count, fail_count, errors}` |
| **주요 디버깅 포인트** | ① `return_inbound_parser.py` import 경로 확인 (`features.parsers.return_inbound_parser`) ② **fitz 직접 import 절대 금지** — parser 내부가 fitz 쓰는지 확인, 쓰면 core/pdf_engine 경유로 수정 ③ UploadFile → 임시 파일 저장 → 파싱 → 임시 파일 삭제 순서 ④ bulk-confirm 전체 rollback 보장 — 중간 실패 시 성공한 건도 rollback |
| **완료 확인 명령** | 샘플 반품 Excel 업로드 → preview JSON 확인 → confirm POST → DB return_history 레코드 생성 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P0-5 세션 |

---

### No.10 — ReturnPage.jsx 프론트 페이지 생성

| 항목 | 내용 |
|---|---|
| **순번** | 10 |
| **Phase/스텝** | P0-6 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/pages/ReturnPage.jsx` |
| **v864 대응 기능** | cargo_overview_tab.py의 `_setup_return_tab()` + ReturnReinboundDialog + ReturnInboundPreviewDialog |
| **작업 목적** | 반품 업무 전체를 React 화면 한 곳에서 처리 — 이력 조회·소량반품·Excel 다량반품 3탭 구성 |
| **구체적 작업** | ① 상단 요약 카드 4개: 총반품건수 / 이번달 / 처리완료 / 대기중 ② 탭1 반품 이력: 컬럼(No./LOT NO/Sub LT/고객/Sale Ref/사유/중량/반품일/상태) + LOT NO·기간 필터 + GET /api/return/list 연결 ③ 탭2 소량반품: LOT NO 검색 → AVAILABLE 톤백 리스트 → 체크선택 → 사유 드롭다운(5개 고정) → 비고 입력 → 실행 → POST /api/return/single 연결 ④ 탭3 Excel 다량반품: 파일 업로드 → preview 테이블 → 경고표시 → 확인실행 → 결과표시 → POST /api/return/bulk-excel + /bulk-confirm 연결 |
| **주요 디버깅 포인트** | ① 탭 전환 useState 초기값 (`'history'` / `'single'` / `'excel'`) ② 소량반품 탭2에서 LOT 검색 후 결과 없을 때 빈 화면 처리 ③ Excel 업로드 시 FormData 생성 — `Content-Type` 헤더 직접 설정 금지 (브라우저 자동 설정) ④ preview 후 confirm 전에 페이지 이탈 시 데이터 초기화 처리 ⑤ 반품 성공 후 탭1 이력 자동 새로고침 |
| **완료 확인 명령** | 브라우저에서 3개 탭 전환 확인 + 소량반품 실행 후 DB 확인 + Excel 업로드 → preview → confirm 흐름 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P0-6 세션 |

---

### No.11 — returnApi.js API 클라이언트 생성

| 항목 | 내용 |
|---|---|
| **순번** | 11 |
| **Phase/스텝** | P0-6 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/api/returnApi.js` |
| **v864 대응 기능** | 없음 (React 신규) |
| **작업 목적** | ReturnPage.jsx에서 사용하는 모든 API 호출 함수 모음 — client.js 패턴 동일하게 작성 |
| **구체적 작업** | ① `getReturnList(params)` — GET /api/return/list ② `getReturnStatistics(params)` — GET /api/return/statistics ③ `postReturnSingle(body)` — POST /api/return/single ④ `postReturnBulkExcel(formData)` — POST /api/return/bulk-excel (FormData) ⑤ `postReturnBulkConfirm(rows)` — POST /api/return/bulk-confirm ⑥ 각 함수 에러 핸들링 — try/catch + 에러 메시지 표준화 |
| **주요 디버깅 포인트** | ① FormData 전송 시 `Content-Type: multipart/form-data` 헤더 직접 설정 금지 ② API base URL — `client.js`의 `fetchJson` 베이스 URL과 일치 확인 ③ bulk-excel 응답에 warnings 배열 없을 때 빈 배열 기본값 처리 |
| **완료 확인 명령** | 브라우저 Network 탭에서 각 API 호출 시 200 응답 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P0-6 세션 |

---

### No.12 — App.jsx에 /return 라우트 추가

| 항목 | 내용 |
|---|---|
| **순번** | 12 |
| **Phase/스텝** | P0-6 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `web/src/App.jsx` |
| **v864 대응 기능** | notebook.add(self.tab_return, text="🔄 Return") |
| **작업 목적** | React Router에 /return 경로 등록하여 ReturnPage 접근 가능하게 함 |
| **구체적 작업** | ① `import ReturnPage from './pages/ReturnPage'` 추가 ② `<Route path="/return" element={<ReturnPage />} />` 추가 |
| **주요 디버깅 포인트** | ① import 경로 대소문자 (`ReturnPage` vs `returnPage`) ② Routes 블록 안에 추가 (바깥에 놓으면 렌더링 안 됨) |
| **완료 확인 명령** | `npm run build` 성공 + 브라우저에서 `http://localhost:5173/return` 접속 시 ReturnPage 렌더링 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P0-6 세션 |

---

### No.13 — MenuBar.jsx에 반품 메뉴·네비 추가

| 항목 | 내용 |
|---|---|
| **순번** | 13 |
| **Phase/스텝** | P0-6 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `web/src/components/MenuBar.jsx` |
| **v864 대응 기능** | menu_registry.py의 `FILE_MENU_INBOUND_ITEMS` 중 "🔄 반품(재입고)" 항목 |
| **작업 목적** | 상단 메뉴에서 반품 탭으로 이동할 수 있게 입고 드롭다운에 항목 추가 |
| **구체적 작업** | ① menuData의 입고 items에 `{ label: '반품(재입고)', action: 'returnModal' }` 추가 ② navLinks 배열에 `{ to: '/return', label: 'Return' }` 추가 ③ App.jsx의 handleMenuAction에서 `case 'returnModal': navigate('/return')` 처리 |
| **주요 디버깅 포인트** | ① action key 중복 — 기존 action key와 겹치지 않게 ② NavLink activeStyle이 /return에서 정상 적용되는지 ③ App.jsx에서 useNavigate 없으면 navigate 호출 불가 |
| **완료 확인 명령** | 브라우저에서 상단 메뉴 입고 클릭 → "반품(재입고)" 항목 확인 → 클릭 시 /return 이동 확인 + 상단 네비바에 Return 탭 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P0-6 세션 |

---

### No.14 — P0 전체 pytest 최종 검증

| 항목 | 내용 |
|---|---|
| **순번** | 14 |
| **Phase/스텝** | P0 최종 검증 |
| **작업 유형** | 테스트 실행 |
| **대상 파일** | `tests/stage_gates/` 전체 + `web/` |
| **v864 대응 기능** | 없음 (품질 검증) |
| **작업 목적** | P0 전체 6개 스텝 완료 후 기존 13개 테스트가 모두 통과하는지 확인 — 신규 파일로 인한 사이드 이펙트 없음을 보장 |
| **구체적 작업** | ① `pytest tests/ -v` 실행 ② 실패 항목 발생 시 자동 수정 후 재실행 ③ `cd web && npm run build` 빌드 성공 확인 ④ 신규 파일 전체 `python -m py_compile` 통과 확인 |
| **주요 디버깅 포인트** | ① 신규 import로 인한 circular import ② return_tab.py / return_write.py가 engine_modules를 직접 import하면 테스트 격리 실패 ③ DB 경로 하드코딩 금지 — `core/config.DB_PATH` 사용 ④ npm build 실패 시 JSX 문법 오류 위치 확인 |
| **완료 확인 명령** | `pytest tests/ -v` → 전체 PASSED + `cd web && npm run build` → Build: success |
| **상태** | ⬜ 대기 |
| **담당 세션** | P0-6 세션 완료 후 |

---

## 🟡 P1 — 핵심 기능 (7개 항목)

---

### No.15 — D/O 후속 연결 백엔드 API

| 항목 | 내용 |
|---|---|
| **순번** | 15 |
| **Phase/스텝** | P1-1 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/routes/do_update.py` |
| **v864 대응 기능** | DoUpdateDialog — LOT 선택 후 D/O 번호·선적일·입항일 업데이트 |
| **작업 목적** | 입고 완료 후 D/O 정보를 나중에 연결하는 업무 흐름 지원 |
| **구체적 작업** | ① `POST /api/do-update/apply` ② 요청: `{lot_no, do_no, ship_date, arrival_date, con_return, free_time}` ③ inventory 테이블 UPDATE ④ audit_log 기록 |
| **주요 디버깅 포인트** | ① inventory 테이블 컬럼명 정확히 일치 ② 존재하지 않는 LOT 요청 시 404 반환 ③ 날짜 형식 `YYYY-MM-DD` 강제 |
| **완료 확인 명령** | `python -m py_compile react_api/routes/do_update.py && echo OK` + 실 LOT DB 업데이트 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P1-1 세션 |

---

### No.16 — D/O 연결 모달 컴포넌트

| 항목 | 내용 |
|---|---|
| **순번** | 16 |
| **Phase/스텝** | P1-1 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/components/DoUpdateModal.jsx` |
| **v864 대응 기능** | DoUpdateDialog 팝업 UI |
| **작업 목적** | MenuBar 입고 메뉴에서 D/O 후속 연결 클릭 시 열리는 모달 |
| **구체적 작업** | ① LOT NO 입력 + 검색 버튼 ② 검색 결과(현재 LOT 정보) 표시 ③ D/O 번호·선적일·입항일·반납일·FREE TIME 입력 폼 ④ 적용 버튼 → POST /api/do-update/apply → 성공 메시지 |
| **주요 디버깅 포인트** | ① Modal 열기/닫기 prop 패턴 — Modal.jsx 공통 컴포넌트 재사용 ② 날짜 입력 타입 `date` HTML input 사용 ③ 검색 전 적용 버튼 클릭 방지 (LOT 미선택 시 disable) |
| **완료 확인 명령** | 브라우저 Modal 열기 → LOT 검색 → 정보 입력 → 적용 → DB 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P1-1 세션 |

---

### No.17 — 톤백 위치 매핑 백엔드 API

| 항목 | 내용 |
|---|---|
| **순번** | 17 |
| **Phase/스텝** | P1-2 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/routes/location_bulk.py` |
| **v864 대응 기능** | TonbagLocationUpload + `_on_tonbag_location_upload()` |
| **작업 목적** | 광양 창고 랙 위치를 톤백별로 매핑 — 단건·Excel 일괄 두 방식 지원 |
| **구체적 작업** | ① `POST /api/location/single-update` — `{lot_no, sub_lt, location}` 단건 위치 변경 ② `POST /api/location/bulk-update` — Excel 업로드 → 파싱 → inventory_tonbag.location 일괄 UPDATE ③ validate_location_format() 호출하여 위치코드 형식 검증 ④ tonbag_move_log 테이블에 이동 이력 기록 |
| **주요 디버깅 포인트** | ① validate_location_format()은 gui → engine 레이어로 이동된 버전 사용 ② 존재하지 않는 sub_lt 요청 시 404 ③ Excel 파싱 헤더 자동 감지 — lot_no·sub_lt·location 컬럼명 alias 처리 |
| **완료 확인 명령** | `python -m py_compile react_api/routes/location_bulk.py && echo OK` + inventory_tonbag.location 업데이트 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P1-2 세션 |

---

### No.18 — 위치 매핑 모달 컴포넌트

| 항목 | 내용 |
|---|---|
| **순번** | 18 |
| **Phase/스텝** | P1-2 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/components/LocationMappingModal.jsx` |
| **v864 대응 기능** | TonbagLocationUpload 다이얼로그 UI |
| **작업 목적** | 창고 직원이 톤백을 새 랙 위치로 이동 후 화면에서 즉시 위치 업데이트 |
| **구체적 작업** | ① 탭1 단건 입력: LOT NO + Sub LT + 위치코드 입력 → POST /api/location/single-update ② 탭2 Excel 업로드: 파일 선택 → preview 테이블 → 일괄 적용 → POST /api/location/bulk-update ③ 위치코드 형식 오류 시 빨간 테두리 + 오류 메시지 표시 |
| **주요 디버깅 포인트** | ① 탭1에서 Sub LT는 숫자 입력 강제 (문자 입력 방지) ② Excel preview에서 오류 행 빨간색 하이라이트 ③ 적용 후 Inventory 페이지 자동 새로고침 트리거 |
| **완료 확인 명령** | 브라우저 단건·Excel 두 탭 동작 확인 + tonbag_move_log 레코드 생성 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P1-2 세션 |

---

### No.19 — Allocation 입력 모달 강화

| 항목 | 내용 |
|---|---|
| **순번** | 19 |
| **Phase/스텝** | P1-3 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/components/AllocationInputModal.jsx` |
| **v864 대응 기능** | AllocationDialog + allocation_parser.py v2.7.1 (6개 고객 양식 자동처리) |
| **작업 목적** | 고객사 Allocation Excel을 업로드하면 자동 파싱 후 예약 적용 |
| **구체적 작업** | ① Excel 업로드 → POST /api/files/upload (기존 API 활용) ② 파싱 결과 preview 테이블 표시 ③ AL-06 SALE_REF_CONFLICT 경고 표시 (동일 SALE REF 다른 고객) ④ LOT_MODE_DUP 경고 — 이미 예약된 LOT 스킵 후 진행 ⑤ 예약 적용 확인 → allocation_plan 레코드 생성 |
| **주요 디버깅 포인트** | ① allocation_parser.py 6개 양식 자동 선택 로직 확인 ② AL-06 에러 vs 경고 구분 처리 ③ LOT_MODE_DUP는 하드에러 아닌 경고로 처리 (스킵 후 계속) |
| **완료 확인 명령** | 샘플 Allocation Excel(1_AAA/2_Song) 업로드 → allocation_plan 레코드 생성 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P1-3 세션 |

---

### No.20 — 출고 이력 조회 페이지

| 항목 | 내용 |
|---|---|
| **순번** | 20 |
| **Phase/스텝** | P1-4 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/pages/OutboundHistoryPage.jsx` |
| **v864 대응 기능** | `_show_outbound_history()` + outbound_history 다이얼로그 |
| **작업 목적** | 출고 완료 건 전체 이력 조회 — 고객사·기간·LOT NO 필터 |
| **구체적 작업** | ① 기간 필터 (시작일~종료일) ② 고객사 드롭다운 ③ LOT NO 검색 ④ 결과 테이블: LOT NO / 고객 / 수량 / 출고일 / 상태 ⑤ CSV 내보내기 버튼 → GET /api/tools/export/csv 활용 ⑥ GET /api/advanced/outbound-history 연결 (백엔드 이미 존재) |
| **주요 디버깅 포인트** | ① /api/advanced/outbound-history 파라미터 형식 확인 ② 기간 필터 — 날짜 형식 `YYYY-MM-DD` 강제 ③ 대량 데이터 페이지네이션 처리 |
| **완료 확인 명령** | 브라우저 필터 동작 확인 + CSV 다운로드 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P1-4 세션 |

---

### No.21 — P1 전체 pytest 최종 검증

| 항목 | 내용 |
|---|---|
| **순번** | 21 |
| **Phase/스텝** | P1 최종 검증 |
| **작업 유형** | 테스트 실행 |
| **대상 파일** | `tests/stage_gates/` 전체 |
| **작업 목적** | P1 완료 후 전체 테스트 통과 확인 — 이 시점이 tkinter 대체 가능 판정 기준 |
| **구체적 작업** | ① `pytest tests/ -v` 전체 통과 ② `npm run build` 성공 ③ **기동님 직접 테스트**: D/O 연결·위치 매핑·Allocation 실측 통과 확인 |
| **주요 디버깅 포인트** | ① P1 신규 라우터 main.py 등록 누락 ② 컴포넌트 import 경로 오류 ③ 실 데이터 테스트 시 숨은 버그 발생 가능 — 별도 수정 세션 필요할 수 있음 |
| **완료 확인 명령** | `pytest tests/ -v` 전체 PASSED + 빌드 성공 + **기동님 직접 실측 통과** |
| **상태** | ⬜ 대기 |
| **담당 세션** | P1 전체 완료 후 |

---

## 🟠 P2 — UX 완성도 (6개 항목)

---

### No.22 — 다크/라이트 테마 토글

| 항목 | 내용 |
|---|---|
| **순번** | 22 |
| **Phase/스텝** | P2-1 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `web/src/index.css`, `web/src/App.jsx`, `web/src/components/MenuBar.jsx` |
| **v864 대응 기능** | theme_mixin.py + ThemeColors + tc() 함수 — 다크 `#0b1322`+`#38bdf8` / 라이트 `#f0f5fc`+`#162040` |
| **작업 목적** | 장시간 작업 시 눈의 피로 감소 — v864 Pro 팔레트 그대로 React에 적용 |
| **구체적 작업** | ① index.css에 CSS variables 정의: `--bg-primary`, `--bg-secondary`, `--text-primary`, `--accent`, `--border` ② 다크 팔레트: bg `#0b1322`, accent `#38bdf8` ③ 라이트 팔레트: bg `#f0f5fc`, accent `#162040` ④ App.jsx에 테마 상태 useState + body className 토글 ⑤ localStorage에 테마 저장 (새로고침 후 유지) ⑥ MenuBar 우측 🌙/☀️ 토글 버튼 |
| **주요 디버깅 포인트** | ① CSS var 미적용 컴포넌트 — 인라인 style에 하드코딩된 색상 있는 파일 전수 확인 ② localStorage는 React 상태 외부 — useEffect로 초기값 로드 ③ 테마 전환 시 flicker — `<html>` 태그에 먼저 class 적용 |
| **완료 확인 명령** | 🌙 클릭 → 전체 화면 다크 전환 확인 → 새로고침 후도 다크 유지 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P2-1 세션 |

---

### No.23 — 제품 마스터 관리 백엔드 API

| 항목 | 내용 |
|---|---|
| **순번** | 23 |
| **Phase/스텝** | P2-2 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/routes/product_master.py` |
| **v864 대응 기능** | ProductMasterDialog — 제품 등록·수정 |
| **작업 목적** | 리튬카보네이트 등 신규 제품 등록·기존 제품 수정을 React에서 처리 |
| **구체적 작업** | ① `GET /api/product/list` ② `POST /api/product/create` ③ `PUT /api/product/update/{id}` ④ product_master 테이블 CRUD ⑤ 제품명 중복 등록 방지 (unique 제약) |
| **주요 디버깅 포인트** | ① product_master 테이블명 실제 확인 ② unique 제약 위반 시 409 Conflict 반환 ③ 삭제는 실 운영 데이터 위험 — soft delete(is_active=0)로 처리 |
| **완료 확인 명령** | `python -m py_compile react_api/routes/product_master.py && echo OK` + CRUD 동작 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P2-2 세션 |

---

### No.24 — 제품 마스터 관리 모달 컴포넌트

| 항목 | 내용 |
|---|---|
| **순번** | 24 |
| **Phase/스텝** | P2-2 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/components/ProductMasterModal.jsx` |
| **v864 대응 기능** | ProductMasterDialog UI |
| **작업 목적** | 제품 목록 조회·신규 등록·수정을 모달 한 화면에서 처리 |
| **구체적 작업** | ① 상단: 제품 목록 테이블 (제품명 / SAP NO / 단위 / 상태) ② 하단: 신규 등록 폼 (제품명·SAP NO·단위·비고) ③ 행 클릭 시 수정 모드 전환 ④ 저장·취소 버튼 |
| **주요 디버깅 포인트** | ① 편집 중 다른 행 클릭 시 저장 여부 확인 다이얼로그 ② 제품명 중복 시 빨간 오류 메시지 표시 |
| **완료 확인 명령** | 브라우저 CRUD(등록·수정·soft delete) 전체 동작 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P2-2 세션 |

---

### No.25 — 정합성 검증 결과 상세 페이지

| 항목 | 내용 |
|---|---|
| **순번** | 25 |
| **Phase/스텝** | P2-3 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/pages/IntegrityPage.jsx` |
| **v864 대응 기능** | integrity_v760_dialog.py — 정합성 검증 시각화 다이얼로그 |
| **작업 목적** | 현재 alert()로만 표시되는 정합성 체크 결과를 상세 테이블로 시각화 |
| **구체적 작업** | ① GET /api/tools/integrity-check 호출 ② 이슈 항목별 테이블: LOT NO / 이슈 유형 / 상세 내용 / 심각도 ③ 자동 수복 버튼 (수복 가능 항목만 활성화) ④ 결과 CSV/Excel 내보내기 ⑤ 무게 보존 법칙 위반 항목 빨간색 하이라이트 |
| **주요 디버깅 포인트** | ① integrity-check API 응답 구조 확인 (이슈 배열 형식) ② 수복 후 페이지 자동 재조회 ③ 이슈 없을 때 "✅ 정합성 정상" 메시지 표시 |
| **완료 확인 명령** | 브라우저 이슈 목록 표시 + 수복 실행 + 재조회 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P2-3 세션 |

---

### No.26 — LOT 상세 모달 컬럼 완성

| 항목 | 내용 |
|---|---|
| **순번** | 26 |
| **Phase/스텝** | P2-4 |
| **작업 유형** | 기존 파일 수정 |
| **대상 파일** | `web/src/components/LotDetailModal.jsx` |
| **v864 대응 기능** | lot_detail_dialog.py — LOT 상세 팝업 + 탭 구성 |
| **작업 목적** | LOT 클릭 시 열리는 상세 모달에 v864 수준의 정보 모두 표시 |
| **구체적 작업** | ① 무게 보존 법칙 시각화: `initial = current + picked (±1kg)` 계산 바 표시 ② 탭1 기본정보 (기존) ③ 탭2 톤백 리스트 (상태별 색상 뱃지) ④ 탭3 이동 이력 (GET /api/tabs/move-log?lot_no=) ⑤ 탭4 반품 이력 (GET /api/return/list?lot_no=) ⑥ 탭5 D/O 정보 섹션 |
| **주요 디버깅 포인트** | ① 탭 추가로 기존 탭 레이아웃 깨짐 ② ±1kg 허용 오차 계산 — 소수점 처리 ③ 이동/반품 이력이 없을 때 빈 테이블 표시 |
| **완료 확인 명령** | 브라우저 LOT 클릭 → 5개 탭 전환 + 무게 계산 바 정상 표시 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P2-4 세션 |

---

### No.27 — P2 전체 pytest 최종 검증

| 항목 | 내용 |
|---|---|
| **순번** | 27 |
| **Phase/스텝** | P2 최종 검증 |
| **작업 유형** | 테스트 실행 |
| **대상 파일** | `tests/stage_gates/` 전체 |
| **작업 목적** | P2 완료 후 전체 테스트 통과 + 다크/라이트 테마 전환 확인 |
| **구체적 작업** | ① `pytest tests/ -v` 전체 통과 ② `npm run build` 성공 ③ 다크/라이트 전환 후 모든 페이지 렌더링 정상 확인 |
| **주요 디버깅 포인트** | ① CSS variable 미적용 컴포넌트 누락 ② 테마 전환 후 특정 페이지 흰색/검은색 잔상 (flicker) |
| **완료 확인 명령** | `pytest tests/ -v` 전체 PASSED + 빌드 성공 + 테마 전환 전체 페이지 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P2 전체 완료 후 |

---

## 🟢 P3 — 고급 기능 (9개 항목)

---

### No.28 — 파싱 템플릿 관리 백엔드 API

| 항목 | 내용 |
|---|---|
| **순번** | 28 |
| **Phase/스텝** | P3-1 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/routes/template_mgmt.py` |
| **v864 대응 기능** | InboundTemplateDialog — 고객사별 PDF/Excel 파싱 템플릿 관리 |
| **작업 목적** | 신규 고객사 추가 시 파싱 템플릿을 React에서 직접 등록·수정 |
| **구체적 작업** | ① `GET /api/templates/inbound/list` ② `POST /api/templates/inbound/create` ③ `PUT /api/templates/inbound/{id}` ④ `DELETE /api/templates/inbound/{id}` ⑤ 템플릿 JSON 직렬화 저장 |
| **주요 디버깅 포인트** | ① 템플릿 JSON 스키마 버전 관리 ② 삭제 시 해당 템플릿으로 파싱된 기존 LOT 연관 처리 ③ 고객사명 중복 방지 |
| **완료 확인 명령** | `python -m py_compile react_api/routes/template_mgmt.py && echo OK` + CRUD 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-1 세션 |

---

### No.29 — 파싱 템플릿 관리 UI 페이지

| 항목 | 내용 |
|---|---|
| **순번** | 29 |
| **Phase/스텝** | P3-1 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/pages/TemplatePage.jsx` |
| **v864 대응 기능** | InboundTemplateDialog UI |
| **작업 목적** | 고객사별 컬럼 매핑 설정을 화면에서 직접 관리 |
| **구체적 작업** | ① 고객사별 템플릿 목록 ② 컬럼 매핑 설정 (헤더명 → SQM 필드 매핑) ③ 테스트 파싱 버튼 (샘플 파일로 파싱 결과 미리보기) ④ 저장·삭제 |
| **주요 디버깅 포인트** | ① 컬럼 매핑 드래그 앤 드롭 구현 복잡도 ② 저장 후 파서에 즉시 반영되는지 확인 |
| **완료 확인 명령** | 브라우저 템플릿 CRUD 전체 동작 + 테스트 파싱 결과 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-1 세션 |

---

### No.30 — 이메일·Telegram 알림 설정 API

| 항목 | 내용 |
|---|---|
| **순번** | 30 |
| **Phase/스텝** | P3-2 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `react_api/routes/notification.py` |
| **v864 대응 기능** | EmailConfigDialog + Telegram bot 설정 (`@Claude_kdnbot`) |
| **작업 목적** | Gmail SMTP·Telegram 알림 설정을 React UI에서 관리 |
| **구체적 작업** | ① `GET/PUT /api/settings/email` — Gmail SMTP 설정 읽기/쓰기 ② `GET/PUT /api/settings/telegram` — Bot token·chat_id 설정 ③ `POST /api/settings/telegram/test` — 테스트 메시지 발송 ④ .env 파일 기반 설정 관리 |
| **주요 디버깅 포인트** | ① .env 파일 읽기/쓰기 권한 ② 비밀번호·토큰 응답 시 마스킹 (`****`) ③ Telegram bot token 유효성 검증 |
| **완료 확인 명령** | 테스트 Telegram 메시지 발송 성공 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-2 세션 |

---

### No.31 — 설정 페이지 UI

| 항목 | 내용 |
|---|---|
| **순번** | 31 |
| **Phase/스텝** | P3-2 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/pages/SettingsPage.jsx` |
| **v864 대응 기능** | SettingsDialog — 이메일·알림·백업 설정 |
| **작업 목적** | 시스템 설정 전체를 한 화면에서 관리 |
| **구체적 작업** | ① 탭1 Gmail SMTP: 서버·포트·계정·비밀번호 입력 + 테스트 발송 ② 탭2 Telegram: Bot token·chat_id + 테스트 발송 ③ 탭3 자동 백업: 백업 경로·주기 설정 ④ 비밀번호 입력 필드 마스킹 처리 |
| **주요 디버깅 포인트** | ① 비밀번호 표시/숨기기 토글 ② 저장 전 변경사항 있을 때 나가기 방지 ③ 테스트 발송 실패 시 오류 메시지 명확히 표시 |
| **완료 확인 명령** | 브라우저 3탭 설정 저장 + Telegram 테스트 발송 성공 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-2 세션 |

---

### No.32 — 반품 통계 대시보드 페이지

| 항목 | 내용 |
|---|---|
| **순번** | 32 |
| **Phase/스텝** | P3-3 |
| **작업 유형** | 신규 파일 생성 |
| **대상 파일** | `web/src/pages/ReturnStatsPage.jsx` |
| **v864 대응 기능** | ReturnStatisticsDialog — 4개 탭(사유별·LOT별·월별·고객별) 통계 |
| **작업 목적** | 반품 패턴 분석으로 공급망 품질 관리 지원 |
| **구체적 작업** | ① 월별 반품 트렌드 라인차트 (recharts LineChart) ② 고객사별 반품 비율 파이차트 (recharts PieChart) ③ 사유코드별 바차트 (recharts BarChart) ④ 기간 필터 (시작일~종료일) ⑤ Excel 내보내기 (openpyxl — 한국어 폰트 NanumGothic 적용) |
| **주요 디버깅 포인트** | ① recharts 데이터 형식 `[{name, value}]` 정확히 맞춰야 렌더링 ② 데이터 없을 때 빈 차트 대신 "데이터 없음" 메시지 ③ Excel 내보내기 한국어 깨짐 — 폰트 경로 확인 |
| **완료 확인 명령** | 브라우저 차트 3종 렌더링 확인 + Excel 다운로드 한국어 정상 표시 확인 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-3 세션 |

---

### No.33 — Return API 자동화 테스트

| 항목 | 내용 |
|---|---|
| **순번** | 33 |
| **Phase/스텝** | P3-4 |
| **작업 유형** | 신규 테스트 파일 생성 |
| **대상 파일** | `tests/stage_gates/test_return_api.py` |
| **v864 대응 기능** | 없음 (신규 테스트) |
| **작업 목적** | Return API 전체 (list·statistics·single·bulk) pytest 자동 검증 |
| **구체적 작업** | ① GET /api/return/list 200 응답 + rows 구조 검증 ② GET /api/return/statistics 200 응답 + 집계 구조 검증 ③ POST /api/return/single 성공 케이스 + 실패 케이스(잘못된 사유코드) ④ POST /api/return/bulk-excel preview 응답 구조 검증 ⑤ 테스트 DB 격리 — 실 DB 오염 방지 |
| **주요 디버깅 포인트** | ① 테스트 DB 격리 — fixtures로 임시 DB 생성 후 teardown ② 반품 처리 후 rollback 검증 — 원래 상태로 복원 확인 ③ 존재하지 않는 LOT 테스트 케이스 |
| **완료 확인 명령** | `pytest tests/stage_gates/test_return_api.py -v` → 전체 PASSED |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-4 세션 |

---

### No.34 — D/O 연결 API 자동화 테스트

| 항목 | 내용 |
|---|---|
| **순번** | 34 |
| **Phase/스텝** | P3-4 |
| **작업 유형** | 신규 테스트 파일 생성 |
| **대상 파일** | `tests/stage_gates/test_do_update.py` |
| **v864 대응 기능** | 없음 (신규 테스트) |
| **작업 목적** | D/O 후속 연결 API 자동 검증 |
| **구체적 작업** | ① POST /api/do-update/apply 성공 케이스 ② 존재하지 않는 LOT 요청 → 404 검증 ③ 날짜 형식 오류 → 422 검증 ④ 업데이트 후 DB 값 검증 + teardown에서 원복 |
| **주요 디버깅 포인트** | ① 테스트 후 DB 원복 필수 — 실 운영 데이터 오염 방지 ② 날짜 형식 `YYYY-MM-DD` 외 입력 시 정확한 에러 반환 |
| **완료 확인 명령** | `pytest tests/stage_gates/test_do_update.py -v` → 전체 PASSED |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-4 세션 |

---

### No.35 — 위치 매핑 API 자동화 테스트

| 항목 | 내용 |
|---|---|
| **순번** | 35 |
| **Phase/스텝** | P3-4 |
| **작업 유형** | 신규 테스트 파일 생성 |
| **대상 파일** | `tests/stage_gates/test_location_bulk.py` |
| **v864 대응 기능** | 없음 (신규 테스트) |
| **작업 목적** | 톤백 위치 매핑 API 자동 검증 |
| **구체적 작업** | ① POST /api/location/single-update 성공 케이스 ② 잘못된 위치코드 형식 → 422 검증 ③ 존재하지 않는 sub_lt → 404 검증 ④ bulk-update Excel 파싱 결과 검증 ⑤ tonbag_move_log 레코드 생성 확인 |
| **주요 디버깅 포인트** | ① 위치코드 형식 — validate_location_format() 규칙 확인 ② bulk 처리 중 일부 실패 시 전체 rollback 검증 |
| **완료 확인 명령** | `pytest tests/stage_gates/test_location_bulk.py -v` → 전체 PASSED |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3-4 세션 |

---

### No.36 — 최종 통합 검증 (tkinter 완전 종료 판정)

| 항목 | 내용 |
|---|---|
| **순번** | 36 |
| **Phase/스텝** | 최종 완료 |
| **작업 유형** | 통합 테스트 + 실측 |
| **대상 파일** | 전체 시스템 |
| **v864 대응 기능** | v864 전체 기능 동등 수준 |
| **작업 목적** | tkinter 완전 종료 공식 판정 — React UI가 v864를 100% 대체함을 확인 |
| **구체적 작업** | ① `pytest tests/ -v` 전체 PASSED (기존 13개 + 신규 3개 = 16개 이상) ② `cd web && npm run build` 빌드 성공 ③ 광양 PC 실 데이터 전체 기능 점검: 입고·출고·반품·위치매핑·Allocation·D/O연결·정합성검증 ④ 다크/라이트 테마 전환 전 페이지 정상 ⑤ Android Termux에서 동일 실행 확인 ⑥ Telegram 원격 제어 정상 동작 |
| **주요 디버깅 포인트** | ① 전체 import 체인 — circular import 최종 확인 ② DB 경로 — `core/config.DB_PATH` 모든 파일 통일 ③ 포트 충돌 — 8000(FastAPI) / 5173(React dev) ④ 실 데이터 테스트 중 발견되는 edge case |
| **완료 확인 명령** | `pytest tests/ -v` 전체 PASSED + `npm run build` 성공 + **기동님 직접 전 기능 실측 통과** → v864 사용 중지 선언 |
| **상태** | ⬜ 대기 |
| **담당 세션** | P3 전체 완료 후 |

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

> ⚠️ 현재 진행 범위: P0-S1 ~ P0-S15 (P0 전체 15단계)
> 세부 내용: 섹션 9 "P0~P4 tkinter 완전 대체 로드맵" 참조
> 작업 완료 시 해당 단계 상태 ⬜ → ✅ 로 MD 파일 직접 업데이트

```
현재 작업 기준 원본은 Claude_SQM_v868 이다.
MASTER_FINAL_v868_통합완성본.md 를 기준으로 작업한다.
세부 작업 내용은 섹션 9의 각 단계를 참조한다.
완료 시 해당 단계 상태를 ⬜ → ✅ 로 MD 파일에 직접 업데이트할 것.

[자동 연속 실행 규칙 — 절대 준수]
- 한 단계 완료 시 즉시 다음 단계 시작 — 절대 멈추지 말 것
- Phase 완료 시 즉시 다음 Phase 시작:
  P0 완료 → 즉시 P1-S1 시작
  P1 완료 → 즉시 P2-S1 시작
  P2 완료 → 즉시 P3-S1 시작
  P3 완료 → 즉시 P4-S1 시작
  P4 완료 → Telegram "🎯 전체 49단계 완료!" 발송
- 사용자 응답 대기(input()) 절대 금지
- 작업 완료 보고 후 멈추지 말고 즉시 다음 단계 진행
- 각 단계 완료 시 반드시 실행:
  python -c "open('logs/completed_steps.txt','a').write('단계ID_PASS\n')"
  python scripts/telegram_notify.py "✅ [단계ID] 완료"

[절대 실행 규칙]
- 절대 사용자에게 불필요한 질문하지 말 것
- 모든 선택은 코드와 로그를 근거로 스스로 판단
- 막히면 스스로 해결 후 진행
- "어떤 순서로 할까요?" "확인해드릴까요?" 같은 모호한 질문 절대 금지
- 사용자는 컴퓨터 앞에 없음 — 간단한 질문도 최대한 스스로 판단

[Telegram 사용 규칙]
✅ 허용 — Telegram으로 보내도 되는 것:
  - 단계 완료 알림: "✅ [P1-S1] 완료"
  - 5분 정기 진행률 보고
  - 오류 발생 즉시 알림
  - 꼭 필요한 선택지 (1/2 또는 1/2/3 형식):
    예) "파일이 이미 존재합니다\n1. 덮어쓰기\n2. 건너뛰기\n1 또는 2 입력"
  - 👤 기동님 직접 확인 단계 알림

❌ 금지 — Telegram으로 보내면 안 되는 것:
  - "어떤 방법으로 진행할까요?" 같은 열린 질문
  - 작업 방향에 대한 의견 요청
  - 불필요한 확인 요청

[기동님 Telegram 응답 방법]
  1, 2, 3 → 선택지 응답 (Bridge가 자동으로 Claude에 전달)
  y / n   → 예/아니오 응답
  자유 문장 → 직접 지시
- 파일 덮어쓰기/삭제 자동 승인
- 테스트 실패 시 원인 분석 → 즉시 수정 → 재검증
- 중단 없이 끝까지 수행
- 이전 단계 PASS 없이 다음 단계 진행 금지
- mock만 통과시키고 실제 engine 호출 생략 금지 ← GPT 실전 경험
- rollback 확인 없이 write API 완료 처리 금지 ← GPT 실전 경험

[단계 완료 기록 규칙 — 반드시 준수]
각 단계 완료 시 아래 두 명령을 반드시 실행할 것:

  python -c "open('logs/completed_steps.txt','a').write('단계ID_단계명_PASS\n')"
  python scripts/telegram_notify.py "✅ [단계ID] 단계명 완료"

예시:
  python -c "open('logs/completed_steps.txt','a').write('P0-S1_Recon_PASS\n')"
  python scripts/telegram_notify.py "✅ [P0-S1] Recon 완료 → P0-S2 진행"

이 기록이 있어야 Telegram 진행률이 업데이트됨. 절대 생략 금지.

[Phase 자동 연속 진행 규칙 — 반드시 준수]
각 Phase 완료 시 멈추지 말고 즉시 다음 Phase를 시작할 것:
  P0 전체 완료 → 즉시 P1-S1 시작
  P1 전체 완료 → 즉시 P2-S1 시작
  P2 전체 완료 → 즉시 P3-S1 시작
  P3 전체 완료 → 즉시 P4-S1 시작
  P4 전체 완료 → "🎯 전체 49단계 완료!" Telegram 발송 후 종료

단, 👤 기동님 직접 확인 단계(P0-S14, P1-S11, P2-S6, P4-S9)에서만 멈추고 대기할 것:
  python scripts/telegram_notify.py "👤 [단계ID] 기동님 직접 확인 필요. Telegram에 y 입력해주세요"
  python scripts/wait_confirm.py "단계ID"

wait_confirm.py 가 없으면 30초 대기 후 자동 진행:
  python -c "import time; time.sleep(30)"

사용자 입력 대기(input()) 절대 금지 — 컴퓨터 앞에 아무도 없음.

[강제 테스트 게이트]
Pre-Test → 구현/수정 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계

[현재 상태]
- Phase 1~7 (기존 v868 구현): 완료
- P0-S1 ~ P0-S15: ⬜ 전체 미시작

[이번 실행 목표 — P0~P4 전체 49단계 완전 자동 실행]
섹션 9의 단계표 순서대로 P0-S1부터 P4-S9까지 멈추지 말고 실행할 것.
각 Phase 완료 후 즉시 다음 Phase 시작.
👤 기동님 확인 단계(P0-S14, P1-S11, P2-S6, P4-S9)에서만 wait_confirm.py 실행 후 대기.
각 단계 완료 시 반드시 완료 확인 명령 실행 후 다음 단계 진행.

핵심 주의 사항 (GPT 실전 경험):
  1. P0-S2: get_db() → get_engine() 전환 — 7개 파일 필수
  2. P0-S10: npm build rollup native 실패 해결 후 빌드 성공 확인
  3. P0-S14: 👤 기동님 직접 확인 단계 — Telegram 알림 발송 후 대기

[P0-S14 Telegram 알림 문구]
"👤 P0-S14: 기동님 직접 확인 필요
 브라우저에서 아래 항목 확인해 주세요:
 ① Inventory 컬럼 토글 ON/OFF 동작
 ② ARRIVAL/CON RETURN/FREE TIME 데이터 표시
 ③ Return 탭 3개 탭 전환
 ④ 소량반품 실행 후 DB 확인
 확인 완료 시 y 입력해 주세요"

[절대 금지]
- rollback 없는 쓰기 API
- fitz 직접 import
- engine_modules 직접 수정
- 테스트 생략
- 중간에 멈춤
- P1 이후 진행 (이번 세션 범위 아님)
```

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
1. 36단계 전체 완료 → tkinter(v864) 완전 대체
2. 각 단계 완료 후 기동님(남기동) 직접 테스트 통과
3. pytest 전체 통과 (자동 검증)
4. Telegram 원격 제어 가능
5. PC/Android 동일 코드 실행 가능
6. Return(반품) 탭 완전 구현 (소량 + Excel 다량)
7. 다크/라이트 테마 전환
8. No.36 최종 통합 검증 통과
   → v864(tkinter) 완전 사용 중지
   → v868(React) 단독 운영 시작
```

### v864 → v868 전환 체크리스트 (기동님 직접 확인)
```text
□ No.14 완료 후: Inventory 컬럼 토글 + Return 탭 동작 확인
□ No.21 완료 후: D/O 연결 + 위치 매핑 + Allocation 동작 확인
□ No.27 완료 후: 다크/라이트 테마 + LOT 상세 모달 확인
□ No.36 완료 후: 전체 기능 최종 실측 → v864 사용 중지 선언
```

---

## 9. P0~P4 tkinter 완전 대체 로드맵 (49단계 통합)

> **기준:** Ruby(Claude) 전수검사 + GPT(OpenAI) 실전 경험 통합본
> **실행 원칙:** Pre-Test → 구현 → Post-Test → 통과 → 다음 단계
> **이전 단계 PASS 없이 다음 진행 절대 금지**
> **상태 범례:** ✅ 완료 / 🔄 진행중 / ⬜ 미시작

---

### 🤖 Claude Code 자율 실행 vs 👤 기동님 직접 확인 구분표

| 구분 | 단계 | 해당 단계 |
|---|---|---|
| 🤖 Claude Code 자율 | 44단계 | P0-S1~S13, P0-S15, P1-S1~S10, P1-S12, P2-S1~S5, P3-S1~S7, P4-S1~S8 |
| 👤 기동님 직접 확인 | **5단계** | **P0-S14, P1-S11, P2-S6, P4-S9(최종)** |
| 🔔 Telegram 알림 후 대기 | 4단계 | P0-S14, P1-S11, P2-S6, P4-S9 |

> Claude Code는 👤 단계 도달 시 **Telegram으로 기동님께 알림 발송 후 대기**
> 기동님 확인 완료 후 다음 단계 진행

---

### 🔴 P0 — 기반 복구 + 운영 필수 | 15단계

| 단계 | 실행 | 핵심 작업 | 대상 파일 | 상태 |
|---|---|---|---|---|
| P0-S1 | 🤖 | Recon — v868 실제 구조 전수 조사 | 전체 폴더 | ⬜ |
| P0-S2 | 🤖 | get_db() → get_engine() 7개 파일 전환 ⚠️GPT실전 | `db.py` + 라우트3개 + 서비스2개 + `write_models.py` | ⬜ |
| P0-S3 | 🤖 | Inventory 누락 7개 컬럼 SELECT 추가 | `inventory_read_service.py` | ⬜ |
| P0-S4 | 🤖 | Inventory 컬럼 토글 바 UI (v864 스타일) | `InventoryPage.jsx` | ⬜ |
| P0-S5 | 🤖 | LOT 상세 모달 API 연결 강화 | `LotDetailModal.jsx` | ⬜ |
| P0-S6 | 🤖 | Return 조회 API (list + statistics) | `return_tab.py` + `return_read_service.py` + `main.py` | ⬜ |
| P0-S7 | 🤖 | Return 소량반품 쓰기 API + rollback 보호 | `return_write.py` + `return_write_service.py` + `main.py` | ⬜ |
| P0-S8 | 🤖 | Return Excel 다량반품 API (preview+confirm) | `return_write.py` (수정) | ⬜ |
| P0-S9 | 🤖 | Return 탭 프론트 (3탭 + API 클라이언트) | `ReturnPage.jsx` + `returnApi.js` + `App.jsx` + `MenuBar.jsx` | ⬜ |
| P0-S10 | 🤖 | npm build 실패 해결 ⚠️GPT실전 (rollup native) | `package.json` + `vite.config.js` | ⬜ |
| P0-S11 | 🤖 | Telegram Bridge y/n/1/2/3 동작 검증 | `telegram_bridge.py` | ⬜ |
| P0-S12 | 🤖 | run_master.bat / run_master.ps1 전체 기동 검증 | `run_master.bat` + `run_master.ps1` | ⬜ |
| P0-S13 | 🤖 | pytest 전체 통과 + npm build 성공 | `tests/` 전체 | ⬜ |
| **P0-S14** | **👤** | **기동님 직접 테스트 — P0 판정** 🔔Telegram알림 | 브라우저 + 광양 PC | ⬜ |
| P0-S15 | 🤖 | P0 완료 보고서 + MD 상태 ✅ 업데이트 | `logs/P0_완료보고서.md` | ⬜ |

> ⚠️GPT실전 = GPT가 실전에서 직접 겪은 문제 — 반드시 선처리 필요

> 📌 **각 단계 완료 시 반드시 실행:**
> `echo P0-SX_단계명_PASS >> logs\completed_steps.txt`
> `python scripts\telegram_notify.py "✅ [P0-SX] 완료"`

---

### 🟡 P1 — 백엔드 안정화 + 핵심 기능 | 12단계

| 단계 | 실행 | 핵심 작업 | 대상 파일 | 상태 |
|---|---|---|---|---|
| P1-S1 | 🤖 | 트랜잭션 경계 보강 — rollback 패턴 전 파일 통일 | `react_api/services/` 전체 | ⬜ |
| P1-S2 | 🤖 | 서비스 레이어 분리 — do_update + location_bulk 신규 | `do_update_service.py` + `location_bulk_service.py` | ⬜ |
| P1-S3 | 🤖 | 예외 처리 표준화 — HTTP 에러 코드 + 한국어 메시지 | `react_api/routes/` 전체 | ⬜ |
| P1-S4 | 🤖 | 로그 체계 완성 — logger + audit_log 기록 | `config_logging.py` + 신규 파일 전체 | ⬜ |
| P1-S5 | 🤖 | 정합성 검증 UI — IntegrityPage.jsx 시각화 | `tools.py` + `IntegrityPage.jsx` (신규) | ⬜ |
| P1-S6 | 🤖 | API 응답 스키마 표준화 — StandardResponse 통일 | `react_api/schemas/common.py` | ⬜ |
| P1-S7 | 🤖 | D/O 연결 + 위치 매핑 API + Modal | `do_update.py` + `location_bulk.py` + 2개 Modal | ⬜ |
| P1-S8 | 🤖 | Allocation 입력 + 출고 이력 조회 | `AllocationInputModal.jsx` + `OutboundHistoryPage.jsx` | ⬜ |
| P1-S9 | 🤖 | N+1 쿼리 최적화 — bulk IN/GROUP BY 전환 | `inventory_read_service.py` + 탭 API | ⬜ |
| P1-S10 | 🤖 | pytest P1 전체 통과 + npm build 성공 | `tests/` 전체 | ⬜ |
| **P1-S11** | **👤** | **기동님 직접 테스트 — P1 판정** 🔔Telegram알림 | 브라우저 + 광양 PC | ⬜ |
| P1-S12 | 🤖 | P1 완료 보고서 + MD 상태 ✅ 업데이트 | `logs/P1_완료보고서.md` | ⬜ |

> 📌 **P1-S11 완료 = tkinter 대체 가능 공식 판정**

---

### 🟠 P2 — 테스트 자동화 + 다크테마 | 6단계

| 단계 | 실행 | 핵심 작업 | 대상 파일 | 상태 |
|---|---|---|---|---|
| P2-S1 | 🤖 | pytest 자동화 — Return/D.O/위치매핑 테스트 신규 | `test_return_api.py` + `test_do_update.py` + `test_location_bulk.py` | ⬜ |
| P2-S2 | 🤖 | rollback 테스트 자동화 — 의도적 실패 시나리오 | `tests/` 신규 | ⬜ |
| P2-S3 | 🤖 | 정합성 자동 테스트 — 무게 보존 법칙 검증 | `tests/` 신규 | ⬜ |
| P2-S4 | 🤖 | 스모크 테스트 + `run_smoke_test.bat` | `run_smoke_test.bat` (신규) | ⬜ |
| P2-S5 | 🤖 | 다크/라이트 테마 토글 (v864 Pro 팔레트) | `index.css` + `App.jsx` + `MenuBar.jsx` | ⬜ |
| **P2-S6** | **👤** | **기동님 직접 테스트 — P2 판정** 🔔Telegram알림 | 브라우저 전체 | ⬜ |

---

### 🟢 P3 — 운영 자동화 + 무중단 체계 | 7단계

| 단계 | 실행 | 핵심 작업 | 대상 파일 | 상태 |
|---|---|---|---|---|
| P3-S1 | 🤖 | Claude Code 프롬프트 최적화 — 단계별 파일 정리 | `prompts/` 폴더 | ⬜ |
| P3-S2 | 🤖 | Telegram Bridge 고도화 — 단계완료 자동 알림 + 에러 즉시 알림 | `telegram_bridge.py` | ⬜ |
| P3-S3 | 🤖 | run_master 완전 자동화 — 사전점검→pytest→FastAPI→빌드→Bridge 순서 | `run_master.bat` + `run_master.ps1` | ⬜ |
| P3-S4 | 🤖 | 자동 보고서 생성 — 단계별 실행 로그 + MD 자동 업데이트 | `scripts/auto_report.py` (신규) | ⬜ |
| P3-S5 | 🤖 | 자동 수복 체계 — npm build / pytest 실패 자동 진단 | `scripts/auto_repair.py` (신규) | ⬜ |
| P3-S6 | 🤖 | 작업 큐 관리 — AUTO_TASKS_MANIFEST.md 기반 자동 실행 | `scripts/queue_runner.py` (신규) | ⬜ |
| P3-S7 | 🤖 | AI 로그 분석 — 반복 오류 패턴 조기 발견 | `scripts/log_analyzer.py` (신규) | ⬜ |

---

### 🔵 P4 — UI 완성 + 반응형 + 최종 판정 | 9단계

| 단계 | 실행 | 핵심 작업 | 대상 파일 | 상태 |
|---|---|---|---|---|
| P4-S1 | 🤖 | 메뉴 체계 완성 — v864 menu_registry 수준 재현 | `MenuBar.jsx` | ⬜ |
| P4-S2 | 🤖 | LOT 상세 모달 완성 — 무게법칙 + 5탭 | `LotDetailModal.jsx` | ⬜ |
| P4-S3 | 🤖 | 입고 모달 완성 — PDF/Excel 파싱 + preview | `InboundModal.jsx` | ⬜ |
| P4-S4 | 🤖 | 출고 모달 완성 — 즉시출고 + Allocation + 취소 | `OutboundModal.jsx` | ⬜ |
| P4-S5 | 🤖 | 탭 페이지 완성 — 기본구현 8개 탭 필터+정렬+모달 연결 | `TonbagPage.jsx` 외 7개 | ⬜ |
| P4-S6 | 🤖 | 상태 UI + 에러 UI — Loading/Error/Empty 표준화 | 공통 컴포넌트 | ⬜ |
| P4-S7 | 🤖 | Dashboard + 반품 통계 완성 — recharts 차트 3종 | `DashboardPage.jsx` + `ReturnStatsPage.jsx` | ⬜ |
| P4-S8 | 🤖 | 반응형 + 설정 페이지 — Android Termux 동일 표시 | `SettingsPage.jsx` + 전체 CSS | ⬜ |
| **P4-S9** | **👤** | **기동님 최종 실측 — v864 완전 종료 판정** 🔔Telegram알림 | 전체 시스템 | ⬜ |

> 📌 **P4-S9 완료 = v864(tkinter) 완전 사용 중지 공식 선언** 🎯

---

### 📊 49단계 전체 일정 요약

| Phase | 단계 범위 | 단계 수 | 🤖자율 | 👤직접 | 예상 세션 | 완료 효과 |
|---|---|---|---|---|---|---|
| 🔴 P0 | P0-S1 ~ S15 | 15단계 | 14 | 1 | 2~3세션 | 일상 업무 90% 가능 |
| 🟡 P1 | P1-S1 ~ S12 | 12단계 | 11 | 1 | 3세션 | tkinter 대체 가능 선언 |
| 🟠 P2 | P2-S1 ~ S6 | 6단계 | 5 | 1 | 2세션 | 테스트 자동화 완성 |
| 🟢 P3 | P3-S1 ~ S7 | 7단계 | 7 | 0 | 2세션 | 무중단 운영 자동화 |
| 🔵 P4 | P4-S1 ~ S9 | 9단계 | 8 | 1 | 3세션 | **tkinter 완전 종료** |
| **합계** | | **49단계** | **45** | **4** | **12~13세션** | 🎯 **v864 완전 종료** |

---

### 🔔 Telegram 알림 발송 기준 (Claude Code → 기동님)

```
단계 완료 시  : "[단계명] ✅ 완료 — 다음 단계 자동 진행합니다"
에러 발생 시  : "[단계명] ❌ 오류 발생 — [오류 내용 300자] — 자동 수정 시도 중"
👤 단계 도달  : "[단계명] 👤 기동님 직접 확인 필요 — 브라우저 접속해 주세요"
전체 완료 시  : "🎯 v864 완전 종료 판정 대기 — 최종 실측 부탁드립니다"
```
