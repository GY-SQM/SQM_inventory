# Stage 1: 누락 다이얼로그 12개 구현

> **원본 (참조)**: `D:\program\sqm_2_upload_clean_v864_2` (v864.2)
> **작업 대상**: `D:\program\SQM_inventory\Claude_SQM_v864_3` (v864.3)
> **수정 파일**: `Claude_SQM_v864_3/frontend/js/sqm-inline.js` + 필요 시 backend API
> **목표**: v864.2에 있는데 v864.3에 누락된 다이얼로그 12개를 JS 모달로 구현

---

## 경로 규칙 (혼동 금지)

- **읽기만**: `D:\program\sqm_2_upload_clean_v864_2\gui_app_modular\dialogs\*.py` (v864.2 원본)
- **수정 대상**: `D:\program\SQM_inventory\Claude_SQM_v864_3\frontend\js\sqm-inline.js` (v864.3)
- **engine_modules/ 수정 금지** (양쪽 모두)

---

## 작업 목록 (우선순위순)

### S등급 (매일 쓰는 기능)

#### 1. LOT Detail Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/lot_detail_dialog.py` (359줄)
- **기능**: LOT 더블클릭 → 톤백 목록 + stock_movement 타임라인 + LOT 기본정보 카드
- **구현**: showLotDetailDialog(lotNo) — 기존 showLotDetail 확장
- **API**: GET /api/action/lot-detail/{lot_no} (이미 존재) + GET /api/tonbags?lot_no=
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현
- [ ] Playwright 검증

#### 2. LOT Status Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/lot_status_dialog.py` (408줄)
- **기능**: 전체 LOT 상태 현황 (AVAILABLE=초록, PARTIAL=파랑, FULL_RSV=보라, PICKED=노랑)
- **구현**: showLotStatusDialog()
- **API**: GET /api/inventory (이미 존재) → 클라이언트에서 상태별 집계
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현
- [ ] Playwright 검증

#### 3. Integrity V760 Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/integrity_v760_dialog.py` (387줄)
- **기능**: 정합성 시각화 (ERROR/WARN/OK 요약 카드 + LOT별 검사 결과 표 + 상세 패널)
- **구현**: showIntegrityReportDialog()
- **API**: GET /api/action/integrity-check (이미 존재)
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현
- [ ] Playwright 검증

#### 4. Column Mapper Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/column_mapper_dialog.py` (206줄)
- **기능**: Excel 업로드 시 컬럼 자동매핑 (좌: Excel 컬럼 → 우: SQM 필드, 드래그 or 드롭다운)
- **구현**: showColumnMapperDialog(excelColumns, onConfirm)
- **API**: 없음 (프론트 전용)
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현
- [ ] 기존 Excel 업로드 모달에 연결

### A등급 (주 1~2회 사용)

#### 5. Product Master Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/product_master_helper.py` (234줄)
- **기능**: 제품 마스터 CRUD (코드, 이름, 단위, 포장타입 등)
- **구현**: showProductMasterDialog()
- **API**: GET /api/q/product-inventory (이미 존재) + 신규 POST 필요 시 추가
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현

#### 6. Product Inventory Report
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/product_inventory_report.py` (203줄)
- **기능**: 제품별 재고 상세 리포트 (제품 선택 → LOT/톤백/중량 표 + CSV 내보내기)
- **구현**: showProductInventoryReportDialog()
- **API**: GET /api/q/product-inventory (이미 존재)
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현

#### 7. Allocation Template Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/allocation_template_dialog.py` (640줄)
- **기능**: 배정 템플릿 프리뷰 (Song양식/Woo양식 탭) + 템플릿 다운로드
- **구현**: showAllocationTemplateDialog()
- **API**: 없음 (정적 템플릿 데이터)
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현

#### 8. Picking List Preview Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/picking_list_preview_dialog.py` (221줄)
- **기능**: 피킹 PDF 파싱 결과 프리뷰 (헤더 정보 + 파싱된 아이템 표 + "DB 반영" 버튼)
- **구현**: showPickingListPreviewDialog(parsedData)
- **API**: 없음 (파싱 결과 표시만)
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현

### B등급 (월 1~2회 또는 optional)

#### 9. PreParse Select Dialog
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/preparse_select_dialog.py` (382줄)
- **기능**: PDF 파싱 전 문서종류 선택 (PACKING_LIST/INVOICE/BL/DO) + 템플릿 선택
- **구현**: showPreParseSelectDialog(onSelect)
- **API**: 없음 (프론트 전용)
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현

#### 10. Help Dialogs
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/help_dialogs.py` (729줄)
- **기능**: 단축키 안내 탭 다이얼로그 (Key/Function/Description 표)
- **구현**: showHelpDetailDialog()
- **API**: GET /api/info/shortcuts (이미 존재) — 현재 renderInfoModal로 표시 중, 탭 UI로 확장
- [ ] v864.2 원본 분석
- [ ] JS 모달 구현

#### 11. Review Center
- **v864.2 원본**: `sqm_2_upload_clean_v864_2/gui_app_modular/dialogs/review_center.py` (385줄)
- **기능**: PDF 뷰어 + ROI 드래그 + OCR 텍스트 추출 + 규칙 편집기
- **구현**: showReviewCenterDialog()
- **API**: 신규 필요 (PDF 페이지 이미지 변환 + OCR)
- **의존성**: PyMuPDF (fitz), Gemini API (optional)
- [ ] v864.2 원본 분석
- [ ] 백엔드 API 구현
- [ ] JS 모달 구현

#### 12. (없음 — product_master_helper는 #5에 포함)
- product_inventory_report가 #6으로 분리됨

---

## 검증 방법

각 다이얼로그 구현 후:
1. `node --check frontend/js/sqm-inline.js` (JS 문법)
2. Playwright 테스트에 해당 data-action 추가
3. v864.2 스크린샷과 육안 비교 (가능 시)

## 완료 기준

- [ ] 11개 다이얼로그 전부 JS 모달로 구현
- [ ] WIP / NOT_READY 0개 유지
- [ ] Playwright 전수 테스트 PASS
- [ ] STAGE1_COMPLETE.md 보고서 작성
