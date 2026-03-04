# SQM v5.8.6.1 — P5-5·P5-7 적용 및 순환참조 수정

## 개요
**P5-5** (config → core.config 전환), **P5-7** (helpers/safe_utils 내부 → core.types) 적용 및,  
core.types ↔ safe_utils **순환 import** 제거를 반영한 패치 버전입니다.  
버전 **5.8.6.1** 반영.

---

## v5.8.6.1에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **P5-5** | run_bootstrap, database, engine, dialogs, statusbar_mixin, backup, parsers, features/ai 등 `from config import` → `from core.config import` 전환 |
| **config.get_settings()** | onestop_inbound 등에서 사용할 설정 딕셔너리 반환 함수 추가, core.config에 re-export |
| **P5-7** | helpers.py, safe_utils.py re-export 내부를 `from core.types import` 로 변경 (대외 API 유지) |
| **순환참조 수정** | core.types에서 safe_date(safe_utils) import 제거 — safe_date는 safe_utils에만 두어 core.types ↔ safe_utils 순환 제거 |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.6.1, VERSION_HISTORY |
| config.py | get_settings() 추가 |
| core/config.py | get_settings re-export 추가 |
| core/types.py | safe_date import 제거 (순환 참조 방지) |
| run_bootstrap.py, engine_modules/database.py, engine.py | core.config 전환 |
| gui_app_modular (dialogs, mixins, utils) | core.config, core.types 전환 |
| utils/backup.py, parsers/*, features/ai/* | core.config 전환 |
| docs/RELEASE_NOTES_v5861.md | **신규** — 본 릴리스 노트 |

---

*작성일: 2026-02-16 | SQM v5.8.6.1*
