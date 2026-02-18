# SQM v5.9.4 Release Notes — 구조 리팩토링

**Release Date:** 2026-02-18  
**Phase:** Phase 3 — 구조 리팩토링

---

## 변경 요약

### P3-1: 대형 파일 Mixin 분할

| 파일 | 이전(줄) | 이후(줄) | 분리된 Mixin |
|------|---------|---------|------------|
| `onestop_inbound.py` | 1,869 | 1,394 | `inbound_upload_mixin.py` (432줄) |
| `database.py` | 1,242 | 673 | `db_schema_mixin.py` (347줄) |

- `InboundUploadMixin`: DB 업로드(`_on_upload`, `_upload_thread`, `_save_to_db`), Excel 내보내기(`_export_to_excel`) 분리
- `DatabaseSchemaMixin`: 테이블 초기화(`_init_*_table`), 마이그레이션(`_migrate_v243`), 스키마 검증(`_verify_schema`), 인덱스 생성(`_create_indexes`) 분리

### P3-2: 50줄 초과 함수 분할

- Mixin 분할로 인해 자연적으로 처리됨
- `_save_to_db` (235줄), `_upload_thread` (98줄) 등 대형 함수가 별도 파일로 이동

### P3-3: COLUMN_REGISTRY 도입 (Round-trip 보장)

- `core/column_registry.py` 신규 생성
- 엑셀 헤더 ↔ DB 컬럼 매핑을 중앙 레지스트리로 관리
- `normalize_header()`: 엑셀 헤더 → DB 컬럼명 변환
- `db_to_excel_header()`: DB 컬럼명 → 엑셀 표준 헤더 변환
- `bulk_import_mixin.py`, `tonbag_location_uploader.py`에서 기존 인라인 정규화를 레지스트리 호출로 교체
- 프로그램에서 생성한 엑셀을 다시 불러올 때 컬럼명 불일치 원천 방지

### P3-4: config → core.config 구조 검증

- 루트 `config.py` → `core/config.py` Facade 구조가 이미 올바르게 구성됨
- 추가 마이그레이션 불필요

---

## 변경된 파일 (7개)

| 파일 | 변경 유형 |
|------|---------|
| `gui_app_modular/dialogs/onestop_inbound.py` | 수정 (Mixin 분리) |
| `gui_app_modular/dialogs/inbound_upload_mixin.py` | **신규** |
| `engine_modules/database.py` | 수정 (Mixin 분리) |
| `engine_modules/db_schema_mixin.py` | **신규** |
| `core/column_registry.py` | **신규** |
| `gui_app_modular/mixins/bulk_import_mixin.py` | 수정 (COLUMN_REGISTRY 적용) |
| `gui_app_modular/utils/tonbag_location_uploader.py` | 수정 (COLUMN_REGISTRY 적용) |

---

## 테스트 체크리스트

- [ ] 프로그램 정상 실행 (DB 초기화)
- [ ] 원스톱 입고: 파싱 → 미리보기 → DB 업로드 정상
- [ ] 원스톱 입고: Excel 내보내기 정상
- [ ] 입고 미리보기 Excel → 다시 불러오기 (Round-trip) 에러 없음
- [ ] 톤백 위치 엑셀 업로드 정상
- [ ] 재고/톤백 리스트 표시 정상

---

**(주) 지와이로지스 2026년 2월 18일**
