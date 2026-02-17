# P5 가이드 — 점진적 core 전환 & 테스트 보강

> **목표**: (1) 기존 `from config` / `from engine_modules.validators` 등을 `from core.xxx import` 로 단계적 교체  
> (2) core/, run_bootstrap 등 리팩터한 영역 단위·통합 테스트 추가

---

## 0. P5 단계별 세분화 (총 14단계)

| 구분 | 단계 | 내용 |
|------|------|------|
| **전환** | **P5-1** | core.config 보강 (API_KEY_SOURCE, save_gemini_model, PG_*, SAVE_RAW_*, DISABLE_OPENAI_* 등 re-export 추가) |
| | **P5-2** | utils.common → core.types 전환 (engine_modules/inventory_modular/utils.py, parsers 3개, allocation_parser 등) |
| | **P5-3** | engine_modules.constants → core.constants 전환 (inbound_mixin, crud_mixin, integrity_mixin, outbound_mixin, do_update_dialog, onestop_inbound, gui_bootstrap) |
| | **P5-4** | engine_modules.validators → core.validators 전환 (database.py, helpers.py, main_app.py, toolbar_mixin) |
| | **P5-5** | config → core.config 전환 (run_bootstrap, database, engine, dialogs, mixins, parsers, features 등) |
| | **P5-6** | formatters 직접 사용처 → core.formatters 전환 (해당되는 파일 있으면) |
| | **P5-7** | re-export 레이어 정리 (helpers.py, safe_utils.py 내부만 from core.types 등으로 변경, 대외 API 유지) |
| **테스트** | **P5-8** | tests/test_core_types.py 추가 (safe_int, safe_float, safe_str, safe_date, normalize_column_name) |
| | **P5-9** | tests/test_core_validators.py 추가 (validate_lot_no, validate_sap_no) |
| | **P5-10** | tests/test_core_formatters.py 추가 (format_number, format_weight, find_column) |
| | **P5-11** | tests/test_core_constants.py 또는 test_core.py 확장 (core.constants import·값 검증) |
| | **P5-12** | tests/test_core_config.py 추가 (core.config import·속성 존재) |
| | **P5-13** | tests/test_run_bootstrap.py 추가 (run_self_check, check_dependencies 등) |
| | **P5-14** | tests/test_config_logging.py, test_file_utils.py (선택) |

- **전환 7단계 (P5-1 ~ P5-7)** + **테스트 7단계 (P5-8 ~ P5-14, 마지막 1개 선택)** = **총 14단계**
- 각 단계 완료 후 `python run.py --version` 및 `pytest tests/` 로 확인 후 커밋 권장.

---

## 1. 점진적 core 전환

### 1.1 전환 매핑 (어디서 무엇을 쓰는지)

| 현재 import | 전환 후 | 비고 |
|-------------|---------|------|
| `from config import DB_PATH, GEMINI_API_KEY, ...` | `from core.config import DB_PATH, GEMINI_API_KEY, ...` | core.config에 없는 항목은 아래 1.2 참고 |
| `from engine_modules.validators import validate_lot_no, validate_sap_no, InventoryValidator` | `from core.validators import ...` | 그대로 대체 가능 |
| `from engine_modules.constants import STATUS_AVAILABLE, DEFAULT_WAREHOUSE, ...` | `from core.constants import ...` | 그대로 대체 가능 |
| `from utils.common import safe_int, safe_float, safe_str, normalize_column_name` | `from core.types import ...` | safe_date 도 core.types 에 있음 |
| `from gui_app_modular.utils.formatters import format_number, format_weight, find_column` | `from core.formatters import ...` | 그대로 대체 가능 |

**주의**: `config` 에서만 쓰는 항목 중 **core.config 가 아직 re-export 하지 않는 것**  
→ 전환 전에 `core/config.py` 의 `from config import (...)` 와 `__all__` 에 추가해야 함.

- `API_KEY_SOURCE`, `save_gemini_model`
- `PG_HOST`, `PG_PORT`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`, `PG_MIN_CONNECTIONS`, `PG_MAX_CONNECTIONS`
- `SAVE_RAW_GEMINI_RESPONSE`, `DISABLE_OPENAI_FALLBACK`
- `sql_group_concat`, `sql_date_format`, `sql_auto_increment` 등은 **config가 config_sql을 re-export** 하므로, core에서 쓸 거면 `core.config` 에 추가하거나 `from config_sql import ...` / `from config import sql_*` 유지.

### 1.2 권장 순서 (한 번에 하나씩, 테스트 후 커밋)

1. **core.config 보강**  
   - 위 목록 중 필요한 것만 `core/config.py` 에 추가.

2. **의존성 적은 모듈부터**  
   - `engine_modules/inventory_modular/utils.py` (utils.common → core.types)  
   - `parsers/document_parser_v2.py`, `parsers/allocation_parser.py` (utils.common → core.types)  
   - `engine_modules/inventory_modular/crud_mixin.py`, `inbound_mixin.py`, `integrity_mixin.py` (engine_modules.constants → core.constants)  
   - `engine_modules/database.py` (config → core.config, validators → core.validators)  
   - `gui_app_modular/utils/helpers.py` (utils.common, engine_modules.validators → core.types, core.validators)  
   - `run_bootstrap.py` (config → core.config)  
   - 나머지: gui_app_modular, parsers, features 등.

3. **re-export 유지**  
   - `gui_app_modular/utils/helpers.py`, `safe_utils.py` 는 다른 GUI 코드가 `from ...helpers import safe_int` 처럼 쓸 수 있으므로, **내부 구현만** `from core.types import ...` 로 바꾸고, 대외적으로는 기존 이름 그대로 re-export 하면 됨.

4. **파일별로**  
   - 한 파일만 바꾼 뒤 `python run.py --version` / `pytest tests/` 등으로 확인 후 커밋.

### 1.3 전환 시 체크리스트 (파일 하나씩)

- [ ] 해당 파일에서 `from config import` / `from engine_modules.validators import` / `from engine_modules.constants import` / `from utils.common import` / `from gui_app_modular.utils.formatters import` 만 바꿈.
- [ ] `from core.xxx import` 시 core에 실제로 있는 심볼만 사용 (없으면 core 보강 후 전환).
- [ ] 저장 후 실행/테스트로 동작 확인.

---

## 2. 테스트 보강

### 2.1 현재 상태

- `tests/test_core.py`: 엔진·상수·DB 테이블·입고 시나리오 등 (engine_modules 중심).
- core/ 패키지, run_bootstrap, config_logging, utils/file_utils 등에 대한 **전용 단위 테스트는 없음**.

### 2.2 추가 권장 테스트

| 대상 | 파일 (신규 권장) | 내용 |
|------|------------------|------|
| **core.types** | `tests/test_core_types.py` | safe_int, safe_float, safe_str, safe_date, normalize_column_name — 경계값·None·빈 문자열·잘못된 타입 |
| **core.validators** | `tests/test_core_validators.py` | validate_lot_no, validate_sap_no — 유효/무효 LOT·SAP 번호 (DB 없이) |
| **core.formatters** | `tests/test_core_formatters.py` | format_number, format_weight, find_column — 소수·단위·컬럼 후보 매칭 |
| **core.constants** | `tests/test_core_constants.py` 또는 기존 test_core 확장 | core.constants import 후 STATUS_*, DEFAULT_WAREHOUSE 등 값 일치 |
| **core.config** | `tests/test_core_config.py` | core.config import 후 DB_PATH, GEMINI_API_KEY 등 존재·타입 (실제 키 값은 검증하지 않도록) |
| **run_bootstrap** | `tests/test_run_bootstrap.py` | run_self_check() 반환 구조, check_dependencies() (필요 시 mock), run_self_diagnostic() 최소 1회 호출로 예외 없음 등 |
| **config_logging** | `tests/test_config_logging.py` | setup_logging() 호출, LOG_LEVEL/LOG_FILE 설정값 |
| **utils.file_utils** | `tests/test_file_utils.py` | smart_path_recovery, get_recent_files, safe_file_backup — 임시 디렉터리/파일로 검증 |

### 2.3 테스트 실행 방법

```bash
# 전체
python -m pytest tests/ -v

# 특정 파일
python -m pytest tests/test_core_types.py -v
python -m pytest tests/test_run_bootstrap.py -v
```

### 2.4 테스트 작성 순서 제안

1. **core.types** (의존성 없음) → test_core_types.py  
2. **core.validators** (DB 불필요) → test_core_validators.py  
3. **core.formatters** → test_core_formatters.py  
4. **core.constants** (기존 test_core.py에 core.constants import 테스트 추가 가능)  
5. **run_bootstrap** (run_self_check, check_dependencies 위주) → test_run_bootstrap.py  
6. **config_logging**, **file_utils** → 필요 시 test_config_logging.py, test_file_utils.py  

---

## 3. 요약

| 작업 | 어떻게 |
|------|--------|
| **점진적 core 전환** | ① core.config에 부족한 config 심볼 추가 ② 의존성 적은 파일부터 `from config/engine_modules/utils/...` → `from core.xxx` 로 교체 ③ 파일 단위로 테스트 후 커밋 |
| **테스트 보강** | ① core.types / validators / formatters / constants / config 전용 test_*.py 추가 ② run_bootstrap, config_logging, file_utils 단위 테스트 추가 ③ `pytest tests/` 로 회귀 확인 |

이 문서를 P5 체크리스트처럼 사용하면서, 전환한 파일·추가한 테스트를 문서 하단이나 REFACTORING_MASTER_PLAN 에 P5 항목으로 적어두면 진행 상황을 추적하기 좋습니다.

---

*작성일: 2026-02-16 | SQM P5 가이드*
