# SQM v5.8.3 — P4 완료 (core/ 공통 라이브러리)

## 개요
리팩토링 마스터 플랜 **P4** 를 완료한 버전입니다.  
**core/** 패키지를 re-export 파사드로 도입해, types·validators·formatters·constants·config·config_logging 을 한 진입점으로 제공합니다.  
기존 `from config` / `from engine_modules.validators` 등 사용처는 변경 없이 유지됩니다.  
버전 **5.8.3** 반영.

---

## v5.8.3에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **core/types.py** | safe_int, safe_float, safe_str, safe_date, normalize_column_name (utils.common, safe_utils re-export) |
| **core/validators.py** | validate_lot_no, validate_sap_no, ValidationResult, InventoryValidator (engine_modules.validators re-export) |
| **core/formatters.py** | format_number, format_weight, format_weight_kg, format_weight_mt, find_column (formatters re-export) |
| **core/constants.py** | STATUS_*, DEFAULT_WAREHOUSE, SAMPLE_WEIGHT_KG 등 (engine_modules.constants re-export) |
| **core/config.py** | DB_PATH, GEMINI_API_KEY, validate_api_key 등 (config re-export) |
| **core/config_logging.py** | setup_logging, LOG_LEVEL, LOG_FILE 등 (config_logging re-export) |
| **REFACTORING_MASTER_PLAN** | P4 항목 ✅ 완료 표시. |

---

## 사용 예 (신규·리팩터 시 권장)

```python
from core.types import safe_int, safe_float, safe_date
from core.validators import validate_lot_no, validate_sap_no
from core.formatters import format_weight, find_column
from core.constants import STATUS_AVAILABLE, DEFAULT_WAREHOUSE
from core.config import DB_PATH, GEMINI_API_KEY
from core.config_logging import setup_logging
```

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.3, VERSION_HISTORY |
| core/__init__.py | **신규** — 패키지 설명 |
| core/types.py | **신규** — types re-export |
| core/validators.py | **신규** — validators re-export |
| core/formatters.py | **신규** — formatters re-export |
| core/constants.py | **신규** — constants re-export |
| core/config.py | **신규** — config re-export |
| core/config_logging.py | **신규** — config_logging re-export |
| docs/REFACTORING_MASTER_PLAN.md | P4 완료 표시, 6.4 문구 수정 |
| docs/RELEASE_NOTES_v583.md | **신규** — 본 릴리스 노트 |

---

*작성일: 2026-02-16 | SQM v5.8.3*
