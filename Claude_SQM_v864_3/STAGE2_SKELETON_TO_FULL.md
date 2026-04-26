# Stage 2: Skeleton 모달 10개 → Full 보강

> **원본 (참조)**: `D:\program\sqm_2_upload_clean_v864_2` (v864.2)
> **작업 대상**: `D:\program\SQM_inventory\Claude_SQM_v864_3` (v864.3)
> **목표**: 현재 10~30줄짜리 Skeleton 모달을 v864.2 수준(200~800줄)으로 보강

---

## 경로 규칙 (혼동 금지)

- **읽기만**: `D:\program\sqm_2_upload_clean_v864_2\gui_app_modular\dialogs\*.py` (v864.2 원본)
- **수정 대상**: `D:\program\SQM_inventory\Claude_SQM_v864_3\frontend\js\sqm-inline.js` (v864.3)
- **engine_modules/ 수정 금지** (양쪽 모두)

---

## 작업 목록

### 1. showSettingsDialog (22줄 → 목표 300줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/settings_dialog.py` (869줄)
- **빠진 것**: API 키 저장/로딩, Gemini 모델 선택, API 테스트, 컨테이너 접미사 토글, BL 선사 등록
- **구현 범위**: 탭 UI (일반/AI/고급), 각 설정 실제 localStorage 저장, Gemini API 테스트 버튼
- [ ] v864.2 원본 분석 (9개 설정 메서드)
- [ ] 탭 UI + 저장 로직 구현
- [ ] 테스트

### 2. showReturnDialog (93줄 → 목표 300줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/return_dialog.py` (401줄)
- **빠진 것**: 톤백 선택기 (Treeview), 인라인 셀 편집, 합계 footer (weight_mt, tonbag_count)
- **구현 범위**: 톤백 체크박스 목록, 수량/사유 인라인 편집, 하단 합계
- [ ] v864.2 원본 분석
- [ ] 톤백 선택기 + 인라인 편집 구현
- [ ] 테스트

### 3. showEmailConfigModal (11줄 → 목표 150줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/email_config_dialog.py` (157줄)
- **빠진 것**: SMTP 테스트 전송, 연결 검증, 설정 파일 저장/로딩
- **구현 범위**: SMTP 폼 + "테스트 전송" 버튼 + 결과 표시
- [ ] 구현

### 4. showAutoBackupSettingsModal (10줄 → 목표 120줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/auto_backup.py` (445줄)
- **빠진 것**: 스케줄 주기 설정, 보존 개수, 활성/비활성 토글, 마지막 백업 시간 표시
- **구현 범위**: 스케줄 폼 + 상태 표시 + localStorage 저장
- [ ] 구현

### 5. showTonbagLocationUploadModal (22줄 → 목표 200줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/tonbag_location_upload.py` (324줄 — location_upload_preview.py 422줄)
- **빠진 것**: 프리뷰 테이블 (변경 전/후 위치), 매핑 확인, 충돌 감지
- **구현 범위**: Excel 업로드 → 프리뷰 표 → 확인 → 실행
- [ ] 구현

### 6. showApprovalQueueModal (27줄 → 목표 200줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/allocation_approval_dialog.py` (471줄)
- **빠진 것**: 승인/반려 버튼, 개별 행 체크박스, 상태 변경 실행, 이력 표시
- **구현 범위**: 체크박스 테이블 + 승인/반려 버튼 + API 호출
- [ ] 구현

### 7. showBarcodeScanUploadModal (15줄 → 목표 150줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/handlers/outbound_handlers.py` 내 _on_barcode_scan_upload (약 200줄)
- **빠진 것**: 파싱 결과 표 (UID/LOT 매칭), 매칭 성공/실패 색상, "출고 실행" 버튼
- **구현 범위**: 파일 업로드 → 파싱 결과 표 → 매칭 확인 → 실행
- [ ] 구현

### 8. showLotAllocationAuditModal (40줄 → 목표 200줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/lot_allocation_audit_mixin.py` (312줄)
- **빠진 것**: LOT 드롭다운 선택, allocation_plan 표 + tonbag_summary 표 (2단)
- **구현 범위**: LOT 선택 → allocation + tonbag 2단 표
- [ ] 구현

### 9. showTestDbResetModal (50줄 → 목표 100줄)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/mixins/keybindings_mixin.py` 내 (약 100줄)
- **빠진 것**: 테이블별 행 수 표시, 선택적 테이블 삭제
- **구현 범위**: 테이블 목록 + 행 수 표시 + 전체/선택 삭제
- [ ] 구현

### 10. showInboundCancelModal (54줄 → 목표 150줄)
- **v864.2 원본**: inbound_handlers.py 내 관련 로직
- **빠진 것**: LOT 목록 드롭다운 (최근 입고 조회), 영향 범위 프리뷰 (톤백 수/연관 문서)
- **구현 범위**: LOT 선택 드롭다운 + 영향 프리뷰 + 확인 → 실행
- [ ] 구현

---

## 완료 기준

- [ ] 10개 모달 모두 v864.2 수준으로 보강
- [ ] Playwright 전수 테스트 PASS
- [ ] STAGE2_COMPLETE.md 보고서 작성
