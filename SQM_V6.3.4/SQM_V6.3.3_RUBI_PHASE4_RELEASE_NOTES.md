# SQM v6.3.3 — RUBI Phase 4 Release Notes (UTF-8)

작성일: 2026-03-05 (KST)

## 목표
- Phase3(스캔 즉시 확정) 기반을 유지하면서, **현장(USB 바코드 스캐너)** 운영에 필요한 UX/리포트 기능을 추가.
- 원칙: STEP1~3에서는 TONBAG 상태 변경 금지, STEP4(스캔)에서만 SOLD(=OUT) 확정.

## 변경사항 요약
### 1) 실시간 바코드 스캔(Enter) 메뉴 추가
- 메뉴: **📟 실시간 바코드 스캔 (Enter)**
- 동작:
  - 입력창 자동 포커스
  - 스캔(입력+Enter) 즉시 1건 확정(SOLD)
  - 성공/실패 로그 리스트 표시
  - Undo(최근 1건) 지원
  - 스캔 리포트(CSV) 저장 버튼 제공

### 2) 스캔 확정 리포트 자동 저장(CSV)
- 기존: 스캔 파일 업로드 후 메시지 표시만
- Phase4:
  - 스캔 확정 성공 시, `output/` 폴더에 자동으로 CSV 저장
  - 파일명 예시: `OUTBOUND_SCAN_{SALE_REF}_YYYYMMDD_HHMMSS.csv`

### 3) 엔진 확장(BarcodeScanEngine)
- `confirm_one_uid_live()` : 실시간 스캔 1건 확정 API
- `export_scan_confirm_report_csv()` : 스캔 확정 결과 CSV 저장 API

## 수정 파일
- `core/barcode_scan_engine.py`
- `gui_app_modular/handlers/outbound_handlers.py`
- `gui_app_modular/menu_registry.py`

## 운영 체크
1) Phase2/3 원칙 유지 확인
- Allocation/Approval/PickingList 단계에서 `inventory_tonbag.status` 변경 없음
2) Phase4 실시간 스캔
- Enter 입력 시 SOLD 전환 + outbound_scan_log 기록
3) Undo
- 최근 1건만 복구(AVAILABLE)

