# SQM Inventory v8.7.1 — Popout Windows (분리 창)

**Release date**: 2026-05-27
**Branch**: `claude/v864-3-sprint0`
**Author**: Nam Kidong with Claude (Opus 4.7)

---

## 🎯 핵심 문제 (사용자 보고)

> "입고 서류 파싱할 때 파싱 결과창과 진행 로그창이 **겹쳐서 잘 보이지 않고**,
>  메인 창 밖으로 **드래그해도 잘려서** 듀얼 모니터로 빼낼 수 없어."

### 근본 원인
1. **겹침** — 두 창 모두 `position: fixed` 였고 기본 좌표가 충돌
   - 파싱 결과: `left:50%; width:min(1450px,96vw)` (가운데, 거의 전체 폭)
   - 파싱 로그: `top:130px; right:28px; width:340px` (우측 상단)
   - → 결과창 우측 위에 로그창이 그대로 얹혀짐 (z-index 10051 vs 10050)
2. **클리핑** — HTML `<div>` 는 PyWebView OS 창의 뷰포트 밖으로 나갈 수 없는 본질적 제약. 종이 밖으로 그릴 수 없는 것과 같음.

---

## ✨ 새 기능: 🪟 Popout (분리 창)

모든 떠다니는 패널의 헤더에 🪟 버튼이 추가되었습니다. 클릭하면 패널이
**별도 OS 창**으로 분리되어 다음이 가능합니다:

- ✅ 메인 창 **밖으로 자유롭게 이동** (좌·우·상·하 어디든)
- ✅ **듀얼 모니터** 두 번째 화면으로 이동
- ✅ 메인 창보다 더 크게 리사이즈
- ✅ 메인 창과 **독립적으로 최소화/최대화**

### 적용된 패널 (9개)

| 패널 | Key | 라이브 미러링 | 위치 |
|---|---|---|---|
| 📊 파싱 결과 | `parse-result` | ✅ tbody 라이브 sync | `sqm-onestop-inbound.js` |
| ⚙️ 파싱 진행 로그 | `parse-log` | ✅ 로그 row 라이브 sync | `sqm-onestop-inbound.js` |
| 🔍 Gemini 비교 | `gemini-compare` | 스냅샷 | `sqm-onestop-inbound.js` |
| 🏭 창고 셀 대시보드 | `wh-dashboard` | 스냅샷 | `sqm-warehouse-dashboard.js` |
| 📋 리스트 뷰 | `listview` | 스냅샷 | `sqm-listview.js` |
| 🗺️ 위치 매핑 | `location-mapping` | 스냅샷 | `sqm-location-mapping.js` |
| 📥 위치재고 임포트 | `location-map-import` | 스냅샷 | `sqm-location-map-import.js` |
| 🔄 Case 3 잔량 처리 | `case3-dialog` | 스냅샷 | `sqm-case3-dialog.js` |
| 🗂️ 메인 데이터 모달 | `data-modal` | 스냅샷 | `sqm-util-modal.js` (showDataModal 전체) |

**라이브 미러링** = 메인에서 데이터가 갱신되면 분리 창 내용도 SSE 로 자동 업데이트
**스냅샷** = 분리 시점의 HTML 을 그대로 표시. 버튼 클릭 → 메인으로 라우팅됨

### 동시 겹침 해소 (위치 기본값 조정)

분리 창과 별개로, 메인 창 안에서의 기본 위치도 겹치지 않도록 재배치:

- **파싱 결과창** — `width: min(1200px, 70vw)` 로 축소, 좌측 정렬 (`left:12px`)
- **파싱 로그창** — 우측 상단 → **우측 하단** (`bottom:18px; right:18px`)
- → 두 창이 좌·우로 나란히 배치되어 겹치지 않음

---

## 🏗 아키텍처

### 신규 파일

**Backend**
- `backend/api/popout.py` — Pub/Sub 라우터 (SSE 기반)
  - `POST /api/popout/snapshot/{key}` — 분리 창 초기 HTML 저장
  - `GET /api/popout/snapshot/{key}` — 분리 창이 fetch
  - `POST /api/popout/m2d/{key}` — 메인 → 분리 창 이벤트
  - `GET /api/popout/m2d/{key}/stream` — 분리 창 SSE 구독
  - `POST /api/popout/d2m/{key}` — 분리 창 → 메인 이벤트
  - `GET /api/popout/d2m/{key}/stream` — 메인 SSE 구독
  - `POST /api/popout/clear/{key}` — 채널 클리어

**Frontend**
- `frontend/popout.html` — 분리 창 호스트 페이지 (테마 CSS 만 로드)
- `frontend/js/sqm-detached-host.js` — 분리 창에서 실행, 스냅샷 inject + SSE 구독
- `frontend/js/sqm-popout.js` — 메인 창의 popout helper (`window.sqmPopOut`, `sqmAddPopOutBtn` 등 노출)

### 데이터 흐름

```
[메인 창]                          [백엔드]                     [분리 창]
   │                                  │                            │
   │  🪟 클릭                          │                            │
   ├─POST /snapshot/{key}─────────────▶│                            │
   │                                  │                            │
   ├──pywebview.api.open_detached────▶ (새 OS 창 생성)              │
   │                                  │                            │
   │                                  │   GET /popout.html?key=... │
   │                                  │◀───────────────────────────┤
   │                                  │   GET /snapshot/{key}      │
   │                                  │◀───────────────────────────┤
   │                                  │───────────HTML────────────▶│
   │                                  │                            │
   │  데이터 갱신 →                    │                            │
   ├─POST /m2d/{key}─────────────────▶│ ────SSE event─────────────▶│ (라이브 업데이트)
   │                                  │                            │
   │                                  │ ◀────POST /d2m/{key}───────┤ (버튼 클릭)
   │◀─────SSE event ──────────────────┤                            │
   │  (eval action expression)        │                            │
   │                                  │                            │
   │                                  │ ◀──beforeunload close──────┤
   │◀──SSE {type:'close'}─────────────┤                            │
   │  (원본 패널 복원)                  │                            │
```

### 액션 라우팅 원리

분리 창은 메인 앱의 거대한 JS 번들을 로드하지 **않으므로** `onclick="window.foo()"` 의 `foo` 는 정의되어 있지 않다. 대신:

1. 분리 창 호스트는 모든 `click` / `input` 을 capture phase 에서 가로챔
2. `onclick` 속성 문자열 (예: `"window.onestopUndo()"`) 을 추출
3. `POST /api/popout/d2m/{key}` 로 메인에 전송
4. 메인의 SSE 구독이 expression 을 받아 indirect `eval` 로 메인 컨텍스트에서 실행

이로써 모든 기존 inline `onclick` 핸들러가 분리 창에서도 자연스럽게 동작합니다.

---

## 🛠 기타 변경

### Baseline fix (이전 커밋 `28880ce`)
- `backend/api/inbound.py` — `google-genai` `Part.from_text` 에 `text=` kwarg 누락 수정 (TypeError 방지)
- `frontend/js/sqm-onestop-inbound.js` — DB 파싱 템플릿 라벨에서 "❌ 미설정" 빨간 경고 제거, 빈 상태로 단순화 + `_clearDbTemplateLabel` 헬퍼 추출, 단일 템플릿 자동 적용 로직 제거 (항상 사용자 명시 선택)
- `.gitignore` — `sqm_v870_clean/.bkit/`, `window_state.json` 런타임 상태 제외

---

## 🧪 검증

- ✅ Python syntax: `backend/api/popout.py`
- ✅ JS syntax (node --check): 6개 수정 파일 + 2개 신규 파일
- ✅ FastAPI 라우터 로딩: `popout router loaded OK (/api/popout/*)`
- ✅ TestClient 통합 테스트: snapshot CRUD + m2d + d2m + status + clear 전부 200
- ⏳ 실제 PyWebView 환경 라이브 테스트 — 사용자 확인 필요 (`run.bat` 또는 `python main_webview.py`)

---

## 🚧 알려진 제약

1. **편집 양방향 동기화 미구현**
   - 파싱 결과창의 셀 더블클릭 편집은 메인에서만 실행됨
   - 분리 창에선 클릭 → 메인에서 모달 열림 → 분리 창이 가려질 수 있음
   - v8.7.2 에서 분리 창 내부 편집 모달 처리 예정

2. **다중 popout 미지원**
   - 같은 key 로 두 번 호출 시 기존 창이 포커스만 됨 (의도된 동작)
   - 다른 key 의 popout 들은 동시 가능

3. **새로고침 시 분리 창 끊김**
   - 메인 페이지 새로고침 → 채널 메모리 휘발 → 분리 창은 ❌ 표시
   - 분리 창의 ✕ 닫기로 회수 가능

4. **일반 브라우저 환경**
   - `pywebview.api` 가 없으면 `window.open()` 폴백 — 작동은 하나 OS 창 분리 불가, 단지 브라우저 새 탭/팝업
