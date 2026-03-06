# SQM v6.3.3 RUBI 패치 노트
**작성일:** 2026-03-05  
**작업자:** Ruby  
**대상 버전:** SQM v6.3.2 → v6.3.3

---

## 패치 배경

LBM AP 고객 Allocation 파일이 두 가지 양식으로 입수됨:
- **Song 양식 (250MT):** 다중 시트, Product 컬럼 있는 시트 자동 선택 필요
- **Woo 양식 (550MT):** 단일 시트, 5행 헤더, Balance/Export/Remark 추가 컬럼, 피벗 혼재

두 양식 모두 자동 파싱 → allocation 배정까지 완전 지원.

---

## 변경 파일 목록 (7개)

| 파일 | 경로 | 변경 내용 |
|------|------|---------|
| `allocation_parser.py` | `parsers/` | v2.5.4 → v2.6.1 |
| `db_migration_mixin.py` | `engine_modules/` | _migrate_v633 추가 |
| `outbound_mixin.py` | `engine_modules/inventory_modular/` | export_type payload 추가 |
| `allocation_template_dialog.py` | `gui_app_modular/dialogs/` | **신규** |
| `menu_registry.py` | `gui_app_modular/` | 메뉴 2개 추가 |
| `main_app.py` | `gui_app_modular/` | _ensure_resources_templates 추가 |
| `advanced_dialogs_mixin.py` | `gui_app_modular/mixins/` | 핸들러 2개 추가 |

---

## 상세 변경 내용

### 1. `parsers/allocation_parser.py` (v2.6.1)

**v2.6.0 변경:**
- `_select_best_sheet()` 신규: 다중 시트에서 LOT+데이터 점수 기반 최적 시트 자동 선택
  - Song 양식: Sheet1(score=3) < '250톤 수출작업'(score=4) → 후자 자동 선택
  - Woo 양식: 단일 시트 → 기존 동작 유지
- 헤더 탐지 조건 완화: PRODUCT 없이 LOT + QTY/SAP 있으면 헤더로 인정
- `AllocationRow.is_sample: bool` 필드 추가 (qty_mt < 0.01 → True 자동 설정)
- `Balance` 컬럼을 qty_mt fallback alias로 추가

**v2.6.1 변경:**
- `AllocationRow.export_type: str` 필드 추가
- `alias_patterns`에 `export_type: ['EXPORT', '수출유형', '반송', 'EXPORT_TYPE']` 추가
- `_extract_rows()`에서 Export 컬럼값 → `row.export_type` 파싱

---

### 2. `engine_modules/db_migration_mixin.py`

**`_migrate_v633_allocation_export_type()` 신규 추가:**
```sql
ALTER TABLE allocation_plan ADD COLUMN export_type TEXT DEFAULT ''
CREATE INDEX idx_alloc_plan_export_type ON allocation_plan(export_type)
```
- 실행 순서: v632 다음, v635 앞
- duplicate column 오류 자동 무시 (멱등성 보장)

---

### 3. `engine_modules/inventory_modular/outbound_mixin.py`

**`reserve_from_allocation()` 내 변경:**
- `has_export_type_col` 플래그 추가 (PRAGMA table_info 동적 감지)
- `export_type_val = _alloc_val(alloc, 'export_type')` 추출
- APPROVAL_QUEUE / LOT / TONBAG 3가지 모드 payload 모두에 `export_type` 추가

---

### 4. `gui_app_modular/dialogs/allocation_template_dialog.py` (**신규**)

**Allocation 양식 미리보기 다이얼로그:**
- Song / Woo 양식 탭 전환
- 본 제품 행 (흰색) / 샘플 행 (주황색 강조) 독립 줄 표시
- `resources/templates/` 파일 우선 로드 (없으면 내장 샘플 데이터 fallback)
- "⬇ 이 양식 다운로드 (Excel)" 버튼 — openpyxl로 생성

**호출:** `AllocationTemplateDialog(parent)`

---

### 5. `gui_app_modular/menu_registry.py`

`FILE_MENU_OUTBOUND_ITEMS`에 추가:
```python
("📄 Allocation 양식 미리보기", "_show_allocation_template_preview", True)  # Allocation 입력 바로 아래
("🔄 반송 출고 현황", "_show_return_export_history", True)                  # 출고 현황 조회 바로 아래
```

---

### 6. `gui_app_modular/main_app.py`

**`_ensure_resources_templates()` 신규 추가:**
- SQM 시작 시 `resources/templates/` 폴더 자동 생성
- 최초 실행 시 `README.txt` 안내 파일 생성
- 폴더 경로: `{프로젝트 루트}/resources/templates/`

**양식 파일 배치 방법:**
```
resources/templates/allocation_template_song.xlsx  ← Song 양식
resources/templates/allocation_template_woo.xlsx   ← Woo  양식
```

---

### 7. `gui_app_modular/mixins/advanced_dialogs_mixin.py`

파일 끝에 2개 메서드 추가:

**`_show_allocation_template_preview()`:**
- `AllocationTemplateDialog` 호출
- 오류 시 CustomMessageBox로 표시

**`_show_return_export_history()`:**
- `allocation_plan.export_type != ''` 행 조회
- 필터: 기간 / 상태 / LOT 검색 / 수출유형(반송/일반수출)
- 반송 행 주황색 강조
- Excel 저장 기능 내장

---

## 파싱 검증 결과

| 항목 | Song 양식 | Woo 양식 |
|------|---------|--------|
| 시트 선택 | 자동: '250톤 수출작업' | 자동: Sheet1 (단일) |
| 헤더 위치 | 2행 | 5행 |
| 매핑 성공 컬럼 | 10개 | 11개 (export_type 포함) |
| 자동 무시 컬럼 | 없음 | Balance, Remark |
| 본제품 행 | 50개 | 110개 |
| 샘플 행 | 50개 | 110개 |
| export_type | '' (해당없음) | '반송' |
| **파싱→배정** | **✅ 완전** | **✅ 완전** |

---

## 배포 방법

```
패치 파일을 SQM 프로젝트 루트에 그대로 덮어씌우기:

PATCH_SQM_v633_RUBI/
├── parsers/allocation_parser.py
├── engine_modules/
│   ├── db_migration_mixin.py
│   └── inventory_modular/outbound_mixin.py
└── gui_app_modular/
    ├── dialogs/allocation_template_dialog.py  ← 신규 (복사만)
    ├── main_app.py
    ├── menu_registry.py
    └── mixins/advanced_dialogs_mixin.py
```

**주의:** `allocation_template_dialog.py`는 신규 파일이므로 덮어씌우기가 아닌 **새 파일 복사**.

---

## DB 마이그레이션

SQM 재시작 시 자동 실행:
```sql
-- allocation_plan 테이블에 컬럼 추가 (이미 있으면 무시)
ALTER TABLE allocation_plan ADD COLUMN export_type TEXT DEFAULT ''
CREATE INDEX idx_alloc_plan_export_type ON allocation_plan(export_type)
```
