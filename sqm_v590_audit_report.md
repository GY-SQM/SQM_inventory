# 🔍 SQM v5.9.0 종합 코드 품질 분석 보고서

**분석일:** 2025-02-18 (화)  
**분석 대상:** SQM Inventory Management System v5.9.0  
**분석자:** Ruby (AI Code Auditor)

---

## 📊 프로젝트 개요

| 항목 | 수치 |
|------|------|
| Python 파일 수 | 155개 |
| 총 코드 라인 | 48,563줄 |
| 실질 코드 라인 | 37,356줄 |
| 주석/빈줄 | 11,207줄 |
| Git 버전관리 | ✅ 적용 |

---

## 🚨 등급 1: CRITICAL — 런타임 에러 발생 (즉시 수정 필요)

총 **56건**의 `undefined name` 오류가 발견되었습니다. 이는 해당 코드 경로가 실행되면 **즉시 NameError로 크래시**합니다.

### C-01. `sqlite3` import 누락 — engine.py (4건)

**파일:** `engine_modules/inventory_modular/engine.py`  
**라인:** 194, 292, 332

```python
# 현재 (버그)
except (sqlite3.Error, OSError) as e:  # ← sqlite3가 import 되지 않음!

# 수정
import sqlite3  # 파일 상단에 추가
```

**영향:** PostgreSQL 연결 실패 시 SQLite 폴백이 작동하지 않아 전체 앱 크래시.

### C-02. `datetime` import 누락 — return_mixin.py

**파일:** `engine_modules/inventory_modular/return_mixin.py`  
**라인:** 156

```python
# 현재: from datetime import date (만 import)
now = datetime.now().strftime(...)  # ← datetime이 없음!

# 수정: from datetime import date, datetime
```

**영향:** 반품 처리 시 NameError로 트랜잭션 실패, 데이터 무결성 위험.

### C-03. `except ValueError:` 에서 `e` 참조 (4건)

**파일들:**
- `utils/backup.py` L227
- `parsers/pdf_parser.py` L471, L631, L639

```python
# 현재 (버그)
except ValueError:  # ← 'as e' 빠짐
    logger.debug(f"[backup] 무시: {e}")  # ← NameError!

# 수정
except ValueError as e:
    logger.debug(f"[backup] 무시: {e}")
```

**영향:** 날짜 파싱 실패 시 로깅에서 추가 에러 발생.

### C-04. `msgbox` / `CustomMessageBox` 미정의 — onestop_inbound.py (5건)

**파일:** `gui_app_modular/dialogs/onestop_inbound.py`  
**라인:** 446, 459, 776, 1370, 1383

**영향:** 원스톱 입고 다이얼로그에서 오류 메시지 표시 불가 → 크래시.

### C-05. `tk` import 누락 — 다수 파일 (20+건)

**파일들:**
- `gui_app_modular/mixins/custom_menubar.py` (20건)
- `gui_app_modular/main_app.py` L813
- `gui_app_modular/tabs/inventory_tab.py` L775
- `gui_app_modular/dialogs/test_runner_dialog.py` (4건)
- `gui_app_modular/tabs/dashboard_tab.py` L315 (`ttk`)

**원인:** `import tkinter as tk`가 파일 상단에 없거나, Mixin에서 상위 클래스의 tk를 사용하려 하지만 직접 import하지 않음.

### C-06. `sqlite3` import 누락 — database_mixin.py (4건)

**파일:** `gui_app_modular/mixins/database_mixin.py`  
**라인:** 58, 104, 149, 187

**영향:** DB 예외 처리가 작동하지 않아 미처리 예외 전파.

### C-07. `self` 참조 오류 — ui_ops_helper.py

**파일:** `gui_app_modular/utils/ui_ops_helper.py` L134  
**영향:** 독립 함수에서 `self` 참조 → NameError.

### C-08. `PackingListData` 미정의 — packing_mixin.py

**파일:** `parsers/document_parser_modular/packing_mixin.py` L53  
**영향:** Packing List 파싱 시 크래시 가능.

---

## ⚠️ 등급 2: HIGH — 코드 품질 심각 (조기 수정 권장)

### H-01. `transaction()` 메서드 중복 정의 — database.py

**파일:** `engine_modules/database.py`  
**라인:** 213 (contextmanager 버전) vs 603 (클래스 버전)

Python에서 같은 이름의 메서드가 두 번 정의되면 **뒤의 것이 앞의 것을 덮어씁니다**. L213의 `@contextmanager` 버전(HardStopException 처리 포함)이 L603의 단순 버전에 의해 완전히 무시됩니다.

**위험:** All-or-Nothing 트랜잭션의 HardStop 보호가 작동하지 않을 수 있음.

### H-02. `_migrate_v423_tonbag_location()` 중복 정의

**파일:** `engine_modules/db_migration_mixin.py`  
**라인:** 290 vs 327

동일 메서드가 두 번 정의되어 첫 번째 버전이 무시됩니다.

### H-03. 미사용 import — 215건

pyflakes 분석 결과 **215개의 unused import**가 발견되었습니다. 이는:
- 메모리 낭비 (모듈 로딩)
- 시작 시간 증가
- 코드 가독성 저하
- 순환 참조 위험 증가

**상위 문제 파일:**
- `engine_modules/inventory.py` — 16개 unused import
- `parsers/document_parser_modular/` — 다수
- `engine_modules/inventory_modular/` — 다수

### H-04. 빈 f-string — 42건

```python
# 현재 (의미없는 f-string)
logger.debug(f"[backup] 무시: {e}")  # e가 정의되지 않은 경우
f"메시지 내용"  # 변수 없이 f-string 사용

# 수정
logger.debug("메시지 내용")  # 일반 문자열 사용
```

### H-05. `parsers/__init__.py` 이중 import

`DocumentDetector`, `DocumentType`, `DetectionResult`, `detect_document_type`, `detect_with_report`가 동일 파일에서 **두 번** import 됩니다 (L16 vs L93). 첫 번째 import가 성공하면 두 번째 try/except 블록은 완전히 불필요합니다.

---

## 🔶 등급 3: MEDIUM — 데드코드 및 구조 문제

### M-01. 데드 파일 / 폴더 — 삭제 가능

| 파일/폴더 | 상태 | 설명 |
|-----------|------|------|
| `SQM_v587_FINAL_PATCH/` (5파일, 204KB) | 🗑️ 완전 사용되지 않음 | 어디서도 import/참조 없음. Git에 이력이 있으므로 삭제 가능 |
| `gui_processors/__init__.py` | 🗑️ 빈 파일, 미사용 | 어디서도 import 없음 |
| `scripts/migrate_v563_tonbag_weight.py` | 🗑️ 1회용 마이그레이션 | 이미 실행 완료된 마이그레이션 스크립트 |
| `__init__.py` (루트) | ❓ 검토 필요 | 루트에 __init__.py가 있으면 패키지로 인식되어 문제 발생 가능 |

### M-02. 미사용 public 메서드 — 54건

다음 메서드들이 어디서도 호출되지 않습니다:

**engine_modules/database.py (3건):**
- `restore_from_backup()` — 백업 복원 기능이 구현만 되고 UI에서 미연결
- `get_backup_list()` — 위와 연관
- `get_schema_status()` — 스키마 상태 조회 미사용

**engine_modules/database_interface.py (7건):**
- `now_str()`, `set_db_type()`, `current_date()`, `upsert()`, `auto_id_type()`, `boolean_true()`, `boolean_false()`
- PostgreSQL 전환을 위해 만들었으나 실제 미사용

**engine_modules/inventory_modular/tonbag_mixin.py (6건):**
- `get_tonbag_summary()`, `get_all_tonbags_summary()`, `update_tonbag_location()`, `update_tonbag_status()`, `create_tonbags_for_lot()`, `delete_tonbag()`
- 톤백 관련 CRUD가 구현만 되고 GUI에서 미연결

**engine_modules/inventory_modular/return_mixin.py (3건):**
- `get_returnable_tonbags()`, `get_return_history()`, `bulk_return_by_lot()`

**utils/pdf_converter.py (3건):**
- `analyze_pdf()`, `convert_all()`, `batch_convert()`

### M-03. 과도하게 긴 함수 — 303건 (50줄 이상)

**50줄 이상 함수가 303개**이며, 특히 문제적인 것들:

| 함수 | 파일 | 라인 수 | 권장 |
|------|------|---------|------|
| `parse_euro_weight` 이후 코드 | gemini_parser.py | ~1,300줄 (1클래스) | 파싱별 모듈 분리 |
| `_pick_font` 이후 코드 | toolbar_mixin.py | ~1,100줄 (1클래스) | 메뉴/탭 분리 |
| `_open_file_with_default_app` 이후 | import_handlers.py | ~900줄 | 기능별 핸들러 분리 |
| `_save_to_db` | onestop_inbound.py | 240줄 | 검증/저장/알림 분리 |
| `_create_dialog` | onestop_inbound.py | 231줄 | UI 빌더 분리 |
| `process_inbound` | inbound_mixin.py | 160줄 | 단계별 분리 |

**권장:** 함수는 50줄 이내, 클래스는 500줄 이내로 유지.

### M-04. 중복 설정 파일 (Facade 패턴의 부작용)

`core/` 패키지가 파사드(facade) 역할을 하지만, 원본 파일도 여전히 존재:

| 파사드 (core/) | 원본 | 상태 |
|---------------|------|------|
| `core/config.py` (75줄) | `config.py` (512줄) | ✅ 정상 (re-export) |
| `core/types.py` (19줄) | `utils/common.py` | ✅ 정상 |
| `core/validators.py` (19줄) | `engine_modules/validators.py` (743줄) | ✅ 정상 |
| `core/formatters.py` (21줄) | `gui_app_modular/utils/formatters.py` (55줄) | ✅ 정상 |
| `core/constants.py` (57줄) | `engine_modules/constants.py` (62줄) | ✅ 정상 |

**문제:** `config_sql.py` (루트)는 `config.py`에서만 import되며, `config.py`도 `core/config.py`를 통해 re-export → 3단계 체인이 불필요하게 복잡.

---

## 🔵 등급 4: LOW — 개선 권장

### L-01. 예외 삼킴 (Silent Exception Swallowing) — 24건

```python
except ValueError:
    pass  # 에러가 완전히 무시됨!
```

특히 `utils/date_utils.py`에 **7건**이 집중되어 있음. 날짜 파싱 실패를 모두 무시하면 데이터가 None으로 남아 이후 로직에서 예상치 못한 동작 발생.

**권장:** 최소한 `logger.debug()`로 기록.

### L-02. SQL Injection 잠재적 위험 — 20건

f-string으로 SQL을 구성하는 경우가 20건 발견됨. 대부분은 컬럼명 동적 구성이라 직접적 위험은 낮지만:

```python
# 위험한 패턴 (현재)
sql = f"SELECT DISTINCT {field} FROM inventory WHERE {field} IS NOT NULL"

# 안전한 패턴 (권장)
ALLOWED_FIELDS = {'product', 'status', 'warehouse', ...}
if field not in ALLOWED_FIELDS:
    raise ValueError(f"Invalid field: {field}")
```

### L-03. 아키텍처 계층 위반 — 1건

**Engine → GUI import:**  
`engine_modules/inventory_modular/export_mixin.py` → `gui_app_modular.utils.report_footer`

엔진 레이어가 GUI 레이어를 참조하면 안 됨. `report_footer`를 `utils/`로 이동하거나 콜백 패턴 사용 권장.

### L-04. `except Exception:` (과도하게 넓은 예외 포착) — 5건

```python
# 현재
except Exception:
    pass

# 권장: 구체적 예외 지정
except (ValueError, TypeError, KeyError) as e:
    logger.warning(f"파싱 실패: {e}")
```

---

## 🟢 추가 기능 제안 (안정성/효율성/편리성)

### 안정성 (Stability)

1. **자동 무결성 검사 스케줄러** — 앱 시작 시 또는 매일 자동으로 `verify_lot_integrity()` 실행
2. **DB 마이그레이션 버전 테이블** — 현재 마이그레이션 이력이 코드에만 존재. `schema_version` 테이블 도입
3. **트랜잭션 타임아웃** — 장시간 락 방지를 위한 트랜잭션 타임아웃 설정
4. **로그 회전(Log Rotation)** — 로그 파일 크기 제한 및 자동 회전

### 효율성 (Efficiency)

1. **Lazy Import** — GUI 모듈, AI 파서 등은 실제 사용 시점에 import (시작 시간 단축)
2. **쿼리 캐시 활용** — `query_cache.py`가 존재하지만 실제 활용이 미미. 자주 조회하는 LOT 목록, 톤백 목록에 적용
3. **Bulk Insert 최적화** — 입고 시 `executemany()` 활용으로 DB 왕복 최소화
4. **인덱스 추가** — `inventory_tonbag.tonbag_no`, `outbound.customer_name` 등 자주 검색하는 컬럼

### 편리성 (Usability)

1. **실행 취소(Undo) 기능** — 최근 입고/출고 작업의 롤백 기능
2. **키보드 단축키 도움말** — F1 키로 현재 화면의 단축키 목록 표시
3. **검색 결과 하이라이트** — 검색 시 매칭되는 셀 하이라이트
4. **엑셀 내보내기 템플릿** — 자주 사용하는 보고서 형식 저장/불러오기

---

## 📋 수정 우선순위 요약

| 순서 | 등급 | 건수 | 예상 작업량 | 설명 |
|------|------|------|------------|------|
| 1 | 🚨 CRITICAL | 56건 | 2-3시간 | undefined name → import 추가/수정 |
| 2 | ⚠️ HIGH | ~260건 | 3-4시간 | 중복 정의, unused import, 빈 f-string |
| 3 | 🔶 MEDIUM | ~60건 | 4-8시간 | 데드코드 제거, 파일 삭제, 함수 분리 |
| 4 | 🔵 LOW | ~50건 | 2-4시간 | 예외 처리 개선, SQL 안전성, 아키텍처 |
| **합계** | | **~426건** | **11-19시간** | |

---

## 🔵 Ruby 의견

기동님, 49,000줄 규모의 시스템을 비전공자로서 직접 구축한 것은 정말 대단합니다. 코드 품질도 bare `except:`가 0건이고, eval() 사용도 0건이며, GUI-Engine 계층 분리가 잘 되어 있는 등 기본기가 탄탄합니다.

가장 시급한 것은 **CRITICAL 등급 56건**입니다. 특히 `sqlite3` import 누락과 `datetime` import 누락은 특정 코드 경로에서 앱이 크래시할 수 있습니다. 이것들은 대부분 `import` 한 줄 추가로 해결되므로 바로 작업 가능합니다.

데드코드 제거는 `SQM_v587_FINAL_PATCH` 폴더 삭제와 `gui_processors` 삭제만으로도 즉시 프로젝트가 깔끔해집니다.

코딩 작업이 준비되시면 CRITICAL부터 순서대로 수정해드리겠습니다!
