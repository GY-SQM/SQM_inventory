# SQM v5.7.8 — 출고 전 필수 정리

## 개요
출고 개발 전 반드시 해야 할 8가지 중, 본 버전에서 적용한 항목과 남은 항목을 정리했습니다.  
버전 **5.7.8** 반영.

---

## v5.7.8에서 완료한 항목

| # | 항목 | 조치 |
|---|------|------|
| 1 | **샘플 1kg 정합성** | `crud_mixin.py`: 로컬 `1.0` 제거 → `engine_modules.constants.SAMPLE_WEIGHT_KG` 단일 사용. 출고 시 롤백 원인 제거. |
| 2 | **상태 체계 (PICKED→SOLD)** | `outbound_mixin.py`: 문자열 `'AVAILABLE'`/`'PICKED'`/`'DEPLETED'` → `STATUS_*` 상수 사용. `constants.py`에 출고 흐름 주석 추가. |
| 4 | **constants 통합** | `gui_app_modular/utils/constants.py`: `DEFAULT_WAREHOUSE`, `DEFAULT_TONBAG_COUNT` → `engine_modules.constants`에서 re-export (단일 소스). |
| 5 | **config 분할** | SQL 호환 함수를 `config_sql.py`로 분리. `config.py`는 래퍼만 유지. 출고/리포트에서 `from config import sql_*` 계속 사용 가능. |
| 6 | **safe_float 통합** | `onestop_inbound.py`: 로컬 `_safe_float` 제거 → `utils.common.safe_float` 사용. 출고 무게 계산과 동일 출처. |
| 9 | **버전** | `version.py`: `__version__ = '5.7.8'`, VERSION_HISTORY 갱신. |

---

## 출고 전 8항목 체크리스트 (참고)

| # | 항목 | v5.7.8 상태 | 비고 |
|---|------|-------------|------|
| 1 | 샘플 1kg 정합성 | ✅ 완료 | 상수 단일 사용 |
| 2 | 상태 체계 PICKED→SOLD | ✅ 완료 | 상수화 + 문서화 |
| 3 | core/ 공통 + safe_int·validate_lot | ⬜ 문서 권장 | safe_int는 common 단일. validate_lot: 출고/엔진은 `engine_modules.validators.validate_lot_no` 권장. |
| 4 | constants 통합 | ✅ 완료 | GUI는 engine re-export |
| 5 | config.py 분할 | ✅ 완료 | config_sql 분리 |
| 6 | safe_float 통합 | ✅ 완료 | onestop → common |
| 7 | UI 7개 (검색 무시, 다크테마, 메뉴 등) | ⬜ 점검 대기 | 출고 화면 전 UI 기반 정비 시 점검 |
| 8 | 테스트 30개 통과 | ⬜ 11개 통과 | 현재 `tests/test_core.py` 11개 전부 통과. 30개는 출고 테스트 추가 후 목표. |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.7.8, VERSION_HISTORY |
| engine_modules/constants.py | 출고 흐름 주석 (AVAILABLE→PICKED→SOLD/DEPLETED) |
| engine_modules/inventory_modular/crud_mixin.py | SAMPLE_WEIGHT_KG import, 로컬 1.0 제거 |
| engine_modules/inventory_modular/outbound_mixin.py | STATUS_AVAILABLE/PICKED/DEPLETED 상수 사용 |
| gui_app_modular/utils/constants.py | DEFAULT_WAREHOUSE, DEFAULT_TONBAG_COUNT re-export from engine |
| gui_app_modular/dialogs/onestop_inbound.py | _safe_float 제거, utils.common.safe_float 사용 |
| config.py | sql_* 구현 → config_sql 호출로 대체 |
| config_sql.py | 신규 — SQL 호환 함수 구현 (db_type 인자) |

---

*작성일: 2026-02-16 | SQM v5.7.8*
