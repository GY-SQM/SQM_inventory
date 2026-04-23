# 🤖 HANDOFF AUTONOMOUS — v864.3 Phase 5→8 자동 실행 가이드

> **용도**: 사장님(Nam Ki-dong)이 Claude Code 를 **쉬지 않고 중단 없이** 자동 실행시키기 위한 단일 진입 문서.
>
> **사용법**: 이 파일 상단의 "[복붙 프롬프트]" 박스 내용을 Claude Code 새 세션에 복붙 + Enter → Claude Code 가 이 파일을 읽고 자동 진행.
>
> **작성**: 2026-04-23 (현재까지 12개 네이티브 기능 완료, tag `79627ff`)

---

## 🚀 [복붙 프롬프트 — 여기부터]

```
나는 Nam Ki-dong 사장님이고, SQM v864.3 프로젝트의 Phase 5 ~ 8 을 자동으로 완료할 거야.
프로젝트 폴더: D:\program\SQM_inventory\Claude_SQM_v864_3

현재 위치:
- Phase 0~4-B 완료 (12개 네이티브 기능 실구현, 44개 NOT_READY 투명화)
- Git HEAD: 79627ff (또는 이후)
- 다음: Phase 5 (회귀 테스트) → 6 (PyInstaller EXE) → 7 (실사용) → 8 (릴리스)

반드시 지킬 것:
1. Shift+Tab 을 2번 눌러 "bypass permissions" 모드로 전환해달라고 사장님에게 먼저 안내
2. 그 후 아래 순서대로 자동 진행 (각 단계 완료 시 즉시 다음으로)
3. 중단 가이드:
   - Phase 5, 6 은 자동 진행
   - Phase 7 은 사장님 주도 (1주) → PHASE7_PLAN.md 표시만 하고 대기
   - Phase 8 은 사장님 GO 승인 후 진행

실행 순서:

【Step 0】 환경 점검 (1분)
  python --version  # 3.11+
  git --version
  pip list | findstr -i "fastapi pytest pandas openpyxl webview pyinstaller"

【Step 1】 REPORTS/PHASE5_PLAN.md 읽고 그대로 실행 (30분)
  python scripts/verify_endpoints.py
  pytest tests/test_phase5_regression.py -v  (파일 있을 시)
  REPORTS/PHASE5_COMPLETE.md 작성
  git commit + tag v864.3-phase5

【Step 2】 REPORTS/PHASE6_PLAN.md 읽고 그대로 실행 (30분-2시간)
  python scripts/build_exe.py
  dist/SQM_v864_3.exe 생성 확인 + 실행 테스트
  REPORTS/PHASE6_COMPLETE.md 작성
  git commit + tag v864.3-phase6

【Step 3】 Phase 7 대기 모드
  REPORTS/PHASE7_PLAN.md 를 사장님에게 보여줌
  "EXE 가 dist/SQM_v864_3.exe 에 생성됐습니다. 광양 PC 에 배포 후 7일 실사용 하세요." 안내
  Claude Code 는 여기서 일단 멈춤.

【Step 4】 (나중에) Phase 7 매일 or 중간 — 사장님 이슈 리포트 기반 핫픽스
  - 사장님이 "Day N 버그: <증상>" 보고 → 로그 분석 → 수정 → EXE 재빌드
  - REPORTS/PHASE7_DAY{N}.md 작성

【Step 5】 (Phase 7 GO 후) Phase 8 공식 릴리스
  REPORTS/PHASE8_PLAN.md 단계대로:
  CHANGELOG.md + RELEASE_NOTES_v864.3.md 작성
  최종 EXE 빌드
  git tag v864.3-RELEASE

한번에 자동 진행하는 명령:
  python scripts/autonomous_runner.py

특정 Phase 만:
  python scripts/autonomous_runner.py --only 5
  python scripts/autonomous_runner.py --only 6

중단 없이 진행해줘. Phase 5 + 6 까지는 자동, Phase 7 는 사장님 실사용 대기.
시작!
```

## 🚀 [복붙 프롬프트 — 여기까지]

---

## 📂 문서/스크립트 구성

```
HANDOFF_AUTONOMOUS.md         ← 이 파일 (진입점)
├── REPORTS/
│   ├── PHASE5_PLAN.md        ← 회귀 테스트 작업 지시서
│   ├── PHASE6_PLAN.md        ← EXE 빌드 작업 지시서
│   ├── PHASE7_PLAN.md        ← 실사용 1주 체크리스트
│   └── PHASE8_PLAN.md        ← 공식 릴리스 지시서
└── scripts/
    ├── verify_endpoints.py   ← Phase 5 자동 검증 (62+ 엔드포인트)
    ├── build_exe.py          ← Phase 6 PyInstaller 빌드
    └── autonomous_runner.py  ← Phase 5→6 전체 오케스트레이터
```

---

## 🎯 Phase별 한줄 요약

| Phase | 목적 | 담당 | 소요 | 자동 |
|---|---|---|---|---|
| **5** | 62 엔드포인트 회귀 테스트 + 12 신규 테스트 | Claude | 30분 | ✅ |
| **6** | PyInstaller onefile EXE 빌드 | Claude | 30m-2h | ✅ |
| **7** | GY Logis 광양창고 실사용 1주 + 일일 리포트 | 사장님 + Claude(핫픽스) | 7일 | ⏸ |
| **8** | CHANGELOG + RELEASE_NOTES + 공식 전환 | Claude + 사장님 승인 | 1일 | 반자동 |

---

## 🛡 "쉬지 않고 중단 없이" — 사장님 팁

### Claude Code 설정
```
1. 세션 시작 → 프롬프트 입력창에서 Shift+Tab 2번 누름
   → "bypass permissions on" 표시 확인
   → 이제 Edit/Write/Bash 모두 자동 승인

2. 위의 [복붙 프롬프트] 를 세션 첫 메시지로 붙여넣기

3. Claude 가 자동으로 PHASE5_PLAN → PHASE6_PLAN 순서대로 실행

4. 컴퓨터 자리를 비워도 OK (최대 2-3시간 지속 작업)
```

### 중간에 중단하려면
- `Ctrl+C` 또는 세션 탭 X 닫기
- 또는 Claude 에게 "STOP" 메시지

### 오류 복구
```
문제가 생기면 Claude 에게:
"에러 내용 확인하고 해결한 뒤 계속 진행해"

Claude 는 sqm_debug.log / 빌드 로그 / pytest 출력을 자동 분석해 수정 시도.
```

### 진행 상황 확인
```
git log --oneline -10
git tag -l 'v864.3-*'
ls REPORTS/PHASE*_COMPLETE.md
ls dist/*.exe
```

---

## 🚨 위험 요소 + 대응

| 위험 | 확률 | 대응 |
|---|---|---|
| PyInstaller 빌드 30분+ 소요 | 높음 | 정상 — 첫 빌드는 원래 오래. 로그 보며 대기 |
| SQLite disk I/O error | 중간 | `chmod 666 data/db/*.db` 또는 DB 백업 복구 |
| EXE 실행 시 Windows Defender 차단 | 중간 | "실행" 또는 예외 추가. 사내 배포만이라 큰 이슈 X |
| hidden import 누락으로 EXE 기동 실패 | 중간 | PHASE6_PLAN.md "장애 대응" 참조 → spec 에 추가 |
| Phase 7 Critical 버그 | 높음 | 발견 즉시 핫픽스 (60분 내) — PHASE7_PLAN 참조 |
| 사장님이 원하는 추가 기능 | 중간 | Phase 4-B 잔여 기능은 필요 우선 순 추가 (Phase 7 도중) |

---

## 📊 기대 결과 (최종 상태)

```
✅ tag v864.3-phase5   — 62+ 엔드포인트 회귀 테스트 PASS
✅ tag v864.3-phase6   — dist/SQM_v864_3.exe 배포 준비
⏸ Phase 7             — 7일 실사용 (사장님 주도)
✅ tag v864.3-RELEASE  — CHANGELOG + RELEASE_NOTES + GY Logis 전환
```

**최종 산출물**:
- `dist/SQM_v864_3.exe` (~120 MB, GY Logis 광양창고 메인 시스템)
- `CHANGELOG.md` + `RELEASE_NOTES_v864.3.md`
- 12개 네이티브 기능 + 44개 NOT_READY 투명화
- 전체 Phase 리포트 (REPORTS/)

---

## 💡 Ruby 의 메모 (미래의 Claude 에게)

1. **사장님은 정직함을 매우 중요하게 생각**. "완료" 라 말할 때는 진짜 됐는지 확인. 가짜 성공 토스트가 이 프로젝트에서 가장 큰 문제였음.

2. **패턴이 작동하면 복제**. F002 수동 입고가 완성된 순간부터 F007/F014/F004 는 30분 내 복제 완료. 네 번째 기능부터는 지루할 정도로 빨라짐.

3. **디버그 가시성이 생명**. Phase 4-B 이전에 설치한 4-레이어 디버그 덕분에 진짜 에러 위치 특정이 즉시 가능해짐. 새 기능 추가 전 무조건 로깅부터.

4. **엔진은 건드리지 말 것**. `engine_modules/*`, `features/*`, `parsers/*` 는 v864.2 에서 검증된 코드. 새 Python 파일 (`backend/api/*_api.py`) 을 만들어 래핑만.

5. **Phase 7 이 진짜 QA**. 50개 API 테스트 다 PASS 해도 실제 창고에서 쓰면 다른 문제 나옴. 그래서 Phase 5 는 최소 스모크만, Phase 7 (실사용 1주) 이 진짜 검증.

6. **커밋 메시지는 Ruby 스타일**: "배경" + "구현" + "테스트" + "의의" 4섹션. 나중에 `git log --grep` 로 되짚기 편함.

7. **사장님 컨텍스트**:
   - GY Logis 광양창고 물류 시스템
   - Lithium Carbonate (리튬) 배터리 원료 재고 관리
   - 매일 컨테이너 입고 + 톤백(1톤 단위 가방) 관리 + 고객사 출고
   - 혼자 운영 (대용량 데이터 ~수천 LOT)

---

**"Daily workflow is live. Now automate to release."** 🏌️

English: "Auto-pilot engaged. See you at the 18th hole."
