# CHANGELOG

## v6.1.9 (2026-02-27)

### 안정화
- 런타임 NameError 핫픽스 반영 (`inventory_tab`, `outbound_scheduled_tab`, `help_dialogs`, `refresh_mixin`, `onestop_inbound`).
- 완전 패치 전 기준선 문서 추가: `docs/PHASE1_BASELINE_20260227.md`.

### 보안/운영
- PC Guard 다중 PC 허용을 기본 동작으로 변경.
  - `python run.py --register-pc`: 기존 허용 목록 유지 + 현재 PC 추가/갱신
  - `python run.py --register-pc --replace-pc-list`: 목록 전체 교체(강제 1대 모드)
- `security/allowed_pcs.json`에 `대흥남기동2025` MAC 4종 추가.

### 릴리즈
- GitHub tag: `v6.1.9`
- GitHub release: `https://github.com/kidongnam1/SQM_inventory/releases/tag/v6.1.9`


## v6.1.8

- Clean Build & Full Feature Integration.
- FastOut(대량출고), Barcode Scan(현장검증), API Server, Integrity Center, Return Mgmt(반품 고도화).


## v6.1.1

- 테마 가시성 개선(ReadableStyle fg/bg 명시, theme_refresh 2차 적용 등).


## v6.1.0

- 출고 로직 개편(피킹리스트 파서, Gate-1 교차검증, 빠른 출고 8톤백 제한).
