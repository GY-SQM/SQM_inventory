# SQM v864-2 to v864-4 Migration Guide

작성일: 2026-04-26
작성자: Ruby

## 1. 문서 목적

이 문서는 `Claude_SQM_v864_2` 원본을 기준으로 `Claude_SQM_v864_4` 변경본을 완성하기 위한 통합 작업 설명서다.

기존 `Claude_SQM_v864_3` 안의 Stage 문서들은 v864-3 기준으로 작성되어 있고, 일부 경로가 `sqm_2_upload_clean_v864_2` 또는 `Claude_SQM_v864_3`에 고정되어 있으며, 인코딩이 깨진 문장이 섞여 있다. 따라서 이 문서를 v864-2에서 v864-4로 옮기는 기준 문서로 사용한다.

## 2. 폴더 역할

| 폴더 | 역할 | 작업 규칙 |
|---|---|---|
| `D:\program\SQM_inventory\Claude_SQM_v864_2` | 원본 기준 | 읽기 전용으로 취급한다. UI, 엔진, DB, 기존 Tkinter 동작을 비교할 때 사용한다. |
| `D:\program\SQM_inventory\Claude_SQM_v864_3` | 이전 작업 문서 보관 | 기존 MD와 handoff 산출물을 참고한다. 코드 변경 대상이 아니다. |
| `D:\program\SQM_inventory\Claude_SQM_v864_4` | 최종 변경 대상 | 실제 수정, 검증, 빌드, 배포 준비는 여기에서만 수행한다. |

## 3. 현재 v864-4 확인 결과

2026-04-26 기준으로 다음 항목은 이미 존재한다. 다시 만들 필요가 없고, 필요한 경우 검증만 수행한다.

| 항목 | v864-4 상태 | 처리 |
|---|---|---|
| `.claude/settings.local.json` | `defaultMode: bypassPermissions` 적용, JSON 문법 검증 완료 | 완료 |
| `docs/handoff/v864_2_structure.json` | 존재 | 완료 |
| `docs/handoff/feature_matrix.json` | 존재 | 완료 |
| `docs/handoff/design_tokens.json` | 존재 | 완료 |
| `main_webview.py` | 존재 | 완료 |
| `backend/api/__init__.py` | 존재 | 완료 |
| `backend/api/*.py` | actions, inbound, outbound, allocation, tonbag, queries 등 존재 | 완료, 기능별 검증 필요 |
| `frontend/index.html` | 존재 | 완료 |
| `frontend/js/sqm-inline.js` | 존재, 대형 통합 JS | 완료, 문법 및 동작 검증 필요 |
| `scripts/verify_endpoints.py` | 존재 | 완료 |
| `scripts/phase5_regression_test.py` | 존재 | 완료 |
| `scripts/build_exe.py` | 존재 | 완료 |
| `REPORTS/PHASE5_COMPLETE.md` | 53 endpoint PASS, pytest 65/65 PASS 기록 존재 | 완료 기록 있음, 최신 재검증 권장 |
| `dist/SQM_v864_3.exe` | 존재 | 산출물명은 v864-4 기준으로 재검토 필요 |

## 4. 마이그레이션 원칙

1. `v864-2`의 검증된 비즈니스 로직은 최대한 재사용한다.
2. `engine_modules`, `features`, `parsers`, `core`는 원본 로직의 Single Source of Truth로 본다.
3. `v864-4`에서는 Tkinter UI를 직접 복사하지 않고 WebView/FastAPI/JS로 연결한다.
4. 입고/출고/반품/Allocation은 All-or-Nothing 원칙을 유지한다.
5. Excel/데이터 입력은 프로그램 내장 템플릿 기반 붙여넣기 또는 파일 업로드 방식으로 통일한다.
6. 이미 v864-4에 구현된 항목은 재구현하지 않고 검증 후 PASS 처리한다.
7. `v864-3` 문서에 남은 `Claude_SQM_v864_3`, `sqm_2_upload_clean_v864_2`, `Claude_SQM_v864_20260329_FULL` 경로는 모두 v864-4 기준으로 바꿔 해석한다.

## 5. 기존 v864-3 문서에서 이어받을 내용

| 기존 문서 | 사용할 내용 | v864-4 기준 보정 |
|---|---|---|
| `STAGE1_MISSING_DIALOGS.md` | 누락 다이얼로그 목록 | 대상 파일을 `Claude_SQM_v864_4\frontend\js\sqm-inline.js`와 `backend\api`로 변경 |
| `STAGE2_SKELETON_TO_FULL.md` | skeleton 모달 보강 목록 | v864-4에 이미 있는 함수는 검증만 수행 |
| `STAGE3_PAGES_HANDLERS.md` | Return/Log 페이지, 입출고 핸들러 이식 항목 | 대상 API를 `backend/api/inbound.py`, `outbound_api.py`, `actions*.py`로 변경 |
| `REPORT_1ST_PHASE_2026-04-26.md` | 1차 포팅 보고 | 완료 주장만 믿지 말고 v864-4에서 재검증 |
| `REPORT_2ND_AUDIT_2026-04-26.md` | 메뉴 1:1 매핑 기준 | v864-4의 `frontend/index.html`과 `sqm-inline.js` 기준으로 재검증 |
| `HANDOFF_v864_3_CURRENT.md` | 현재 세션 인계 내용 | v864-4 경로로 변환 후 참고 |
| `TIER2_BRIEF.md` | 85개 기능 매핑과 stage gate | v864-4 검증 체크리스트로 활용 |

## 6. 작업 단계

### Stage 0. 기준선 고정

목표: v864-2 원본과 v864-4 대상의 비교 기준을 고정한다.

작업:
- `v864-2`는 읽기 전용으로 둔다.
- `v864-4`에서만 수정한다.
- v864-4 설정 파일 JSON 문법을 확인한다.
- v864-4 실행 진입점과 API 라우터가 로드되는지 확인한다.

검증:

```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_4
Get-Content .\.claude\settings.local.json -Raw | ConvertFrom-Json | Out-Null
python -m py_compile main_webview.py backend\api\__init__.py
node --check frontend\js\sqm-inline.js
```

현재 상태:
- `.claude/settings.local.json`은 이미 JSON_OK 확인됨.
- `backend`, `frontend`, `scripts` 구조는 이미 존재함.

### Stage 1. v864-2 구조/기능 기준 복구

목표: v864-2의 메뉴, 탭, 툴바, 단축키, 핵심 다이얼로그를 v864-4 기준으로 빠짐없이 매핑한다.

기준 파일:
- `v864-2\gui_app_modular\menu_registry.py`
- `v864-2\gui_app_modular\main_app.py`
- `v864-2\gui_app_modular\tabs\*.py`
- `v864-2\gui_app_modular\dialogs\*.py`
- `v864-4\docs\handoff\v864_2_structure.json`
- `v864-4\docs\handoff\feature_matrix.json`

v864-4 구현 위치:
- `frontend\index.html`
- `frontend\js\sqm-inline.js`
- `frontend\js\handlers\menubar.js`
- `frontend\js\handlers\toolbar.js`
- `backend\api\actions.py`
- `backend\api\queries.py`

체크리스트:
- [ ] v864-2 메뉴 항목이 v864-4 `data-action`에 모두 대응되는지 확인
- [ ] 사이드바 9개 탭이 v864-4에서 모두 이동 가능한지 확인
- [ ] 툴바 7개 버튼이 v864-4에서 모두 연결되는지 확인
- [ ] F5, Ctrl+F, Escape, Tab 이동 등 단축키가 WebView에서 정상인지 확인
- [ ] 미구현 기능은 조용히 실패하지 않고 명확히 NOT_READY 또는 준비 중으로 표시

이미 반영된 것으로 보이는 항목:
- `frontend/index.html`
- `frontend/js/handlers/menubar.js`
- `frontend/js/handlers/toolbar.js`
- `frontend/js/shortcuts.js`
- `frontend/js/router.js`

### Stage 2. 누락 다이얼로그 포팅

목표: v864-2 Tkinter 다이얼로그를 v864-4 JS 모달 또는 FastAPI API로 동등 구현한다.

우선순위 S:

| 기능 | v864-2 기준 | v864-4 구현 위치 | 현재 판단 |
|---|---|---|---|
| LOT 상세 | `dialogs/lot_detail_dialog.py` | `showLotDetail`, `/api/action/lot-detail-v760/{lot_no}` | 구현 흔적 있음, 검증 필요 |
| LOT 상태/정합성 | `dialogs/lot_status_dialog.py`, `integrity_v760_dialog.py` | `showIntegrityV760Modal`, `/api/action/integrity-report` | 구현 흔적 있음, 검증 필요 |
| Column Mapper | `dialogs/column_mapper_dialog.py` | Excel 업로드 모달 내부 | 별도 확인 필요 |
| 제품 마스터 | `product_master_helper.py` | 제품 마스터 모달/API | 구현 여부 확인 필요 |
| 제품별 재고 리포트 | `product_inventory_report.py` | 제품별 재고 모달/API | 구현 여부 확인 필요 |

우선순위 A:

| 기능 | v864-2 기준 | v864-4 구현 위치 | 현재 판단 |
|---|---|---|---|
| Allocation Template | `allocation_template_dialog.py` | Allocation 업로드/템플릿 모달 | 확인 필요 |
| Picking List Preview | `picking_list_preview_dialog.py` | `showPickingList...`, outbound API | 확인 필요 |
| PreParse Select | `preparse_select_dialog.py` | OneStop inbound parse flow | 확인 필요 |
| Help Dialogs | `help_dialogs.py` | info/actions API와 modal | 확인 필요 |
| Review Center | `review_center.py` | 선택 기능, OCR/PDF API 필요 | 후순위 |

검증:

```powershell
rg -n "showLotDetail|showIntegrityV760Modal|showProductMaster|showProductInventory|showPicking|showColumn" frontend\js\sqm-inline.js
rg -n "lot-detail|integrity-report|product|picking" backend\api
```

### Stage 3. Skeleton 모달 보강

목표: v864-4에 이름만 있거나 간단한 toast 수준인 모달을 v864-2 수준으로 보강한다.

대상:

| 기능 | v864-2 기준 | v864-4 함수/API | 필요 작업 |
|---|---|---|---|
| Settings | `settings_dialog.py` | `showSettingsDialog`, `showEmailConfigModal`, settings API | API 키, Gemini, BL 규칙, 저장/로드 확인 |
| Return | `return_dialog.py` | `showReturnDialog`, `/api/action3/return-create` | 톤백 선택, 수량/사유 편집, 합계 footer |
| Email Config | `email_config_dialog.py` | `showEmailConfigModal` | SMTP 테스트 전송 |
| Auto Backup | `auto_backup.py` | `showAutoBackupSettingsModal` | 주기/보존/상태 표시 |
| Tonbag Location Upload | `tonbag_location_upload.py` | `showTonbagLocationUploadModal`, `/api/tonbag/location-upload` | dry_run/preview/save 분리 필요 |
| Approval Queue | `allocation_approval_dialog.py` | `showApprovalQueueModal`, allocation API | 승인/반려/이력 |
| Barcode Scan Upload | outbound handler | `showBarcodeScanUploadModal`, outbound API | CSV 파싱, UID/LOT 매칭 |
| Lot Allocation Audit | `lot_allocation_audit_mixin.py` | `showLotAllocationAuditModal` | LOT별 allocation/tonbag 2단 테이블 |
| Test DB Reset | `keybindings_mixin.py` | `showTestDbResetModal` | 테이블별 건수 표시, 선택 삭제 |
| Inbound Cancel | inbound handler | `showInboundCancelModal` | LOT 선택, 영향 범위 preview, rollback |

현재 v864-4에서 함수명이 확인된 항목:
- `showTonbagLocationUploadModal`
- `showInboundCancelModal`
- `showApprovalQueueModal`
- `showIntegrityV760Modal`
- `showReturnDialog`
- `showLotAllocationAuditModal`
- `showTestDbResetModal`
- `showBarcodeScanUploadModal`
- `showEmailConfigModal`
- `showAutoBackupSettingsModal`

따라서 위 항목은 “새로 생성”이 아니라 “v864-2와 동등성 검증 및 부족분 보강”으로 처리한다.

### Stage 4. 핵심 업무 플로우 이식

목표: v864-2의 실제 업무 흐름을 v864-4 WebView에서 동일하게 수행한다.

#### 4.1 PDF 스캔 입고

v864-2 기준:
- `gui_app_modular/dialogs/onestop_inbound.py`
- BL / Packing List / Invoice / D/O 4개 슬롯
- cross-check, parse error recovery, manual edit, final commit

v864-4 위치:
- `frontend/js/sqm-inline.js`의 `showOneStopInboundModal`
- `backend/api/inbound.py`
- parser 재사용: `features/parsers/*`

검증:
- 4개 파일 슬롯 존재
- dry_run과 save 분리
- parse error recovery 표시
- 저장 전 preview 편집 가능
- 저장 실패 시 DB rollback

#### 4.2 출고

v864-2 기준:
- `gui_app_modular/handlers/outbound_handlers.py`
- OneStop outbound, quick outbound, barcode scan, picking list, proof doc audit

v864-4 위치:
- `showOneStopOutboundModal`
- `showBarcodeScanUploadModal`
- `backend/api/outbound_api.py`
- `data/proof_docs`

검증:
- LOT/톤백 선택
- scan 검증
- proof document 저장
- audit log 조회
- OUTBOUND 확정 전 재고 수량 초과 차단

#### 4.3 Allocation

v864-2 기준:
- `gui_app_modular/dialogs/allocation_dialog.py`
- allocation preview, inline edit, shortage warning, approval, apply

v864-4 위치:
- `backend/api/allocation_api.py`
- `frontend/js/sqm-inline.js`
- `frontend/js/pages/allocation.js`

검증:
- Excel 업로드
- 중복 LOT 검사
- 부족 수량 경고
- 승인 대기
- 승인 반영
- 취소/리셋

#### 4.4 반품/재입고

v864-2 기준:
- `return_dialog.py`
- `return_history`
- cargo overview와 연결

v864-4 위치:
- `showReturnDialog`
- `backend/api/actions3.py`
- `frontend/js/pages/return.js`

검증:
- 반품 등록
- 반품 입고 Excel
- 반품 사유 통계
- return history 표시
- 재입고 시 상태와 수량 rollback

### Stage 5. 페이지 보강

목표: v864-4 페이지가 v864-2 탭 수준의 정보량과 조작성을 갖도록 한다.

대상:

| 페이지 | v864-2 기준 | v864-4 파일 | 보강 포인트 |
|---|---|---|---|
| Inventory | inventory/cargo tabs | `frontend/js/pages/inventory.js`, `sqm-inline.js` | 24컬럼, 필터, 정렬, status tab |
| Allocation | allocation tab | `pages/allocation.js` | LOT summary + detail, 승인/취소 |
| Picked | picked tab | `pages/picked.js` | reserved/picked revert |
| Outbound | outbound tab | `pages/outbound.js` | 출고 취소, 반품 확정 |
| Return | cargo overview | `pages/return.js` | 사유/날짜 필터, 상세 drawer |
| Move | movement tab | `pages/tonbag.js` 또는 move page | 위치 lookup |
| Dashboard | dashboard tab | `pages/dashboard.js` | KPI drill-down, integrity cards |
| Log | log tab | `pages/log.js` | type/date/search/export |
| Scan | scan tab | `pages/scan.js` | 5개 상태 전환, 빠른 스캔, 무음 토글 |

### Stage 6. Backend API 정리

목표: v864-4 FastAPI가 v864-2 엔진을 안전하게 호출하도록 한다.

현재 v864-4 API 구조:
- `backend/api/__init__.py`
- `backend/api/actions.py`
- `backend/api/actions2.py`
- `backend/api/actions3.py`
- `backend/api/inbound.py`
- `backend/api/outbound_api.py`
- `backend/api/allocation_api.py`
- `backend/api/tonbag_api.py`
- `backend/api/queries.py`
- `backend/api/queries2.py`
- `backend/api/queries3.py`
- `backend/api/dashboard.py`
- `backend/api/info.py`
- `backend/api/controls.py`

필수 규칙:
- 모든 write API는 preflight 후 commit한다.
- 실패 시 rollback한다.
- API 응답은 `{ok, data, error, detail, message}` 형태로 통일한다.
- 파일 업로드는 확장자, 크기, 빈 파일을 먼저 검증한다.
- DB 경로는 `D:\program\SQM_inventory\Claude_SQM_v864_4\data\db\sqm_inventory.db` 기준으로 확인한다.

### Stage 7. 검증

최소 검증 명령:

```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_4

python -m py_compile main_webview.py
python -m py_compile backend\api\__init__.py
python -m py_compile backend\api\inbound.py
python -m py_compile backend\api\outbound_api.py
python -m py_compile backend\api\allocation_api.py

node --check frontend\js\sqm-inline.js

python scripts\verify_endpoints.py
python -m pytest tests\test_phase5_regression.py -v --tb=short
python scripts\test_all_menus_playwright.py --headless
```

참고:
- 기존 `REPORTS/PHASE5_COMPLETE.md`에는 `verify_endpoints.py` 53/53 PASS, pytest 65/65 PASS 기록이 있다.
- 하지만 문서 생성 이후 코드가 바뀌었을 수 있으므로 최종 배포 전에는 반드시 재실행한다.

### Stage 8. 빌드/배포

현재 확인:
- `dist\SQM_v864_3.exe` 존재

v864-4 기준 결정 필요:
- 배포 파일명을 계속 `SQM_v864_3.exe`로 유지할지
- 또는 `SQM_v864_4.exe`로 새로 빌드할지 결정해야 한다.

권장:
- 내부 폴더가 `Claude_SQM_v864_4`라면 배포 파일도 `SQM_v864_4.exe`로 맞춘다.
- 단, 기존 실행/문서/스크립트가 `SQM_v864_3.exe`를 참조하면 한 번에 모두 바꾼다.

빌드:

```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_4
python scripts\build_exe.py
```

배포 전:
- v864-2 EXE와 DB 백업
- v864-4 EXE 실행 확인
- 기존 DB 조회 확인
- 입고 1건, 출고 1건, 보고서 1건 smoke test
- 24시간 rollback 가능 상태 유지

## 7. 기능별 완료 판정표

| 구분 | 완료 조건 | 이미 있으면 처리 |
|---|---|---|
| 메뉴 | v864-2 메뉴가 v864-4 data-action에 1:1 대응 | 재구현하지 않고 Playwright로 클릭 검증 |
| 다이얼로그 | v864-2 입력 필드, preview, save 흐름 재현 | 함수 존재 시 동작만 검증 |
| API | 200/400/422/500 응답이 명확하고 rollback 보장 | endpoint 존재 시 실패 케이스 추가 검증 |
| Excel 업로드 | 템플릿, 붙여넣기, 파일 업로드 모두 지원 | 기존 업로드 모달 확장 |
| PDF 입고 | BL/PL/Invoice/D/O 4-slot + cross-check | OneStop inbound 검증 |
| 출고 | preflight, proof docs, audit log | outbound API 검증 |
| 리포트 | v864-2 헤더/하단 문구 규칙 유지 | Excel/PDF 샘플 확인 |
| 설정 | API 키 ENV -> keyring -> INI 순서 | settings modal/API 검증 |
| 빌드 | EXE 생성 및 실행 | 산출물명 v864-4 기준 확인 |

## 8. 남은 리스크

1. `v864-3` 문서 일부가 인코딩 깨짐 상태라 그대로 복사하면 안 된다.
2. `v864-4`의 일부 보고서와 EXE 이름이 아직 v864.3 표기를 사용한다.
3. `docs/FEATURE_PROGRESS.md`는 오래된 상태일 수 있다. 최신 코드는 `rg`, `verify_endpoints.py`, Playwright 결과로 판단한다.
4. `sqm-inline.js`가 매우 커졌기 때문에, 향후에는 기능별 JS 파일로 분리하는 것이 좋다.
5. `__pycache__`, `dist`, `build`, 로그, 임시 파일은 문서 비교 대상에서 제외한다.

## 9. 최종 Definition of Done

- [ ] v864-4 `.claude/settings.local.json` JSON_OK
- [ ] v864-4 안에 v864-3 또는 v864_20260329_FULL 하드코딩 경로 없음
- [ ] `node --check frontend\js\sqm-inline.js` PASS
- [ ] `python scripts\verify_endpoints.py` PASS
- [ ] `python -m pytest tests\test_phase5_regression.py` PASS
- [ ] `python scripts\test_all_menus_playwright.py --headless` PASS
- [ ] 입고 -> Allocation -> 출고 -> 반품 -> 보고서 E2E 수동 또는 자동 검증 PASS
- [ ] EXE 빌드 산출물명 결정 및 실행 확인
- [ ] v864-2 백업 및 rollback 계획 문서화

## 10. 다음 작업자에게 줄 한 줄 지시

`D:\program\SQM_inventory\Claude_SQM_v864_2`는 원본으로 읽기만 하고, `D:\program\SQM_inventory\Claude_SQM_v864_4`에서만 수정한다. 이 문서의 Stage 0부터 검증하고, 이미 구현된 기능은 재구현하지 말고 PASS 처리하며, 남은 차이만 v864-2 동작과 대조해 보강한다.
