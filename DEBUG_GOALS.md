# SQM 디버깅 목표 (골 형식)

> **이 문서의 목적:** 디버깅 목표를 "완료기준 체크박스"로 미리 박아두어,
> 세션이 중간에 끊겨도 **다음 세션이 첫 미체크 항목부터 자율로 이어서** 끝까지 달리게 한다.
>
> **사용법**
> 1. 아래 *템플릿*을 복사해 `## 진행 중인 목표` 아래에 새 목표 블록을 만든다.
> 2. Claude 에게 한 줄만 지시: **"DEBUG_GOALS.md 의 첫 미체크 목표를 완료기준 다 채울 때까지 진행해."**
> 3. Claude 는 멈춰 묻지 않고(합리적 기본값으로 진행) 완료기준을 모두 통과시킨 뒤 단계별 커밋·푸시한다.

---

## 작성 규칙 (왜 한 번에 끝나는가)
- **완료기준(Acceptance)** 을 "테스트로 검증 가능한 형태"로 적는다 → 끝났는지 자동 판정 가능.
- **실행 규칙에 "막혀도 멈추지 말고 진행"** 을 명시 → 세션이 사용자 답을 기다리다 회수되는 일을 없앤다.
- **범위**를 좁게 적는다(건드릴 파일 / 건드리지 말 것) → 엉뚱한 대형 리팩터 방지.
- 항목을 끝낼 때마다 `[ ]` → `[x]` 로 바꾸고 커밋 → 진행상황이 git 에 영구 기록된다.

---

## 📋 템플릿 (복사해서 사용)

```markdown
### 목표: <한 줄 제목>
- 상태: 🔴 미착수 | 🟡 진행중 | ✅ 완료
- 등록일: YYYY-MM-DD

**배경 / 증상**
- 무엇이 잘못 동작하나 (재현 절차 / 에러 메시지 / 기대 vs 실제)

**범위**
- 건드릴 곳: <파일/모듈>
- 절대 건드리지 말 것: <보호할 기존 기능>

**완료 기준 (전부 [x] 되면 종료)**
- [ ] 증상 재현 안 됨 (재현 절차로 확인)
- [ ] 회귀 테스트 추가: tests/test_<name>.py
- [ ] `python -m pytest tests/ -q --ignore=tests/test_inbound_doc_detector_artifact_guard.py --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes` 그린
- [ ] LOT 무결성(initial=current+picked) 유지
- [ ] 기존 입고/출고 흐름 정상

**실행 규칙**
- 각 단계마다 git commit (fix:/feat: 접두, 한국어)
- 막혀도 멈춰 묻지 말고 합리적 기본값으로 진행 후 결과 보고
- 완료기준 전부 통과 시 `claude/debugging-session-optimization-t3ayma` 로 push
```

---

## 🔎 전수 감사 결과 — 흐름 끊김 로직 에러 백로그 (2026-06-15)

> **감사 관점:** "로직 A 다음 B로 진행돼야 하는데 멈추는 경우" + "데이터를 받아야 하는데
> 못 받아 조용히 멈추는 경우" = **흐름 연속성(flow continuity) 에러**.
> 정적 코드 감사로 도출 — **줄번호/일부 항목은 추정이므로, 고치기 전 "재현 확인" 단계가 완료기준에 포함**.
>
> **기계 검사 베이스라인:** 문법 에러 0(325파일 컴파일 통과), 핵심 모듈/라우터 정상 로드, 225 테스트 통과.
> 따라서 아래 에러들은 임포트가 아니라 **실행 흐름 로직**에 있음.

**집계:** 🔴 흐름차단 16 · 🟡 부분끊김 21 · 🟢 경미 11 (총 ~48)

> ### ✅ 검증 상태 (2026-06-15 전수 대조)
> - **백로그 42건(A1~A9·B1~B12·C1~C10·D1~D11) 전부 조치 완료 + 테스트 검증.** v8.8.0 릴리즈.
> - 41건은 전용 회귀 테스트(`tests/test_debug_goals_*.py`) 통과. **C1은 오탐**(이력은 엔진
>   `confirm_outbound`이 기록, `test_confirm_outbound_stock_movement_recorded`가 검증) → 체크 유지.
> - **전수 검사 중 회귀 1건 발견·수정:** `return_reinbound_engine.py` `logger` 미정의 NameError로
>   반품 preflight가 엉뚱한 사유로 차단되던 버그 → 수정, `test_debug_goals_d5` 그린 회복.
> - **현재 테스트: 325 passed (headless 기준).** 문법 에러 0.
> - 줄번호는 조치 후 코드가 바뀌어 *위치 표기일 뿐* — 실제 상태는 위 테스트가 보증.

**권장 진행 순서(물 흐르듯):** A. 앱 시작/연결 → B. 입고/할당 → C. 출고/피킹 → D. 무결성/반품.
각 영역은 🔴부터. 항목 끝낼 때마다 `[ ]`→`[x]`, 커밋.

---

### 영역 A — 앱 시작 / 백엔드 연결 / 화면 전환  (사용자 "시작 시 에러" 직접 원인)

- [x] **🔴 A1** `main_webview.py:~775` 스플래시가 `/api/health`에서 `res.ok` 검증 없이 `res.json()` → 백엔드 500이어도 lots/bags/mt=0으로 진행. **재현 확인 후** `if(!res.ok) throw` 추가.
- [x] **🔴 A2** `main_webview.py:~1109` `wait_for_api` 타임아웃 후 에러 HTML이 `on_loaded` 미발화로 안 그려져 **흰 화면 고착(추정)**. → 에러 상태에서 화면 표시 강제.
- [x] **🔴 A3** `backend/api/__init__.py:~137` DB 마이그레이션 실패를 `logging.warning`만 하고 시작 계속 → 테이블 미생성 → 이후 API "no such table" → UI 빈 상태. → 핵심 마이그레이션 실패 시 명시적 차단/재시도.
- [x] **🟡 A4** `frontend/js/api-client.js:~45` 빈/204 응답을 `{}`로 반환 → 상위가 "정상"으로 오인. → status·success 명시 검증.
- [x] **🟡 A5** `frontend/js/pages/inventory.js:~19` 응답을 배열로 가정하나 `{total,data}` 객체일 수 있음 → `filter()` 에러로 화면 멈춤. → `extractRows` 사용.
- [x] **🟡 A6** `frontend/js/pages/dashboard.js:~50` / `allocation.js:~12` / `picked.js` 200 OK + `data` 필드 없거나 `{success:false}`인데 빈 테이블로 조용히 진행. → 응답 구조 검증 + 에러 분기.
- [x] **🟡 A7** `frontend/js/main.js:~76` 라우터 init 실패를 `console.error`만 → 사이드바 탭 무동작(다른 화면 못 감). → fail-safe 또는 에러 배너.
- [x] **🟡 A8** `main_webview.py:~509` `wait_for_api` 타임아웃 시 사용자 피드백 없음(흰 화면). → 타임아웃 배너 + 재시도.
- [x] **🟢 A9** `outbound.js:~46` 출고확정 fetch 실패 시 토스트만, 재시도 수단 없음. → 재시도 버튼.

---

### 영역 B — 입고확정 / 할당(allocation) / 문서파싱

- [x] **🔴 B1** `engine_modules/inventory_modular/outbound_mixin.py:~2479` `apply_approved`에서 SQL에 상수명(`ALLOC_WF_APPLIED` 등)을 문자열 대신 식별자로 사용 → **구문 오류로 승인 반영 0건(추정)**. → 파라미터/따옴표로 교정 + 재현 테스트.
- [x] **🔴 B2** `backend/api/inbound.py:~1520` PDF 입고가 `PENDING`으로만 저장되고 AVAILABLE 자동 전환/안내 없음 → 사용자가 수동확정 전까지 가용재고에 안 잡혀 **흐름 끊김**. → 자동 전환 또는 명시적 다음단계 안내.
- [x] **🔴 B3** `backend/api/inbound.py:~1484` 파싱 0건인데 `ok:true, saved_count:0` 반환 → 프론트가 성공으로 다음 진행. → 0건이면 경고/실패 상태.
- [x] **🔴 B4** `backend/api/allocation_api.py:~363` 모든 행 검증 실패(reserved=0)면 `success=False`로 "전체 실패" 표시 → 부분/정상 케이스 혼동. → processed>0면 부분성공 + 사유 분리.
- [x] **🟡 B5** `backend/api/allocation_api.py:~372` 예약 후 실제 RESERVED 톤백 수 재검증 없이 카운트만 신뢰 → 일부만 예약돼도 통과(나머지 AVAILABLE에 갇힘). → 예약 직후 상태 재조회 검증.
- [x] **🟡 B6** `outbound_mixin.py:~2461` `apply_approved`가 AVAILABLE 톤백 부족분을 `continue` 스킵하지만 success=true → 일부 LOT 예약 누락. → 실패건 errors 수집.
- [x] **🟡 B7** `backend/api/sales_order_validation.py:~146` 검증만 하고 상태 전환(다음 단계)을 호출 안 함 → 검증 PASS인데 PICKED/SOLD 미진행. → 검증→전환 체이닝 또는 안내.
- [x] **🟡 B8** `backend/api/inbound.py:~438` 반품입고 Excel 일부 행 LOT 못 찾으면 침묵 스킵 → 어느 행 실패인지 미표시. → 행별 사유 반환.
- [x] **🟡 B9** `backend/api/allocation_api.py:~815` export 후 원본 상태 유지 → 수정본 재업로드 시 DUPLICATE 충돌. → 편집/스테이징 상태 플래그.
- [x] **🟢 B10** `backend/api/location_candidates.py:~24` 최신 batch 없으면 후보 `{}` → 위치 자동배정 흐름 멈춤(추정). → "위치데이터 없음" 명시.
- [x] **🟢 B11** `inbound_mixin.py:~173` lot_no 없으면 early return → 나머지 검증 스킵, 어디서 멈췄는지 불명확. → 검증 모아서 한번에 반환.
- [x] **🟢 B12** `backend/api/allocation_api.py:~281` AI 컬럼매핑 실패 시 조용한 폴백 → 키 미설정이면 원인 불명. → "Gemini 키 미설정" 명시.

---

### 영역 C — 출고 / 피킹 / 바코드 스캔

- [x] **🔴 C1** `backend/api/outbound_api.py:~801` PICKED→SOLD 전환 후 `stock_movement` INSERT 누락 → 이력 0행(감사추적 끊김). → INSERT 추가 + 재현 테스트.
- [x] **🔴 C2** `core/barcode_scan_engine.py:~1089` LOT 스캔 STEP1(→PICKED) 후 상위 `inventory.status`/`_recalc_lot_status` 미호출 → LOT 상태 불일치로 다음 단계 혼선. → STEP1 후 재계산 호출.
- [x] **🔴 C3** `engine_modules/inventory_modular/outbound_mixin.py:~759` `stop_at_picked=True` 경로에서 `allocation_plan` 기록 누락 → 이후 확정 스캔이 target 못 찾아 SOLD 불가. → 해당 경로 allocation_plan INSERT 필수화.
- [x] **🔴 C4** `backend/api/outbound_api.py:~318` allocation 미등록 LOT 스캔 시 `LOT_SCAN_BLOCKED`만 조용히 반환(errors=[]) → 사용자가 왜 막혔는지 모름. → 차단 사유 메시지 + 선행조건 명확화.
- [x] **🟡 C5** `barcode_scan_engine.py:~1154` 대량 스캔 시 `processed_lots`에 None 섞여 `_recalc` 조용히 skip → 일부 current_weight 미갱신(추정). → 루프 내 직접 수집 + None 필터.
- [x] **🟡 C6** `barcode_scan_engine.py:~1036` 소량 LOT 오차허용 `max(1.0, target*0.001)` 과대 → TARGET_EXCEEDED 오판정. → 비율 상/하한 재설정.
- [x] **🟡 C7** `outbound_api.py:~802` (onestop) SOLD 전환 시 `current_weight=0` 하드코딩 → PICKED/AVAILABLE 잔량 있어도 0 → 부분반품 복구 불가. → 재계산으로 대체.
- [x] **🟡 C8** `outbound_api.py:~396` 피킹리스트 파싱 부분실패 시 warnings/items 미반환 → 어디가 문제인지 불명. → 부분결과 반환.
- [x] **🟢 C9** `barcode_scan_engine.py:~1160` 트랜잭션 컨텍스트 내부 명시적 `commit()` 중복(추정). → 구조 정리.
- [x] **🟢 C10** `engine_modules/inventory_modular/shipment_mixin.py` 사실상 미구현 + 전용 테스트 0 → 선적-재고 정합 흐름 공백. → 최소 구현 + 테스트.

---

### 영역 D — 무결성 검사 / 반품 / 재고조정 / 상태복원

- [x] **🔴 D1** `engine_modules/inventory_modular/return_mixin.py:~332` 반품이 `RETURN` 상태에서 멈추고 `finalize_return_to_available` 미호출 → 가용재고로 안 돌아옴(2단계 수동). → 자동 진행 또는 API 공개.
- [x] **🔴 D2** `backend/api/status_revert_api.py:~291` 상태복원이 inventory 상태만 바꾸고 `current_weight/picked_weight` 미복구 → SOLD→PICKED 복원 시 `initial=current+picked` 깨짐. → 복원 후 재계산.
- [x] **🔴 D3** `backend/api/integrity_api.py:~25` `/check`가 `picked>initial` 류 edge case를 못 잡고 `details:[]` 반환 → "이상 없음" 오판. → `verify_lot_integrity` 결과 반영.
- [x] **🟡 D4** `backend/api/status_revert_api.py:~396` `execute_status_revert` 후 `_recalc_current_weight` 미호출 → AVAILABLE→PENDING 복원해도 무게 그대로. → 복원 후 lot별 재계산.
- [x] **🟡 D5** `engine_modules/return_reinbound_engine.py:~162` 재계산 실패를 debug 로그로 무시한 채 COMMIT → current_weight 미복구 채로 확정(추정). → 재계산 전 engine 검증, 실패 시 롤백.
- [x] **🟡 D6** `engine_modules/inventory_modular/preflight_mixin.py:~45` preflight 결과를 process로 전달/재검증 안 함 → 실제 add 단계 초과 감지 시 부분 입고. → preflight↔실행 교차검증.
- [x] **🟡 D7** `engine_modules/inventory_modular/adjust_executor.py` 조정 시 `rowcount` 검증 없이 success 집계(추정) → 0행인데 성공으로 카운트. → UPDATE 후 rowcount 확인.
- [x] **🟡 D8** `engine_modules/return_reinbound_engine.py:~287` `_restore_tonbags` 내부 검증이 UPDATE 사이에 있어 실패 시 부분 변경 후 롤백(원자성 위반 추정). → BEGIN 전 전체 preflight.
- [x] **🟢 D9** `backend/api/inventory_adjust_api.py:~79` `return_to_available` 액션이 `_recalc_current_weight` 미호출 → 무게 미복구. → 재계산 추가.
- [x] **🟢 D10** `engine_modules/lot_balance_checker.py:~15` `ok=False` 반환해도 호출자가 무시 가능 → 불완전 LOT 생성. → 필수 검증 단계로 승격.
- [x] **🟢 D11** `integrity_mixin.py:~475` 정합성 warnings가 API 응답에 누락 → 사용자가 주의사항 못 봄. → `/check`에 warnings 포함.

---

### 다음 액션
초기 백로그 42건은 **모두 조치·검증 완료**(위 검증 상태 참조). 새 디버깅 목표는
위 *템플릿*을 복사해 `## 진행 중인 목표` 아래에 추가하고, Claude 에게
**"DEBUG_GOALS.md 의 첫 미체크 목표를 완료기준 다 채울 때까지 진행해"** 라고 지시한다.
> ⚠️ 새 골 작성 시: 줄번호·"추정" 항목은 **고치기 직전 grep로 위치 재확인**.

---

## 🤖 AI 오케스트레이션 개선 (LangChain/LangGraph/LangSmith 청사진 검토 반영, 2026-06-15)

> 외부 AI가 제안한 청사진을 면밀 검토한 결과: **프레임워크 도입은 비채택**(우리는 이미
> 멀티 백엔드 추상화·무결성 게이트·parsing_log 트레이싱을 자체 구현, ~80% 보유. LangSmith는
> 통관 데이터 외부 전송 리스크). **유효 패턴만 네이티브로** 반영한다.

- [x] **✅ P1 — PL 파싱 신뢰도 점수 DB 영속화** (LangSmith-lite). `parsing_log.confidence_score`
      컬럼 추가(신규 CREATE + 기존 DB 멱등 ALTER), `_log_parse_result` 신뢰도 파라미터,
      `/api/ai/parse-pl` 엔드포인트가 doc_confidence 기록. 테스트 4종(329 passed). *(완료)*

- [ ] **🔴 P0 — 검증기반 "프롬프트 교정 재파싱" 루프** (LangGraph Node 3 패턴, 네이티브 구현)
  - 배경: 현재는 "Gemini 실패→OpenAI 폴백 1회" + "LOT 누락 힌트 재시도 1회"만. 일반화된
    "검증 실패 → 프롬프트/조건 교정 → 재파싱(최대 N회)" 루프 부재. PL 헤더합 vs 행합 검증이
    soft-warning(`gemini_parser.py:1043`)이라 통과돼버림.
  - 범위: `features/ai/gemini_parser.py`(파싱 후 검증 훅), `features/parsers/document_parsing_service.py`.
    절대 건드리지 말 것: ocr_auto_tuner의 동시성/Circuit Breaker, 입고 PENDING 게이트.
  - 완료 기준:
    - [ ] plain Python 루프: `attempt<MAX_RETRY(기본3)` 동안 parse→validate(Σ행=헤더합)→실패 시 교정 프롬프트로 재파싱
    - [ ] 교정 전략 최소 2종(숫자 오인식 "정수만 추출", 누락 LOT "기존 제외 후 나머지")
    - [ ] 최대 재시도 횟수 상한 + 각 시도 parsing_log 기록(method='gemini_retryN', confidence)
    - [ ] 회귀 테스트: 1차 실패→2차 성공 시나리오 그린
    - [ ] LangGraph/LangChain 의존성 추가 금지 (네이티브 유지)

- [ ] **🟢 P2 — 프롬프트/좌표 변경 이력 감사** (컴플라이언스). audit_log 또는 parsing_log에
      프롬프트 버전/좌표 범위 기록 → "왜 이번 파싱이 달라졌나" 역추적. *(여유 시)*

---

## 완료된 목표 (기록 보관)

- ✅ **P1 (2026-06-15)** PL 파싱 신뢰도 DB 영속화 — `parsing_log.confidence_score` + 테스트 4종.
<!-- 완료된 목표는 여기로 옮겨 ✅ 로 보관 -->
