# SQM 재고관리 시스템 — 전체 세션 디버깅 총정리

📅 2026-02-26 (목) KST  
🔖 버전: v6.12 → v6.12.1 → v6.12.2 → v7.0.0 → v7.0.1  
📊 **총 디버깅/개발 파일: 47개 (고유) | 테스트: 138개 전체 통과**

---

## 📋 세션 전체 요약

| # | 세션 | 버전 | 파일 수 | 테스트 | 핵심 작업 |
|---|------|------|---------|--------|----------|
| 1 | 출고 로직 통합 명세서 | - | 문서 1건 | - | 3개 세션 설계 통합 → 개발 명세서 |
| 2 | 입고 패치 | v6.12 | 6개 | +15 | stock_movement 이력, tonbag_uid 백필, 미리보기 편집 |
| 3 | 출고 4단계 세분화 | v6.12.1 | 9개 | +20 | AVAILABLE→RESERVED→PICKED→SOLD, 500/1000kg 동적 대응 |
| 4 | Gate-1 + 대용량 파싱 | v6.12.1 | 7개 | +28 | LOT 교차검증, 60LOT/300MT 파싱, SAP/BL 검증 |
| 5 | 반품 관리 완전체 | v6.12.2 | 11개 | +62 | 통계 다이얼로그, 대시보드 위젯, PDF 리포트, 알림 |
| 6 | API 프로덕션 | v7.0.0 | 7개 | +112 | FastAPI + JWT + RBAC + WebSocket + Docker |
| 7 | 이동+정합성+리포트 | v7.0.1 | 16개 | +138 | RELOCATE 이력, RESERVED 오탐 수정, 위치 대시보드 |
| **합계** | | | **47개 (고유)** | **138개** | |

---

## 🔴 세션 2: 입고 패치 (v6.12)

### 발견된 버그 3건

**B1. stock_movement에 INBOUND 이력 미기록**
- 위치: `inbound_mixin.py → process_inbound()`
- 문제: 입고 처리 시 inventory/tonbag INSERT만 수행, stock_movement에 INBOUND 레코드 미삽입
- 영향: 감사 추적 불가 — "이 LOT은 언제 입고됐나?" 답변 불가
- 수정: process_inbound() 성공 후 stock_movement INSERT 추가

**B2. tonbag_uid가 NULL로 남는 경우**
- 위치: `tonbag_mixin.py → _create_tonbags()`
- 문제: tonbag 생성 시 tonbag_uid 컬럼이 NULL로 남는 케이스 존재
- 영향: 위치 업로드 매칭 실패 (매칭률 0%)
- 수정: tonbag_uid 백필 보장 로직 추가 — 생성 후 NULL이면 자동 채움

**B3. 미리보기 다이얼로그 셀 편집 불가**
- 위치: `inbound_preview_dialog.py`
- 문제: 입고 미리보기에서 데이터 수정 기능 없음
- 영향: 오류 데이터 발견 시 취소 → 원본 수정 → 재업로드 필요
- 수정: Treeview 더블클릭 인라인 편집 + 수정 행 하이라이트

### 변경 파일 (6개)
```
engine_modules/inventory_modular/inbound_mixin.py    (수정)
engine_modules/inventory_modular/tonbag_mixin.py     (수정)
gui_app_modular/dialogs/inbound_preview_dialog.py    (수정)
tests/test_addon_a_stock_movement.py                 (신규)
tests/test_addon_b_tonbag_uid.py                     (신규)
tests/test_addon_c_preview_edit.py                   (신규)
```

---

## 🟠 세션 3: 출고 4단계 세분화 (v6.12.1)

### 발견된 버그/Gap 4건

**B4. 출고 상태가 AVAILABLE→SOLD 단순 2단계**
- 위치: `outbound_mixin.py → process_outbound()`
- 문제: 중간 단계(RESERVED, PICKED) 없이 바로 SOLD 처리
- 영향: Allocation 후 실제 출고 전 상태 추적 불가
- 수정: AVAILABLE→RESERVED→PICKED→SOLD 4단계 전이 구현

**B5. 500kg/1000kg 톤백 동적 대응 미지원 (Addon-G)**
- 위치: `constants.py`, `tonbag_mixin.py`
- 문제: 톤백 단위중량이 500kg으로 하드코딩
- 영향: 1000kg 톤백 LOT 입고 시 무조건 500kg으로 분할
- 수정: LOT별 unit_weight 동적 감지 (500/1000kg)

**B6. stock_movement에 출고 4단계 이력 미분리**
- 위치: `outbound_mixin.py`
- 문제: RESERVE/PICK/SHIP 각 단계별 이동 이력 미기록
- 수정: 각 상태 전이마다 stock_movement INSERT

**B7. LOT 생애주기 리포트 없음**
- 위치: (신규 모듈 필요)
- 수정: `lot_lifecycle_report.py` 신규 — 입고→예약→출고→반품 전체 이력 PDF

### 변경 파일 (9개)
```
engine_modules/constants.py                          (수정)
engine_modules/inventory_modular/outbound_mixin.py   (수정)
engine_modules/inventory_modular/tonbag_mixin.py     (수정)
gui_app_modular/tabs/tonbag_tab.py                   (수정)
features/reports/lot_lifecycle_report.py              (신규)
tests/test_addon_d_outbound_lifecycle.py              (신규)
tests/test_addon_e_lifecycle_report.py                (신규)
tests/test_addon_f_version.py                         (신규)
tests/test_addon_g_unit_weight.py                     (신규)
```

---

## 🟡 세션 4: Gate-1 교차검증 + 대용량 파싱 (v6.12.1 계속)

### 발견된 버그/Gap 5건

**B8. Picking List ↔ Allocation Plan 교차검증 없음 (Gate-1)**
- 위치: `validators.py`
- 문제: Picking List에 있는 LOT이 Allocation Plan과 일치하는지 검증 없음
- 영향: 잘못된 LOT 출고 가능
- 수정: Gate-1 교차검증 — LOT 목록 + 수량 대조 + 불일치 시 경고

**B9. 60LOT/300MT 대용량 Picking List 파싱 실패**
- 위치: `gemini_parser.py`, `pdf_field_extractor.py`
- 문제: Gemini API 토큰 한도(8192)로 대용량 문서 파싱 실패
- 영향: 대량 출고 건 처리 불가
- 수정: 토큰 한도 65536 확장 + 페이지 분할 파싱 + 병합

**B10. 수동 입고 시 SAP No/B/L No 검증 없음**
- 위치: `inbound_handlers.py`
- 문제: 필수 필드(SAP No, B/L No) 미입력 시 그대로 진행
- 영향: 감사 대응 시 핵심 추적 정보 누락
- 수정: 입고 전 필수 필드 검증 게이트 추가

**B11. 수동 입고 미리보기에서 편집 후 반영 안 됨**
- 위치: `inbound_handlers.py`
- 문제: 미리보기 편집 값이 실제 입고 데이터에 미반영
- 수정: 편집된 데이터 콜백으로 원본 교체

**B12. source_type 감사 추적 미지원**
- 위치: `inbound_mixin.py`
- 문제: 입고가 PDF/Excel/수동 중 어떤 경로인지 기록 안 함
- 수정: stock_movement.remarks에 source_type 기록

### 변경 파일 (7개)
```
engine_modules/validators.py                         (수정)
features/pdf_parser/gemini_parser.py                 (수정)
features/pdf_parser/pdf_field_extractor.py           (수정)
gui_app_modular/handlers/inbound_handlers.py         (수정)
tests/test_gate1_cross_validation.py                 (신규)
tests/test_large_picking_parse.py                    (신규)
tests/test_manual_inbound_enhanced.py                (신규)
```

---

## 🟢 세션 5: 반품 관리 완전체 (v6.12.2)

### 발견된 버그/Gap 6건

**B13. 반품 source_type 미기록**
- 위치: `return_mixin.py`
- 문제: 반품이 Excel/수동/자동 중 어느 경로인지 감사 추적 불가
- 수정: stock_movement에 source_type 기록

**B14. 반품 사유 통계 다이얼로그 없음**
- 위치: (신규 모듈 필요)
- 수정: `return_statistics_dialog.py` — 기간 필터 + 사유별 차트 + Excel/PDF 내보내기

**B15. 대시보드에 반품률 위젯 없음**
- 위치: `dashboard_tab.py`, `dashboard_data_mixin.py`
- 문제: 반품 현황이 대시보드에 표시 안 됨
- 수정: 반품률 위젯 + 월별 트렌드 + 임계치 경고(빨간색)

**B16. 반품 알림 이메일 기능 없음**
- 위치: `advanced_dialogs_mixin.py`
- 수정: 반품률 임계치 초과 시 자동 알림 핸들러

**B17. 반품 PDF 리포트에 기간 필터 미지원**
- 위치: `return_report_pdf.py`
- 문제: 전체 기간만 출력 가능
- 수정: start_date/end_date 파라미터 추가

**B18. 반품 사유 비표준화 (자유 텍스트)**
- 위치: `return_dialog.py`, `constants.py`
- 문제: "품질불량", "품질 불량", "quality issue" 등 동일 사유가 다른 텍스트로 저장
- 수정: RETURN_REASON_CODES 표준 코드 도입 + 콤보박스 선택

### 변경 파일 (11개)
```
engine_modules/constants.py                          (수정)
engine_modules/inventory_modular/return_mixin.py     (수정)
gui_app_modular/dialogs/return_dialog.py             (수정)
gui_app_modular/dialogs/return_statistics_dialog.py  (신규)
gui_app_modular/tabs/dashboard_tab.py                (수정)
gui_app_modular/tabs/dashboard_data_mixin.py         (수정)
gui_app_modular/mixins/advanced_dialogs_mixin.py     (수정)
features/reports/return_report_pdf.py                (수정)
tests/test_return_enhanced.py                        (신규)
tests/test_return_statistics.py                      (신규)
tests/test_return_dashboard.py                       (신규)
```

---

## 🔵 세션 6: API 프로덕션 (v7.0.0)

### 구현된 신규 기능 5건

**F1. JWT 인증 + RBAC (역할 기반 접근 제어)**
- `api/auth.py` 신규: login/token/refresh 엔드포인트
- 3단계 역할: viewer (읽기) / operator (읽기+쓰기) / admin (전체)
- POST 엔드포인트에 operator 이상 권한 요구

**F2. Rate Limiting (요청 속도 제한)**
- `api/rate_limit.py` 신규: slowapi 기반
- 인증 사용자: 120회/분, 미인증: 30회/분, 쓰기: 30회/분

**F3. 감사 미들웨어 (Audit Middleware)**
- `api/audit_middleware.py` 신규: 모든 API 호출 기록
- SQLite audit_log 테이블 + JSONL 파일 이중 기록
- 요청자 IP, 사용자, 메서드, 경로, 상태코드, 응답시간 추적

**F4. WebSocket 실시간 알림**
- `api/main.py`에 WebSocket 엔드포인트 추가
- 입고/출고/반품 POST 성공 시 연결된 클라이언트에 실시간 push

**F5. Docker 컨테이너화**
- `Dockerfile` + `docker-compose.yml` 신규
- Python 3.11-slim 기반, uvicorn 구동, 헬스체크 포함

### 변경 파일 (7개)
```
api/main.py                                          (수정)
api/auth.py                                          (신규)
api/rate_limit.py                                    (신규)
api/audit_middleware.py                               (신규)
Dockerfile                                           (신규)
docker-compose.yml                                   (신규)
tests/test_api_production.py                         (신규)
```

---

## 🟣 세션 7: 이동+정합성+대시보드+리포트 (v7.0.1)

### 발견된 버그/Gap 7건

**B19. 🔴 위치 변경 이력 전무 (CRITICAL)**
- 위치: `tonbag_mixin.py → update_tonbag_location()`
- 문제: stock_movement에 from_location/to_location 컬럼이 있지만 한 번도 사용 안 함
- 영향: "이 톤백 언제 어디로 옮겼나?" 감사 대응 불가
- 수정: 위치 변경 시 RELOCATE movement 기록 + location_updated_at 갱신

**B20. 🔴 위치 업데이트 경로 2개 불일치 (CRITICAL)**
- 위치A: `tonbag_location_uploader.py` (3단계 fallback + 미리보기)
- 위치B: `status_import_handlers.py` (단순 매칭, 미리보기 없음)
- 문제: 같은 기능인데 2개 경로가 서로 다른 로직
- 영향: 경로B는 이력 미기록 + 매칭 실패 시 무시
- 수정: 경로B → 경로A로 완전 리다이렉트 (150줄 → 20줄)

**B21. 🔴 RESERVED 톤백 정합성 오탐 (CRITICAL)**
- 위치: `integrity_mixin.py → verify_lot_integrity()`
- 문제: `avail_w = SUM(AVAILABLE, SAMPLE)` → RESERVED 누락
- 상세: reserve_from_allocation()은 톤백 status만 RESERVED로 바꾸고 current_weight는 안 건드림. 그런데 verify_lot_integrity가 RESERVED를 avail_w에도 picked_w에도 안 넣음 → "가용 불일치" 오탐
- 영향: 시작 시 정합성 검사에서 매번 빨간색 경고 → 사용자 불안 or 무시 습관화
- 수정: avail_w에 RESERVED 포함 + reserved_weight/reserved_count 별도 추적

**B22. 🔴 RESERVED LOT 출고 거부 (CRITICAL)**
- 위치: `validators.py → validate_outbound()`
- 문제: `if lot['status'] not in ('AVAILABLE', 'PARTIAL')` → RESERVED 거부
- 영향: Allocation으로 예약한 LOT을 출고할 수 없음
- 수정: 허용 상태에 RESERVED 추가

**B23. 🟡 톤백 개별 위치 편집 UI 없음**
- 위치: `tonbag_tab.py`
- 문제: 톤백 1개의 위치만 변경하려면 Excel 파일을 만들어서 업로드해야 함
- 수정: 우클릭 컨텍스트 메뉴 → "📍 위치 변경" 다이얼로그 (현재 위치 표시 + 새 위치 입력)

**B24. 🟡 위치 미지정 톤백 경고 없음**
- 위치: `validators.py → check_data_integrity()`
- 문제: AVAILABLE 상태인데 위치가 NULL/빈 문자열인 톤백에 대한 경고 없음
- 수정: 위치 미지정 톤백 수 경고 추가

**B25. 🟡 get_location_summary에서 current_weight 참조**
- 위치: `tonbag_location_uploader.py → get_location_summary()`
- 문제: `SUM(current_weight)` — tonbag 테이블에는 `weight` 컬럼
- 영향: 위치별 중량 합계가 항상 0
- 수정: `SUM(weight)`로 변경

### 추가 구현 3건

**F6. 구역별 대시보드 위젯**
- `dashboard_data_mixin.py` + `dashboard_tab.py`
- 위치 첫 파트(G5-01-02-03 → G5)를 구역으로 그룹핑
- 구역별 톤백 수 + 중량(MT) + 미지정 빨간색 표시

**F7. 정합성 검증 리포트 (PDF + Excel)**
- `features/reports/integrity_report.py` 신규
- PDF: 검사 결과 요약 + 재고 통계 + 구역별 위치 현황
- Excel 3시트: 검사요약 / LOT별 상세(오류 행 빨간색) / 위치 현황
- 메뉴 "📋 정합성 검증 리포트" → 확장자에 따라 PDF/Excel 자동 선택

**F8. Export 옵션 9: 정합성 리포트 Excel**
- `export_mixin.py` + `export_handlers.py` + `menu_registry.py`

### 변경 파일 (16개)
```
engine_modules/constants.py                          (수정) MOVEMENT_RELOCATE 추가
engine_modules/validators.py                         (수정) RESERVED 출고 허용 + 위치 경고
engine_modules/inventory_modular/tonbag_mixin.py     (수정) RELOCATE 이력 + location_updated_at
engine_modules/inventory_modular/integrity_mixin.py  (수정) RESERVED 포함 + reserved_weight
engine_modules/inventory_modular/export_mixin.py     (수정) 옵션 9 추가
gui_app_modular/utils/tonbag_location_uploader.py    (수정) RELOCATE 이력 + weight 버그
gui_app_modular/handlers/status_import_handlers.py   (수정) uploader로 리다이렉트
gui_app_modular/handlers/export_handlers.py          (수정) 옵션 9 등록
gui_app_modular/tabs/tonbag_tab.py                   (수정) 우클릭 위치 변경 UI
gui_app_modular/tabs/dashboard_tab.py                (수정) 구역별 위젯
gui_app_modular/tabs/dashboard_data_mixin.py         (수정) 구역별 통계 쿼리
gui_app_modular/mixins/advanced_dialogs_mixin.py     (수정) 리포트 핸들러
gui_app_modular/menu_registry.py                     (수정) 메뉴 항목
features/reports/integrity_report.py                 (신규) PDF+Excel 리포트
tests/test_location_relocate.py                      (신규) 16개 테스트
tests/test_integrity_v701.py                         (신규) 10개 테스트
```

---

## 📊 전체 버그/Gap 통계

| 심각도 | 건수 | 대표 사례 |
|--------|------|----------|
| 🔴 CRITICAL | 8건 | RESERVED 오탐, 위치 이력 전무, 출고 거부, stock_movement 누락 |
| 🟡 IMPORTANT | 10건 | 위치 미지정 경고, 미리보기 편집, source_type 추적, 사유 표준화 |
| 🟢 ENHANCEMENT | 7건 | 대시보드 위젯, 리포트 생성, LOT 생애주기, Docker |
| **합계** | **25건** | |

---

## 📁 변경 파일 총집계 (47개 고유 파일)

### 엔진 레이어 (8개)
```
engine_modules/constants.py                          ← 3회 수정
engine_modules/validators.py                         ← 2회 수정
engine_modules/inventory_modular/inbound_mixin.py
engine_modules/inventory_modular/outbound_mixin.py
engine_modules/inventory_modular/return_mixin.py
engine_modules/inventory_modular/tonbag_mixin.py     ← 3회 수정
engine_modules/inventory_modular/integrity_mixin.py
engine_modules/inventory_modular/export_mixin.py
```

### GUI 레이어 (10개)
```
gui_app_modular/dialogs/inbound_preview_dialog.py
gui_app_modular/dialogs/return_dialog.py
gui_app_modular/dialogs/return_statistics_dialog.py  (신규)
gui_app_modular/handlers/inbound_handlers.py
gui_app_modular/handlers/status_import_handlers.py
gui_app_modular/handlers/export_handlers.py
gui_app_modular/tabs/tonbag_tab.py                   ← 2회 수정
gui_app_modular/tabs/dashboard_tab.py                ← 2회 수정
gui_app_modular/tabs/dashboard_data_mixin.py         ← 2회 수정
gui_app_modular/mixins/advanced_dialogs_mixin.py     ← 2회 수정
gui_app_modular/menu_registry.py
gui_app_modular/utils/tonbag_location_uploader.py
```

### Features 레이어 (5개)
```
features/pdf_parser/gemini_parser.py
features/pdf_parser/pdf_field_extractor.py
features/reports/lot_lifecycle_report.py             (신규)
features/reports/return_report_pdf.py
features/reports/integrity_report.py                 (신규)
```

### API 레이어 (4개, 모두 신규)
```
api/main.py
api/auth.py                                          (신규)
api/rate_limit.py                                    (신규)
api/audit_middleware.py                               (신규)
```

### 인프라 (2개, 모두 신규)
```
Dockerfile                                           (신규)
docker-compose.yml                                   (신규)
```

### 테스트 (16개, 모두 신규)
```
tests/test_addon_a_stock_movement.py
tests/test_addon_b_tonbag_uid.py
tests/test_addon_c_preview_edit.py
tests/test_addon_d_outbound_lifecycle.py
tests/test_addon_e_lifecycle_report.py
tests/test_addon_f_version.py
tests/test_addon_g_unit_weight.py
tests/test_gate1_cross_validation.py
tests/test_large_picking_parse.py
tests/test_manual_inbound_enhanced.py
tests/test_return_enhanced.py
tests/test_return_statistics.py
tests/test_return_dashboard.py
tests/test_api_production.py
tests/test_location_relocate.py
tests/test_integrity_v701.py
```

---

## 🧪 테스트 진행 현황

| 세션 | 추가 테스트 | 누적 | 결과 |
|------|------------|------|------|
| 세션 2 (입고) | 15개 | 15 | ✅ 전체 통과 |
| 세션 3 (출고) | 5개 | 20 | ✅ 전체 통과 |
| 세션 4 (Gate-1) | 8개 | 28 | ✅ 전체 통과 |
| 세션 5 (반품) | 34개 | 62 | ✅ 전체 통과 |
| 세션 6 (API) | 50개 | 112 | ✅ 전체 통과 |
| 세션 7 (이동+정합성) | 26개 | 138 | ✅ 전체 통과 |

---

## 🏗️ 아키텍처 변화

```
v6.12 (시작점)
├── 입고: PDF/Excel → 기본 처리
├── 출고: AVAILABLE → SOLD (2단계)
├── 반품: 기본 재입고
└── 테스트: 0개

    ↓ 7개 세션, 47개 파일, 25건 디버깅 ↓

v7.0.1 (현재)
├── 입고: PDF/Excel/수동 → Gate-0/1 검증 → 미리보기 편집 → 이력 기록
├── 출고: AVAILABLE→RESERVED→PICKED→SOLD (4단계) + 500/1000kg 동적
├── 반품: 사유 표준화 + 통계 + PDF/Excel 리포트 + 대시보드 + 알림
├── 이동: RELOCATE 이력 + 구역 대시보드 + 정합성 리포트
├── API: FastAPI + JWT + RBAC + WebSocket + Rate Limiting + Docker
├── 감사: stock_movement 4대 축 (INBOUND/OUTBOUND/RETURN/RELOCATE)
├── 검증: 정합성 5+7가지 + RESERVED 포함 + 자동 시작 검사
└── 테스트: 138개 전체 통과
```

---

*Generated by Ruby — SQM Session Debug Report*
