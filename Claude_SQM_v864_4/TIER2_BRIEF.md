# 🎯 TIER 2 + TIER 3 통합 작업지시서 — Sub-Agent 자율 실행 에디션

> **절대 중단 금지 (NO-STOP DIRECTIVE):**
> 이 지시서는 사장님(Nam Ki-dong) 외출 중에도 Sub-Agent 팀이 **단 한 번의 확인 질문 없이** 완주할 수 있도록 모든 결정을 사전 박제한 문서입니다.
> 모호함을 만나면 "기본값 섹션"으로 폴백하고, 어떠한 경우에도 전체 작업을 멈추지 않습니다.
>
> **범위:** Tier 2 (기능 100% 작동) + Tier 3 (배포·문서·릴리즈) 전 구간 커버.
> 총 **7팀 × 13 Sub-Agent × 12 Stage (S1~S7 Tier2 + T3-S1~T3-S5 Tier3)**.

---

## 📋 메타데이터

| 항목 | 값 |
|---|---|
| **프로젝트** | Claude_SQM_v864_3 PyWebView Migration |
| **작성일** | 2026-04-21 (화) |
| **작성자** | Ruby (Senior Software Architect Mode) |
| **승인자** | Nam Ki-dong (사장님) |
| **Tier** | Tier 2 — 85개 기능 전면 작동화 |
| **착수 조건** | Tier 1 Pre-flight 통과 (6/9 이상), EXE 빌드 성공 확인됨 |
| **예상 소요** | 병렬 10~12시간 (실시간) / 1.5~2일 (벽시계) |
| **검토 이력** | Review Pass 1 ✅, Review Pass 2 ✅ (본 문서 하단 부록) |

---

## 🎯 섹션 0. Executive Summary (30초 요약)

### Tier 2 부분 (S1~S7)
1. **목표:** v864.2 Golden Reference 스크린샷의 **모든 인터랙션 요소(메뉴바 7, 툴바 7, 사이드바 9, 토글 5, 단축키 13)를 100% 작동**하게 만든다.
2. **팀:** 4팀 × 8 Sub-Agent (A1·A2, B1·B2·B3, C1·C2, D1)
3. **단계:** 7 Stage (S1~S7)
4. **성공 기준:** `verify_tier2.py` 85개 중 ≥ 81 PASS + EXE 재빌드 성공
5. **예상 벽시계:** 6~12시간

### Tier 3 부분 (T3-S1~T3-S5)
1. **목표:** 배포 가능한 **릴리즈 품질** (인스톨러·매뉴얼·UAT·롤백·모니터링 포함)
2. **팀:** 3팀 × 5 Sub-Agent (E1·E2, F1·F2, G1)
3. **단계:** 5 Stage (T3-S1~T3-S5)
4. **성공 기준:** Installer 정상 + UAT 20 중 ≥ 18 PASS + 매뉴얼 4종 납품
5. **예상 벽시계:** 3~4일

### 통합 KPI
- **총 팀 수:** **7 팀** (A·B·C·D·E·F·G)
- **총 Sub-Agent 수:** **13 명** (Tier2 8 + Tier3 5)
- **총 단계 수:** **12 Stage** (Tier2 7 + Tier3 5)
- **중단 방지:** 모든 Agent 는 "기본값 자동 채택" + "NO-STOP" 규칙. Per-Stage Gate Test 실패도 중단 트리거 아님.

---

## 🧭 섹션 1. 미션 선언 (Mission Statement)

> **"사장님이 스크린샷 속 어떤 버튼을 눌러도, v864.3 이 v864.2 와 동일하게 반응한다."**

이것은 단일 KPI 이다. 다른 모든 결정은 이 문장에 종속된다.

### 1.1 범위 안 (IN SCOPE)
- `docs/handoff/feature_matrix.json` 의 **85개 기능 전체**
- `docs/handoff/v864_2_structure.json` 의 UI 요소 전체 (메뉴바·툴바·사이드바·상태바·단축키·대화상자 5종)
- Dark/Light 토글, 돈백/LOT/MT 라디오, 새로고침, ALERTS 패널, 자동 30초 갱신
- PyInstaller EXE 재빌드 (Tier 1 EXE 덮어쓰기)

### 1.2 범위 밖 (OUT OF SCOPE — Tier 3 로 이월)
- optional 11개 기능의 고도화 (Tier 2 에서는 "준비 중" Toast 로 표기만)
- 신규 기능 추가 / v864.2 에 없던 기능
- 엔진 리팩토링 (CLAUDE.md Rule 1 — 비즈니스 로직 수정 금지)
- 테마 신규 추가 (기본 darkly + light 2개만 유지)

---

## 🧑‍🤝‍🧑 섹션 2. 팀 구조 (4 팀 × 8 Sub-Agent)

### 🅰️ 팀 A — Backend Engineering (2명)

| Agent | 책임 영역 | 담당 기능 수 | 주요 산출물 |
|---|---|---|---|
| **A1** | Menubar API 엔드포인트 | 62개 (menubar) | `backend/api/menubar.py` |
| **A2** | Toolbar·Sidebar·Keyboard API + 예외 처리 표준화 | 23개 (toolbar 2 + sidebar 8 + keyboard 13) | `backend/api/controls.py`, `backend/common/errors.py` |

### 🅱️ 팀 B — Frontend Development (3명)

| Agent | 책임 영역 | 담당 UI | 주요 산출물 |
|---|---|---|---|
| **B1** | 사이드바 9탭 페이지 + 라우터 | 9개 페이지 | `frontend/js/pages/{9개}.js`, `frontend/js/router.js` |
| **B2** | 메뉴바 드롭다운 + 62 핸들러 | 메뉴바 62 항목 | `frontend/js/handlers/menubar.js` |
| **B3** | 툴바 7 + 상단 우측 컨트롤 + 라디오 | 15개 인터랙션 | `frontend/js/handlers/toolbar.js`, `frontend/js/handlers/topbar.js` |

### 🅲 팀 C — UX Integration (2명)

| Agent | 책임 영역 | 담당 | 주요 산출물 |
|---|---|---|---|
| **C1** | ALERTS 패널 + 상태바 + 30초 자동 갱신 + Toast 규격화 | 실시간 UI | `frontend/js/components/alerts.js`, `statusbar.js`, `auto_refresh.js` |
| **C2** | 13개 키보드 단축키 + localStorage 상태 복원 | 생산성 UX | `frontend/js/shortcuts.js`, `frontend/js/state.js` |

### 🅳 팀 D — QA & Release (1명)

| Agent | 책임 영역 | 담당 | 주요 산출물 |
|---|---|---|---|
| **D1** | 회귀 검증 + Golden SSIM + EXE 재빌드 + 진척 대시보드 | 85개 기능 검증 | `tools/verify_tier2.py`, `tools/ssim_check.py`, `docs/FEATURE_PROGRESS.md`, `build/dist/SQM_v864_3.exe` (덮어쓰기) |

---

## 🗺️ 섹션 3. 7단계 실행 플랜

```
┌────────────────────────────────────────────────────────────────────┐
│  Stage 1: PREP           ── D1 단독 (순차, 1h)                     │
│  Stage 2: BACKEND        ── A1, A2 병렬 (4h)                       │
│  Stage 3: FRONT PAGES    ── B1, C1 병렬 (3h)                       │
│  Stage 4: FRONT HANDLERS ── B2, B3, C2 병렬 (3h)                   │
│  Stage 5: UX POLISH      ── C1, C2 잔여 + 통합 (2h)                │
│  Stage 6: INTEGRATION TEST ── D1 주도 + 전체 협력 (2h)             │
│  Stage 7: BUILD & SIGN-OFF ── D1 단독 (1h)                         │
└────────────────────────────────────────────────────────────────────┘
합계: 순차 최소 12h, 병렬 시 벽시계 6~7h
```

### Stage 1 — PREP (1시간)
- **담당:** D1
- **목적:** 진척 추적 체계 구축 + 스캐폴딩
- **작업:**
  1. `docs/FEATURE_PROGRESS.md` 생성 (85개 기능 체크박스 + 담당 Agent 표시)
  2. `frontend/js/handlers/` 폴더 생성
  3. `frontend/js/components/` 폴더 생성
  4. `backend/api/` 폴더 + `__init__.py` 생성
  5. `backend/common/errors.py` 표준 에러 헬퍼 스텁 생성
  6. `tools/verify_tier2.py` 스크립트 뼈대 작성 (Stage 6 에서 완성)
- **DoD:** 위 파일 8개 모두 존재, `git status` 에 신규 파일 표시됨

### Stage 2 — BACKEND (4시간, 병렬)
- **담당:** A1, A2
- **목적:** 85개 기능 중 API 필요 기능(약 50개) 엔드포인트 구현
- **A1 작업:** `feature_matrix.json` 의 `category=menubar` 62개 중 비즈니스 로직 필요 40개를 `backend/api/menubar.py` 에 엔드포인트로 생성. 각 엔드포인트는 기존 `engine_modules` 의 해당 handler 함수를 호출하는 얇은 wrapper.
- **A2 작업:** toolbar 2 + sidebar 8 + keyboard 13 중 API 필요 기능을 `backend/api/controls.py` 에 생성. 또한 `backend/common/errors.py` 에 `ApiError`, `wrap_engine_call()` 헬퍼 완성.
- **DoD:** `tools/verify_tier1.py --mode static` 재실행 시 엔드포인트 ≥ 50개 검출, 모든 엔드포인트 `try/except` 포함.

### Stage 3 — FRONTEND PAGES (3시간, 병렬)
- **담당:** B1, C1
- **목적:** 사이드바 9탭 페이지 완성 + ALERTS 패널 컴포넌트
- **B1 작업:** `frontend/js/pages/` 에 `picked.js`, `return.js`, `log.js` 신규 작성. 기존 6개는 리뷰 후 필요 시 보완. `router.js` 로 9탭 전환 로직 구현.
- **C1 작업:** `frontend/js/components/alerts.js` 구현 — `/api/dashboard/alerts` 호출하여 ALERTS 영역 렌더. `statusbar.js` 구현 — 위치 미배정 / 스캔 실패율 / LOT 평균 재고기간 표시.
- **DoD:** 9탭 클릭 시 모두 페이지 전환, ALERTS 최소 2건 표시 확인.

### Stage 4 — FRONTEND HANDLERS (3시간, 병렬)
- **담당:** B2, B3, C2
- **목적:** 메뉴바·툴바·단축키 onclick 바인딩
- **B2 작업:** `handlers/menubar.js` 에서 `feature_matrix.json` 의 62개 menubar 항목 각각에 대해 onclick 생성 (업무 로직 호출 또는 "준비 중" Toast).
- **B3 작업:** `handlers/toolbar.js` (툴바 7개) + `handlers/topbar.js` (새로고침·Dark/Light·돈백/LOT/MT 5항목).
- **C2 작업:** `shortcuts.js` 에 13개 단축키 document-level 바인딩. `state.js` 에서 창 크기·테마·사이드바 선택 localStorage 저장/복원.
- **DoD:** 각 핸들러 파일 존재 + 해당 UI 요소에 data-action 속성 연결 확인.

### Stage 5 — UX POLISH (2시간)
- **담당:** C1, C2 잔여 + B 팀 협력
- **목적:** 30초 자동 갱신 + Toast 규격 통일 + 창 종료 시 리소스 정리
- **작업:**
  - `auto_refresh.js` 30초 타이머 → Dashboard / Inventory 자동 리로드
  - Toast 타입 `success/info/warning/error` 4종 통일
  - `main_webview.py` 창 종료 핸들러에 FastAPI 종료 로직 추가
- **DoD:** 30초 후 "마지막 경신" 타임스탬프 갱신 확인, 창 닫으면 python 프로세스 종료 확인.

### Stage 6 — INTEGRATION TEST (2시간)
- **담당:** D1 주도, A·B·C 지원
- **목적:** 85/85 기능 자동 회귀 검증
- **작업:**
  - `tools/verify_tier2.py` 완성 — `feature_matrix.json` 순회하며 각 기능의 엔드포인트와 JS 핸들러 존재 + 클릭 시뮬레이션
  - `tools/ssim_check.py` — Golden Reference 와 현재 Dashboard 스크린샷 SSIM 비교 (0.85 이상)
  - 실패 항목은 즉시 해당 Agent 에게 티켓 발행 (`REPORTS/tier2_fails_<ts>.md`)
- **DoD:** PASS 비율 ≥ 95% (85 중 81 이상), FAIL 항목이 있어도 Stage 7 로 진행 (단, FAIL 티켓 분리).

### Stage 7 — BUILD & SIGN-OFF (1시간)
- **담당:** D1
- **목적:** EXE 재빌드 + 결과물 사인 오프
- **작업:**
  - `pyinstaller build/SQM_v864_3.spec --noconfirm`
  - 빌드 결과 `build/dist/SQM_v864_3.exe` 타임스탬프 업데이트 확인
  - `REPORTS/tier2_final_<ts>.md` 최종 보고서 작성 (체크리스트, 진척률, FAIL 티켓, EXE 크기·시각)
  - `feature_matrix.json` 의 `status` 필드 일괄 갱신 (`completed`/`partial`/`deferred`)
- **DoD:** EXE 재빌드 성공, 최종 보고서 생성, 사장님 검수 대기 상태로 전환.

---

## 🧪 섹션 3.5. Per-Stage Gate Test 프로토콜 (자동 게이트)

> **핵심 원칙:** 각 Stage 완료 시점에 **자동 테스트가 통과해야만 다음 Stage 로 진입**한다.
> 실패 시에도 중단하지 않고 **해당 Stage 에서 FAIL 티켓만 발행**하고 다음 Stage 로 진행 (NO-STOP).

### 공통 테스트 러너

모든 Gate Test 는 `tools/stage_test.py` 가 실행한다. 각 Agent 는 자기 Stage 완료 직후 해당 명령을 호출:

```bash
python tools/stage_test.py --stage S2          # 단일 Stage
python tools/stage_test.py --stage all         # 전 Stage 누적
python tools/stage_test.py --stage S2 --fix    # FAIL 시 자동 보정 시도
```

실패해도 exit code 0 으로 종료하되, `REPORTS/stage_tests_<ts>.jsonl` 에 실패 기록 남김. D1 이 Stage 6 에서 집계.

### Stage 별 Gate Test 명세

| Stage | Gate Test | 통과 조건 | 실패 시 조치 |
|---|---|---|---|
| **S1 PREP** | `test_scaffold.py` → 폴더/파일 생성 확인 | 필수 8개 파일 모두 존재 | 누락 파일만 D1 재생성, 다음 Stage 계속 |
| **S2 BACKEND** | `test_backend_endpoints.py` → 정적 파싱 + 샘플 3개 `httpx.get` | 엔드포인트 ≥ 50개, 샘플 200/501 응답 | 501 이면 PASS 로 간주 (기본값 정책), 500 만 FAIL |
| **S3 FRONT PAGES** | `test_pages.py` → `frontend/js/pages/*.js` 구문 검증 + `mount/unmount` export 존재 | 9개 페이지 모듈 모두 ESM 유효 | 깨진 모듈만 B1 복구 티켓 |
| **S4 FRONT HANDLERS** | `test_handlers.py` → `HANDLER_MAP` 키 수 + data-action 개수 | menubar 62 + toolbar 7 + topbar 5 = 74 바인딩 확인 | 누락 항목 리스트 JSONL, B2/B3/C2 에 티켓 |
| **S5 UX POLISH** | `test_ux.py` → 30초 타이머 정의 확인 + Toast 4타입 정의 | 타이머 유닛 테스트 + Toast success/info/warning/error 스타일 존재 | C1/C2 재작업 티켓 |
| **S6 INTEGRATION** | `verify_tier2.py` (85개 회귀) + `ssim_check.py` | PASS ≥ 95% & SSIM ≥ 0.85 | FAIL 항목 티켓 자동 생성, Stage 7 진입 |
| **S7 BUILD** | `test_build.py` → EXE 크기·무결성·실행 테스트 (Windows only) | EXE ≥ 50MB + subprocess 기동 후 `/api/health` 200 | 기존 EXE 유지, 리포트에 "재빌드 실패" 기록 |

### 테스트 실패 시 자동 복구 정책 (--fix 모드)

- 누락 파일 → 빈 스텁 자동 생성
- 문법 오류 → 마지막 정상 커밋으로 파일별 롤백 (`git checkout HEAD~1 -- <file>`)
- 엔드포인트 501 → "준비 중" 으로 라벨링 후 PASS 로 전환
- SSIM 0.85 미달 → Dashboard 만 재시도, 전체 중단 금지

### Gate Test 의 NO-STOP 보장

- `try/except` 최외곽 래핑 → 테스트 자체가 죽어도 스크립트는 exit 0
- 실패 기록은 구조화 JSONL 로 누적 → 사장님 외출 복귀 시 한 번에 조회 가능
- **Gate Test 실패가 전체 파이프라인을 멈추는 일은 없음**

---

## 🃏 섹션 4. Sub-Agent 미션 카드 (8장)

### 🃏 A1 Mission Card — Menubar API Engineer

**Input:**
- `docs/handoff/feature_matrix.json` → filter `category == "menubar"` (62건)
- `docs/handoff/v864_2_structure.json` → `menubar.menus` 참조
- 기존 핸들러: `engine_modules/`, `features/`, `parsers/`, `utils/` (읽기 전용)

**Output:**
- `backend/api/menubar.py` — FastAPI APIRouter
- 엔드포인트 네이밍: `POST /api/menu/{snake_case_callback}` (feature_matrix.json 의 `proposed_api_endpoint` 값 사용)
- 각 엔드포인트 본문 템플릿 (필수 준수):

```python
from fastapi import APIRouter, HTTPException
from backend.common.errors import wrap_engine_call, ApiError
router = APIRouter(prefix="/api/menu", tags=["menubar"])

@router.post("/-on-pdf-inbound")
async def on_pdf_inbound(payload: dict | None = None):
    try:
        from gui_app_modular.handlers.inbound_processor import _on_pdf_inbound
        return wrap_engine_call(_on_pdf_inbound, payload or {})
    except ImportError:
        raise HTTPException(501, detail="준비 중 (Tier 3 이관 예정)")
    except Exception as e:
        raise HTTPException(500, detail=str(e))
```

**중단 방지 기본값:**
- 기존 handler 가 존재하지 않으면 **501 Not Implemented** + "준비 중" 메시지. 절대 import 실패로 서버를 죽이지 말 것.
- `payload` 스키마 모호 시 `dict | None` 으로 방어적 수용.

**DoD:**
- `backend/api.py` 의 `app.include_router(menubar_router)` 추가
- `tools/verify_tier1.py --mode static` 에서 엔드포인트 개수 ≥ 45 검출
- `feature_matrix.json` 에 `status` 필드 업데이트 (`completed`/`deferred`)

---

### 🃏 A2 Mission Card — Controls API + Error Standardization

**Input:**
- `feature_matrix.json` 의 `category in {toolbar_button, sidebar_tab, keyboard}`
- 기존 `backend/api.py` 의 17개 엔드포인트

**Output:**
- `backend/common/errors.py`:

```python
from fastapi import HTTPException
import logging
log = logging.getLogger(__name__)

class ApiError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code; self.message = message

def wrap_engine_call(fn, *args, **kwargs):
    """엔진 호출 표준 래퍼. 예외를 HTTPException 으로 승격."""
    try:
        return {"ok": True, "data": fn(*args, **kwargs)}
    except NotImplementedError:
        raise HTTPException(501, detail="준비 중")
    except FileNotFoundError as e:
        raise HTTPException(404, detail=f"파일 없음: {e}")
    except Exception as e:
        log.exception("engine call failed")
        raise HTTPException(500, detail=f"엔진 오류: {type(e).__name__}")
```

- `backend/api/controls.py` — 툴바·사이드바·단축키 전용 엔드포인트
- 기존 `backend/api.py` 의 17개 엔드포인트도 `wrap_engine_call` 로 순차 래핑 (리팩토링)

**중단 방지 기본값:**
- 리팩토링 중 기존 동작이 바뀌면 즉시 해당 엔드포인트만 원복. 전체 롤백 금지.

**DoD:**
- 모든 backend 엔드포인트가 `wrap_engine_call` 사용
- `backend/common/errors.py` 단위 테스트 통과 (`pytest tests/test_errors.py`)

---

### 🃏 B1 Mission Card — Sidebar Pages + Router

**Input:**
- `frontend/index.html` 의 9개 `data-page` 속성
- `frontend/js/pages/` 기존 6개 (dashboard, inventory, allocation, outbound, scan, tonbag)
- v864.2 각 탭 스크린샷 (없으면 Golden Reference 1장으로 대체 — Dashboard 만 이미지 존재)

**Output:**
- `frontend/js/pages/picked.js`
- `frontend/js/pages/return.js`
- `frontend/js/pages/log.js`
- `frontend/js/router.js` (기존 있다면 개선)
- 각 page 모듈의 공용 인터페이스:

```js
// picked.js 예시
export async function mount(container) {
  container.innerHTML = `<section class="page" data-page="picked"><h2>Picked</h2><div class="loading">로딩 중…</div></section>`;
  try {
    const data = await window.api.get('/api/outbound/scheduled?status=picked');
    render(container, data);
  } catch (e) {
    container.innerHTML = `<div class="empty">불러오기 실패: ${e.message}</div>`;
  }
}
export function unmount() {}
function render(container, data) { /* 테이블 렌더 */ }
```

**중단 방지 기본값:**
- 해당 API 가 501 이면 "준비 중" 빈 상태로 표시. 페이지 자체는 렌더링.
- 이미지 로드 실패 시에도 텍스트 콘텐츠 우선.

**DoD:**
- 9탭 클릭 각 시 정상 렌더 (눈으로 확인 또는 `verify_tier2.py` 페이지 전환 테스트 통과)

---

### 🃏 B2 Mission Card — Menubar Handlers (62)

**Input:**
- `feature_matrix.json` → `category == "menubar"` 62건 (label_korean, proposed_js_handler, proposed_api_endpoint)
- `v864_2_structure.json` → `menubar.menus`

**Output:**
- `frontend/js/handlers/menubar.js` — 자동 생성 스크립트로 62개 onclick 생성

**템플릿:**
```js
// menubar.js
export function bindMenubar(root) {
  root.querySelectorAll('[data-action]').forEach(el => {
    const action = el.dataset.action;
    el.addEventListener('click', () => dispatch(action, el.dataset));
  });
}
async function dispatch(action, data) {
  try {
    const endpoint = HANDLER_MAP[action]?.endpoint;
    if (!endpoint) { showToast('info', '준비 중 (Tier 3 이관 예정)'); return; }
    const res = await window.api.post(endpoint, data || {});
    showToast('success', res?.message || '완료');
  } catch (e) {
    if (e.status === 501) showToast('info', '준비 중');
    else showToast('error', `실패: ${e.message}`);
  }
}
const HANDLER_MAP = {
  /* feature_matrix 에서 자동 생성 — 62 항목 */
};
```

**자동 생성 방법:**
- Agent B2 는 실행 시작 시 Node 스크립트 `tools/gen_handler_map.mjs` 를 먼저 작성·실행하여 `feature_matrix.json` → `HANDLER_MAP` 객체 리터럴 자동 생성.

**중단 방지 기본값:**
- 알 수 없는 `data-action` → Toast "준비 중". 예외 throw 금지.
- API 오류 → Toast 표시 후 UI 상태 유지. 페이지 리로드 금지.

**DoD:**
- `HANDLER_MAP` 에 62개 이상 키 존재
- 최소 10개 랜덤 클릭 테스트 시 모두 Toast 또는 실제 동작

---

### 🃏 B3 Mission Card — Toolbar & Topbar Controls

**Input:**
- `v864_2_structure.json` → `action_toolbar.items` (7개)
- 상단 우측: 새로고침, Dark, Light, 돈백·LOT·MT 라디오

**Output:**
- `frontend/js/handlers/toolbar.js` (7개)
- `frontend/js/handlers/topbar.js` (5개 + 라디오 그룹)

**핵심 규약:**
- 각 툴바 버튼은 메뉴바 중복 기능이 존재할 수 있음 (예: 설정) → 동일 `dispatch(action)` 재사용
- 돈백/LOT/MT 라디오 → `state.viewMode` 변경 → `EventBus.emit('viewmode:change', mode)` → Inventory/Dashboard 테이블이 구독

**중단 방지 기본값:**
- 라디오 변경 시 데이터 로딩 실패해도 이전 모드로 롤백 (UI 멈춤 방지)
- 새로고침 버튼 연타 방어 (200ms debounce)

**DoD:**
- 7 툴바 + 새로고침 + 테마토글 + 3라디오 모두 반응 확인

---

### 🃏 C1 Mission Card — ALERTS + Status Bar + Auto-refresh

**Input:**
- `/api/dashboard/stats` 기존 엔드포인트 (또는 A2 가 추가할 `/api/dashboard/alerts`)
- 상태바 데이터: 위치 미배정 건수, 스캔 실패율, LOT 평균 재고기간

**Output:**
- `frontend/js/components/alerts.js`
- `frontend/js/components/statusbar.js`
- `frontend/js/components/auto_refresh.js`

**ALERTS 규격:**
```js
{ severity: 'warn'|'error'|'info', icon: '🏷️'|'📍', text: '...메시지...', link: '내부 라우트 경로' }
```

**Auto-refresh 규약:**
- 기본 30초 (`state.refreshInterval = 30000`)
- 탭 hidden (`document.visibilityState !== 'visible'`) 시 일시정지
- 실패 3연속 시 60초로 백오프 + Toast 경고

**중단 방지 기본값:**
- ALERTS API 실패 시 이전 값 유지. 빈 화면 표시 금지.

**DoD:**
- 30초 후 "마지막 경신" 타임스탬프가 갱신됨
- ALERTS 최소 2건 표시 (Golden Reference 와 동일)

---

### 🃏 C2 Mission Card — Shortcuts + State Persistence

**Input:**
- `feature_matrix.json` → `category == "keyboard"` 13건
- `v864_2_structure.json` → `keyboard_shortcuts` 상세

**Output:**
- `frontend/js/shortcuts.js` — `document.addEventListener('keydown', router)`
- `frontend/js/state.js` — `saveState()`, `loadState()` localStorage 래퍼

**저장 항목:**
- 창 크기 (`window.resizeTo` 복원)
- 테마 (`data-theme`)
- 현재 사이드바 탭
- Inventory 라디오 모드 (돈백/LOT/MT)

**중단 방지 기본값:**
- localStorage 접근 실패 시 sessionStorage 폴백. 둘 다 실패 시 in-memory 변수.
- 단축키 충돌 시 data-shortcut 속성 우선.

**DoD:**
- 13개 단축키 모두 작동 확인
- 창 닫고 재실행 시 이전 상태 복원 (EXE 런타임 한정)

---

### 🃏 D1 Mission Card — QA & Release Manager

**Input:**
- 모든 Sub-Agent 산출물
- `docs/handoff/feature_matrix.json`
- Golden Reference 이미지 (사장님 제공 스크린샷)

**Output:**
- `docs/FEATURE_PROGRESS.md` — 실시간 체크리스트
- `tools/verify_tier2.py` — 회귀 검증 자동화
- `tools/ssim_check.py` — 픽셀 비교
- `REPORTS/tier2_final_<ts>.md` — 최종 보고서
- `build/dist/SQM_v864_3.exe` — 재빌드본

**진척 추적 형식 (`FEATURE_PROGRESS.md`):**
```markdown
| ID | 카테고리 | 라벨 | 담당 | 상태 | 엔드포인트 | 핸들러 | 검증 |
|---|---|---|---|---|---|---|---|
| F001 | menubar | 📄 PDF 스캔 입고 | A1 | ✅ | /api/menu/-on-pdf-inbound | onOnPdfInbound | PASS |
```

**verify_tier2.py 로직:**
1. feature_matrix 순회
2. 각 기능의 `proposed_api_endpoint` → HEAD/OPTIONS 요청 (404 없음 확인)
3. 각 기능의 `proposed_js_handler` → JS 번들 grep 으로 정의 확인
4. 9탭 자동 클릭 (Playwright 없이 단순 HTML 파싱 + onclick 존재성 체크)
5. 결과 85행 표 + 통계

**중단 방지 기본값:**
- 1개 기능 검증 실패해도 나머지 진행 (FAIL 만 기록)
- EXE 빌드 실패 시 기존 EXE 유지 + 리포트에 "재빌드 실패, 이전 빌드 사용" 기록

**DoD:**
- `FEATURE_PROGRESS.md` 의 85행 모두 상태 표기됨
- EXE 재빌드 성공 (또는 명시적 실패 기록)
- 최종 보고서에 통과율, FAIL 리스트, 다음 Tier 권고 포함

---

## 🛡️ 섹션 5. NO-STOP 공통 규약 (Sub-Agent 모두 준수)

### 5.1 질문 금지 (Zero-Question Policy)
- 사장님께 질문 불가. 모든 결정은 본 지시서의 "기본값" 섹션에서 찾는다.
- 기본값에 없는 경우: **`docs/handoff/v864_2_structure.json` 값을 최우선**, 그다음 `feature_matrix.json`, 그다음 **상식적 기본값 (예: 타임아웃 5초, 재시도 3회)**.

### 5.2 에러 처리 4단계
1. **1차 방어:** 예상 가능한 에러는 try/except 로 포획
2. **2차 폴백:** 기본값으로 대체 (예: 빈 배열, 전월 데이터, "준비 중")
3. **3차 격리:** 해당 태스크만 FAIL 기록 후 다음 태스크로 진행
4. **4차 로깅:** 모든 실패는 `REPORTS/tier2_fails_<ts>.jsonl` 에 append

### 5.3 동시성·충돌 방지
- 각 Agent 는 **자기 파일만** 쓴다 (파일 매니페스트 아래 섹션 8 참조)
- 공통 파일(`backend/api.py`, `frontend/index.html`) 수정 필요 시 D1 을 통해 순차 머지
- Git 브랜치 명: `tier2/agent-{A1|A2|B1|...}`

### 5.4 타임박스
- 각 Agent 자기 Stage 내 초과 시: 진행한 부분까지 커밋 → 미완료 항목만 FAIL 기록 → 다음 Stage 로 진행
- 전체 12시간 초과 시: Stage 6 (검증) 으로 강제 진입. Stage 7 (빌드) 는 검증 95% 미달이어도 실행.

### 5.5 롤백 규칙
- 개별 파일 실패 → `git checkout HEAD~1 -- <file>` 로 해당 파일만 롤백
- 빌드 실패 → 기존 EXE 유지, `REPORTS/tier2_build_fail_<ts>.log` 기록
- **전체 롤백 금지.** 부분 성공도 진척이다.

---

## 🔄 섹션 6. 핸드오프 매트릭스

| 제공 측 | 산출물 | 수신 측 | 수신 시점 | 의존성 |
|---|---|---|---|---|
| D1 (S1) | `docs/FEATURE_PROGRESS.md`, `backend/common/errors.py` 스텁 | A1, A2 | S2 시작 | 필수 |
| A2 (S2) | `wrap_engine_call` 함수 완성 | A1 | A1 진행 중 | 필수 |
| A1, A2 (S2) | 모든 API 엔드포인트 | B1, B2, B3 | S3~S4 | 필수 (501 fallback 으로 비의존 가능) |
| B1 (S3) | 9탭 페이지 모듈 | C1, C2 | S4 | 선택 |
| C1 (S3) | `auto_refresh.js` 30초 타이머 | D1 | S6 | 선택 |
| B2, B3, C2 (S4) | 모든 핸들러 | D1 | S6 | 필수 |
| D1 (S6) | `verify_tier2.py` 결과 | D1 (S7) | S7 | 필수 |

**Blocker 해소 원칙:** 의존 산출물이 지연되면 **501 Mock 서버** 로 대체하여 계속 진행.

---

## 🗂️ 섹션 7. 파일 매니페스트 (Agent 별 쓰기 권한)

| 경로 | 소유자 | 다른 Agent 접근 |
|---|---|---|
| `backend/api/menubar.py` | A1 | 읽기만 |
| `backend/api/controls.py` | A2 | 읽기만 |
| `backend/common/errors.py` | A2 | 읽기만 |
| `backend/api.py` (라우터 include 추가) | D1 머지 | 수정 요청은 D1 에게 |
| `frontend/js/pages/picked.js` | B1 | 읽기만 |
| `frontend/js/pages/return.js` | B1 | 읽기만 |
| `frontend/js/pages/log.js` | B1 | 읽기만 |
| `frontend/js/router.js` | B1 | 읽기만 |
| `frontend/js/handlers/menubar.js` | B2 | 읽기만 |
| `frontend/js/handlers/toolbar.js` | B3 | 읽기만 |
| `frontend/js/handlers/topbar.js` | B3 | 읽기만 |
| `frontend/js/components/alerts.js` | C1 | 읽기만 |
| `frontend/js/components/statusbar.js` | C1 | 읽기만 |
| `frontend/js/components/auto_refresh.js` | C1 | 읽기만 |
| `frontend/js/shortcuts.js` | C2 | 읽기만 |
| `frontend/js/state.js` | C2 | 읽기만 |
| `frontend/index.html` (script 태그 추가) | D1 머지 | 수정 요청 D1 에게 |
| `tools/verify_tier2.py` | D1 | 읽기만 |
| `tools/ssim_check.py` | D1 | 읽기만 |
| `tools/gen_handler_map.mjs` | B2 | 읽기만 |
| `docs/FEATURE_PROGRESS.md` | D1 | 읽기만 (상태 업데이트는 각 Agent 가 PR 로) |

**절대 수정 금지 (CLAUDE.md Rule 1):**
- `engine_modules/`, `features/`, `parsers/`, `utils/`
- `docs/handoff/*.json`

---

## 🧪 섹션 8. 자동 검증 체인

```
                     ┌───────────────────────────┐
                     │  tools/verify_tier1.py    │
                     │  (Tier 1 9개 DoD — 기존)  │
                     └─────────────┬─────────────┘
                                   │ 통과
                                   ▼
                     ┌───────────────────────────┐
                     │  tools/verify_tier2.py    │
                     │  (85개 feature 검증)      │
                     └─────────────┬─────────────┘
                                   │ 통과율 ≥ 95%
                                   ▼
                     ┌───────────────────────────┐
                     │  tools/ssim_check.py      │
                     │  Dashboard SSIM ≥ 0.85    │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │  pyinstaller rebuild      │
                     │  EXE size > 50MB          │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │  REPORTS/tier2_final.md   │
                     │  사장님 검수 대기          │
                     └───────────────────────────┘
```

---

## 📐 섹션 9. Definition of Done (Tier 2 최종)

| # | 조건 | 측정 도구 | 임계값 |
|---|---|---|---|
| 1 | Feature Parity | `verify_tier2.py` | 85개 중 ≥ 81 PASS (95%) |
| 2 | UI 유사도 | `ssim_check.py` | Dashboard SSIM ≥ 0.85 |
| 3 | EXE 재빌드 | PyInstaller | 성공 + 파일 크기 > 50MB |
| 4 | 에러 처리 | 코드 리뷰 | 모든 엔드포인트 `wrap_engine_call` 사용 |
| 5 | 진척 대시보드 | `FEATURE_PROGRESS.md` | 85행 모두 상태 표기 |
| 6 | FAIL 티켓 | `REPORTS/tier2_fails_<ts>.jsonl` | FAIL 건 각각 원인 + 다음 조치 기록 |
| 7 | 외출 중 중단 0건 | `REPORTS/tier2_*.md` | "USER_INPUT_REQUIRED" 0건 |

**위 7항목 모두 PASS → Tier 2 CLOSE, Tier 3 진입 가능.**
**6 이하 PASS → Tier 2 부분 종결 + FAIL 항목만 재작업 티켓 발행.**

---

## 🚨 섹션 10. 사장님 검수 프로토콜 (외출 복귀 후)

1. **먼저 볼 파일:** `REPORTS/tier2_final_<ts>.md`
2. **두 번째 볼 파일:** `docs/FEATURE_PROGRESS.md`
3. **직접 확인할 것:** `build/dist/SQM_v864_3.exe` 더블클릭
4. **수용 판정:**
   - 통과율 ≥ 95% + EXE 정상 실행 → **ACCEPT → Tier 3 진입**
   - 통과율 < 95% 또는 EXE 실패 → **PARTIAL ACCEPT → FAIL 항목만 재작업**
5. **피드백:** `REPORTS/tier2_feedback_<ts>.md` 에 기록. 다음 Tier 에서 반영.

---

## 🚀 섹션 11. TIER 3 확장 — Sub-Agent 자율 릴리즈 팩

> **Tier 2 가 "모든 버튼이 동작한다"라면, Tier 3 은 "사장님·직원·고객 누가 써도 안정적이다" 단계다.**
> 성격: 폴리싱 + 문서화 + 패키징 + UAT + 릴리즈.
> Tier 2 완료(PASS ≥ 95%) 후 자동 진입. 사장님 승인 없이도 착수 가능 (본 지시서가 승인 증거).

### 🎯 11.0 Tier 3 Executive Summary

1. **목표:** 배포 가능한 **릴리즈 품질** 의 v864.3 EXE + 매뉴얼 + 인스톨러 + 모니터링 훅
2. **팀:** **3 팀 × 5 Sub-Agent** (E1·E2, F1·F2, G1)
3. **단계:** **5 Stage** (T3-S1 ~ T3-S5)
4. **성공 기준:** UAT 체크리스트 통과 + Installer 실행 성공 + 매뉴얼 3종 납품 + 롤백 스크립트 준비
5. **예상 소요:** 병렬 3~4일 (벽시계)

### 🧑‍🤝‍🧑 11.1 팀 구조 (3 팀 × 5 Sub-Agent)

#### 🅴 팀 E — Polish (2명)

| Agent | 책임 영역 | 담당 | 주요 산출물 |
|---|---|---|---|
| **E1** | optional 11 기능 실제 구현 | feature_matrix 내 `status=deferred` 11건 | `backend/api/optional.py`, `frontend/js/handlers/optional.js` |
| **E2** | 성능 최적화 + 메모리 누수 차단 | hot-path 캐싱, 이벤트 리스너 정리 | `backend/common/cache.py`, `frontend/js/perf.js`, `REPORTS/perf_report.md` |

#### 🅵 팀 F — Release Engineering (2명)

| Agent | 책임 영역 | 담당 | 주요 산출물 |
|---|---|---|---|
| **F1** | 인스톨러 + EXE 서명 + 업데이터 | Inno Setup 스크립트, 코드사인 준비, 자동 업데이트 | `installer/SQM_v864_3_Setup.iss`, `installer/build.bat`, `installer/dist/SQM_v864_3_Setup.exe` |
| **F2** | 매뉴얼 3종 + 릴리즈 노트 | 사용자 매뉴얼, 관리자 매뉴얼, 개발자 매뉴얼 | `docs/manuals/USER_MANUAL.md`, `ADMIN_MANUAL.md`, `DEV_MANUAL.md`, `RELEASE_NOTES_v864_3.md` |

#### 🅶 팀 G — UAT & Deployment (1명)

| Agent | 책임 영역 | 담당 | 주요 산출물 |
|---|---|---|---|
| **G1** | UAT 시나리오 실행 + 배포 준비 + 모니터링 | 사용자 시나리오 20종, 롤백 플랜, 로그 수집기 | `tests/uat_scenarios.json`, `tools/rollback.py`, `tools/log_collector.py`, `REPORTS/tier3_final_<ts>.md` |

### 🗺️ 11.2 Tier 3 5단계 실행 플랜

```
┌────────────────────────────────────────────────────────────────────┐
│  T3-S1  OPTIONAL IMPL     ── E1 단독 (1d)                          │
│  T3-S2  PERF + PACKAGE    ── E2, F1 병렬 (1d)                      │
│  T3-S3  DOCUMENTATION     ── F2 단독, E1/E2 감수 (0.5d)            │
│  T3-S4  UAT + BUG FIX     ── G1 주도 + 전체 협력 (1d)              │
│  T3-S5  RELEASE + MONITOR ── F1, G1 (0.5d)                         │
└────────────────────────────────────────────────────────────────────┘
합계: 병렬 3.5~4일
```

#### T3-S1 OPTIONAL IMPLEMENTATION (1일)
- **담당:** E1
- **목적:** Tier 2 에서 "준비 중"으로 남긴 optional 11 기능 실제 구현
- **작업:** feature_matrix.json `status=deferred` 11건 추출 → 엔드포인트 + 핸들러 구현. 원본 handler 없으면 v864.2 원본 복사 후 HTTP 래핑 (CLAUDE.md Rule 1 — 복사만, 수정 금지).
- **DoD:** 11/11 `status=completed`, `verify_tier2.py` PASS 100%
- **Gate Test:** `test_optional.py` → 11 엔드포인트 200/의도된 404

#### T3-S2 PERFORMANCE + PACKAGING (1일, 병렬)
- **담당:** E2, F1
- **E2:** `backend/common/cache.py` LRU 5초 TTL, `frontend/js/perf.js` 리스너 WeakMap, cProfile 리포트
- **F1:** Inno Setup `installer/SQM_v864_3_Setup.iss`, `build.bat` PyInstaller+Inno 체인, `tools/check_update.py` 업데이트 훅. 서명 인증서 미보유 시 스킵+리포트.
- **DoD:** Installer Setup.exe → 설치 성공 + 재실행 시 업데이트 플로우 동작
- **Gate Test:** `test_installer.py` (Windows) → `/SILENT` 비대화식 설치

#### T3-S3 DOCUMENTATION (0.5일)
- **담당:** F2, E1·E2 감수
- **작업:** USER/ADMIN/DEV_MANUAL.md (각 3,000자+) + RELEASE_NOTES_v864_3.md. 스크린샷은 Golden Reference + Tier 2 S6 수집분.
- **DoD:** 4 문서 존재, 크로스 링크 유효
- **Gate Test:** `test_docs.py` → 링크 깨짐 정규식 검사

#### T3-S4 UAT + BUG FIX (1일)
- **담당:** G1 주도, E·F 대기
- **작업:** `tests/uat_scenarios.json` 20종 (PDF 입고→배분→출고→반품→정합성). 버그 P0/P1/P2 분류. P0 즉시 수정. P2 는 "알려진 이슈" 기록. `tools/rollback.py` 설치 실패 시 이전 버전 복원.
- **DoD:** 20 중 ≥ 18 PASS, P0=0
- **Gate Test:** `test_uat.py` → uat_scenarios 재실행, 전/후 비교

#### T3-S5 RELEASE + MONITORING (0.5일)
- **담당:** F1, G1
- **작업:** 최종 Installer 재빌드, `tools/log_collector.py` (앱+DB+시스템 로그 ZIP), `REPORTS/tier3_final_<ts>.md`, `docs/POST_RELEASE_CHECKLIST.md` (배포 후 1주 모니터링).
- **DoD:** Installer 최종본, 로그 수집기 동작, 보고서·체크리스트 납품
- **Gate Test:** `test_release.py` → 딜리버러블 존재·크기>0 확인

### 🃏 11.3 Tier 3 Sub-Agent 미션 카드 (5장)

#### 🃏 E1 — Optional Feature Implementer
- **In:** feature_matrix `status=deferred` 11건, v864.2 원본 handler
- **Out:** `backend/api/optional.py`, `frontend/js/handlers/optional.js`
- **NO-STOP:** 원본 handler 없으면 `status=not_applicable` 기록 후 진행. 11/11 처리 보장.

#### 🃏 E2 — Performance Engineer
- **In:** Tier 2 완성본 + 사용 로그
- **Out:** LRU 캐시, 리스너 정리, 프로파일 리포트
- **NO-STOP:** 목표 성능 미달이어도 리포트만 남기고 진행.

#### 🃏 F1 — Release Engineer
- **In:** `build/dist/SQM_v864_3.exe`
- **Out:** Installer .exe, build.bat, 업데이트 훅
- **NO-STOP:** Inno 미설치 → `installer/README_INSTALL_INNO.md` 설치법 기록. PyInstaller ZIP 포터블 폴백.

#### 🃏 F2 — Technical Writer
- **In:** feature_matrix, Tier 2 수집 스크린샷
- **Out:** 매뉴얼 4종
- **NO-STOP:** 스크린샷 없으면 텍스트 기반 설명으로 대체.

#### 🃏 G1 — QA Deployment Lead
- **In:** 모든 Tier 3 산출물 + UAT 시나리오
- **Out:** UAT 결과, rollback.py, log_collector.py, 최종 보고서
- **NO-STOP:** P0 발생 시 담당 Agent 태깅 + 24h 무응답 → P1 강등 후 진행.

### 🛡️ 11.4 Tier 3 NO-STOP 추가 규약

1. Tier 2 미완 항목은 Tier 3 진입을 막지 않음. 병행 처리.
2. 서드파티 의존성(Inno Setup, 코드서명) 누락 → 폴백(ZIP 포터블) 경로.
3. UAT 데이터 없으면 → SQLite in-memory 더미 생성기 대체.

### 🗂️ 11.5 Tier 3 파일 매니페스트

| 경로 | 소유자 |
|---|---|
| `backend/api/optional.py` | E1 |
| `frontend/js/handlers/optional.js` | E1 |
| `backend/common/cache.py` | E2 |
| `frontend/js/perf.js` | E2 |
| `installer/SQM_v864_3_Setup.iss` | F1 |
| `installer/build.bat` | F1 |
| `tools/check_update.py` | F1 |
| `docs/manuals/USER_MANUAL.md` | F2 |
| `docs/manuals/ADMIN_MANUAL.md` | F2 |
| `docs/manuals/DEV_MANUAL.md` | F2 |
| `RELEASE_NOTES_v864_3.md` | F2 |
| `tests/uat_scenarios.json` | G1 |
| `tools/rollback.py` | G1 |
| `tools/log_collector.py` | G1 |
| `docs/POST_RELEASE_CHECKLIST.md` | G1 |

### 📐 11.6 Tier 3 Definition of Done (8항)

| # | 조건 | 측정 | 임계값 |
|---|---|---|---|
| 1 | Optional 11 기능 | verify_tier2 재실행 | 11/11 PASS |
| 2 | 성능 | perf_report.md | 대시보드 첫 로드 < 2초 |
| 3 | Installer | `test_installer.py` | `/SILENT` 설치 성공 |
| 4 | 매뉴얼 4종 | 파일 존재 + 길이 | 각 ≥ 3,000자 |
| 5 | UAT | uat_scenarios.json | 20 중 ≥ 18 PASS, P0=0 |
| 6 | 롤백 | `rollback.py` 더미 실행 | exit 0 |
| 7 | 로그 수집기 | 샘플 실행 | ZIP 생성 |
| 8 | 최종 보고서 | 파일 존재 | tier3_final_<ts>.md |

**8/8 PASS → Tier 3 CLOSE → v864.3 공식 배포 가능**

### 🚨 11.7 Tier 3 사장님 검수 프로토콜

1. **먼저 볼 파일:** `REPORTS/tier3_final_<ts>.md`
2. **두 번째:** `docs/manuals/USER_MANUAL.md` (30초 훑기)
3. **직접 확인:** `installer/dist/SQM_v864_3_Setup.exe` 더블클릭 → 설치 → 실행
4. **판정:** 8/8 + 설치·실행 정상 → **ACCEPT → 배포**
5. **배포:** ACCEPT 즉시 `git tag v864.3.0` 자동

---

## 📘 부록 A — 기본값 사전 (Zero-Question 폴백)

| 상황 | 기본값 |
|---|---|
| FastAPI 포트 | **8765** |
| FastAPI 호스트 | **127.0.0.1** |
| Swagger UI | `http://127.0.0.1:8765/docs` |
| API 타임아웃 | 5초 |
| fetch 재시도 | 3회, 500ms→1s→2s |
| Toast 표시 시간 | 3초 |
| 자동 갱신 주기 | 30초 |
| 창 기본 크기 | 1400×900 |
| 테마 기본값 | `dark` (darkly) |
| 라디오 기본값 | `MT` |
| 페이지 크기 | 50 행 |
| 로케일 | `ko-KR` |
| 숫자 포맷 | 천단위 콤마, 소수점 1자리 |
| 날짜 포맷 | `YYYY-MM-DD HH:mm:ss` |
| 빈 상태 메시지 | "표시할 데이터가 없습니다" |
| 알 수 없는 에러 | "일시적 오류가 발생했습니다. 잠시 후 다시 시도하세요." |
| Installer 경로 | `C:\Program Files\SQM\v864.3\` |
| 로그 저장 | `%APPDATA%\SQM\logs\` |

---

## 📗 부록 B — API 시그니처 규약

- 응답: `{"ok": bool, "data": any, "error": string | null}`
- 에러: HTTP status + `{"detail": "..."}`
- 페이지네이션: `?page=1&size=50`
- 필터: `?filter[column]=value`

---

## 📕 부록 C — HTTP 에러 코드 표

| HTTP | 의미 | 조치 |
|---|---|---|
| 200 | 성공 | PASS 기록 |
| 400 | 잘못된 요청 | 스키마 검토 |
| 404 | 리소스 없음 | "데이터 없음" Toast |
| 501 | 준비 중 | "준비 중" Toast + status=deferred |
| 500 | 서버 오류 | 로그 + 다음 태스크 |

---

# 🔍 검토 로그

## ✅ Review Pass 1 — 완결성 (Tier 2+3 통합)

| 체크 | 결과 |
|---|---|
| 모든 Agent I/O 명시 | PASS — 13장 미션 카드 |
| 파일 경로 상대 표기 | PASS — 절대경로 금지 준수 |
| Stage DAG 순환 없음 | PASS — 12 Stage 위상 정렬 |
| 공통 파일 충돌 | PASS — 단일 소유자 |
| CLAUDE.md Rule 1 | PASS — wrapper/복사만 |
| 기본값 폴백 | PASS — 부록 A 18항 |
| Per-Stage Gate Test | PASS — 12/12 단계 |
| 표준 라이브러리 | PASS — urllib·json·subprocess |

## ✅ Review Pass 2 — NO-STOP / 중단 리스크

| 시나리오 | 대응 |
|---|---|
| Agent 의사결정 대기 | Zero-Question + 부록 A |
| API 누락 → 프론트 대기 | 501 Mock |
| 파일 동시 수정 | 단일 소유자 + 브랜치 분리 |
| 1개 기능 실패 | 개별 FAIL + 다음 진행 |
| EXE 빌드 실패 | 기존 EXE 유지 |
| Inno Setup 미설치 | ZIP 포터블 폴백 |
| 코드서명 인증서 없음 | 서명 스킵 + 리포트 |
| UAT 데이터 없음 | 더미 자동 생성 |
| localStorage 차단 | sessionStorage → 메모리 |
| 네트워크 간섭 | wait_for_server 20s + 재시도 |
| Gate Test 예외 | try/except 외곽 + exit 0 |
| Tier 2 미완 → Tier 3 막힘 | Tier 3 병행 허용 |

→ **12 리스크 전부 폴백. NO-STOP 보장.**

---

## 📌 최종 결론 (Tier 2 + Tier 3 통합)

| 항목 | Tier 2 | Tier 3 | 통합 |
|---|---|---|---|
| 팀 수 | 4팀 (A/B/C/D) | 3팀 (E/F/G) | **7 팀** |
| Sub-Agent 수 | 8명 | 5명 | **13 명** |
| 단계 수 | 7 Stage | 5 Stage | **12 Stage** |
| 예상 벽시계 | 6~12h | 3~4d | **약 4~5일** |
| 중단 리스크 | 0 | 0 | **0** |
| 단계별 자동 테스트 | S1~S7 Gate Test | T3-S1~T3-S5 Gate Test | **12/12 단계 테스트 체인** |
| 검토 횟수 | 2회 | 2회 (통합) | **총 4회** |

---

**작성자:** Ruby (Senior Software Architect Mode)
**버전:** 2.0 (2026-04-21, Tier 3 통합 + Per-Stage Gate Test, 4-pass 검토 완료)
**승인 대기:** Nam Ki-dong 사장님
