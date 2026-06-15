# SQM Inventory v8.8.1 — 따뜻한 테마 · 라이트 모드 정합 · 회귀 수정

**릴리즈 날짜**: 2026-06-15
**브랜치**: `claude/debugging-session-optimization-t3ayma`
**이전 버전**: v8.8.0
**테스트**: 325 passed / 1 deselected (headless 기준, 회귀 무영향)

---

## 🎯 개요

v8.8.0(디버깅 백로그 전수 조치) 직후 진행한 **전수 검사에서 회귀 1건을 발견·수정**하고,
사용자 요청(“너무 검고 너무 밝아 보기 힘들다”)에 따라 **따뜻한 테마**를 적용했습니다.
그 과정에서 라이트 모드가 다크 전용 스타일에 덮여 깨지던 문제를 함께 정합시키고,
혼동을 주던 레이아웃 CSS 파일명을 정리했습니다. **로직/데이터 동작 변경은 없습니다.**

---

## 🔴 회귀 수정 (데이터 흐름)

### 반품 재입고 엔진 `logger` 미정의 (NameError)
- **파일**: `engine_modules/return_reinbound_engine.py`
- 샘플 이중복구 감지 경고에서 정의되지 않은 `logger` 호출 → **NameError가 `except`에 삼켜져
  “샘플 검증 중 오류”라는 엉뚱한 사유로 반품 preflight가 차단**되던 버그.
- 모듈에 `logger` 정의(`logging.getLogger(__name__)`) 추가로 해결.
- v8.8.0이 “백로그 전수 조치 완료”였지만 실제로는 이 항목(D5 회귀 테스트)이 red였고,
  전수 검사로 발견 → **325 passed 그린 회복**.

---

## 🎨 UI — 따뜻한 테마 (다크/라이트 모두)

순흑·순백을 피해 배경을 살짝 띄우고 글씨를 따뜻한 톤으로 바꿔 **눈부심/번짐을 줄이고
대비(WCAG AAA)를 확보**했습니다. **기능적 강조색(파랑)·상태색·시맨틱은 유지**.

| 토큰 | 이전 (차가움) | 이후 (따뜻함) |
|---|---|---|
| 다크 배경 | `#070e1a` 순흑 | `#1a1714` 웜 차콜 |
| 다크 글씨 | `#dce8fa` | `#f2ebdf` 웜 크림 (대비 ~14:1) |
| 라이트 배경/카드 | `#ffffff` 순백 | `#fbf7f0` 웜 화이트 |
| 라이트 글씨 | `#0f2040` 네이비 | `#2b2419` 웜 차콜 (대비 ~12:1) |

- **파일**: `frontend/css/design-system.css`, `frontend/css/layout.css` (팔레트 블록 4곳)
- `luxury.css` 입력창이 `!important`로 차가운 남흑 배경을 강제하던 것 → 테마 변수(`var(--field-bg)`)화.

---

## 🟡 UI — 라이트 모드 깨짐 수정

다크 전용 “luxury/HARDEN” 스타일이 테마 무관 `!important`로 적용돼,
라이트 모드에서 **밝은 화면 위에 어두운 요소가 떠 있던** 문제를 테마 변수로 전환:

- **드롭다운/하위 메뉴**: 남흑 배경+흰 글씨 → `var(--menu-bg)`/`var(--menu-fg)`
- **테이블 헤더**: 다크+골드 글씨 → `var(--table-header)`/`var(--text-secondary)`
- **모달**: 다크 글래스 → `var(--modal-surface)`
- **입력창 포커스**: 클릭 시 검게 변하던 것 → `var(--field-bg)`
- **타이틀바**: `#020817` → `var(--menubar-bg)`
- 드롭다운 화살표/섹션라벨 흰색 → `currentColor`/`var(--text-muted)`
- **파일**: `frontend/css/luxury.css`, `frontend/css/layout.css`

---

## 🔧 정리 (Chore)

### `v864-layout.css` → `layout.css`
- “v864”(=v8.6.4) 라벨이 앱 8.8.x와 안 맞아 **“왜 옛 버전을 기준 삼지?” 혼동**을 유발 →
  버전 중립 이름으로 변경 (`design-system.css` / `layout.css` / `luxury.css` 트리오).
- 참조 갱신: `index.html`, `popout.html`의 `<link>`.
- 헤더 주석을 “용도 설명 + 최초 도입 v8.6.4 기록”으로 정리(이력 보존, 오해 제거).

### 캐시버스터 갱신
- 모든 CSS `<link>`의 `?v=`를 `20260615theme1`로 통일 →
  **새 테마가 강제 새로고침(Ctrl+F5) 없이 즉시 반영**. detached 창에도 토큰 추가.

---

## ✅ 검증
- 전체 테스트 **325 passed / 1 deselected** (headless: GUI·실DB 테스트 제외).
- 문법 에러 0, 코드에 `v864-layout` 활성 참조 0, CSS 중괄호 균형 정상.
- ⚠️ 실제 화면 렌더링은 Windows 앱 전용이라 **본인 PC에서 다크/라이트 토글로 최종 확인 권장**.
