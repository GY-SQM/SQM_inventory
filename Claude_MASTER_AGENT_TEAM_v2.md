# ═══════════════════════════════════════════════════════════════
# SQM AGENT TEAM MASTER — v1.0
# 프로젝트: SQM 재고관리 시스템 (React + FastAPI + SQLite)
# 작성일: 2026-04-09
# ═══════════════════════════════════════════════════════════════

---

## 🎯 SECTION 1: MISSION (전체 목표)

> 이 섹션은 **모든 에이전트가 공통으로 읽는** 유일한 섹션입니다.
> 팀 리더가 팀을 생성할 때 이 MISSION을 공유합니다.

### 1.1 프로젝트 개요

- **시스템명:** SQM 재고관리 (Stock Quality Management)
- **기술 스택:** React + Vite (프론트) / FastAPI (백엔드) / SQLite (DB)
- **현재 버전:** v8.7.1
- **프로젝트 경로:** `F:\프로그램\Sqm 재고관리\Claude_SQM_v871`
- **DB 위치:** `sqm_inventory.db` (프로젝트 루트)

### 1.2 금회 작업 목표

> ⚠ 매 작업마다 이 섹션을 구체적으로 업데이트할 것

```
[목표 예시 — 실제 작업 시 교체]
P2 리팩토링:
  - onestop_inbound.py → Orchestrator + Service + Repository 분리
  - outbound_mixin → 동일 패턴 적용
  - 전체 pytest 통과 확인
```

### 1.3 SQM 불변 규칙 (모든 에이전트 필독)

| # | 규칙 | 위반 시 |
|---|------|---------|
| R1 | **1 LOT = 톤백 N개(500kg/1000kg) + 샘플 1개(1kg)**. 총무게 = (톤백수 × 단가) + 1. | 재고 정합성 파괴 |
| R2 | **sub_lt 삭제 금지.** UNIQUE INDEX 키 + 샘플 판별(=0). 53개 파일 연동. | 시스템 전면 장애 |
| R3 | **파일명 Claude_ 접두사 필수.** 한글 "클로드_" 금지. | 배치파일 인코딩 충돌 |
| R4 | **LOT 정규식 `\d{8,11}` 범위.** 고정 10자리 금지 (OCR 오독 대비). | 파싱 실패 |
| R5 | **배치파일은 CP949 + CRLF.** UTF-8 BOM 금지. | Windows 실행 실패 |

---

## 📋 SECTION 2: TASK BOARD (칸반 보드)

> 팀 리더가 이 보드를 기준으로 작업을 분배합니다.
> 각 태스크에는 **담당 에이전트**, **의존성**, **완료 조건**이 명시됩니다.

### 태스크 상태 코드

| 코드 | 의미 |
|------|------|
| `TODO` | 미착수 |
| `IN_PROGRESS` | 진행 중 (담당자 배정됨) |
| `BLOCKED` | 의존 태스크 미완료로 대기 |
| `REVIEW` | 완료 후 팀 리더 검증 대기 |
| `DONE` | 검증 완료 |

### 태스크 목록 템플릿

```
┌──────┬─────────────────────────────────┬──────────┬──────────┬─────────────────┐
│ ID   │ 태스크                           │ 담당      │ 상태      │ 의존성           │
├──────┼─────────────────────────────────┼──────────┼──────────┼─────────────────┤
│ T-01 │ InboundOrchestrator 뼈대 생성    │ BACKEND  │ TODO     │ 없음             │
│ T-02 │ lot_service.py 분리             │ BACKEND  │ TODO     │ T-01            │
│ T-03 │ duplicate_service.py 분리       │ BACKEND  │ TODO     │ T-01            │
│ T-04 │ stock_service.py 분리           │ BACKEND  │ TODO     │ T-02, T-03      │
│ T-05 │ inbound_repository.py 생성      │ BACKEND  │ TODO     │ T-01            │
│ T-06 │ 입고 화면 API 연결 수정           │ FRONTEND │ BLOCKED  │ T-04, T-05      │
│ T-07 │ 입고 화면 UI 상태관리 리팩토링     │ FRONTEND │ TODO     │ 없음             │
│ T-08 │ BL/PL/DO 파서 pytest 추가        │ PARSER   │ TODO     │ 없음             │
│ T-09 │ Orchestrator 통합 pytest         │ PARSER   │ BLOCKED  │ T-04            │
│ T-10 │ 최종 교차 검증 (5항목 체크리스트)  │ LEADER   │ BLOCKED  │ T-06, T-08, T-09│
└──────┴─────────────────────────────────┴──────────┴──────────┴─────────────────┘
```

> ⚠ BLOCKED 태스크는 의존 태스크가 DONE이 되면 자동 해제됩니다.
> 팀 리더는 해제 시점에 해당 에이전트에게 메시지를 보냅니다.

---

## 👤 SECTION 3: AGENT ROLES (역할 정의서)

> 각 에이전트는 **자기 섹션만** 상세히 읽습니다.
> 다른 에이전트 섹션은 "이런 역할이 있다" 정도만 인지합니다.

---

### 3.1 TEAM LEADER (팀 리더)

**역할:** 오케스트레이터 — 작업 분배, 진행 모니터링, 결과 종합, 충돌 해결

**책임 범위:**
- TASK BOARD 관리 (상태 업데이트)
- SYNC POINT에서 팀원 결과 수집 및 종합
- 최종 교차 검증 5항목 체크리스트 실행
- Telegram 보고 (진행률, 완료, 오류)
- 팀원 간 파일 충돌 발생 시 중재

**금지 사항:**
- 직접 코드 수정하지 않음 (검증만 수행)
- 팀원 작업 도중 태스크 재배정하지 않음 (SYNC POINT에서만)

**교차 검증 5항목 (T-10에서 실행):**
```
□ 1. SQL 문법 오염 (인라인 주석 -- 포함 여부)
□ 2. status write 경로 SOLD/OUTBOUND 방향 확인
□ 3. 예외처리 상위 연결 (RuntimeError 차단 여부)
□ 4. python3 -m py_compile 전 파일 통과
□ 5. 의도적 미채택 항목 코드 미유입 확인
```

---

### 3.2 FRONTEND AGENT (프론트엔드 에이전트)

**역할:** React + Vite 전담 — UI 컴포넌트, 상태관리, API 연결

**접근 범위:**
```
허용: src/            (React 소스 전체)
      public/         (정적 파일)
      vite.config.js
      package.json

금지: react_api/      (백엔드 영역)
      parsers/        (파서 영역)
      *.db            (DB 직접 접근 금지)
```

**작업 원칙:**
- API 엔드포인트 변경이 필요하면 **BACKEND 에이전트에 메시지**로 요청
- UI/로직 분리 원칙 준수 (비즈니스 로직은 API로 위임)
- 상태관리는 React hooks 사용 (전역 상태 최소화)

**완료 조건:**
- `npm run build` 에러 0
- 브라우저 콘솔 에러 0
- 변경된 컴포넌트 스크린샷 또는 설명을 LEADER에게 보고

---

### 3.3 BACKEND AGENT (백엔드 에이전트)

**역할:** FastAPI + SQLite 전담 — API 라우트, 서비스 레이어, DB 쿼리

**접근 범위:**
```
허용: react_api/      (FastAPI 전체)
      *.db            (SQLite 읽기/쓰기)
      core/           (공통 유틸)
      features/       (비즈니스 로직)

금지: src/            (프론트엔드 영역)
      parsers/document_parser_modular/  (파서 내부 수정 금지)
```

**작업 원칙:**
- N+1 쿼리 금지 (JOIN 또는 배치 쿼리 사용)
- 모든 DB 작업은 트랜잭션 내에서 실행
- WAL 모드 PRAGMA 유지 확인
- threading.local() 사용으로 세션 격리
- API 엔드포인트 추가/변경 시 **FRONTEND 에이전트에 메시지**로 알림

**완료 조건:**
- `python3 -m py_compile` 전 파일 통과
- 해당 API 엔드포인트 curl 테스트 성공
- SQL 인라인 주석(--) 미포함 확인

---

### 3.4 PARSER/TEST AGENT (파서 + 테스트 에이전트)

**역할:** 문서 파서 유지보수 + 전체 pytest 담당

**접근 범위:**
```
허용: parsers/                    (파서 전체)
      tests/                     (테스트 전체)
      features/parsers/          (파싱 관련 feature)

금지: src/                       (프론트엔드)
      react_api/                 (백엔드 — 테스트 호출만 가능)
```

**작업 원칙:**
- 파서 수정 시 반드시 해당 문서 유형의 테스트 케이스 추가
- LOT 정규식: `\d{8,11}` 범위 유지 (R4 규칙)
- Gemini API 호출 실패 시 OCR 폴백 경로 검증
- pytest는 `-x --tb=short` 옵션으로 실행 (첫 실패에서 중단)

**완료 조건:**
- `pytest tests/ -x --tb=short` 전체 통과
- 커버리지 보고서 LEADER에게 전달
- 새 파서 패턴 추가 시 샘플 파일 명시

---

## 🔄 SECTION 4: SYNC POINTS (동기화 시점)

> 에이전트들이 **서로 기다리고 결과를 교환하는** 체크포인트입니다.
> 팀 리더가 각 SYNC POINT에서 모든 담당자의 완료를 확인합니다.

```
SYNC-1: 뼈대 완성
─────────────────────────────────────────────
  시점: BACKEND가 T-01 완료 후
  확인: Orchestrator 클래스 + 빈 Service 인터페이스 존재
  해제: FRONTEND T-06 BLOCKED 해제
  행동: LEADER → FRONTEND에게 "API 구조 확정, 연결 시작" 메시지

SYNC-2: 서비스 레이어 완성
─────────────────────────────────────────────
  시점: BACKEND가 T-02~T-05 전부 DONE
  확인: 모든 Service + Repository py_compile 통과
  해제: PARSER T-09 BLOCKED 해제
  행동: LEADER → PARSER에게 "통합 테스트 시작" 메시지

SYNC-3: 최종 통합
─────────────────────────────────────────────
  시점: FRONTEND T-06~T-07 + PARSER T-08~T-09 전부 DONE
  확인: npm run build 성공 + pytest 전체 통과
  해제: LEADER T-10 실행
  행동: LEADER가 교차 검증 5항목 직접 실행
```

---

## ⚠ SECTION 5: ABSOLUTE RULES (절대 규칙)

> 모든 에이전트가 반드시 준수해야 하는 규칙입니다.
> 위반 시 팀 리더가 해당 태스크를 ROLLBACK합니다.

### 5.1 파일 충돌 방지

```
규칙: 각 에이전트는 자신의 접근 범위 밖 파일을 수정하지 않는다.
예외: core/ 폴더의 공통 유틸은 LEADER 승인 후에만 수정 가능.
충돌 발생 시: LEADER가 git diff로 확인 후 수동 merge.
```

### 5.2 메시지 프로토콜

```
에이전트 간 메시지 형식:

  [FROM: BACKEND] [TO: FRONTEND]
  TYPE: API_CHANGE
  DETAIL: POST /api/inbound/process → 파라미터 변경
  ACTION_REQUIRED: InboundForm.jsx 수정 필요

  [FROM: PARSER] [TO: LEADER]
  TYPE: TEST_RESULT
  DETAIL: pytest 42 passed, 0 failed
  ACTION_REQUIRED: 없음
```

### 5.3 중단 없는 실행 규칙

```
★★★ 최우선 규칙 ★★★

1. Phase/Task 경계에서 멈추지 말고 다음 작업으로 계속 진행한다.
2. 확인 질문이 필요한 경우 Telegram으로만 보낸다 (개방형 질문 금지).
3. 선택지가 있으면 2~3개 버튼으로 Telegram 전송한다.
4. 10분간 응답 없으면 Ruby 추천안으로 자동 진행한다.

이 규칙은 3회 이상 강조한다:
- 멈추지 않는다.
- 멈추지 않는다.
- 멈추지 않는다.
```

### 5.4 산출물 규칙

```
- 기본: 패치 버전 (변경 파일만) 제공
- 풀버전: 기동님 명시적 요청 시에만
- ZIP 구조: Claude_SQM_vXXX_PATCH\ 하위에 실제 설치 경로 유지
- 파일명: Claude_ 접두사 필수
```

---

## 📊 SECTION 6: TEAM SETUP (팀 생성 명령)

> 기동님이 Claude Code에서 아래 프롬프트로 팀을 생성합니다.

### 6.1 환경 설정 (1회만)

```bash
# settings.json에 추가 또는 환경변수 설정
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### 6.2 팀 생성 프롬프트 (자연어)

```
이 프로젝트의 MASTER 파일(MASTER_AGENT_TEAM_v1.md)을 읽고
에이전트 팀을 구성해줘:

1. Frontend Agent: src/ 전담, React+Vite UI 수정
2. Backend Agent: react_api/ + features/ 전담, FastAPI+SQLite
3. Parser/Test Agent: parsers/ + tests/ 전담, pytest 실행

TASK BOARD의 태스크를 각 에이전트에게 배분하고,
SYNC POINT에 따라 동기화하면서 진행해줘.
Telegram 보고는 SYNC POINT마다 한 번씩.
```

### 6.3 팀원 직접 소통 (Shift+Down)

```
팀 리더 터미널에서:
  Shift+Down → 프론트 에이전트로 이동 → 직접 지시 가능
  Shift+Down → 백엔드 에이전트로 이동
  Shift+Down → 파서 에이전트로 이동
  Shift+Down → 다시 팀 리더로 복귀
```

---

## 📝 SECTION 7: TELEGRAM INTEGRATION (텔레그램 연동)

> 기존 telegram_bridge.py v5 기반, 팀 리더만 감시

### 7.1 보고 시점

| 이벤트 | Telegram 메시지 |
|--------|----------------|
| 팀 생성 완료 | "🏗 에이전트 팀 생성: 프론트/백엔드/파서 3명" |
| SYNC-1 도달 | "🔄 SYNC-1 뼈대 완성 — 프론트 작업 해제" |
| SYNC-2 도달 | "🔄 SYNC-2 서비스 완성 — 통합 테스트 시작" |
| SYNC-3 도달 | "✅ SYNC-3 최종 통합 — 교차 검증 시작" |
| 전체 완료 | "🎉 전체 완료 — 교차 검증 5/5 통과" |
| 오류 발생 | "🚨 [AGENT] 오류: {내용} — 자동 재시도 중" |

### 7.2 기동님 명령어

| 명령 | 동작 |
|------|------|
| `/status` | 전체 태스크 보드 현황 |
| `/team` | 각 에이전트 현재 작업 |
| `/stop` | 전체 팀 중지 |
| `/pause [agent]` | 특정 에이전트만 일시 정지 |

---

## 📎 APPENDIX: 작업별 커스터마이징 가이드

> 새로운 작업을 시작할 때마다 아래를 수정합니다:

```
수정 필요 섹션:
  1. SECTION 1.2 — 금회 작업 목표 (매번 교체)
  2. SECTION 2 — TASK BOARD 태스크 목록 (매번 교체)
  3. SECTION 4 — SYNC POINTS (태스크에 맞게 조정)

수정 불필요 섹션:
  1. SECTION 1.3 — 불변 규칙 (영구 고정)
  2. SECTION 3 — AGENT ROLES (역할 고정, 범위만 미세 조정)
  3. SECTION 5 — ABSOLUTE RULES (영구 고정)
  4. SECTION 6 — TEAM SETUP (환경 고정)
```

---

# END OF MASTER
