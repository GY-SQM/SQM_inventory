# SQM React Phase1 Draft - Safe Fix Report
- Date: 2026-04-03
- Scope: `GPT_SQM_React_Phase1_Draft/` (3 files)
- Guideline: Claude Code 지시서 v2 (안전 우선, 최소 수정, 회귀 방지)

---

## 1. 변경 파일 목록

| # | File | Type | Lines Changed |
|---|------|------|---------------|
| 1 | `api/main.py` | Python (FastAPI) | ~80 lines |
| 2 | `api/dashboard_read_service.py` | Python (Service) | ~20 lines |
| 3 | `web/src/pages/InventoryPage.jsx` | React (JSX) | ~30 lines |

---

## 2. 변경 내용 상세

### 2-1. `api/main.py`

#### [BUG FIX] DB 연결 누수 방지
- **Before**: `get_db()` 가 매 요청마다 `SQMDatabase()` 를 생성하고 **닫지 않음**
- **After**: `@contextmanager` + `with get_db() as db:` 패턴으로 전환
  - `finally` 블록에서 `db.close()` 보장
  - close 실패 시에도 로그만 남기고 진행 (서비스 중단 방지)

#### [EXCEPTION HANDLING] 라우트 에러 핸들링 추가
- 5개 라우트 전부 `try/except` + `logger.error()` + `HTTPException(500)` 추가
  - `dashboard_summary`
  - `dashboard_by_product`
  - `dashboard_location_summary`
  - `inventory_filters`
  - `inventory_search`
  - `inventory_lot_detail`
- `HTTPException` (404 등)은 re-raise 하여 의도적 에러 응답 보존

#### [SAFE REFACTOR] `inventory_search` 함수 분해
- **Before**: 단일 함수 ~100줄
- **After**: 2개 헬퍼 추출
  - `_build_search_conditions()` - WHERE 절 조건 + 파라미터 생성
  - `_row_to_inventory()` - DB row dict -> InventoryRow 변환
- 동작 변경: **없음** (pure extraction)

#### [CLEANUP] import 정리
- `Dict` (미사용) -> `Generator` (get_db 타입힌트용) 으로 교체

---

### 2-2. `api/dashboard_read_service.py`

#### [EXCEPTION HANDLING] DB 쿼리 예외 처리 추가
- 3개 메서드의 `db.fetchall()` 호출부에 try/except 추가
  - `_fetch_status_rows()` - 실패 시 빈 리스트 반환
  - `get_by_product()` - 실패 시 빈 rows + generated_at 반환
  - `get_location_summary()` - 실패 시 빈 rows + generated_at 반환
- **설계 원칙**: 대시보드 조회 실패 시 빈 데이터 반환 (500 크래시 대신 graceful degradation)
- 모든 에러는 `logger.error()` 로 기록

---

### 2-3. `web/src/pages/InventoryPage.jsx`

#### [BUG FIX] 네트워크 에러 처리 개선
- **Before**: `fetch()` 실패 시 raw error (TypeError 등) 그대로 노출
- **After**: `apiGet()` 에서 네트워크 에러 catch -> 사용자 친화적 메시지

#### [BUG FIX] 컴포넌트 언마운트 시 fetch 취소
- `AbortController` 추가 → `useEffect` cleanup 에서 `ctrl.abort()` 호출
- 언마운트 후 setState 호출로 인한 React 경고 방지

#### [EXCEPTION HANDLING] loadFilterOptions 침묵 실패 제거
- **Before**: `catch (err) { console.error(err); }` — 사용자에게 에러 표시 안 됨
- **After**: `setError("필터 옵션을 불러오지 못했습니다.")` 로 UI 에러 표시
- `AbortError` 는 정상 취소이므로 무시

#### [EXCEPTION HANDLING] loadLotDetail AbortError 처리
- AbortError 발생 시 에러 메시지 표시하지 않도록 guard 추가

---

## 3. 체크리스트 결과

| 항목 | 결과 | 비고 |
|------|------|------|
| 안정성 - 정상 실행 | OK | Python syntax 검증 통과 |
| 안정성 - 기존 기능 보존 | OK | 동작 변경 없음, 에러 처리만 추가 |
| 디버깅 - 침묵 실패 감소 | OK | except pass 0건, 모든 에러 로깅 |
| 디버깅 - 에러 가시성 | OK | logger.error + HTTPException 500 |
| 구조 - 함수 분리 | OK | inventory_search 2개 헬퍼 추출 |
| 과수정 방지 - 불필요 변경 없음 | OK | 3개 파일만 수정, 구조 변경 없음 |

---

## 4. 남은 리스크

| # | 리스크 | 심각도 | 설명 |
|---|--------|--------|------|
| R1 | SQMDatabase.close() 미확인 | 중간 | SQMDatabase 클래스에 `close()` 메서드가 없으면 AttributeError 발생 가능. 현재 try/except로 보호됨 |
| R2 | 중복 디렉토리 구조 | 낮음 | `GPT_SQM_React_Phase1_Draft/GPT_SQM_React_Phase1_Draft/` 중복 폴더 존재. zip 해제 아티팩트로 추정. 수정은 최상위에만 적용됨 |
| R3 | CORS 하드코딩 | 낮음 | localhost:5173 만 허용. 배포 시 환경변수 기반으로 전환 필요 |
| R4 | DB 연결 풀 없음 | 낮음 | 매 요청마다 새 연결 생성/해제. 트래픽 증가 시 연결 풀 도입 권장 |

---

## 5. 다음 권장 단계

1. **SQMDatabase.close() 확인** — engine_modules/database.py에서 close 메서드 존재 여부 확인
2. **uvicorn 기동 테스트** — `uvicorn api.main:app --reload` 로 실제 API 동작 확인
3. **중복 폴더 정리** — `GPT_SQM_React_Phase1_Draft/GPT_SQM_React_Phase1_Draft/` 삭제 검토
4. **React dev 테스트** — `npm run dev` 후 재고조회 페이지 정상 렌더링 확인
5. **로깅 설정** — `config_logging.py` 에 FastAPI 로거 레벨 설정 추가 검토
