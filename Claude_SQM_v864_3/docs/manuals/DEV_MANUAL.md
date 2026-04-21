# 🛠️ SQM Inventory v8.6.4.3 — 개발자 매뉴얼

> **대상:** Python/JS 개발자 / Ruby Sub-Agent / 사장님(개발 모드)
> 작성: 2026-04-21 | 버전: v8.6.4.3

---

## 1. 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  PyWebView (네이티브 창)                                    │
│   └─ frontend/index.html                                    │
│        ├─ js/main.js  (Entry, ESM)                          │
│        │   ├─ router.js → pages/{9개}.js                    │
│        │   ├─ handlers/{menubar,toolbar,topbar,shortcuts}   │
│        │   ├─ components/{alerts,statusbar,auto_refresh}    │
│        │   └─ {api-client,toast,state}.js                   │
│        └─ css/{design-system, v864-layout}.css              │
└──────────────────────────┬──────────────────────────────────┘
                           │ fetch http://127.0.0.1:8765/api/*
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI (uvicorn, daemon Thread)                           │
│   └─ backend/api.py  (FastAPI app + CORS)                   │
│        ├─ api/menubar.py   (62 엔드포인트)                  │
│        ├─ api/controls.py  (23)                             │
│        ├─ api/optional.py  (11, Tier 3)                     │
│        └─ common/{errors, cache}.py                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ wrap_engine_call(...)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  v864.2 비즈니스 로직 (수정 금지)                           │
│   engine_modules/, features/, parsers/, utils/              │
│        └─ SQLite (sqm.db)                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 폴더 구조

```
Claude_SQM_v864_3/
├─ CLAUDE.md                    # 프로젝트 영구 메모리 (수정 시 신중)
├─ TIER1_PLAN.md, TIER2_BRIEF.md
├─ main_webview.py              # 진입점 (PyWebView + FastAPI 스레드)
├─ requirements_webview.txt
├─ build/SQM_v864_3.spec        # PyInstaller spec
├─ installer/                   # Inno Setup
│   ├─ SQM_v864_3_Setup.iss
│   └─ build.bat
├─ backend/
│   ├─ api.py                   # FastAPI app + 라우터 include
│   ├─ api/
│   │   ├─ menubar.py controls.py optional.py
│   │   └─ __init__.py
│   └─ common/
│       ├─ errors.py            # ApiError, wrap_engine_call
│       └─ cache.py             # LRU @cached
├─ frontend/
│   ├─ index.html               # v864.2 레이아웃 (절대 임의 변경 금지)
│   ├─ css/
│   │   ├─ design-system.css    # 디자인 토큰 → CSS 변수
│   │   └─ v864-layout.css      # v864.2 레이아웃 전용
│   └─ js/
│       ├─ main.js              # ESM Entry
│       ├─ router.js api-client.js toast.js state.js shortcuts.js perf.js
│       ├─ pages/{dashboard,inventory,allocation,outbound,picked,return,move,log,scan,tonbag}.js
│       ├─ handlers/{menubar,toolbar,topbar}.js
│       └─ components/{alerts,statusbar,auto_refresh}.js
├─ docs/
│   ├─ handoff/{v864_2_structure,feature_matrix,design_tokens}.json   # 수정 금지
│   ├─ manuals/{USER,ADMIN,DEV}_MANUAL.md
│   └─ FEATURE_PROGRESS.md
├─ tests/uat_scenarios.json
├─ tools/
│   ├─ verify_tier1.py verify_tier2.py
│   ├─ rollback.py log_collector.py check_update.py
│   └─ stage_test.py            # Per-Stage Gate Test
└─ engine_modules/ features/ parsers/ utils/    # v864.2 원본 (수정 금지)
```

---

## 3. 빠른 개발 환경

```cmd
git clone <repo>
cd Claude_SQM_v864_3
python -m venv venv
venv\Scripts\activate
pip install -r requirements_webview.txt
python main_webview.py
```

브라우저 모드 (PyWebView 없이): 자동 폴백으로 기본 브라우저 열림.

---

## 4. API 엔드포인트 카탈로그

| Prefix | 모듈 | 기능 수 |
|---|---|---|
| `/api/health, /api/dashboard/*, /api/inventory/*` 등 | `backend/api.py` | 17 |
| `/api/menu/*` | `backend/api/menubar.py` | 62 |
| `/api/controls/*` | `backend/api/controls.py` | 23 |
| `/api/optional/*` | `backend/api/optional.py` | 11 |
| **합계** | | **113+** |

전체 목록: `http://127.0.0.1:8765/docs` (Swagger UI)

### 응답 표준
```json
{ "ok": true, "data": <any>, "error": null }
```

### 에러 표준
- 400 잘못된 요청 / 404 없음 / 501 준비 중 / 500 서버 오류
- 모든 엔드포인트는 `wrap_engine_call` 사용 권장

---

## 5. Frontend 모듈 시스템

- **모듈 형식:** ES Modules (ESM, `<script type="module">`)
- **번들러 없음:** Vanilla JS, 직접 import 체인
- **라우터:** `router.js` 가 `pages/*.js` 를 동적 import → mount/unmount 라이프사이클
- **상태 저장:** `state.js` 가 localStorage → sessionStorage → 메모리 3단 폴백

각 페이지 모듈 인터페이스:
```js
export async function mount(container) { /* DOM 렌더 */ }
export function unmount() { /* cleanup */ }
```

---

## 6. 빌드

### 6.1 PyInstaller
```cmd
pyinstaller build\SQM_v864_3.spec --noconfirm
```
산출: `build\dist\SQM_v864_3.exe` (약 192MB)

### 6.2 Inno Setup
```cmd
installer\build.bat
```
산출: `installer\dist\SQM_v864_3_Setup.exe`

### 6.3 ZIP 포터블 (Inno 미설치 시)
`installer\build.bat` 가 자동 폴백.

---

## 7. 테스트

| 도구 | 용도 | 명령 |
|---|---|---|
| `verify_tier1.py` | Tier 1 9 DoD 정적/런타임 | `python tools\verify_tier1.py --mode auto` |
| `verify_tier2.py` | 85 기능 회귀 | `python tools\verify_tier2.py` |
| `stage_test.py` | Per-Stage Gate Test | `python tools\stage_test.py --stage all` |

리포트는 `REPORTS/` 에 저장.

---

## 8. 주요 규칙 (CLAUDE.md Rule)

1. **Rule 1:** `engine_modules/`, `features/`, `parsers/`, `utils/` 절대 수정 금지. wrapper 만 작성.
2. **Rule 2:** UI/Logic 분리 — `frontend/` 에 비즈니스 로직 금지
3. **Rule 3:** 85 기능 누락 금지 (optional 11 도 "준비 중" 으로라도 표시)
4. **Rule 4:** 모든 endpoint try/except + 모든 fetch try/catch + Toast
5. **Rule 5:** 색상 하드코딩 금지 → CSS 변수 사용

---

## 9. 디버깅 팁

- **PyWebView 개발자 도구:** `webview.start(debug=True)` 로 실행 → 우클릭 → 검사
- **API 직접 호출:** `curl http://127.0.0.1:8765/api/health`
- **Swagger:** `http://127.0.0.1:8765/docs`
- **로그 실시간:** `tail -f %APPDATA%\SQM\logs\sqm_webview.log`

---

## 10. 기여 가이드

- 새 기능: `feature_matrix.json` 확인 → 해당 ID 의 endpoint/handler 작성
- PR 시 `verify_tier2.py` 통과 필수
- 커밋 메시지: `[Tier-X] [Stage-Y] 변경 요약`

---

**본 매뉴얼 버전:** v1.0 (2026-04-21, Ruby 작성)
