# GPT_ClaudeCode_P0_종료직전_통합지시서_강화판.md
생성일: 2026-04-04 18:12 (Asia/Seoul)
인코딩: UTF-8
기준:
- MASTER_FINAL_v867_통합완성본.md
- P0 백엔드 엔진 연결 수정 결과
- pytest 89개 통과
- 누락 탭 5개 구현 완료
- 전체 API 30개 엔드포인트 상태
- dev 서버 정상 동작

---

## [질문]
P0 종료 직전 단계에서 Claude Code에 바로 투입할 수 있는 실제 md 파일 형태의 통합 지시서를 작성하라.

## [질문의도]
현재 P0는 백엔드 핵심 연결과 주요 누락 탭 보강까지 상당 부분 완료되었다.
그러나 운영 완료 판정에는 아직 다음 3개가 남아 있다.

1. 프론트 운영 빌드 성공
2. Telegram Bridge 동작 검증
3. run_master.bat / run_master.ps1 실행 검증

따라서 이번 문서는 위 3개를 최우선 순서로 처리하고,
마지막에 P0 완료 보고서를 남기도록 하는
실전 투입용 종료 직전 통합 지시서다.

---

## 1. 현재 상태 요약

현재까지 확인된 상태는 다음과 같다.

- pytest: 89개 전부 통과
- Write API 4개가 SQMInventoryEngineV3 경유로 정상 연결
- 누락 탭 5개 구현 완료
  - MovePage `/move`
  - ScanPage `/scan`
  - LogPage `/log`
  - SummaryPage `/summary`
  - CargoOverviewPage `/cargo`
- 전체 API: 30개 엔드포인트
- dev 서버: 정상 동작 가능
- 현재 남은 핵심 이슈:
  - `npm run build` 실패 (rollup native / vite v8 / Windows 계열 추정)
  - Telegram Bridge 동작 미검증
  - `run_master.bat` / `run_master.ps1` 동작 미검증

---

## 2. 최우선 작업 순서

이번 작업은 아래 순서를 반드시 그대로 따른다.

```text
P0. npm run build 실패 원인 해결
P1. Telegram Bridge 동작 검증
P2. run_master.bat / run_master.ps1 실행 검증
P3. P0 완료 보고서 작성
```

---

## 3. 강제 실행 규칙

### 3-1. 진행 원칙
- 절대 사용자에게 질문하지 말 것
- 가능한 모든 판단은 스스로 내릴 것
- 실패 시 자동 수정 후 재시도할 것
- 로그와 결과를 반드시 남길 것
- 단계별 PASS 전에는 다음 단계로 넘어가지 말 것

### 3-2. 금지 사항
- `npm run build` 성공 전 운영 완료 선언 금지
- Telegram Bridge 검증 전 run_master 완료 선언 금지
- run_master 검증 전 P0 완료 보고서 작성 금지
- 테스트 실패 상태에서 다음 단계 진입 금지
- 문제 원인을 추정만 하고 실제 검증 없이 종료 금지

### 3-3. 단계 공통 흐름
모든 단계는 반드시 아래 순서를 따른다.

```text
Pre-Test
→ 실행
→ 결과 확인
→ 실패 시 수정
→ Re-Test
→ PASS
→ 다음 단계
```

---

## 4. [P0] 프론트 빌드 문제 해결

### 4-1. 목표
`npm run build`를 성공시켜
프론트가 개발 모드뿐 아니라 운영 모드에서도 빌드 가능함을 증명한다.

### 4-2. 우선 점검 순서
아래 순서를 기본으로 수행한다.

```bash
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
npm run build
```

Windows 환경이면 PowerShell 기준으로 동등 명령으로 수행한다.

### 4-3. 추가 점검 항목
아래 항목을 순서대로 점검한다.

- Node 버전 확인
- npm 버전 확인
- `vite` 버전 확인
- `rollup` 버전 확인
- lockfile 충돌 여부 확인
- optional/native dependency 설치 누락 여부 확인
- Windows 환경에서 rollup native binary 누락 여부 확인
- package.json dependency / devDependency 정합성 확인

### 4-4. 수정 허용 범위
필요 시 아래 수정은 허용한다.

- `node_modules` 재설치
- `package-lock.json` 재생성
- `vite` 버전 조정
- `rollup` 버전 조정
- build script 보정
- OS별 install script 보정

단, 수정 시 반드시 아래를 기록할 것.

- 수정 전 증상
- 수정 원인
- 수정한 파일
- 수정 후 결과

### 4-5. PASS 조건
아래를 모두 만족해야 PASS다.

- `npm run build` exit code 0
- build 산출물 생성 확인
- import 오류 없음
- vite/rollup 관련 fatal error 없음

### 4-6. 산출물
아래를 문서화한다.

- `docs/P0_BUILD_FIX_REPORT.md`

보고서에는 최소 아래를 넣는다.

- 실패 원인
- 조치 내용
- 변경 파일
- 최종 build 결과
- 남은 리스크

---

## 5. [P1] Telegram Bridge 동작 검증

### 5-1. 목표
Telegram Bridge가 실제로 Claude 작업 흐름을 중단 없이 이어받을 수 있는지 검증한다.

### 5-2. 검증 항목
반드시 아래를 확인한다.

- Claude 출력이 Telegram으로 전달되는가
- 최근 출력 300~500자가 포함되는가
- 현재 질문/선택/다음 단계 문맥이 포함되는가
- 가능한 응답 방법 안내가 포함되는가
- `y / n` 응답이 정상 반영되는가
- `1 / 2 / 3` 응답이 정상 반영되는가
- 자유 문장 명령이 정상 반영되는가
- idle/wait 상태에서 bridge가 정상 반응하는가

### 5-3. 테스트 시나리오
최소 아래 시나리오를 돌린다.

1. yes/no 유형 대기
2. 1/2/3 선택 유형 대기
3. 자유 문장 지시 입력
4. 무응답/idle 상태 처리
5. 오류 메시지 전파 여부

### 5-4. PASS 조건
아래를 모두 만족해야 PASS다.

- Telegram으로 메시지가 정상 수신된다
- 응답이 실제 흐름에 반영된다
- 메시지 포맷이 기준에 맞는다
- 중단/멈춤 상태에서 bridge가 정상 이어준다

### 5-5. 산출물
아래를 문서화한다.

- `docs/P0_TELEGRAM_BRIDGE_VALIDATION_REPORT.md`

보고서에는 최소 아래를 넣는다.

- 테스트 시나리오
- 성공/실패 결과
- 메시지 예시
- 오류 발생 시 수정 내용
- 최종 PASS 여부

---

## 6. [P2] run_master.bat / run_master.ps1 실행 검증

### 6-1. 목표
실제 운영 흐름이 아래처럼 살아 있는지 검증한다.

```text
BAT / PS1 실행
→ 사전 점검
→ Telegram Bridge 실행
→ Claude 실행
→ MASTER 기준 작업 진행
```

### 6-2. 점검 항목
아래 항목을 모두 확인한다.

- `run_master.bat` 존재 여부
- `run_master.ps1` 존재 여부
- `.env` 로드 여부
- logs/docs 폴더 확인
- bridge 파일 존재 여부
- MASTER 파일 경로 확인
- 실행 중 경로 오류 여부
- 실행 중 권한 오류 여부
- 실행 로그 생성 여부

### 6-3. 실행 검증
아래 두 흐름 모두 확인한다.

- BAT 기준 실행
- PS1 기준 실행

가능하면 각각 1회 이상 실제 기동 확인하고,
성공/실패 여부를 명시할 것.

### 6-4. PASS 조건
아래를 모두 만족해야 PASS다.

- BAT가 정상 실행된다
- PS1이 정상 실행된다
- `.env`가 정상 로드된다
- bridge와 MASTER 연결이 확인된다
- 로그 파일이 생성된다

### 6-5. 산출물
아래를 문서화한다.

- `docs/P0_RUN_MASTER_VALIDATION_REPORT.md`

보고서에는 최소 아래를 넣는다.

- BAT 실행 결과
- PS1 실행 결과
- 환경변수 로드 결과
- 로그 생성 여부
- 수정 파일 및 수정 내용
- 최종 PASS 여부

---

## 7. [P3] P0 완료 보고서 작성

### 7-1. 목표
P0 단계 전체를 종료할 수 있는 수준으로 정리한다.

### 7-2. 완료 보고서 파일
아래 파일을 작성한다.

- `docs/P0_COMPLETION_REPORT.md`
- `docs/P0_OPERATION_VALIDATION_REPORT.md`

### 7-3. `P0_COMPLETION_REPORT.md`에 포함할 내용
- P0 목표 요약
- 완료된 변경 사항
- 변경 파일 목록
- Write API 연결 결과
- 누락 탭 구현 결과
- 테스트 통과 현황
- build 결과
- Telegram Bridge 결과
- run_master 결과
- 남은 이슈
- P1 진입 권고

### 7-4. `P0_OPERATION_VALIDATION_REPORT.md`에 포함할 내용
- 운영 관점 검증 항목
- build 검증 결과
- Bridge 검증 결과
- BAT/PS1 실행 검증 결과
- 로그/문서 산출물 목록
- 운영 진입 가능 여부 판단

### 7-5. PASS 조건
아래를 모두 만족해야 P0 종료 문서 작성 완료로 본다.

- build 보고서 존재
- bridge 보고서 존재
- run_master 보고서 존재
- completion 보고서 존재
- operation validation 보고서 존재

---

## 8. 단계별 진입 게이트

### Gate A: P0 → P1 진입 조건
- `npm run build` 성공
- build 보고서 작성 완료

### Gate B: P1 → P2 진입 조건
- Telegram Bridge 검증 PASS
- bridge 보고서 작성 완료

### Gate C: P2 → P3 진입 조건
- `run_master.bat` / `.ps1` 검증 PASS
- run_master 보고서 작성 완료

### Gate D: P3 → 최종 종료 조건
- `P0_COMPLETION_REPORT.md` 작성 완료
- `P0_OPERATION_VALIDATION_REPORT.md` 작성 완료

---

## 9. 최종 완료 조건

아래를 모두 만족해야 이번 작업을 종료할 수 있다.

```text
1. npm run build 성공
2. Telegram Bridge 정상 동작
3. run_master.bat / run_master.ps1 정상 실행
4. 보고서 5종 작성 완료
```

보고서 5종은 아래다.

- `docs/P0_BUILD_FIX_REPORT.md`
- `docs/P0_TELEGRAM_BRIDGE_VALIDATION_REPORT.md`
- `docs/P0_RUN_MASTER_VALIDATION_REPORT.md`
- `docs/P0_COMPLETION_REPORT.md`
- `docs/P0_OPERATION_VALIDATION_REPORT.md`

---

## 10. Claude Code 실행 선언

Claude Code는 이번 문서를 기준으로 아래 원칙을 따른다.

- 질문 없이 진행한다
- 추정이 아니라 실제 실행 결과로 판정한다
- 실패 시 자동 수정 후 재시도한다
- 이전 단계 PASS 전에는 다음 단계로 넘어가지 않는다
- 모든 결과는 문서로 남긴다

이번 작업은 P0 종료 직전 운영 검증 및 마감 작업이다.
새 기능 추가보다
현재 결과물을 운영 가능한 상태로 닫는 것을 우선한다.
