# Codex Autonomous Run — v864-2 to v864-4

작성일: 2026-04-26
목적: 사용자가 외출 중이어도 Codex를 다시 시작한 뒤 중단 없이 `v864-2` 원본 기준으로 `v864-4` 변경 작업, 검증, 정리까지 진행하기 위한 단일 진입 문서.

## 1. 폴더 역할 고정

절대 혼동하지 않는다.

```text
D:\program\SQM_inventory\Claude_SQM_v864_2
= 원본 폴더. 읽기 전용 기준.

D:\program\SQM_inventory\Claude_SQM_v864_3
= 기존 MD/작업 설명서 참고용.

D:\program\SQM_inventory\Claude_SQM_v864_4
= 실제 변경 대상 폴더. 모든 수정, 검증, 빌드, 최종 문서 작성은 여기에서 수행.
```

## 2. Codex 다시 시작 방법

새 Codex 세션을 열고 작업 폴더를 반드시 v864-4로 잡는다.

```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_4
codex
```

Codex가 시작되면 아래 프롬프트를 그대로 붙여넣는다.

```text
나는 지금 외출 중이니 중단 없이 자동으로 진행해줘.

작업 폴더:
D:\program\SQM_inventory\Claude_SQM_v864_4

폴더 역할:
- D:\program\SQM_inventory\Claude_SQM_v864_2 = 원본, 읽기 전용
- D:\program\SQM_inventory\Claude_SQM_v864_3 = 기존 MD 참고용
- D:\program\SQM_inventory\Claude_SQM_v864_4 = 실제 수정 대상

반드시 먼저 읽을 문서:
1. D:\program\SQM_inventory\Claude_SQM_v864_4\V864_2_TO_V864_4_MIGRATION_GUIDE.md
2. D:\program\SQM_inventory\Claude_SQM_v864_4\CODEX_AUTONOMOUS_RUN_V864_2_TO_V864_4.md
3. D:\program\SQM_inventory\Claude_SQM_v864_4\REPORTS\PHASE5_COMPLETE.md
4. D:\program\SQM_inventory\Claude_SQM_v864_4\docs\FEATURE_PROGRESS.md

진행 규칙:
- v864-2는 절대 수정하지 말고 읽기만 해.
- v864-3은 기존 작업 설명서 참고용으로만 사용해.
- 실제 수정은 v864-4에서만 해.
- 이미 v864-4에 구현된 것은 재구현하지 말고 검증 후 PASS 처리해.
- 미구현 또는 불완전한 항목만 v864-2 동작과 대조해서 보강해.
- 입고/출고/반품/Allocation은 All-or-Nothing 원칙을 지켜.
- Excel/데이터 입력은 내장 템플릿 기반 붙여넣기 또는 파일 업로드 방식으로 통일해.
- 작업 중 경로가 v864-3, v864_20260329_FULL, sqm_2_upload_clean_v864_2로 남아 있으면 v864-4 기준으로 보정해.

수행 순서:
1. v864-4 설정과 경로 하드코딩 점검
2. node --check frontend\js\sqm-inline.js
3. Python 핵심 파일 py_compile
4. scripts\verify_endpoints.py 실행
5. tests\test_phase5_regression.py 실행
6. scripts\test_all_menus_playwright.py --headless 실행 가능하면 실행
7. 실패한 항목만 v864-2 원본과 비교해서 v864-4에 수정
8. 다시 검증
9. 최종 결과를 D:\program\SQM_inventory\Claude_SQM_v864_4\REPORTS\V864_2_TO_V864_4_FINAL_SUMMARY.md 로 작성

허용:
- 필요한 파일 수정
- 테스트/검증 실행
- 보고서 작성

금지:
- v864-2 수정
- v864-3 코드 수정
- git reset --hard
- 사용자 변경분 되돌리기

최종 응답에는 변경 파일, 검증 결과, 남은 리스크만 간단히 정리해줘.
```

## 3. 준비되어 있어야 하는 작업 설명서

현재 준비 완료:

| 문서 | 위치 | 용도 |
|---|---|---|
| 통합 마이그레이션 가이드 | `V864_2_TO_V864_4_MIGRATION_GUIDE.md` | v864-2 원본에서 v864-4로 옮기는 전체 기준 |
| 자동 실행 진입 문서 | `CODEX_AUTONOMOUS_RUN_V864_2_TO_V864_4.md` | Codex 재시작 후 붙여넣을 명령과 운영 규칙 |
| Phase 5 검증 보고 | `REPORTS\PHASE5_COMPLETE.md` | 기존 endpoint/pytest PASS 기록 확인 |
| 기능 진행표 | `docs\FEATURE_PROGRESS.md` | 85개 기능 매핑의 오래된 기준. 최신 판단은 재검증 우선 |

참고용:

| 문서 | 위치 | 주의 |
|---|---|---|
| `STAGE1_MISSING_DIALOGS.md` | `v864-3` | v864-3 기준이므로 경로를 v864-4로 해석 |
| `STAGE2_SKELETON_TO_FULL.md` | `v864-3` | 인코딩 깨짐이 있으므로 항목만 참고 |
| `STAGE3_PAGES_HANDLERS.md` | `v864-3` | 실제 구현 대상은 v864-4 |
| `REPORT_1ST_PHASE_2026-04-26.md` | `v864-3` | 완료 주장 재검증 필요 |
| `REPORT_2ND_AUDIT_2026-04-26.md` | `v864-3` | 메뉴 매핑 참고용 |

## 4. 현재까지 완료된 내용

### 4.1 설정 파일 정리

`v864-2`:

```text
D:\program\SQM_inventory\Claude_SQM_v864_2\.claude\settings.local.json
```

완료:
- `"defaultMode": "bypassPermissions"` 추가
- JSON 깨짐 수정
- 29번 줄 근처 잘못된 `\|` 이스케이프 수정
- 51번 줄 내부 따옴표 누락 수정
- `ConvertFrom-Json` 기준 JSON_OK 확인

`v864-4`:

```text
D:\program\SQM_inventory\Claude_SQM_v864_4\.claude\settings.local.json
```

완료:
- `"defaultMode": "bypassPermissions"` 추가
- v864-2와 같은 JSON 오류 수정
- `Claude_SQM_v864_3`, `Claude_SQM_v864_20260329_FULL` 하드코딩 경로를 `Claude_SQM_v864_4` 기준으로 변경
- 이전 경로 잔존 없음 확인
- JSON_OK 확인

### 4.2 마이그레이션 기준 문서 작성

작성 완료:

```text
D:\program\SQM_inventory\Claude_SQM_v864_4\V864_2_TO_V864_4_MIGRATION_GUIDE.md
```

내용:
- 세 폴더 역할 고정
- 기존 v864-3 Stage 문서의 한계 정리
- v864-4 현재 산출물 확인
- Stage 0부터 Stage 8까지 작업 순서 작성
- 이미 구현된 것은 PASS 처리하고 부족분만 보강하도록 규칙화
- 검증 명령과 최종 DoD 정의

### 4.3 v864-4 산출물 확인

확인된 주요 파일/폴더:

```text
backend\api\__init__.py
backend\api\actions.py
backend\api\actions2.py
backend\api\actions3.py
backend\api\inbound.py
backend\api\outbound_api.py
backend\api\allocation_api.py
backend\api\tonbag_api.py
backend\api\queries.py
backend\api\queries2.py
backend\api\queries3.py
frontend\index.html
frontend\js\sqm-inline.js
frontend\js\handlers\menubar.js
frontend\js\handlers\toolbar.js
frontend\js\pages\*.js
scripts\verify_endpoints.py
scripts\phase5_regression_test.py
scripts\build_exe.py
REPORTS\PHASE5_COMPLETE.md
dist\SQM_v864_3.exe
```

주의:
- `dist\SQM_v864_3.exe`가 이미 있으나, 최종 배포 파일명을 `SQM_v864_4.exe`로 바꿀지 결정이 필요하다.

## 5. 자동 진행 시 실행할 검증 명령

기본 검증:

```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_4

Get-Content .\.claude\settings.local.json -Raw | ConvertFrom-Json | Out-Null

node --check frontend\js\sqm-inline.js

python -m py_compile main_webview.py
python -m py_compile backend\api\__init__.py
python -m py_compile backend\api\inbound.py
python -m py_compile backend\api\outbound_api.py
python -m py_compile backend\api\allocation_api.py
python -m py_compile backend\api\tonbag_api.py

python scripts\verify_endpoints.py
python -m pytest tests\test_phase5_regression.py -v --tb=short
```

가능하면 추가:

```powershell
python scripts\test_menu_playwright.py --headless --standalone
python scripts\test_all_menus_playwright.py --headless
```

빌드:

```powershell
python scripts\build_exe.py
```

## 6. 남은 핵심 점검 항목

우선 점검:
- v864-4에 남은 v864-3 또는 v864_20260329_FULL 경로 하드코딩
- `frontend/js/sqm-inline.js` 문법 오류
- backend API 라우터 import 실패
- verify_endpoints 실패 항목
- pytest 회귀 실패 항목
- 메뉴 클릭 시 아무 반응 없는 data-action
- NOT_READY가 아닌데 실제 기능이 동작하지 않는 항목

기능별 점검:
- PDF 스캔 입고: BL/PL/Invoice/D/O 4-slot, dry_run, save, rollback
- 수동 입고: 내장 템플릿, 붙여넣기, 파일 업로드
- D/O 후속 연결: 8개 필드 update
- 톤백 위치 매핑: preview, 충돌 감지, save
- 반품/재입고: return_history, 상태 rollback
- Allocation: shortage warning, 승인, 승인 반영
- 출고: scan 검증, proof docs, audit log
- 보고서/Excel: 헤더와 하단 문구 규칙
- 설정: API key ENV -> keyring -> INI 순서

## 7. 최종 보고서 작성 위치

자동 작업이 끝나면 반드시 아래 파일을 만든다.

```text
D:\program\SQM_inventory\Claude_SQM_v864_4\REPORTS\V864_2_TO_V864_4_FINAL_SUMMARY.md
```

보고서에 포함할 내용:

```markdown
# v864-2 to v864-4 Final Summary

## 기준 폴더
- v864-2 원본
- v864-3 문서 참고
- v864-4 변경 대상

## 수행 내용
- 설정 파일 정리
- 경로 하드코딩 정리
- 기능 보강
- 테스트 수정
- 문서 작성

## 변경 파일
| 파일 | 변경 내용 |

## 검증 결과
| 명령 | 결과 | 비고 |

## 이미 구현되어 PASS 처리한 항목
| 항목 | 근거 |

## v864-2와 비교해 보강한 항목
| 항목 | v864-2 기준 | v864-4 변경 |

## 남은 리스크
| 리스크 | 영향 | 다음 조치 |

## 최종 판정
- PASS / PARTIAL / BLOCKED 중 하나
```

## 8. 중단 없이 진행할 때의 판단 기준

Codex는 다음 기준으로 스스로 판단한다.

| 상황 | 처리 |
|---|---|
| 이미 v864-4에 구현됨 | 재구현하지 않고 검증 |
| 테스트 실패 | 실패 원인 파일만 수정 |
| v864-2와 v864-4 동작 차이 | v864-2를 기준으로 v864-4 보강 |
| 외부 네트워크 필요 | 꼭 필요할 때만 승인 요청 |
| 빌드 산출물명 혼동 | 문서에 리스크로 남기고, 가능하면 v864-4명으로 통일 |
| v864-2 수정 필요처럼 보임 | 수정하지 않고 v864-4에 대응 로직 구현 |

## 9. 최종 목표

최종 목표는 단순히 파일을 옮기는 것이 아니다.

`v864-2`의 업무 동작을 기준으로 `v864-4` WebView/FastAPI 구조에서 다음을 만족해야 한다.

- 메뉴와 탭은 v864-2 사용자가 혼동하지 않을 정도로 대응
- 입고, Allocation, 출고, 반품, 보고서 흐름이 끊기지 않음
- 실패는 조용히 묻히지 않고 명확한 오류 또는 NOT_READY로 표시
- DB write는 preflight 후 commit, 실패 시 rollback
- Excel/데이터 입력은 내장 템플릿 기반 붙여넣기 또는 파일 업로드로 통일
- 최종 검증 결과와 남은 리스크가 MD로 남음

