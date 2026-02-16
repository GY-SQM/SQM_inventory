# 엔트리 포인트 및 공통 기능 라이브러리 검토

> **목적**: 엔트리 포인트 1곳 명확화 + 공통 기능 중 라이브러리화 후보 정리  
> **작성일**: 2026-02-16

---

## 1. 엔트리 포인트 (1곳)

### 공식 진입점

| 방식 | 동작 |
|------|------|
| `python run.py` | **공식 엔트리**. 부트스트랩(점검, MAC Guard, 자동 백업) 후 GUI 실행 |
| `python -m gui_app_modular` | **동일**. `gui_app_modular/__main__.py`가 `run.main()`을 호출하여 같은 경로로 실행 |

실제 진입 로직은 **`run.main()` 한 곳**에만 있습니다.

### 부트스트랩 순서 (run.main())

1. `--version` / `--check` → 즉시 처리 후 종료
2. MAC Guard (선택: `--no-mac-check`로 비활성화)
3. 환경 점검 (`run_self_check`, 선택: `--no-check`로 생략)
4. 필수 의존성 확인 (`check_dependencies`)
5. `--cli` → CLI 테스트, `--backup` → 백업만, 그 외 → **GUI** (`run_gui()`)

### 그 외 실행 경로

| 파일 | 용도 |
|------|------|
| `gui_app_modular/main_app.py` 직접 실행 | **개발/테스트용**. 부트스트랩 없이 GUI만 띄움. `--db`, `--theme` 지원. 정식 실행은 `run.py` 권장. |

---

## 2. 공통 기능 — 라이브러리화 후보

프로젝트 내에서 이미 공통으로 쓰이는 부분과, 별도 패키지로 분리했을 때 이득이 있는 후보만 정리했습니다.

### 2.1 이미 단일 소스로 쓰는 공통 유틸 (유지)

| 모듈 | 내용 | 라이브러리화 |
|------|------|--------------|
| **utils/common.py** | `safe_float`, `safe_str`, `safe_int`, `normalize_column_name` | ✅ **분리 적합**. 의존성 없고 다른 프로젝트에서도 그대로 사용 가능. |
| **engine_modules/constants.py** | 상태/창고/무게/날짜 형식 등 비즈니스 상수 | ⬜ SQM 전용. 필요 시 하위 패키지에서 `from engine_modules.constants import ...` 로 재사용. |
| **config_sql.py** | DB별 SQL 표현 (`sql_group_concat`, `sql_date_format` 등) | ✅ **분리 적합**. DB 추상화만 필요할 때 독립 패키지로 분리 가능. |

### 2.2 DB·백업 레이어 (재사용 가능)

| 모듈 | 내용 | 라이브러리화 |
|------|------|--------------|
| **engine_modules/database.py** | `SQMDatabase`: 연결, 실행, 트랜잭션, WAL, 백업 | ✅ **후보**. SQLite 앱 공통 레이어로 쓸 수 있음. 의존성: config(DB_PATH), db_migration_mixin. |
| **utils/backup.py** | `BackupManager`, `force_backup`, `list_backups`, `restore_latest` | ✅ **후보**. DB 경로·백업 디렉터리만 주입하면 다른 프로젝트에서 재사용 가능. |

### 2.3 검증·무결성 (도메인 결합도에 따라)

| 모듈 | 내용 | 라이브러리화 |
|------|------|--------------|
| **engine_modules/validators.py** | `validate_lot_no`, `validate_lot_no_unique`, 규칙 검증 | ⬜ SQM LOT/비즈니스 규칙과 밀접. 공용 라이브러리보다는 `engine_modules` 내 단일 소스로 두고, 출고/입고에서만 import 권장. |
| **utils/integrity_check.py** | `IntegrityChecker`, `run_integrity_check` | ⬜ DB 스키마·비즈니스 규칙 의존. 필요 시 엔진 쪽으로 이관해 재고 도메인과 함께 유지하는 편이 자연. |

### 2.4 GUI·경로 유틸 (앱 의존)

| 모듈 | 내용 | 라이브러리화 |
|------|------|--------------|
| **gui_app_modular/utils/** | `custom_messagebox`, `safe_utils`, `helpers`, `table_styler` 등 | ⬜ tk/ttkbootstrap·앱 구조에 묶여 있음. 라이브러리보다는 앱 전용 유틸로 유지. |
| **utils/path_utils.py** | `get_app_base_dir`, `resolve_reports_dir` | ⬜ 설정/경로 규칙 의존. 경로 정책 통일 후 필요 시 공용 유틸로 승격 가능. |

### 2.5 정리 요약

| 구분 | 모듈 | 권장 |
|------|------|------|
| **지금도 공용으로 쓰기 좋음** | `utils/common.py` | 유지. 필요 시 별도 패키지(예: `sqm_common` 또는 공용 유틸 패키지)로 분리 검토. |
| **DB 추상화만 쓸 때** | `config_sql.py` | 유지. 다른 프로젝트에서 SQLite/PG 호환만 필요하면 복사 또는 작은 패키지로 분리 가능. |
| **재사용 후보** | `engine_modules/database.py`, `utils/backup.py` | 현재 구조 유지. 새 프로젝트에서 SQLite+백업 패턴 재사용 시 이 둘을 기준으로 추출 검토. |
| **도메인 전용** | validators, integrity_check, parsers, gui_app_modular/utils | 라이브러리 분리보다는 **엔트리 1곳 + import 출처 정리**로 관리. |

---

## 3. 권장 import 출처 (출고·신규 코드 기준)

| 용도 | import |
|------|--------|
| safe_float / safe_int / safe_str | `from utils.common import ...` |
| 비즈니스 상수 (STATUS_*, SAMPLE_WEIGHT_KG, DEFAULT_WAREHOUSE) | `from engine_modules.constants import ...` |
| LOT 검증 | `from engine_modules.validators import validate_lot_no` (또는 모듈 함수) |
| SQL 호환 표현 | `from config import sql_group_concat, sql_date_format, ...` |
| DB 인스턴스 | 엔진/마이그레이션 경유 (`engine.db` 등) |

---

*작성일: 2026-02-16 | SQM v5.7.8*
