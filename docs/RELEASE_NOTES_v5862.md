# SQM v5.8.6.2 — P5-8~14 단위테스트 및 전체 수집 순환참조 방지

## 개요
**P5-8 ~ P5-14** 단위 테스트 추가(core types/validators/formatters/constants/config, run_bootstrap, config_logging, file_utils) 및  
전체 `pytest tests/` 수집 시 발생하던 **순환 참조**·**AttributeError** 방지를 반영한 패치 버전입니다.

---

## v5.8.6.2에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **P5-8** | `test_core_types.py` — safe_int, safe_float, safe_str, normalize_column_name (경계값·None·빈 문자열) |
| **P5-9** | `test_core_validators.py` — validate_lot_no, validate_sap_no (유효/무효 케이스) |
| **P5-10** | `test_core_formatters.py` — format_number, format_weight, format_weight_kg/mt, find_column |
| **P5-11** | `test_core_constants.py` — STATUS_*, DEFAULT_WAREHOUSE, SAMPLE_WEIGHT_KG, BL_PREFIXES, DATE_FORMAT 등 |
| **P5-12** | `test_core_config.py` — BASE_DIR, DB_PATH, DB_TYPE, get_db_info, get_settings 존재·타입 검증 |
| **P5-13** | `test_run_bootstrap.py` — run_self_check() 구조, check_dependencies(), print_self_check_report() |
| **P5-14** | `test_config_logging.py`, `test_file_utils.py` — LOG_LEVEL/setup_logging, smart_path_recovery, get_recent_files, safe_file_backup |
| **순환 참조 방지** | test_core_constants/formatters/validators에서 `core.*` 대신 `engine_modules.constants`, `gui_app_modular.utils.formatters`, `engine_modules.validators` 직접 import |
| **engine_modules 방어** | `engine_modules/__init__.py` — PreflightMixin/SQMInventoryEngine None일 때 setattr 루프 스킵 |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.6.2, VERSION_HISTORY |
| engine_modules/__init__.py | PreflightMixin/SQMInventoryEngine None 방어로 setattr 루프 감쌈 |
| tests/test_core_constants.py | engine_modules.constants 직접 import (순환 방지) |
| tests/test_core_formatters.py | gui_app_modular.utils.formatters 직접 import (순환 방지) |
| tests/test_core_validators.py | engine_modules.validators 직접 import (순환 방지) |
| tests/test_core_types.py | **신규** — P5-8 |
| tests/test_core_validators.py | **신규** — P5-9 (위와 동일 파일) |
| tests/test_core_formatters.py | **신규** — P5-10 (위와 동일 파일) |
| tests/test_core_constants.py | **신규** — P5-11 (위와 동일 파일) |
| tests/test_core_config.py | **신규** — P5-12 |
| tests/test_run_bootstrap.py | **신규** — P5-13 |
| tests/test_config_logging.py | **신규** — P5-14 |
| tests/test_file_utils.py | **신규** — P5-14 |
| docs/RELEASE_NOTES_v5862.md | **신규** — 본 릴리스 노트 |

---

## 테스트 결과

- **전체 스위트**: `pytest tests/` → **70 passed** (기존 11 + 신규 59).

---

*작성일: 2026-02-16 | SQM v5.8.6.2*
