# SQM v6.3.3 — RUBI Phase 3 (Barcode Scan = Immediate Confirm)

- 작성일: 2026-03-05 (KST)
- 적용 대상: `SQM_V6.3.3_RUBI_PHASE2_FULL_*` 기반

## 목적
리오님 운영 규칙(랜덤 출고)에 맞춰 **출고 톤백을 사전에 특정하지 않고**,
**현장 바코드 스캔 시점에만** 톤백을 즉시 확정 처리합니다.

## 핵심 규칙
- STEP1~3(Allocation/Approval/Picking List)에서는 `inventory_tonbag.status`를 변경하지 않음 (Phase2 유지)
- STEP4(Scan)에서만 확정:
  - 바코드 스캔된 UID → **즉시 SOLD(=OUT 확정)**
- 출고 목표(Target)는 **allocation_plan.qty_mt(중량)** 합계 기준으로 검증
- **All-or-Nothing**:
  - UID 미존재/중복확정/Target 초과 등이 1건이라도 있으면 전체 롤백(확정 0건)

## 변경 파일
1) `core/barcode_scan_engine.py`
- `outbound_scan_log`(best-effort) 테이블 자동 생성
- `process_barcode_scan_confirm_out()` 추가: 스캔 파일/리스트 → 즉시 확정
- `undo_last_scan_confirm()` 추가: 최근 확정 1건 Undo(관리자용)

2) `gui_app_modular/handlers/outbound_handlers.py`
- 환경변수 `SQM_OUTBOUND_MODE`가 `random_scan_confirm`(기본)일 때:
  - "바코드 스캔 업로드" 동작이 **UID 대조(PASS/FAIL)** 방식이 아니라
  - **스캔 즉시 확정(OUT=SOLD)** 으로 동작

## 운영 방법
- 기본(권장):
  - `SQM_OUTBOUND_MODE` 미설정 → 기본값 `random_scan_confirm` 적용
- 강제 설정(선택):
  - Windows CMD:
    - `set SQM_OUTBOUND_MODE=random_scan_confirm`
  - PowerShell:
    - `$env:SQM_OUTBOUND_MODE='random_scan_confirm'`

## 주의
- Target(중량)이 `allocation_plan`에 없으면 확정이 차단됩니다.
- Target 초과는 0.1% 또는 최소 1kg 허용 오차를 둡니다.

