# Stage 3: 페이지 보강 + 핸들러 로직 이식

> **원본 (참조)**: `D:\program\sqm_2_upload_clean_v864_2` (v864.2)
> **작업 대상**: `D:\program\SQM_inventory\Claude_SQM_v864_3` (v864.3)
> **목표**: Skeleton 페이지 2개 보강 + v864.2 핸들러 핵심 비즈니스 로직 이식

---

## 경로 규칙 (혼동 금지)

- **읽기만**: `D:\program\sqm_2_upload_clean_v864_2\gui_app_modular\` (v864.2 원본)
- **수정 대상**: `D:\program\SQM_inventory\Claude_SQM_v864_3\frontend\js\sqm-inline.js` + `backend/api/` (v864.3)
- **engine_modules/ 수정 금지** (양쪽 모두)

---

## Part A: Skeleton 페이지 보강

### 1. Return 페이지 (현재 5열 Skeleton → Full)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/tabs/cargo_overview_tab.py` (약 800줄)
- **현재 v864.3**: LOT/Product/Qty/Date/Reason 5열 기본 표
- **보강 항목**:
  - 반품 사유별 필터 버튼 (품질불량/수량초과/오배송/고객변심)
  - 날짜 범위 필터
  - 재입고 처리 버튼 (선택 행 → 재입고 실행)
  - 반품 통계 요약 카드 (총 건수, 사유별 비율)
  - 상세 펼침 (톤백 목록)
- [ ] 구현
- [ ] 테스트

### 2. Log 페이지 (현재 4열 Skeleton → Full)
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/tabs/log_tab.py` (약 400줄)
- **현재 v864.3**: Time/Type/LOT/Detail 4열 + limit 선택
- **보강 항목**:
  - 이벤트 유형 필터 (INBOUND/OUTBOUND/MOVE/RETURN/SYSTEM)
  - 날짜 범위 필터 (오늘/이번주/이번달/전체)
  - 검색 (LOT 번호 또는 상세 텍스트)
  - 상세 펼침 (event_data JSON 보기)
  - CSV 내보내기 버튼
- [ ] 구현
- [ ] 테스트

---

## Part B: 핸들러 비즈니스 로직 이식

### 3. 출고 핸들러 — Proof Document 감사 추적
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/handlers/outbound_handlers.py` (2,868줄)
- **핵심 로직** (이식 대상):
  - `_s1_get_proof_base_dir()` — 증빙 폴더 경로
  - `_s1_write_audit()` — 출고 시 감사 기록 자동 생성
  - `_s1_open_audit_viewer()` — 감사 이력 뷰어
  - `_sob_parse_csv_scan_file()` — 바코드 스캔 CSV 파싱
  - `_sob_prefetch_lot_data()` — LOT 데이터 사전 조회
- **구현 위치**: `backend/api/outbound_api.py` 에 POST 엔드포인트 추가
- [ ] v864.2 원본 핵심 로직 분석
- [ ] FastAPI 엔드포인트 구현
- [ ] JS에서 호출 연결

### 4. 입고 핸들러 — Multi-Format 감지
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/handlers/inbound_handlers.py` (1,105줄)
- **핵심 로직** (이식 대상):
  - `_detect_excel_type()` — "manual"/"auto"/"return"/"outbound" 자동 감지
  - `_import_inbound_excel_auto()` — Packing/Invoice/BL 형식별 파싱
  - `_import_inbound_manual_template()` — Song 양식 수동 입고
  - `_show_inbound_spreadsheet_dialog()` — 입고 데이터 프리뷰+편집
  - `_archive_processed_file()` — 처리 완료 파일 아카이브
- **구현 위치**: `backend/api/inbound.py` 보강
- [ ] v864.2 원본 핵심 로직 분석
- [ ] FastAPI 엔드포인트 보강
- [ ] JS에서 호출 연결

### 5. Allocation Dialog 심화
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/allocation_dialog.py` (1,616줄, 42개 메서드)
- **현재 v864.3**: showAllocationUploadModal (82줄 — 파일 업로드만)
- **빠진 핵심 기능**:
  - 인라인 셀 편집 (더블클릭 → 편집 → Enter)
  - Ctrl+C/V/X 클립보드 지원
  - 중복 LOT 체크 (`_check_duplicate_allocation_file`)
  - Shortage 경고 (`_build_reserve_shortage_warnings`)
  - 단계별 상태 관리 (RESERVE → EXECUTE → CONFIRM)
  - 예약 취소/리셋
- **구현**: showAllocationUploadModal 확장 (편집 모드 + 검증 + 단계 진행)
- [ ] v864.2 원본 핵심 42메서드 분류
- [ ] 핵심 20개 메서드 JS 이식
- [ ] 테스트

---

## 완료 기준

- [ ] Return 페이지 Full 수준
- [ ] Log 페이지 Full 수준
- [ ] 출고 proof-doc 감사 추적 동작
- [ ] 입고 multi-format 감지 동작
- [ ] Allocation 인라인 편집 + 검증 동작
- [ ] Playwright 전수 테스트 PASS
- [ ] STAGE3_COMPLETE.md 보고서 작성

---

## Stage 1~3 완료 후 = v864.2와 100% 동등

| Stage | 완성도 변화 | 핵심 |
|-------|------------|------|
| 현재 | 65% | |
| Stage 1 완료 | → 80% | 누락 다이얼로그 12개 |
| Stage 2 완료 | → 90% | Skeleton→Full 10개 |
| Stage 3 완료 | → 100% | 페이지 + 핸들러 심화 |
