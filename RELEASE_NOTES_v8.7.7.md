# SQM Inventory v8.7.7 — 앱 시작/응답 흐름 안정화

**릴리즈 날짜**: 2026-06-15
**브랜치**: `claude/debugging-session-optimization-t3ayma`
**이전 버전**: v8.7.6
**테스트**: 240 passed, 1 deselected

---

## 🎯 개요

DEBUG_GOALS.md의 흐름 연속성(flow continuity) 백로그 중 앱 시작/백엔드 연결 영역 A1~A4를 3-AI 협업 방식으로 재현·테스트·수정한 안정화 릴리즈입니다.

이번 릴리즈는 “실패했는데 정상처럼 보이는” 흐름을 줄이고, 시작 단계 오류를 화면과 로그에 명확히 드러내도록 개선했습니다.

---

## ✅ 주요 수정

### A1: 스플래시 API 실패 은폐 방지
- **파일**: `main_webview.py`
- 스플래시가 `/api/health` 응답에서 `res.ok` 확인 없이 `res.json()`을 호출하던 문제 수정
- `/api/health` HTTP 실패, status 실패, 카운터 비정상 값을 명시적으로 차단
- `/api/dashboard/kpi`도 HTTP 실패, `{ok:false}`, 비정상 `current_stock_mt`를 검증
- 실패 시 `reportSplashError()`로 화면 상태 표시, `console.error`, `/api/log/frontend-error` 전송
- 기존처럼 조용히 `lots/bags/mt=0`으로 정상 진행하는 흐름 차단

### A2: API 시작 실패 오류 화면 강제 표시
- **파일**: `main_webview.py`
- `wait_for_api()` 타임아웃 후 오류 HTML이 표시되지 않거나 흰 화면으로 고착될 수 있는 흐름 보강
- 오류 화면 로드 전/후 `_force_show_main_window()` 호출
- error phase `on_loaded()`에서도 창 표시 강제
- `window.html = error_html` 동기화로 PyWebView 초기화 race 대응
- `wait_for_api()`가 루프마다 최신 `API_PORT`를 반영하도록 수정
- 타임아웃 로그에 마지막 probe URL/예외를 남겨 원인 추적 강화

### A3: DB 마이그레이션 실패 시 앱 시작 차단
- **파일**: `backend/api/__init__.py`
- DB 마이그레이션 실패를 `logging.warning`만 남기고 계속 시작하던 문제 수정
- 실패 시 `logging.exception()`으로 traceback 기록 후 `RuntimeError` 발생
- 불완전한 스키마 상태에서 FastAPI가 정상 기동되는 흐름 차단
- SQLite 연결에 `timeout=30`, `PRAGMA busy_timeout=30000` 적용
- 마이그레이션 중간 실패 시 DB connection close 보장

### A4: api-client 빈 응답 성공 오인 방지
- **파일**: `frontend/js/api-client.js`
- `res.json()` 실패를 `catch { return {}; }`로 처리하던 패턴 제거
- 204/205 No Content 응답은 명시 객체로 반환:
  - `ok: true`
  - `success: true`
  - `status`
  - `data: null`
  - `noContent: true`
- 빈 body는 `empty response` `ApiError`로 처리
- JSON 파싱 실패는 `invalid json response` `ApiError`로 처리
- HTTP 2xx라도 `ok:false` 또는 `success:false`면 업무 실패로 승격
- `playSuccess()`는 응답 의미 검증 이후에만 실행

---

## 🧪 신규 회귀 테스트

추가된 테스트 파일:

- `tests/test_debug_goals_a1_splash_health.py`
- `tests/test_debug_goals_a2_error_screen_force_show.py`
- `tests/test_debug_goals_a3_migration_fail_fast.py`
- `tests/test_debug_goals_a4_api_client_empty_response.py`

검증 범위:

- 스플래시 `/api/health` / KPI 응답 검증
- API 시작 실패 시 오류 화면 강제 표시
- DB 마이그레이션 실패 fail-fast
- api-client 빈/204/업무 실패 응답 처리

---

## ✅ 검증 결과

실행 명령:

```bash
python -m pytest tests/test_debug_goals_a4_api_client_empty_response.py tests/test_phase1_js_error_handler.py -q
python -m pytest tests/ -q --ignore=tests/test_inbound_doc_detector_artifact_guard.py --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes
```

결과:

```text
17 passed in 0.07s
240 passed, 1 deselected in 8.98s
```

---

## 📌 커밋 범위

주요 커밋:

- `a8ec972` fix: api-client 빈 응답 성공 오인 방지
- `ab49975` fix: DB 마이그레이션 실패 시 시작 차단
- `574f65a` fix: API 시작 실패 오류 화면 강제 표시
- `1765795` fix: 스플래시 API 실패 은폐 방지
- `a639b72` chore: AI 협업 기준 문서 추적 정리

---

## ⚠️ 참고

- 로컬 `.bkit/*` 상태 파일과 엑셀 임시 파일은 릴리즈 커밋에 포함하지 않았습니다.
- GUI 실기동은 Windows/PyWebView 환경 의존이므로 이번 검증은 headless pytest와 정적 회귀 테스트 중심으로 수행했습니다.
