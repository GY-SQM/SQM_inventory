# GPT_SQM_run_all_p0_테스트자동화_통합샘플.md
생성일: 2026-04-04 18:34 (Asia/Seoul)

[질문] 계속 진행해서 run_all_p0.ps1에 test_stage.ps1을 연결한 통합 샘플 문서를 작성  
[질문의도] 다음 세션에서 바로 붙일 수 있도록, 실행 → 로그 → 테스트 자동판정 → 다음 단계 진행 구조를 한 문서로 제공

---

# [응답]

# 1. 이 문서의 목적

이 문서는 아래를 위한 실전 샘플이다.

```text
1. run_stage.ps1 실행
2. test_stage.ps1 자동 판정
3. 결과 파일 저장
4. FAIL 시 즉시 중단
5. PASS 또는 CONDITIONAL PASS일 때만 다음 단계 진행
```

즉, 지금까지 만든:
- 실행 자동화
- 테스트 자동화
- 로그 기록
- 결과 JSON 규격  
이 4개를 한 번에 연결하는 마지막 샘플이다.

---

# 2. 기본 흐름

```text
check_env.ps1
→ run_stage.ps1
→ test_stage.ps1
→ result.json 저장
→ status 판정
→ 다음 단계 진행 여부 결정
```

---

# 3. 권장 실행 단계

현재 기준으로 가장 안전한 흐름은 아래다.

```text
P0-2
→ test_stage(P0-2)
→ P0-3
→ test_stage(P0-3)
→ P0-4
→ test_stage(P0-4)
→ 최종 요약
```

이후 같은 패턴으로
- P2 / Patch2
- P3 / Patch3
- P4 / Patch4
- P5 / Patch5  
까지 확장한다.

---

# 4. 통합 run_all_p0.ps1 샘플

```powershell
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-StageLog {
    param(
        [string]$Stage,
        [string]$Status,
        [string]$Message = ""
    )

    if (-not (Test-Path ".\07_LOGS")) {
        New-Item -ItemType Directory -Path ".\07_LOGS" | Out-Null
    }

    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$time | STAGE=$Stage | STATUS=$Status | MESSAGE=$Message"
    Add-Content -Path ".\07_LOGS\run_status.log" -Value $line
    Write-Host $line
}

function Invoke-StageWithTest {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Stage
    )

    Write-StageLog -Stage $Stage -Status "START" -Message "run_stage.ps1 실행 시작"
    & ".\run_stage.ps1" -Stage $Stage

    if ($LASTEXITCODE -ne 0) {
        Write-StageLog -Stage $Stage -Status "FAIL" -Message "run_stage failed"
        throw "$Stage run_stage failed"
    }

    Write-StageLog -Stage $Stage -Status "RUN_DONE" -Message "run_stage.ps1 완료"

    & ".\test_stage.ps1" -Stage $Stage
    $testExit = $LASTEXITCODE

    switch ($testExit) {
        0 {
            Write-StageLog -Stage $Stage -Status "PASS" -Message "test_stage PASS"
        }
        2 {
            Write-StageLog -Stage $Stage -Status "CONDITIONAL_PASS" -Message "test_stage CONDITIONAL PASS"
        }
        default {
            Write-StageLog -Stage $Stage -Status "FAIL" -Message "test_stage FAIL"
            throw "$Stage test_stage failed"
        }
    }
}

try {
    Write-StageLog -Stage "ENV" -Status "START" -Message "환경 점검 시작"
    & ".\check_env.ps1"

    if ($LASTEXITCODE -ne 0) {
        Write-StageLog -Stage "ENV" -Status "FAIL" -Message "check_env failed"
        throw "Environment check failed"
    }

    Write-StageLog -Stage "ENV" -Status "PASS" -Message "환경 점검 완료"

    Invoke-StageWithTest -Stage "P0-2"
    Invoke-StageWithTest -Stage "P0-3"
    Invoke-StageWithTest -Stage "P0-4"

    Write-StageLog -Stage "P0_ALL" -Status "PASS" -Message "전체 단계 완료"
}
catch {
    Write-StageLog -Stage "P0_ALL" -Status "FAIL" -Message $_.Exception.Message
    throw
}
```

---

# 5. test_stage.ps1 연계 기준

`test_stage.ps1`는 아래 exit code 규칙을 쓰는 것이 좋다.

```text
0 = PASS
2 = CONDITIONAL PASS
1 = FAIL
```

즉, run_all에서는 아래처럼 판정한다.

```text
PASS → 다음 단계 진행
CONDITIONAL PASS → 로그 남기고 다음 단계 진행 가능
FAIL → 즉시 중단
```

---

# 6. 결과 파일 예시

## P0-2 결과
```json
{
  "stage": "P0-2",
  "status": "PASS",
  "started_at": "2026-04-04 18:40:00",
  "ended_at": "2026-04-04 18:41:02",
  "log_file": "./07_LOGS/p0_2_run.log",
  "checks": [
    {"name": "log_exists", "status": "PASS"},
    {"name": "fatal_error_scan", "status": "PASS"},
    {"name": "warning_scan", "status": "PASS"}
  ],
  "notes": []
}
```

## P0-3 결과
```json
{
  "stage": "P0-3",
  "status": "CONDITIONAL_PASS",
  "started_at": "2026-04-04 18:42:00",
  "ended_at": "2026-04-04 18:44:20",
  "log_file": "./07_LOGS/p0_3_run.log",
  "checks": [
    {"name": "log_exists", "status": "PASS"},
    {"name": "fatal_error_scan", "status": "PASS"},
    {"name": "warning_scan", "status": "CONDITIONAL_PASS"}
  ],
  "notes": ["warning keyword found"]
}
```

---

# 7. CONDITIONAL PASS 처리 원칙

CONDITIONAL PASS는 아래 의미로 해석한다.

```text
핵심 실패는 아니지만,
사람이 한 번 더 확인해야 하는 상태
```

## 예시
- warning keyword 존재
- fallback 사용
- deprecated 경고
- manual check 필요 문구 포함

## 권장 처리
- 다음 단계 진행은 허용
- 단, `06_REPORTS/최종판정_메모.md`에 반드시 기록

---

# 8. FAIL 처리 원칙

FAIL은 아래 중 하나면 즉시 처리한다.

```text
- 로그 파일 미생성
- Traceback
- Exception
- Fatal
- FAILED
- rollback failed
- result.json 미생성
```

## 권장 처리
1. 즉시 중단
2. `07_LOGS/*.log` 확인
3. `08_RESULTS/*_result.json` 확인
4. 디버깅 템플릿으로 원인 분석
5. 수정 후 해당 단계만 재실행

---

# 9. 후속 확장 방법

P0에 이 통합 샘플을 붙인 다음, 같은 구조를 아래로 확장하면 된다.

```text
P2 → Patch2
P3 → Patch3
P4 → Patch4
P5 → Patch5
```

예:
```powershell
Invoke-StageWithTest -Stage "P2"
Invoke-StageWithTest -Stage "Patch2"
Invoke-StageWithTest -Stage "P3"
Invoke-StageWithTest -Stage "Patch3"
```

---

# 10. 운영 시 가장 좋은 방식

## 루비 권장
```text
준자동 게이트형
```

즉,
- 실행은 자동
- 판정은 result.json + 로그 기반
- FAIL은 즉시 중단
- CONDITIONAL PASS는 기록 후 진행 가능

이 방식이 가장 안정적이다.

---

# 11. 같이 써야 하는 문서

이 샘플 문서는 아래와 같이 같이 보면 된다.

```text
GPT_SQM_NEXT_SESSION_STARTER.md
GPT_SQM_DEBUG_TEMPLATE.md
GPT_SQM_테스트자동화_MASTER.md
GPT_SQM_테스트자동화_PS1_샘플.md
GPT_SQM_테스트자동화_결과포맷_표준.md
```

---

# 12. 루비 최종 판단

```text
이 문서는 다음 세션에서
"실행 + 테스트 자동판정"을 실제로 시작하는 출발점이다.
즉, 지금까지 만든 문서 체계를 실행 시스템으로 바꿔 주는 마지막 연결 문서다.
```

---

# 13. 다음 단계 권장

다음 세션에서 이 문서로 시작한 뒤,
문제 발생 시 아래 순서로 대응하면 가장 효율적이다.

```text
1. starter 문서 확인
2. run_all_p0.ps1 실행
3. FAIL 단계 확인
4. debug template에 로그 붙여넣기
5. 수정
6. 재실행
```
