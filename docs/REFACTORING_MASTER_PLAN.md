# SQM 리팩토링 마스터 플랜 — 통합 분석

> **Cursor 분석** (엔트리 포인트, 공통 라이브러리 검토) + **Claude 분석** (루트 정리, 중복 함수, config/constants) 을 통합한 **단일 최적안**입니다.  
> **작성일**: 2026-02-16

---

## 1. 엔트리 포인트 — 최종 결론

| 파일 | 역할 | 상태 | 조치 |
|------|------|------|------|
| **run.py** | ★ 유일한 메인 진입점 (GUI/CLI/백업/점검) | ✅ 명확 | 유지. 진입 로직은 여기만 둠. |
| **gui_app_modular/__main__.py** | `python -m gui_app_modular` 시 진입 | ✅ OK | **run.main() 위임** 유지 (이미 반영됨). |
| **SQM_실행.bat** | Windows 실행 → run.py 호출 | ✅ OK | 공식 실행용으로 유지. |
| **run.bat** | `python main.py` 호출 | ❌ **삭제 대상** | **main.py 없음** → 실행 실패·혼란 원인. **삭제 후 SQM_실행.bat 하나로 통일.** |

**권장**: run.bat 삭제, 매뉴얼/퀵스타트에서 "run.bat" → "SQM_실행.bat" 또는 "python run.py" 로 수정.

---

## 2. 루트 레벨 파일 정리

루트에 있는 주요 .py 파일 역할이 뒤섞여 있으므로, **역할별 분리·이동**을 권장합니다.

| 파일 | 줄 수 | 실제 역할 | 제안 |
|------|-------|-----------|------|
| **run.py** | ~490 | 진입점 + 진단 + 백업 호출 | **진입점만** 남기고, 진단/백업는 별도 모듈로 분리해 import (예: `run_app_bootstrap.py` 또는 `core/` 내). 목표: **100줄 이하** 진입점. |
| **config.py** | 736 | 설정 + API키 + 로깅 + SQL유틸 + 파일유틸 | **분할 필수**. 아래 §5 참고. |
| **preflight.py** | ~880 | 입고 전 검증 | **engine_modules/** 또는 **core/** 로 이동 (입고 검증은 엔진/비즈니스 레이어). |
| **pdf_converter.py** | ~780 | PDF 변환 | **utils/** 또는 **features/** 로 이동. |
| **ui_ops_helper.py** | ~640 | GUI 에러처리/진행바 | **gui_app_modular/utils/** 로 이동. |
| **version.py** | ~62 | 버전 정보 | ✅ **루트 유지**. |
| **migrate_v563_*.py** | ~100 | 일회성 마이그레이션 | **scripts/** 로 이동 또는 보관 후 삭제. |

---

## 3. 중복 함수 — 단일 소스로 통일

**같은 함수가 2~3곳에 정의**되어 있으면, 한 곳만 수정해도 다른 곳에 반영되지 않아 버그가 지속됩니다. **반드시 1곳을 “진짜 구현”으로 두고, 나머지는 re-export 또는 삭제**해야 합니다.

| 함수 | 정의 위치 (현재) | 중복 수 | **단일 소스 제안** |
|------|------------------|--------|---------------------|
| **safe_int** | utils/common.py, gui/helpers.py (re-export) | 2 | **utils/common.py** 유일 구현. GUI는 `from utils.common import safe_int` 만 사용. (이미 정리됨) |
| **safe_float** | utils/common.py, onestop 등에서 사용 | 1 | **utils/common.py** 유일. (이미 정리됨) |
| **safe_date** | gui/safe_utils.py (→str), gui/helpers.py (→date) | 2 (시그니처 다름) | **용도 분리**: `safe_date_to_date`(helpers), `safe_date_str`(safe_utils) 로 이름·역할 명확화. 둘 다 **한쪽에서 구현**, 다른 쪽은 wrapper/re-export. |
| **format_number** | gui/safe_utils.py, gui/helpers.py | 2 | **1곳으로 통일** (예: gui_app_modular/utils/formatters.py 또는 core/formatters.py). |
| **format_weight** | gui/safe_utils (format_weight_mt/kg), gui/helpers, engine/utils | 3 | **1곳으로 통일** (formatters 모듈). engine은 필요 시 import. |
| **find_column** | gui/safe_utils.py, gui/helpers.py | 2 | **1곳 구현**, 나머지 re-export. |
| **validate_lot_no** | engine/database.py, engine/validators.py, gui/helpers.py | 3 | **engine_modules/validators.py** 를 단일 소스. GUI·DB는 여기 import. helpers는 얇은 wrapper만 허용. |
| **validate_sap_no** | engine/database.py, engine/validators.py, gui/helpers.py | 2 | **engine_modules/validators.py** 단일 소스. |

**원칙**: “한 번 고치면 전부 반영” 되도록, **구현은 한 파일·한 함수**만 두고 나머지는 `from ... import ...` 또는 최소한의 wrapper.

---

## 4. constants — 2개 파일 정리

| 파일 | 역할 | 문제 | 제안 |
|------|------|------|------|
| **engine_modules/constants.py** | 비즈니스 상수 (상태, 무게, 창고, 날짜 형식) | — | ✅ **비즈니스 상수 단일 소스** 유지. GUI·엔진 모두 여기서 import. |
| **gui_app_modular/utils/constants.py** | GUI 상수 + **ttkbootstrap/tk 로드** + 버전 등 | **실제로는 “상수”보다 라이브러리 로드·부트스트랩** | **이름 변경 권장**: `constants.py` → `gui_bootstrap.py` (또는 `gui_env.py`). “상수만 모은 파일”이 아님을 명시. 비즈니스 값은 engine_modules.constants re-export. |

---

## 5. config.py — 역할별 분할 (736줄 → 여러 모듈)

**5가지 역할이 한 파일에 섞여 있음** → 유지보수·출고 코드에서 “설정이 어디 있는지” 찾기 어렵습니다.

| 역할 | 내용 예시 | 제안 모듈 |
|------|------------|-----------|
| 설정 로드 | _load_settings, get_db_info, 경로(BASE_DIR, DB_DIR 등) | **config.py** (설정·경로만, 얇게) 또는 **core/config.py** |
| API 키 관리 | save_api_key_secure, validate_api_key, keyring 연동 | **config_api.py** 또는 config 내 `api` 서브모듈 |
| 로깅 | setup_logging, LOG_LEVEL, LOG_FILE | **config_logging.py** 또는 **core/logging_config.py** |
| SQL 유틸 | sql_group_concat, sql_date_format 등 | ✅ 이미 **config_sql.py** 로 분리됨. config.py는 래퍼만 유지. |
| 파일 유틸 | smart_path_recovery, safe_file_backup, get_recent_files | **utils/file_utils.py** 또는 **core/file_utils.py** (config가 아님) |

**목표**: config.py는 “설정 읽기 + 경로 + (선택) API키 진입점” 정도만 두고, 나머지는 위 모듈로 분리해 **한 파일 200~300줄 이하** 유지.

---

## 6. 목표 구조 — 통합 제안 (Cursor + Claude)

**단계적 적용**을 권장합니다. 한 번에 core/ 로 옮기기보다, **먼저 단일 소스 정리·config 분할·루트 정리**를 하고, 필요 시 **core/** 를 도입합니다.

### 6.1 Phase 1 — 즉시 적용 (엔트리·중복·배치)

- **run.bat 삭제**. 실행은 **SQM_실행.bat** 또는 `python run.py` / `python -m gui_app_modular` 만 사용.
- 문서에서 run.bat → SQM_실행.bat 또는 run.py 로 수정.
- **중복 함수**: validate_lot_no / validate_sap_no → **engine_modules/validators.py** 단일 소스로 사용처 전환. safe_* / format_* / find_column → **1곳 구현 + re-export** 테이블대로 정리.

### 6.2 Phase 2 — 루트 정리·이동

- **preflight.py** → engine_modules/ (또는 core/ 생성 시 core/).
- **pdf_converter.py** → utils/ 또는 features/.
- **ui_ops_helper.py** → gui_app_modular/utils/.
- **migrate_v563_*.py** → scripts/.
- **run.py** 슬림화: 진단·백업 호출 등은 별도 모듈로 분리해 import.

### 6.3 Phase 3 — config 분할·constants 정리

- config.py 를 **설정·경로·API키 진입**만 두고, 로깅/파일유틸/SQL(이미 분리됨) 분리.
- GUI constants → **gui_bootstrap.py** 로 이름 변경 및 역할 명시.

### 6.4 Phase 4 — core/ 공통 라이브러리 ✅ 적용

아래 구조로 **core/** 를 re-export 파사드로 도입함. 기존 from config / engine_modules / utils 사용처는 변경 없음.

```
sqm/
├── run.py              ← 진입점만 (100줄 이하 목표)
├── version.py
│
├── core/                   ← ★ 공통 라이브러리 (선택)
│   ├── __init__.py
│   ├── types.py            ← safe_int, safe_float, safe_str, safe_date (utils/common 이관)
│   ├── validators.py       ← validate_lot_no, validate_sap_no (engine validators 이관 또는 re-export)
│   ├── formatters.py       ← format_number, format_weight, find_column
│   ├── constants.py        ← engine_modules.constants 이관 또는 re-export
│   ├── config.py           ← 설정 로드만 (경로, DB, API키)
│   └── config_logging.py   ← setup_logging
│
├── engine_modules/         ← 비즈니스 로직 (core/ 또는 utils/ import)
├── gui_app_modular/        ← GUI (core/ 또는 utils/ import)
├── features/               ← AI 등
├── parsers/
├── utils/                  ← backup, path_utils, file_utils 등 (core 없으면 여기 유지)
└── scripts/                ← 마이그레이션 등 일회성
```

**core/ 도입 시 import 규칙**:

- `from core.types import safe_int, safe_float`
- `from core.validators import validate_lot_no`
- `from core.constants import STATUS_AVAILABLE`
- `from core.config import DB_PATH, GEMINI_API_KEY`

**core/ 미도입 시** (현 구조 유지):

- `from utils.common import safe_int, safe_float`
- `from engine_modules.validators import validate_lot_no`
- `from engine_modules.constants import STATUS_AVAILABLE`
- `from config import ...`

둘 중 하나로 **일관되게** 가져가면 됩니다.

---

## 7. 액션 체크리스트 (우선순위)

| 순위 | 항목 | 담당 | 비고 |
|------|------|------|------|
| P0 | run.bat 삭제, 문서에서 SQM_실행.bat/run.py 로 수정 | ✅ 완료 | 혼란 제거 |
| P1 | validate_lot_no / validate_sap_no 단일 소스(validators) + 사용처 전환 | ✅ 완료 | 버그 예방 |
| P1 | format_number / format_weight / find_column 단일 소스 정리 | ✅ 완료 | 중복 제거 |
| P2 | config.py 분할 (로깅, 파일유틸, API키 분리) | ✅ 완료 | config_logging + utils/file_utils |
| P2 | GUI constants → gui_bootstrap.py 등 역할에 맞는 이름으로 변경 | ✅ 완료 | 의미 명확 |
| P2 | preflight / pdf_converter / ui_ops_helper / migrate 스크립트 이동 | ✅ 완료 | 루트 정리 |
| P3 | run.py 슬림화 (진단·백업 모듈 분리) | ✅ 완료 | run_bootstrap.py 분리, 진입점 ~96줄 |
| P4 | core/ 도입 여부 결정 및 단계적 이전 | ✅ 완료 | re-export 파사드 (types, validators, formatters, constants, config, config_logging) |
| P5 | 점진적 core 전환 | — | 기존 from config / engine_modules / utils → from core.xxx 단계적 교체. **가이드**: docs/P5_CORE_MIGRATION_AND_TESTS_GUIDE.md |
| P5 | 테스트 보강 | — | core/, run_bootstrap, config_logging, file_utils 단위·통합 테스트 추가. **가이드**: 동일 문서 참고. |

---

## 8. 요약

- **엔트리**: run.py 1곳, __main__.py는 run.main() 위임. **run.bat 제거·SQM_실행.bat 통일.**
- **중복 함수**: safe_*/format_*/find_column/validate_* **단일 소스** 지정 및 re-export로 통일.
- **constants**: 비즈니스는 engine_modules.constants, GUI용은 gui_bootstrap 등으로 **이름·역할 분리**.
- **config**: 설정/API/로깅/파일유틸 **역할별 분할**, SQL은 이미 config_sql.py.
- **루트**: preflight·pdf_converter·ui_ops_helper·migrate **이동**, run은 진입점만 유지.
- **core/**: Phase 1~3 안정화 후 **선택**으로 도입. 도입 시 types/validators/formatters/constants/config 일원화.

이 문서를 기준으로 **Phase 1부터 순서대로 적용**하면, 엔트리 포인트와 공통 라이브러리 구조가 **최적·일관**되게 정리됩니다.

---

*작성일: 2026-02-16 | Cursor·Claude 통합 분석 | SQM v5.7.8*
