# SQM v5.8.6 — P5-1~4 점진적 core 전환

## 개요
리팩토링 P5 **전환 1~4단계**를 반영한 버전입니다.  
core.config 보강, utils.common → core.types, engine_modules.constants → core.constants, engine_modules.validators → core.validators 전환을 적용했고, 실행·테스트로 검증했습니다.  
**P5-5(config→core.config), P5-7(helpers/safe_utils 내부 core.types)는 이후 단계로 남겨 둠.**  
버전 **5.8.6** 반영.

---

## v5.8.6에서 반영한 내용

| 단계 | 내용 |
|------|------|
| **P5-1** | core.config 보강 — API_KEY_SOURCE, save_gemini_model, PG_*, SAVE_RAW_*, DISABLE_OPENAI_*, BACKUP_* re-export 추가 |
| **P5-2** | utils.common → core.types 전환 (engine_modules/inventory_modular/utils.py, parsers 4개, onestop_inbound.py 등 7파일) |
| **P5-3** | engine_modules.constants → core.constants 전환 (outbound/crud/inbound/integrity_mixin, gui_bootstrap, onestop_inbound, do_update_dialog) |
| **P5-4** | engine_modules.validators → core.validators 전환 (database.py, helpers.py, main_app.py, toolbar_mixin) |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.6, VERSION_HISTORY |
| core/config.py | re-export 항목 추가 (P5-1) |
| engine_modules/inventory_modular/utils.py | core.types |
| engine_modules/inventory_modular/{outbound,crud,inbound,integrity}_mixin.py | core.constants |
| engine_modules/database.py | core.validators |
| gui_app_modular/utils/helpers.py | core.validators (validate_*), re-export는 utils.common 유지 |
| gui_app_modular/utils/gui_bootstrap.py | core.constants |
| gui_app_modular/main_app.py, mixins/toolbar_mixin.py | core.validators |
| gui_app_modular/dialogs/onestop_inbound.py, do_update_dialog.py | core.types, core.constants |
| parsers/document_parser_v2.py, allocation_parser.py, document_parser_modular/*.py | core.types |
| docs/REFACTORING_MASTER_PLAN.md | P5 문구 정리 |
| docs/RELEASE_NOTES_v586.md | **신규** — 본 릴리스 노트 |

---

## 미적용 (이후 단계)

- **P5-5**: run_bootstrap, dialogs, features 등 `from config import` → `from core.config import`
- **P5-7**: helpers.py, safe_utils.py re-export 내부를 `from core.types import` 로 변경 (대외 API 유지)

---

*작성일: 2026-02-16 | SQM v5.8.6*
