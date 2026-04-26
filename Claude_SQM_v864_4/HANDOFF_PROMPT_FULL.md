# 🏁 Phase 3 → Phase 8 Full Journey Handoff Prompt

> **용도**: 다음 세션 (또는 그 다음 세션)에서 Phase 3 부터 Phase 8 (최종 릴리스) 까지 일관된 맥락으로 이어서 작업하기 위한 **단 하나의 복붙 명령어**.
>
> **작성**: Ruby (Senior Software Architect) · **일자**: 2026-04-21 (화) 22:00 KST
> **Baseline 커밋**: `5f7f5ff (HEAD -> main)` — Phase 2 Step 3 완전 종료 지점 (rollback 가능)

---

## 📋 사용법 (3단계)

1. **Claude 데스크톱 → "+ 새 채팅"**
2. **모델 선택 → "Claude Opus 4.6"** (긴 맥락 유지 유리)
3. **아래 파란 박스 내용을 첫 메시지에 그대로 복붙 → Enter**

한 세션에서 Phase 3~8 을 전부 끝낼 필요는 없다. 세션 컨텍스트가 70% 근접하면 Opus 가 스스로 `HANDOFF_PROMPT_PHASE{N+1}.md` 를 생성하고 새 세션으로 넘기도록 명시했다.

---

## 🎯 [복붙용 프롬프트 — 여기부터]

```
나는 Nam Ki-dong 사장님이고, SQM v864.3 마이그레이션 프로젝트의 Phase 3 ~ Phase 8 (최종 릴리스) 를 이어서 진행한다.
프로젝트 폴더: D:\program\SQM_inventory\Claude_SQM_v864_3
Rollback Baseline: git 커밋 5f7f5ff (Phase 2 Step 3 완전 종료 지점, HEAD -> main)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【0】 작업 착수 전 반드시 다음 6개 파일을 병렬로 읽고 완전히 파악해줘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. CLAUDE.md (프로젝트 영구 메모리 + 8-Phase 로드맵 + Phase 3 Next Target)
2. REPORTS/PHASE3_PLAN.md (Phase 3 Q1/Q2/Q3 상세 실행 계획)
3. REPORTS/PHASE2_STEP3.md (직전 완료 보고서 — 증거 확보)
4. docs/handoff/feature_matrix.json (85 기능 매핑 — Phase 4 기준)
5. frontend/index.html (UI 현 상태)
6. backend/main.py (라우터 등록 현 상태)

현재 상태 스냅샷 (2026-04-21 22:00 KST 기준):
- Phase 0~2 완료 (Safety Net → UI Manifest → TOP3 엔드포인트 + 런타임 검증)
- HTTP 200 전환, favicon 200, F039/F050 headless, CSS 수정, /health 8/8 모듈
- git 커밋 5f7f5ff 에 Phase 2 Step 3 전체 고정됨
- 전체 진행률 ≈ 35%, 남은 Phase 6 개, 예상 릴리스 2026-05-09 ~ 2026-05-25

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【1】 Phase 3 → Phase 8 순차 실행 규약 (8-Phase Roadmap)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

각 Phase 는 반드시 아래 5단계 게이트를 지킬 것:
  (a) 시작 전: REPORTS/PHASE{N}_PLAN.md 작성 (없으면 신규, 있으면 검토)
  (b) 실행: 계획서대로 코드 구현 + 스모크 테스트 (curl / TestClient)
  (c) 보고: REPORTS/PHASE{N}_COMPLETE.md 완료 보고서 작성
      → Professional Debugging Protocol 7 섹션 + 3 Mandatory Checks 준수
  (d) 사장님 검수: 육안 확인 + 스샷 1장 공유 → GO 사인 받으면 다음 진행
  (e) git 커밋: "feat(v864.3): Phase {N} complete — {요약}" + 태그 v864.3-phase{N}

━━━ Phase 3 — Dashboard KPI 실데이터 + 건강성 가시화 ━━━
- 기간: 80분 (1 세션 내 완료 가능)
- 범위: PHASE3_PLAN.md Q1+Q2+Q3 전부
  · Q1: GET /api/dashboard/kpi 신설 + 4개 카드 실데이터 (60분)
  · Q2: 상태바 🟢 Engine 8/8 상시 표시 (15분)
  · Q3: docs/health_check_guide.md 작성 (5분)
- DoD: Dashboard 에 실제 숫자 + 상태바 모듈 카운터 + 건강성 가이드
- 산출물: REPORTS/PHASE3_COMPLETE.md, 태그 v864.3-phase3

━━━ Phase 4 — 82개 기능 점진 활성화 (NotReady → 실구현) ━━━
- 기간: 5~7일 (다중 세션 분할)
- 전략: feature_matrix.json 기준 사용빈도 Top 순으로 25개씩 3배치
  · 4-A 배치: Top 25 (입출고/LOT/재고조회 핵심)
  · 4-B 배치: Middle 25 (리포트/엑셀/프린트)
  · 4-C 배치: Last 32 (optional 11 + 관리자 기능 포함)
- 규약: 각 기능 구현 시 wrap_engine_call 래퍼 필수, backend/legacy/* 수정 금지
- DoD: 85/85 기능이 "NotReady" 가 아닌 "실데이터 응답" 또는 "의도된 빈 화면"
- 산출물: REPORTS/PHASE4_BATCH_A.md / _B.md / _C.md, 각 배치마다 git 태그

━━━ Phase 5 — 회귀 테스트 자동화 (v864.2 ↔ v864.3 비교) ━━━
- 기간: 2일
- 범위: pytest + Playwright 로 UI 스샷 비교 + 85 엔드포인트 응답 diff
- SSIM 임계값: 0.85 이상 (CLAUDE.md 품질 기준과 일치)
- DoD: CI 에서 v864.2 snapshot vs v864.3 Preview 차이 자동 리포트
- 산출물: tests/regression/, REPORTS/PHASE5_COMPLETE.md, 태그 v864.3-phase5

━━━ Phase 6 — PyInstaller EXE 빌드 + 배포 ━━━
- 기간: 1일
- 범위: PyInstaller 6.2.0 onefile 모드, favicon.ico 임베드, --noconsole
- 사전 점검: SQLite DB 경로 동적 resolve (sys._MEIPASS 대응)
- DoD: 단일 EXE 실행 시 GY Logis 광양 로컬 환경에서 정상 기동
- 산출물: dist/SQM_v864_3.exe, REPORTS/PHASE6_COMPLETE.md, 태그 v864.3-phase6

━━━ Phase 7 — 사장님 실사용 1주 + 버그 수집 ━━━
- 기간: 7일 (실사용 관찰 기간)
- 범위: GY Logis 광양 현장에서 Nam Ki-dong 사장님이 매일 사용, 이슈 리포트
- 규약: 매일 1회 REPORTS/PHASE7_DAY{N}.md 에 발견 이슈 기록
- 긴급 버그는 즉시 핫픽스 후 re-build, 비긴급은 Phase 8 전 일괄 처리
- DoD: 7일간 Critical 버그 0 건 유지 + 사장님 승인
- 산출물: REPORTS/PHASE7_SUMMARY.md, 태그 v864.3-phase7

━━━ Phase 8 — 🏆 v864.3 공식 릴리스 ━━━
- 기간: 1일
- 범위: CHANGELOG.md 작성, GitHub Release, GY Logis 현장 전환 공지
- 롤백 계획: v864.2 EXE 백업 유지, 24시간 혼용 운영
- DoD: GY Logis 물류창고 메인 시스템으로 v864.3 공식 전환 완료
- 산출물: CHANGELOG.md, RELEASE_NOTES_v864.3.md, 태그 v864.3-RELEASE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【2】 세션 관리 규칙 (Opus 컨텍스트 위생)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Opus 세션 컨텍스트가 70% 에 근접하면:
  · 진행 중인 Phase 는 일단락 (테스트/커밋까지만)
  · HANDOFF_PROMPT_PHASE{다음N}.md 를 자동 생성
  · 사장님께 "새 세션 시작 권장" 알리고 현재 세션은 깨끗이 종료
- 매 Phase 완료 시 반드시 git commit + tag 후 사장님 승인 대기
- 긴급 혼선 발생 시: git reset --hard 5f7f5ff (baseline 복원)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【3】 작업 원칙 (Never Break These)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- CLAUDE.md Rule 1: backend/legacy/*, engine_modules/*, features/*, parsers/*, utils/* 수정 금지
- CLAUDE.md Rule 2: UI/Logic Decoupling — frontend 에 비즈니스 로직 금지
- CLAUDE.md Rule 3: Feature Parity 100% — 85 기능 누락 0
- CLAUDE.md Rule 4: 모든 엔드포인트 wrap_engine_call 래핑, 모든 fetch try/catch + Toast
- 응답 계약: NotReady = HTTP 200 + body.ok=false + detail.code='NOT_READY'
- 디자인 토큰: design-tokens.css 변수만 사용, 하드코딩 금지

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【4】 Ruby 페르소나 + 응답 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

내 페르소나: Ruby (Senior Software Architect + PGA Tour Golfer)
응답 형식: [Question] [Intent] [Response] — 질문/응답 시각 기록, Deep-Dive 3 follow-ups
         Best Practice 우선 제시, 영어/베트남어 한 줄 발음 표기로 마무리.
의견 제시: "The old situation was X, my current opinion is Y" 형식
비유: 중학생도 이해할 수 있는 쉬운 비유로 복잡한 개념 설명
디버깅: Professional Debugging Protocol 7 섹션 + 3 Mandatory Checks 준수
금지: 사과, 사실 조작. 모호 시 즉시 역질문.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【5】 지금 바로 할 것
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 6개 파일 읽기 완료 후, REPORTS/PHASE3_PLAN.md Q1 부터 착수.
Q1 완료 → 스모크 테스트 → 스샷 요청 → Q2 진입 → Q3 진입 →
REPORTS/PHASE3_COMPLETE.md 작성 → git commit + 태그 v864.3-phase3 →
사장님 승인 받으면 Phase 4-A 배치 계획서 (REPORTS/PHASE4_PLAN.md) 작성 후 시작.

지금 Phase 3 Q1 부터 착수해줘.
```

## 🎯 [복붙용 프롬프트 — 여기까지]

---

## 📊 이 프롬프트가 다른 HANDOFF_PROMPT_PHASE3.md 와 다른 점

| 비교 | HANDOFF_PROMPT_PHASE3.md | HANDOFF_PROMPT_FULL.md (이 파일) |
|---|---|---|
| 범위 | Phase 3 (Q1+Q2+Q3) 1 개 세션 | Phase 3 → Phase 8 전체 여정 |
| Phase 완료 게이트 | Q1-3 DoD 체크리스트 | 5단계 게이트 (계획→실행→보고→검수→커밋) |
| 세션 관리 | 언급 없음 | 컨텍스트 70% 룰 + auto handoff 생성 |
| Baseline commit | 없음 | `5f7f5ff` 명시 (rollback 가능) |
| Phase 별 소요 | 80분 | 3~7일 (Phase 4+) · 총 ≈ 3주 |
| 사장님 검수 | 스샷 1장 | Phase 마다 GO 사인 대기 |

---

## 💡 Tips (새 세션 Opus 에게)

1. **첫 6 파일 Read 는 병렬로** — 6개 동시 요청 시 응답 속도 ~2배
2. **Phase 3 는 반드시 한 세션 내 완료** (80 분이므로 컨텍스트 여유)
3. **Phase 4 는 배치별로 3 세션 권장** (25 기능 × 3 배치 = 3 세션)
4. **Phase 5-6 은 각각 1 세션** (테스트/빌드는 도구 의존적, 짧게 집중)
5. **Phase 7 은 사장님이 주도**, Opus 는 버그 리포트 받아 핫픽스만
6. **Phase 8 는 릴리스 의식** — 사장님과 함께 커밋 + 태그 + 공지

---

## 🔐 롤백 시나리오 요약

| 상황 | 명령어 | 복원 지점 |
|---|---|---|
| Phase 3 중 치명 버그 | `git reset --hard v864.3-phase2-step3` 또는 `5f7f5ff` | Phase 2 Step 3 완전 종료 |
| Phase 4 배치 중 실패 | `git reset --hard v864.3-phase3` | Phase 3 완료 직후 |
| Phase 7 실사용 Critical 버그 | `git reset --hard v864.3-phase6` + EXE 재빌드 | 빌드 직후, Phase 7 재개 |
| Phase 8 릴리스 실패 | v864.2 EXE 로 임시 복구, Phase 7 재진입 | 사장님 구버전 + Critical 핫픽스 |

---

## 🏌️ Ruby 의 메모 (미래의 나에게)

Phase 3 는 짧지만, Phase 4 가 진짜 산이다 (82 기능 = 체력전).
- 각 배치 25 기능 × 평균 30 분 = 12.5 시간 × 3 배치 = ≈ 38 시간
- 사장님 본업 병행 고려해 **하루 2-3 시간씩 5-7 일** 분산 권장
- NotReady soft-fail 이 이미 설치되어 있으므로, 미구현 기능은 그대로 두고 배치 단위로 전진 가능

Phase 5 회귀 테스트를 **Phase 4 직후** 에 넣은 이유는, 배포 직전 한 번에 검사하면 실패 원인 추적이 어렵기 때문이다 (골프로 치면, 18 번 홀에서 스윙 교정하지 말고 라운드 중간에 템포 체크하는 것과 같다).

---

**작성**: Ruby (Senior Software Architect)
**일자**: 2026-04-21 (화) 22:00 KST
**다음 세션 기대 개시**: 사장님 복붙 직후
**최종 도달 목표**: v864.3-RELEASE 태그 + GY Logis 현장 전환 (≈ 2026-05-09 ~ 05-25)
