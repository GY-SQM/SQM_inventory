# GY Logis UI Master Guide — FINAL
> **Nam Ki-dong 전용 AI 앱 개발 UI 헌법**
> 작성: Ruby (Senior Architect) | 완성: 2026-06-03
> 출처: ChatGPT + Gemini + Ruby 3자 분석 통합본

---

## 📋 목차

1. [디자인 철학](#1-디자인-철학)
2. [AI 프롬프트 마스터 명령어](#2-ai-프롬프트-마스터-명령어)
3. [색상 시스템 — 60-30-10 룰](#3-색상-시스템--60-30-10-룰)
4. [듀얼 테마 토큰 전체표](#4-듀얼-테마-토큰-전체표)
5. [레이아웃 & 컴팩트 규칙](#5-레이아웃--컴팩트-규칙)
6. [타이포그래피](#6-타이포그래피)
7. [컴포넌트 규칙](#7-컴포넌트-규칙)
8. [Step Workflow UI](#8-step-workflow-ui)
9. [Collapsible Log Panel](#9-collapsible-log-panel)
10. [네비게이션 규칙](#10-네비게이션-규칙)
11. [현재 상태 항상 표시](#11-현재-상태-항상-표시)
12. [설정 저장 — config.json](#12-설정-저장--configjson)
13. [듀얼 테마 JavaScript](#13-듀얼-테마-javascript)
14. [기능 보존 프로세스](#14-기능-보존-프로세스)
15. [Function Mapping Table](#15-function-mapping-table)
16. [AI 기능 보존 명령어](#16-ai-기능-보존-명령어)
17. [상황별 추가 프롬프트](#17-상황별-추가-프롬프트)
18. [프로젝트별 적용 가이드](#18-프로젝트별-적용-가이드)
19. [절대 금지 사항](#19-절대-금지-사항)
20. [나중에 필요할 때 추가할 것](#20-나중에-필요할-때-추가할-것)
21. [기술 스택 선택 가이드 — React vs HTML/CSS/JS vs Tkinter](#21-기술-스택-선택-가이드--react-vs-htmlcssjs-vs-tkinter)

---

## 1. 디자인 철학

```
목표: 초보자도 즉시 사용할 수 있는 고급 업무용 SaaS UI
참고: Microsoft 365 / Notion / Linear / Retool / Supabase Dashboard

핵심 원칙:
- 화면 하나당 핵심 작업 1개만 배치
- 기능이 많더라도 화면은 단순하고 직관적으로
- 사용자가 지금 해야 할 작업을 가장 먼저 보여줌
- 컴팩트: 큰 화면에서도 1100px 이내로 집중
- 장시간 사용해도 눈이 피로하지 않은 다크 모드 기본

★ UI 구현 기술 스택 (필수 준수)
- UI는 반드시 순수 HTML + CSS + JavaScript 로 만든다
- React, Vue, Angular 등 프레임워크 사용 금지
- Bootstrap, Tailwind 등 외부 CSS 라이브러리 사용 금지
- Tkinter로 UI 만들지 않는다 — 데스크탑 앱도 PyWebView + HTML/CSS/JS
- CSS 변수(Custom Properties)로 모든 색상 관리
- 파일 1개(HTML)로 완성되도록 구성 권장
```

---

## 2. AI 프롬프트 마스터 명령어

> **모든 앱/프로그램 개발 시 AI 프롬프트 맨 앞에 붙여넣기**

```
【GY Logis UI Design System — STRICT RULES】

▶ TECH STACK — 절대 준수
UI는 반드시 순수 HTML + CSS + JavaScript 로만 구현한다.
React / Vue / Angular / Bootstrap / Tailwind 사용 금지.
Tkinter UI 금지 — 데스크탑 앱은 PyWebView + HTML/CSS/JS.
CSS 변수(--token)로만 색상 관리. hex 직접 입력 금지.

▶ DESIGN PHILOSOPHY
Target: Professional SaaS-level UI
Style: Compact. Focused. One task per screen. No visual noise.
Reference: Microsoft 365, Notion, Linear, Retool, Supabase Dashboard

▶ 60-30-10 COLOR RULE
60% → Background (--bg-base): 페이지 배경 — 가장 넓은 영역
30% → Surface/Card (--bg-surface): 카드, 패널, 컨테이너
10% → Accent (--accent): 버튼, 링크, 강조, 활성 상태
절대 색상을 균등하게 분배하지 말 것.

▶ DUAL THEME — CSS Variable Only
모든 색상은 CSS 변수로만 사용. 컴포넌트에 hex 코드 직접 입력 금지.
<html> 태그의 data-theme 속성으로 전환.
저장: localStorage key "gy-theme"
로드 순서: localStorage → prefers-color-scheme → 기본값 "dark"

▶ DARK THEME (기본값) :root
--bg-base:        #0F1117
--bg-surface:     #1E2130
--bg-elevated:    #252A3D
--border:         #2E3347
--text-primary:   #F1F5F9
--text-secondary: #94A3B8
--accent:         #4F8EF7
--success:        #22C55E
--warning:        #F59E0B
--danger:         #EF4444
--shadow:         rgba(0,0,0,0.4)

▶ LIGHT THEME [data-theme="light"]
--bg-base:        #F8FAFC
--bg-surface:     #FFFFFF
--bg-elevated:    #F1F5F9
--border:         #E2E8F0
--text-primary:   #0F172A
--text-secondary: #64748B
--accent:         #2563EB
--success:        #16A34A
--warning:        #D97706
--danger:         #DC2626
--shadow:         rgba(0,0,0,0.1)

▶ TYPOGRAPHY — ONE FONT RULE
Font: 'Noto Sans KR', 'Inter', sans-serif (1종만)
H1: 28px / 700
H2: 20px / 600
Body: 14px / 400
Caption: 12px / 400 / var(--text-secondary)
한 화면에 최대 3가지 폰트 크기만 사용

▶ LAYOUT
Max-width: 1100px, 중앙정렬 (margin: 0 auto)
태블릿: 900px
메인 패딩: 24px
카드 패딩: 20px 24px
Border-radius: 12px(카드) / 8px(버튼,입력) / 6px(배지)
전체 폭(100vw) 레이아웃 절대 금지

▶ SPACING — 8px Grid
xs:4px / sm:8px / md:16px / lg:24px / xl:40px
모든 여백은 4의 배수만 사용

▶ STEP WORKFLOW (물류/재고 앱 필수)
복잡한 작업은 반드시 단계형으로:
① 입력 → ② 검증 → ③ 실행 → ④ 결과
- 현재 단계 강조 표시
- 완료 단계 ✓ 체크마크
- 미래 단계 회색 처리

▶ COLLAPSIBLE LOG PANEL
- 기본 상태: 접힘 (collapsed) — 절대 기본으로 열어두지 말 것
- 토글: ▼ 로그 보기 / ▲ 숨기기
- 최대 높이: 200px (스크롤)
- 배경: var(--bg-elevated)
- 폰트: 12px monospace

▶ NAVIGATION
- 사이드바 메뉴 최대 7개
- 권장: Dashboard / Import / Process / Report / Settings (+ 2개)
- 모든 화면: 현재 위치 + 현재 사용자 + 현재 작업 표시

▶ COMPONENTS
버튼: height 40px / padding 0 20px / radius 8px
      섹션당 Primary 최대 1~2개
입력창: height 40px / border 1px solid var(--border) / radius 8px
테이블: 줄무늬 / 헤더 var(--bg-elevated) / 숫자 우측 정렬
아이콘: lucide-react 또는 heroicons만 사용
모달: box-shadow 0 8px 32px var(--shadow) / 최소화

▶ THEME TOGGLE
위치: 우측 상단 고정
크기: 36x36px
아이콘: 🌙 다크 / ☀️ 라이트
전환 애니메이션: 0.2s ease

▶ USER SETTINGS
config.json 저장:
{"theme":"dark","font_size":14,"language":"ko",
 "sidebar_collapsed":false,"log_panel_open":false}

▶ STYLE KEYWORDS
"Dark mode default. Professional SaaS. Compact.
Data-focused. Step workflows. Clean sidebar. No decorative fluff."
```

---

## 3. 색상 시스템 — 60-30-10 룰

> 14살도 이해하는 비유: **방 인테리어와 같음**
> - 60% = 벽과 바닥 (배경, 가장 넓음)
> - 30% = 가구 (카드, 패널)
> - 10% = 포인트 소품 (버튼, 강조)

```
■■■■■■  60%  --bg-base    페이지 배경
■■■      30%  --bg-surface 카드, 패널
■        10%  --accent     버튼, 강조
```

**이 비율을 지키면 어떤 화면도 산만해지지 않는다.**

---

## 4. 듀얼 테마 토큰 전체표

| 토큰 | Dark | Light | 비율 | 용도 |
|------|------|-------|------|------|
| `--bg-base` | #0F1117 | #F8FAFC | **60%** | 페이지 배경 |
| `--bg-surface` | #1E2130 | #FFFFFF | **30%** | 카드/패널 |
| `--bg-elevated` | #252A3D | #F1F5F9 | 보조 | 헤더/드롭다운/테이블헤더 |
| `--border` | #2E3347 | #E2E8F0 | — | 구분선 |
| `--text-primary` | #F1F5F9 | #0F172A | — | 제목/본문 |
| `--text-secondary` | #94A3B8 | #64748B | — | 설명/캡션 |
| `--accent` | #4F8EF7 | #2563EB | **10%** | 버튼/링크/강조 |
| `--success` | #22C55E | #16A34A | — | 성공 상태 |
| `--warning` | #F59E0B | #D97706 | — | 경고 |
| `--danger` | #EF4444 | #DC2626 | — | 오류/삭제 |
| `--shadow` | rgba(0,0,0,0.4) | rgba(0,0,0,0.1) | — | 모달 그림자 |

> ⚠️ **주의**: Accent 색상은 테마별로 다르게 설정.
> 어두운 배경 → 밝은 파랑(#4F8EF7)
> 밝은 배경 → 진한 파랑(#2563EB)

---

## 5. 레이아웃 & 컴팩트 규칙

```
┌─────────────────────────────────────────┐
│ Header (60px) — 제목 + 상태 + 테마버튼  │
├────────────────────────────────────────-┤
│ Status Bar (34px) — 현재위치/사용자/상태│
├──────────┬──────────────────────────────┤
│          │                              │
│ Sidebar  │  Main Content               │
│ (220px)  │  (max-width 1100px 중앙정렬) │
│ 최대7개  │                              │
│          │  [KPI Cards × 4]            │
│          │  [Chart or Table]           │
│          │  [Log Panel — 접힘]         │
│          │                              │
└──────────┴──────────────────────────────┘
```

**컴팩트 핵심 규칙:**
- 큰 화면에서 절대 전체 폭으로 늘리지 않음
- `max-width: 1100px; margin: 0 auto;` 항상 적용
- 카드로 묶어서 그룹핑 — 관련 기능은 반드시 같은 카드 안에

---

## 6. 타이포그래피

| 구분 | 크기 | 굵기 | 색상 | 용도 |
|------|------|------|------|------|
| H1 Title | 28px | 700 | --text-primary | 페이지 제목 |
| H2 Section | 20px | 600 | --text-primary | 섹션 제목 |
| Body | 14px | 400 | --text-primary | 본문, 버튼 |
| Caption | 12px | 400 | --text-secondary | 설명, 배지 |

**규칙:**
- 폰트 1종만: `'Noto Sans KR', 'Inter', sans-serif`
- 한 화면에 최대 3가지 크기
- 동시에 4가지 색상 초과 금지

---

## 7. 컴포넌트 규칙

### 버튼
```
높이: 40px (소형: 32px)
패딩: 0 20px
Radius: 8px
Primary: --accent 색상 (섹션당 1~2개만)
Secondary: outline 스타일
Danger: --danger 색상 (삭제/중지에만)
```

### 입력창 / 셀렉트
```
높이: 40px
Border: 1px solid var(--border)
Radius: 8px
배경: var(--bg-elevated)
포커스: border-color var(--accent)
```

### 테이블
```
헤더: var(--bg-elevated) 배경
행 높이: 36~42px
줄무늬: 짝수 행 약간 다른 배경
숫자: 우측 정렬 필수
hover: var(--bg-elevated) 강조
필터/검색: 기본 제공
```

### 배지 (Badge)
```
패딩: 3px 9px
Radius: 20px (pill 형태)
5가지: blue / green / yellow / red / gray
```

### 카드 (Card)
```
배경: var(--bg-surface)
Border: 1px solid var(--border)
Radius: 12px
패딩: 20px 24px
관련 기능은 반드시 같은 카드로 묶기
```

---

## 8. Step Workflow UI

> ChatGPT 제안 채택 — 물류/재고/위험물 앱 필수 패턴

```
① 파일 선택  →  ② 데이터 검증  →  ③ 처리 실행  →  ④ 결과 확인
   [현재]          [대기중]           [대기중]         [대기중]
```

**규칙:**
- 완료 단계: ✓ + 녹색
- 현재 단계: 번호 + 파란색 강조
- 미래 단계: 번호 + 회색
- 이전/다음 버튼 하단 배치
- 단계 이동 시 현재 단계 배지 업데이트

**적용 대상:**
- SQM 입고 등록: ①BL업로드 →②파싱검증 →③LOT매핑 →④DB저장
- SQM 출고 처리: ①출고요청 →②재고확인 →③승인 →④완료
- OCR 처리: ①이미지업로드 →②OCR추출 →③검수 →④저장

---

## 9. Collapsible Log Panel

> ChatGPT 제안 채택 — 화면 공간 절약 핵심

```
기본 상태 (접힘):
┌─────────────────────────────────────┐
│ ▼ 시스템 로그                        │
└─────────────────────────────────────┘

펼친 상태:
┌─────────────────────────────────────┐
│ ▲ 시스템 로그 숨기기                  │
├─────────────────────────────────────┤
│ 09:14:22  [OK]   입고 등록 완료       │
│ 11:08:47  [WARN] 검사 지연            │
│ 13:45:11  [ERR]  중량 불일치          │
└─────────────────────────────────────┘
최대 높이 200px / 스크롤
```

**AI 명령어 추가:**
```
로그 패널은 기본 접힘 상태로 구현.
기본으로 열려있으면 안 됨.
```

---

## 10. 네비게이션 규칙

**사이드바 최대 7개** (ChatGPT 채택)

```
권장 메뉴 구성:
1. Dashboard   — 전체 현황
2. Import      — 입고 관리
3. Process     — 처리/출고
4. Report      — 보고서
5. Settings    — 설정
6. (업무 특화) — 프로젝트별
7. Help        — 도움말
```

**저빈도 기능 처리 (숨김 원칙):**
```
자주 쓰는 기능 → 메인 화면에 표시
가끔 쓰는 기능 → "⋯ 더보기" 버튼 안에 숨김
거의 안 쓰는 기능 → Settings > Advanced 섹션
절대 삭제하지 말 것 — 숨김 ≠ 삭제
```

---

## 11. 현재 상태 항상 표시

> ChatGPT 제안 채택 — 모든 화면에 필수

```
┌──────────────────────────────────────────────┐
│ • 시스템 정상  │ 현재: 입고관리  │ 알림: 3건  │
└──────────────────────────────────────────────┘
```

**모든 화면에 반드시 포함:**
- 현재 메뉴/페이지 이름
- 현재 로그인 사용자
- 현재 작업 상태 또는 알림 수

---

## 12. 설정 저장 — config.json

> ChatGPT 제안 채택

```json
{
  "theme": "dark",
  "font_size": 14,
  "language": "ko",
  "sidebar_collapsed": false,
  "log_panel_open": false
}
```

**PyWebView 연동:**
```python
import json, os

CONFIG_PATH = "config.json"

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"theme": "dark", "font_size": 14, "language": "ko"}

def save_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 13. 듀얼 테마 JavaScript

> 모든 프로젝트 공통 — 그대로 복붙

```javascript
// theme.js — 모든 프로젝트 공통
(function() {
  const KEY = 'gy-theme';

  // 1. 저장값 → OS 설정 → 기본 dark 순서
  function getInitialTheme() {
    const saved = localStorage.getItem(KEY);
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark' : 'light';
  }

  // 2. 테마 적용
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(KEY, theme);
    const icon = document.getElementById('themeIcon');
    if (icon) icon.textContent = theme === 'dark' ? '🌙' : '☀️';
  }

  // 3. 토글 (버튼 onclick에 연결)
  window.toggleTheme = function() {
    const current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  };

  // 4. 초기 실행
  applyTheme(getInitialTheme());
})();
```

**CSS 뼈대:**
```css
:root {
  --bg-base: #0F1117;
  --bg-surface: #1E2130;
  --accent: #4F8EF7;
  /* ... 나머지 토큰 */
}
[data-theme="light"] {
  --bg-base: #F8FAFC;
  --bg-surface: #FFFFFF;
  --accent: #2563EB;
  /* ... */
}
body {
  background: var(--bg-base);
  color: var(--text-primary);
  transition: background 0.2s, color 0.2s;
}
/* 컴포넌트는 항상 변수만 사용 */
.card { background: var(--bg-surface); border: 1px solid var(--border); }
```

---

## 14. 기능 보존 프로세스

> 기존 프로그램에 새 UI 적용 시 안전 절차

```
기존 프로그램
    ↓
① Git 백업 (필수)
   git add . && git commit -m "UI 리팩토링 전 백업"
    ↓
② UI Inventory 추출
   기존 메뉴/버튼/기능 전체 목록 작성
    ↓
③ Function Mapping Table 작성
   기존 함수 → 새 위치 1:1 매핑
    ↓
④ 처리방식 결정
   유지 / 통합 / 숨김 / 제거(승인 후만)
    ↓
⑤ 점진적 적용
   색상 교체 → 레이아웃 → 개별 화면 (한 번에 전체 금지)
    ↓
⑥ 기존 함수 1:1 연결 확인
    ↓
⑦ Smoke Test
    ↓
⑧ 최종 비교표 확인
```

**문제 발생 시 즉시 복구:**
```bash
git checkout .          # 마지막 커밋으로 복구
git reset --hard HEAD   # 완전 초기화
```

**UI / 로직 파일 분리 (권장):**
```
📁 프로젝트
├── ui/
│   ├── styles.css    ← 여기만 건드림
│   ├── layout.html   ← 여기만 건드림
│   └── theme.js      ← 여기만 건드림
└── logic/
    ├── inbound.py    ← 절대 건드리지 않음
    ├── outbound.py   ← 절대 건드리지 않음
    └── database.py   ← 절대 건드리지 않음
```

---

## 15. Function Mapping Table

> ChatGPT 제안 채택 — UI 작업 전 반드시 작성

```markdown
## [프로그램명] Function Mapping Table — 날짜

| 기존 메뉴 | 기존 버튼명 | 기존 함수명 | 새 UI 위치 | 처리방식 | 테스트 |
|----------|-----------|-----------|----------|---------|-------|
| 입고관리  | BL 불러오기 | load_bl() | Import Card | 유지 | □ |
| 입고관리  | 파싱 실행   | parse_bl() | Step ① 버튼 | 유지 | □ |
| 출고관리  | 출고 처리   | process_out() | Process Card | 유지 | □ |
| 설정      | 환경설정    | open_settings() | Settings | 유지 | □ |
| 도구      | 로그 보기   | show_log() | Log Panel | 숨김→접기 | □ |
| 도구      | DB 백업     | backup_db() | Settings>Advanced | 숨김 | □ |
```

**처리방식 4분류:**
| 분류 | 의미 | 주의 |
|------|------|------|
| **유지** | 같은 위치, 같은 이름 | — |
| **통합** | 유사 기능 카드로 묶기 | — |
| **숨김** | More/Advanced로 이동 | 삭제 아님! |
| **제거** | 완전 삭제 | 반드시 사용자 승인 후 |

---

## 16. AI 기능 보존 명령어

> UI 리팩토링 시 이 명령어를 앞에 붙여넣기

```
【UI 리팩토링 기능 보존 명령어】

▶ STEP 1: 작업 전 Inventory 추출
기존 프로그램의 모든 메뉴/버튼/기능을 스캔해서
Function Mapping Table을 먼저 만들어줘. 하나도 빠뜨리지 말 것.

| 기존 메뉴 | 기존 버튼명 | 기존 함수명 | 새 UI 위치 | 처리방식 | 테스트 |

▶ STEP 2: 처리방식 규칙
- 유지: 같은 위치 유지
- 통합: 유사 기능 묶기
- 숨김: "⋯ More" 또는 Advanced로 이동 (삭제 아님)
- 제거: 사용자 승인 없이 절대 금지

▶ STEP 3: 변경 허용 / 금지
허용: 색상(CSS 변수 교체) / 레이아웃 재배치 / 폰트 크기
금지: 기존 함수명 삭제 / 로그·설정·백업 기능 제거 /
      DB·API 로직 수정 / 한 번에 전체 리팩토링

▶ STEP 4: 점진적 적용 순서
1단계: CSS 색상 변수 교체만 → 확인 후 2단계
2단계: 레이아웃(헤더/사이드바) 교체 → 확인 후 3단계
3단계: 개별 화면 카드/테이블 UI → 화면별 확인

▶ STEP 5: 완료 후 Smoke Test 보고
- [ ] 모든 버튼 → 기존 함수 실행 여부
- [ ] 데이터 표시 정상
- [ ] 저장/로드/내보내기 정상
- [ ] 숨김 기능 접근 가능
- [ ] 로그 패널 동작
- [ ] 다크/라이트 테마 전환 정상
```

---

## 17. 상황별 추가 프롬프트

### 데스크탑 앱 (PyWebView / Electron)
```
Desktop app at 1280x800.
Sidebar: 220px fixed left. Content: remaining width.
No mobile breakpoints.
```

### 데이터 대시보드 (SQM Revenue)
```
Row 1: KPI cards × 4 — icon + large number(32px bold) + label
Row 2: Chart
Row 3: Data table (numbers right-aligned)
```

### 단계형 워크플로우 (입고/출고)
```
Top: Step indicator (① ② ③ ④)
Middle: Current step content in card
Bottom: Prev/Next buttons + Log Panel(collapsed)
```

### 모바일 앱
```
Mobile-first. Max-width 390px.
Bottom navigation, max 5 items.
Touch targets 44×44px minimum.
```

### 리스트/피드 (Email Monitor)
```
Feed/list style. Badge notifications. Timeline layout.
Each item: icon + title + timestamp + status badge.
```

---

## 18. 프로젝트별 적용 가이드

| 프로젝트 | 레이아웃 패턴 | 핵심 추가 키워드 |
|----------|-------------|----------------|
| SQM 재고관리 | 사이드바 + Step Workflow + Log Panel | data-heavy, table-centric |
| GY Revenue Dashboard | KPI 4개 → 차트 → 테이블 | executive view |
| GY Remote Launcher | 그리드 버튼 패널 | control panel, status indicators |
| Email Monitor | 피드 리스트 | feed, badge, timeline |
| GY Equipment Dashboard | 폼 + 미리보기 | form-centric, export |
| OCR 프로그램 | Step Workflow 4단계 | image upload, extraction |

---

## 19. 절대 금지 사항

| ❌ 하지 말 것 | ✅ 대신 할 것 |
|-------------|------------|
| `background: #1E2130` 직접 입력 | `var(--bg-surface)` 사용 |
| 폰트 여러 종 혼합 | Noto Sans KR 하나만 |
| 전체 폭(100vw) 레이아웃 | max-width 1100px + 중앙정렬 |
| 섹션에 Primary 버튼 3개 이상 | 1~2개만 |
| 로그 패널 기본 열림 | 기본 접힘 |
| 메뉴 8개 이상 | 최대 7개 |
| 이모지를 아이콘 대용 | lucide / heroicons |
| 다크모드에 #000000 | #0F1117 이상 |
| 한 번에 전체 UI 리팩토링 | 단계적으로 화면별 적용 |
| AI가 기능 자동 제거 | 반드시 사용자 승인 후 |
| 저빈도 기능 삭제 | More / Advanced로 숨김 |

---

## 20. 나중에 필요할 때 추가할 것

> **지금 당장 필요 없음 — 아래 시점에 추가**

| 항목 | 추가 시점 |
|------|---------|
| 모바일 반응형 상세 규칙 | 모바일 앱 개발 시 |
| 차트(Chart.js) 테마 연동 | 차트 기능 추가 시 |
| 애니메이션/마이크로인터랙션 | 완성도 높일 때 |
| 접근성 WCAG 2.1 AA | 외부 고객용 앱 시 |
| React 컴포넌트 훅 버전 | React 전환 시 |

---

## 📌 빠른 참조 카드

```
새 앱 만들 때:
→ Section 2 (마스터 명령어) 복붙 + Section 17 (상황별) 추가

기존 앱 UI 바꿀 때:
→ Section 14 (기능 보존 프로세스) + Section 16 (AI 명령어) 사용

테마 구현:
→ Section 13 (JavaScript) 복붙

색상 모르겠으면:
→ Section 4 (토큰 전체표) 참조

뭔가 빠진 것 같으면:
→ Section 15 (Mapping Table) 작성
```

---

*GY Logis UI Master Guide — FINAL*
*Ruby, Senior Architect | 2026-06-03*
*출처: Ruby(기본) + ChatGPT(UX 패턴) + Gemini(색상 비율) 3자 통합*
