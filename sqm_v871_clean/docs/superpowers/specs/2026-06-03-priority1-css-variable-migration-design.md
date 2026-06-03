# SQM v871 UI 개선 — Priority 1: CSS HEX → 변수 마이그레이션 설계

**날짜:** 2026-06-03  
**작성:** Claude (GY UI Master Guide 기반)  
**범위:** Priority 1 — 하드코딩 HEX 색상 53개를 CSS 변수로 교체  
**게이트:** 각 Priority 완료 후 전수검사 통과 시에만 다음 Priority 진행

---

## 1. 실행 흐름

```
① git 백업 커밋
      ↓
② Codex: 전 파일 HEX 패턴 스캔 → 색상·위치 목록 생성
      ↓
③ Claude: 매핑표 작성
   - 기존 CSS 변수 매칭 가능 → 교체 (방식 A)
   - 스플래시/애니메이션 전용 → 신규 변수 생성 후 교체 (방식 B)
      ↓
④ 파일별 교체 적용 (index.html → detached/*.html → CSS 파일 순)
      ↓
⑤ ━━━━ QA 게이트 ━━━━
   [코드 레벨 → 시각 레벨 → 기능 레벨]
      ↓
⑥ QA 전 항목 통과 확인 후 → Priority 2 진행
```

---

## 2. 매핑 기준

### 2-1. 기존 변수 매핑 (방식 A)

| 하드코딩 HEX 계열 | 교체할 기존 변수 | 매핑 근거 |
|---|---|---|
| `#070e1a`, `#0f1520` 계열 | `var(--bg-root)` | 최외곽 배경색 |
| `#1a2035`, `#1e2a45` 계열 | `var(--bg-surface)` | 카드/패널 배경 |
| `#252d40`, `#2a3350` 계열 | `var(--bg-elevated)` | 헤더/드롭다운 |
| `#2980b9`, `#4a9eff`, `#38bdf8` 계열 | `var(--accent)` | 강조/버튼 |
| `#27ae60`, `#52c87e` 계열 | `var(--success)` | 성공 상태 |
| `#e74c3c`, `#e06868` 계열 | `var(--danger)` | 오류/삭제 |
| `#f59e0b`, `#e8943a` 계열 | `var(--warning)` | 경고 |
| `rgba(0,0,0,0.X)` 계열 | `var(--shadow)` | 그림자 |

**매핑 판정 기준:** 색상값 차이 ±15 이내 + 의미(배경/강조/상태) 일치 → 기존 변수로 교체.  
그 이상이거나 의미 불일치 → 신규 변수 생성.

### 2-2. 신규 변수 생성 (방식 B)

**접두사 규칙: `--sqm-`** (프로젝트 고유 변수 구분)

| 용도 | 변수명 | 특징 |
|---|---|---|
| 스플래시 배경 | `--sqm-splash-bg` | 테마 무관 (단일값) |
| 스플래시 그러데이션 시작 | `--sqm-splash-grad-start` | 테마 무관 |
| 스플래시 그러데이션 끝 | `--sqm-splash-grad-end` | 테마 무관 |
| 로딩바 하이라이트 | `--sqm-loading-highlight` | 테마 무관 |
| 스플래시 텍스트 | `--sqm-splash-text` | 테마 무관 |

### 2-3. 신규 변수 위치

```css
/* design-system.css 맨 아래 별도 섹션으로 추가 */

/* ── SQM 프로젝트 전용 변수 (테마 무관) ── */
:root {
  --sqm-splash-bg:         #070e1a;
  --sqm-splash-grad-start: #0a1628;
  --sqm-splash-grad-end:   #1a2a4a;
  --sqm-loading-highlight: #4fc3f7;
  --sqm-splash-text:       #e0e8f0;
}
```

> 스플래시 색상은 테마 전환과 무관하므로 `:root` 1곳에만 정의.

### 2-4. 교체 제외 대상

| 상황 | 이유 |
|---|---|
| `rgba(255,255,255,0.05)` 미세 투명도 | 변수화 시 오히려 가독성 저하 |
| JS 내 색상 문자열 비교 `=== '#4a9eff'` | 로직 변경 → Priority 1 범위 초과 |
| SVG `fill`/`stroke` 인라인 속성 | 별도 작업으로 분리 |

---

## 3. QA 게이트 체크리스트

Priority 1 완료 후 전 항목 통과 시에만 Priority 2 진행.

### 3-1. 코드 레벨

```
□ git diff 전체 — 색상 교체 외 로직 변경 없는지
□ HEX 잔존 검색: 허용 제외 목록 외 0건
□ 신규 --sqm-* 변수 design-system.css :root에 전부 정의됐는지
□ CSS 변수 오타: 정의 안 된 변수명 참조 없는지
□ 다크/라이트 변수 교차 배치 없는지
```

### 3-2. UI 섹션별 시각 전수검사 (다크 → 라이트 → 다크)

| # | 섹션 | 확인 항목 |
|---|---|---|
| 1 | 스플래시 화면 | 배경 그러데이션, 로딩바, 텍스트 가시성 |
| 2 | 타이틀바 | 배경색, 텍스트, 아이콘 |
| 3 | 메뉴바 | 배경, 드롭다운, hover, 구분선 |
| 4 | 액션 툴바 | 버튼 7개 색상, 아이콘, hover/active |
| 5 | 사이드바 (접힘) | 아이콘, 활성 메뉴 강조, 배지 |
| 6 | 사이드바 (펼침) | 텍스트, 하위 메뉴 |
| 7 | KPI 카드 5개 | 카드 배경, 수치, 이모지, 구분선 |
| 8 | 인벤토리 테이블 | 헤더, 줄무늬, 셀 텍스트, 정렬 |
| 9 | 모달 (각 유형) | 배경, 테두리, 버튼, 오버레이 |
| 10 | 토스트 알림 | success/warning/danger 색상 |
| 11 | 팝아웃 창 | popout.html 독립 스타일 유지 |
| 12 | AI 채팅 | detached/ai_chat.html 색상 |
| 13 | 정합성 검사 | detached/integrity.html 색상 |

### 3-3. 기능 레벨

```
□ 다크/라이트 전환 시 전체 화면 색상 즉시 반영
□ 페이지 새로고침 후 테마 유지 (localStorage)
□ 사이드바 접기/펼치기 색상 정상
□ 드롭다운 열기/닫기 색상 정상
□ 테이블 hover 강조 동작
□ 모달 열기/닫기 오버레이 정상
□ 버튼 hover/active 상태 정상
```

### 3-4. 통과 기준

| 레벨 | 기준 |
|---|---|
| 코드 | HEX 잔존 0건, CSS 오타 0건 |
| 시각 | 13섹션 × 다크/라이트 = 26개 체크 전부 통과 |
| 기능 | 7개 항목 전부 통과 |
| **판정** | 3개 레벨 모두 통과 시에만 Priority 2 진행 |

---

## 4. 대상 파일 목록

| 파일 | 예상 교체 수 | 우선순위 |
|---|---|---|
| `frontend/index.html` | ~40개 | 1순위 (메인) |
| `frontend/detached/ai_chat.html` | ~5개 | 2순위 |
| `frontend/detached/integrity.html` | ~5개 | 2순위 |
| `frontend/popout.html` | ~3개 | 3순위 |
| `frontend/css/design-system.css` | 신규 변수 추가만 | 4순위 |

---

## 5. 실행 팀 구성

| Priority | 팀 | 이유 |
|---|---|---|
| Priority 1 (이 작업) | Claude + Codex | Codex 스캔 → Claude 의미 검토 + 교체 |
| Priority 2 (폰트 통일) | Claude 단독 | 단순 교체 |
| Priority 3 (내비 구조) | Claude + Codex + 서브에이전트 | 다중 JS 모듈 동시 변경 |
| Priority 4 (max-width) | Claude 단독 | CSS 1줄 추가 |
