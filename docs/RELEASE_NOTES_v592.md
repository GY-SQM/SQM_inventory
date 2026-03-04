# SQM v5.9.2 Release Notes — P2 코드 위생

**Release Date:** 2026-02-18

---

## 개요

Phase 1 — P2 코드 위생 작업. `except + pass` 패턴 전면 제거, bare except 정리, DB 경로 통일, 성능 개선, 미사용 import 정리.

---

## P2-1: `except + pass` → 로깅 전환 (11파일)

`pass`로 조용히 삼키던 예외를 `logger.debug(f"Suppressed: {e}")`로 전환하여 추적 가능하게 수정.

| 파일 | 수정 개소 |
|------|-----------|
| `gui_app_modular/dialogs/onestop_inbound.py` | 2 |
| `features/ai/gemini_parser.py` | 1 |
| `parsers/do_free_time_ocr.py` | 2 |
| `parsers/document_parser_modular/do_mixin.py` | 3 |
| `parsers/document_parser_modular/bl_mixin.py` | 1 |
| `gui_app_modular/dialogs/test_runner_dialog.py` | 2 |
| `utils/date_utils.py` | 7 |
| `run.py` | 1 |
| `tests/test_core.py` | 1 |

---

## P2-2: bare `except Exception:` 제거

| 파일 | 변경 |
|------|------|
| `gui_app_modular/utils/tree_enhancements.py` | `except Exception:` → `except (ValueError, TypeError) as e: logger.debug(...)` |

---

## P2-3: DB 경로 하드코딩 통일

| 파일 | 변경 |
|------|------|
| `engine_modules/database.py` | fallback 경로 `data/sqm_inventory.db` → `data/db/sqm_inventory.db` (config.py 표준 일치) |

---

## P2-4: `re.compile` 함수 내부 → 모듈 레벨 이동

| 파일 | 변경 |
|------|------|
| `parsers/do_free_time_ocr.py` | `date_pat = re.compile(...)` → 모듈 레벨 `_RE_DATE = re.compile(...)` |

매 함수 호출 시 재컴파일 방지 → 성능 향상.

---

## P2-5: 미사용 import 정리

| 파일 | 제거된 import |
|------|---------------|
| `engine_modules/inventory_modular/inbound_mixin.py` | `DATE_FORMAT`, `DATETIME_FORMAT` |
| `gui_app_modular/main_app.py` | `get_app_base_dir` |
| `gui_app_modular/mixins/custom_menubar.py` | `RIGHT`, `BOTH` |

---

## 수정된 파일 목록 (17개)

1. `gui_app_modular/dialogs/onestop_inbound.py`
2. `features/ai/gemini_parser.py`
3. `parsers/do_free_time_ocr.py`
4. `parsers/document_parser_modular/do_mixin.py`
5. `parsers/document_parser_modular/bl_mixin.py`
6. `gui_app_modular/dialogs/test_runner_dialog.py`
7. `gui_app_modular/utils/tree_enhancements.py`
8. `utils/date_utils.py`
9. `run.py`
10. `tests/test_core.py`
11. `engine_modules/database.py`
12. `engine_modules/inventory_modular/inbound_mixin.py`
13. `gui_app_modular/main_app.py`
14. `gui_app_modular/mixins/custom_menubar.py`
15. `version.py`
16. `VERSION.txt`
17. `updates/latest.json`
