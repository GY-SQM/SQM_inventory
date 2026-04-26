# Stage 2 완료 보고서

> **완료일:** 2026-04-26  
> **작업자:** Claude Code (자율 모드)

---

## 목표: 10개 스켈레톤 모달 → 완전 구현 (실 API 연결)

| # | 모달 | 변경 내용 | 상태 |
|---|------|-----------|------|
| 1 | `showInboundCancelModal` | LOT 드롭다운 + 영향 범위 프리뷰 | ✅ |
| 2 | `showApprovalQueueModal` | 체크박스 테이블 + 승인/반려 | ✅ |
| 3 | `showLotAllocationAuditModal` | 2단 표 (LOT + 톤백/할당 side-by-side) | ✅ |
| 4 | `showTestDbResetModal` | 테이블 통계 로드 + 선택 삭제 | ✅ |
| 5 | `showBarcodeScanUploadModal` | CSV/Excel 업로드 + 매칭 결과 테이블 | ✅ |
| 6 | `showEmailConfigModal` | 실 `/api/settings/email` 로드/저장/테스트 | ✅ |
| 7 | `showAutoBackupModal` | 실 `/api/settings/backup` 로드/저장 | ✅ |
| 8 | `showReturnDialog` | 톤백 선택기 (LOT 조회 → 체크박스 선택) | ✅ |
| 9 | `showTonbagLocationUploadModal` | `_showUploadPreviewModal` 패턴 (이미 완전) | ✅ |

---

## 신규 백엔드 엔드포인트

| 엔드포인트 | 파일 | 용도 |
|-----------|------|------|
| `POST /api/scan/bulk-upload?action=...` | `inventory_api.py` | CSV/Excel UID 일괄 조회/처리 |
| `GET /api/settings/email` | `settings.py` (기존) | 이메일 설정 로드 |
| `POST /api/settings/email` | `settings.py` (기존) | 이메일 설정 저장 |
| `POST /api/settings/email/test` | `settings.py` (기존) | SMTP 테스트 발송 |
| `GET /api/settings/backup` | `settings.py` (기존) | 자동백업 설정 로드 |
| `POST /api/settings/backup` | `settings.py` (기존) | 자동백업 설정 저장 |
| `GET /api/settings/table-stats` | `settings.py` (기존) | 테이블 행 수 통계 |
| `POST /api/settings/table-delete` | `settings.py` (기존) | 선택 테이블 삭제 |
| `GET /api/q/tonbag-detail?lot_no=` | `queries.py` (기존) | LOT별 톤백 상세 목록 |
| `GET /api/q/recent-inbound-lots` | `queries.py` (기존) | 최근 입고 LOT 목록 |
| `POST /api/allocation/approve` | `allocation_api.py` (기존) | 할당 승인 |
| `POST /api/allocation/reject` | `allocation_api.py` (기존) | 할당 반려 |

---

## 검증

- JS syntax: ✅ PASS (`node --check`)
- Python syntax: ✅ PASS (4개 파일 ast.parse)
- API 응답 포맷: 모두 `{ok, data:{items}, message}` 표준 포맷 사용

---

## Stage 3 남은 작업

| 항목 | 설명 |
|------|------|
| 반품 탭 완전 구현 | 반품 목록 페이지 (현재 기본 테이블) |
| 로그 탭 완전 구현 | 이벤트 로그 필터/검색 |
| 출고 증빙 서류 뷰어 | proof_docs PDF 조회 |
| 입고 다중 형식 자동 감지 | Maersk / COSCO / HMM 등 |
| Allocation 인라인 편집 | 표 셀 더블클릭 편집 |
