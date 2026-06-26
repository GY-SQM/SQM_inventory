# SQM Dashboard UI 재설계 — C+B Hybrid Phase A–C 설계 문서

- **작성일**: 2026-06-26
- **버전**: v1.0
- **대상 시스템**: SQM Inventory Manager v8.8.1+
- **작성자**: Ruby (Claude Code AI Architect)
- **승인 대기**: 남기동 대표

---

## 1. 개요 (Overview)

### 1.1 목적
SQM 기존 탭형 UI를 **경영 관제(C형) + 운영 드릴다운(B형)** 하이브리드 구조로 교체한다.
단일 앱에서 CEO 대시보드 뷰와 담당자 운영 뷰를 동시에 제공한다.

### 1.2 배경
- 현재 UI: 탭 전환 방식, KPI 요약 없음, 화면 이동 빈번
- 개선 목표: 실시간 KPI 7개를 한눈에, 알림 클릭 → 상세 테이블 즉시 드릴다운
- 기술 스택 유지: PyWebView + FastAPI + vanilla JS + SQLite (리그레이션 최소화)

---

## 2. 설계 방향 (Design Direction)

### 2.1 레이아웃 구조

```
[사이드바 아이콘] | [타이틀바]
                 | [KPI 카드 ×7]
                 | [주간 차트 | 실시간 알림]
                 | [B형 드릴다운 테이블 — 알림 클릭 시 슬라이드인]
```

### 2.2 두 가지 뷰 역할

| 뷰 | 대상 사용자 | 트리거 |
|----|-----------|--------|
| C형 대시보드 | CEO / 관리자 | 앱 시작 시 기본 화면 |
| B형 드릴다운 | 운영 담당자 | 알림 클릭 or 사이드바 메뉴 진입 |

---

## 3. KPI 카드 명세 (7개)

| # | 카드명 | 데이터 소스 | API 필드 | 색상 |
|---|--------|-----------|----------|------|
| 1 | 현재 재고량 (MT) | inventory | `SUM(current_weight)` WHERE status=AVAILABLE | 파랑 (#4fc3f7) |
| 2 | 입고 대기 건수 | bl_master | `COUNT(*)` WHERE status=PENDING | 초록 (#66bb6a) |
| 3 | 출고 대기 건수 | allocation | `COUNT(*)` WHERE status=PENDING | 오렌지 (#ffa726) |
| 4 | 피킹 완료 (MT) | inventory | `SUM(picked_weight)` WHERE date=TODAY | 청록 (#26c6da) |
| 5 | 정합성 알림 수 | integrity_check | 불변식 위반 LOT 수 | 빨강 (#ef5350) |
| 6 | LOT 총 수량 | inventory | `COUNT(DISTINCT lot_no)` WHERE active | 보라 (#ab47bc) |
| 7 | 반품 대기 건수 | return | `COUNT(*)` WHERE status=PENDING | 코랄 (#ff7043) |

**불변식 검증**: `initial_weight = current_weight + picked_weight` (±1kg 허용)
→ 위반 LOT는 KPI #5에 카운트 + 알림 패널에 즉시 표시

---

## 4. 컴포넌트 명세

### 4.1 사이드바
- 너비: 56px 고정 (아이콘 전용)
- 아이콘 hover → CSS `::after` 툴팁 표시 (라벨 텍스트)
- 9개 메뉴: 대시보드 / 재고 / 입고 / 출고 / 피킹 / 톤백 / 로그 / 반품 / 스캔
- 활성 탭: `rgba(79,195,247,0.15)` 배경 + `#4fc3f7` 아이콘 색

### 4.2 타이틀바
- 높이: 44px
- 좌: S.I.M.S 로고 + 현재 페이지명
- 우: 정합성 경고 배지 + 현재 시간 (KST)

### 4.3 KPI 카드 ×7
- 그리드: `repeat(7, 1fr)` (가로 균등 분할)
- 각 카드: 상단 컬러 바 3px + 라벨 + 큰 숫자 + 보조 설명 + 델타 배지
- 클릭 시: 해당 페이지로 이동 (예: 카드 #5 클릭 → 정합성 드릴다운)

### 4.4 주간 입출고 차트
- 타입: 그룹 바 차트 (입고/출고 나란히, 최근 7일)
- 라이브러리: Chart.js (경량, 기존 CDN 추가만 필요)
- 데이터: `/api/dashboard/weekly` 엔드포인트

### 4.5 실시간 알림 패널
- 너비: 320px 고정
- 항목: severity(err/warn/info/ok) + 제목 + 설명 + 시간
- 클릭 시: B형 드릴다운 테이블 슬라이드인 (화면 아래 영역에 표시)

### 4.6 B형 드릴다운 테이블
- 기본: 숨김 상태 (`display:none`)
- 트리거: 알림 패널 항목 클릭 OR 사이드바 메뉴 직접 진입
- 구성: 상단 탭(정합성위반/전체재고/입고대기 등) + 페이지네이션 테이블
- 컬럼: 컨텍스트에 따라 동적 변경

---

## 5. API 설계 (신규 엔드포인트)

### 5.1 대시보드 요약
```
GET /api/dashboard/summary
Response: {
  stock_mt: float,          // KPI #1
  inbound_pending: int,     // KPI #2
  outbound_pending: int,    // KPI #3
  picked_today_mt: float,   // KPI #4
  integrity_alerts: int,    // KPI #5
  lot_count: int,           // KPI #6
  return_pending: int,      // KPI #7
  updated_at: datetime
}
```

### 5.2 주간 추이
```
GET /api/dashboard/weekly
Response: {
  labels: [str×7],          // 요일 레이블
  inbound_mt: [float×7],
  outbound_mt: [float×7]
}
```

### 5.3 정합성 알림 목록
```
GET /api/dashboard/alerts
Response: [{
  id: str,
  severity: "err"|"warn"|"info"|"ok",
  title: str,
  desc: str,
  lot_no: str|null,
  created_at: datetime
}]
```

---

## 6. 구현 단계 (Phase A → B → C)

### Phase A — 파일럿 대시보드 (즉시 시작 가능)
**목표**: 신규 대시보드 화면 1개를 실제 앱에 추가 (기존 화면 영향 0)

| 순서 | 작업 | 파일 |
|------|------|------|
| A-1 | `/api/dashboard/summary` 엔드포인트 추가 | `backend/api/dashboard_api.py` (신규) |
| A-2 | `/api/dashboard/weekly` 엔드포인트 추가 | 동일 파일 |
| A-3 | `/api/dashboard/alerts` 엔드포인트 추가 | 동일 파일 |
| A-4 | `dashboard.js` 리팩토링 (KPI 카드 ×7 + 차트 + 알림) | `frontend/js/pages/dashboard.js` |
| A-5 | Chart.js CDN 추가 | `frontend/index.html` |
| A-6 | 사이드바 아이콘 + 툴팁 CSS | `frontend/css/layout.css` |
| A-7 | 회귀 테스트 실행 (410개 기준) | `pytest` |

### Phase B — 기존 화면 B형 테이블로 교체
**목표**: 9개 페이지 중 5개를 B형 wide 테이블로 점진적 교체
- inventory, allocation, outbound, picked, return 순서로 교체
- 기존 탭 기능은 사이드바 메뉴로 대체

### Phase C — CSS 통일 + 디자인 토큰 정리
**목표**: `luxury.css` + `design-system.css` 통합, 다크/라이트 테마 완성
- CSS 변수 일원화, 컬러 토큰 정리
- 기존 인라인 스타일 제거

---

## 7. 제약 사항 (Constraints)

1. **`window.confirm` 사용 금지** — 반드시 `sqmConfirmAsync` 사용 (PyWebView 블로킹)
2. **실 DB 직접 수정 금지** — API/서비스 계층 경유 필수
3. **불변식 유지** — `initial_weight = current_weight + picked_weight` (±1kg)
4. **410개 회귀 테스트 통과** — Phase A 완료 후 전체 실행
5. **단일 인스턴스 패턴 유지** — PyWebView 재시작 방식 변경 없음

---

## 8. 시각 목업 참조

- 파일: `SQM_v874_clean/.brainstorm/dashboard-mockup.html`
- 확정 레이아웃: C형 대시보드(KPI×7 + 차트 + 알림) → 알림 클릭 → B형 드릴다운
- 테마: 다크 (`#0d1117` 배경, `#4fc3f7` 포인트 컬러)

---

## 9. 성공 기준 (Definition of Done)

- [ ] KPI 7개 실시간 업데이트 (30초 폴링 or WebSocket)
- [ ] 정합성 경고 알림 클릭 → B형 테이블 드릴다운 동작
- [ ] 주간 차트 실제 DB 데이터 연결
- [ ] 사이드바 툴팁 정상 작동
- [ ] 410개 기존 회귀 테스트 전체 통과
- [ ] `window.confirm` 미사용 확인 (grep 검증)

---

*이 문서는 `superpowers:writing-plans` 스킬로 구현 플랜 전환 준비 완료.*
