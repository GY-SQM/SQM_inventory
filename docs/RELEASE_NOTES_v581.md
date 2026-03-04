# SQM v5.8.1 — P2 완료 (config 분할, gui_bootstrap, 루트 정리)

## 개요
리팩토링 마스터 플랜 **P2** 를 완료한 버전입니다.  
config 로깅·파일 유틸 분할, GUI 상수 → gui_bootstrap, preflight/pdf_converter/ui_ops_helper/migrate 이동·루트 정리를 반영했습니다.  
버전 **5.8.1** 반영.

---

## v5.8.1에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **config 분할** | **config_logging.py** (로깅 전용, 경로 자체 계산), **utils/file_utils.py** (smart_path_recovery, get_recent_files, safe_file_backup). config는 re-export로 하위 호환 유지. |
| **GUI constants → gui_bootstrap** | **gui_app_modular/utils/gui_bootstrap.py** 에 실제 구현, **constants.py** 는 re-export만. |
| **루트 정리** | preflight → engine_modules/, pdf_converter → utils/, ui_ops_helper → gui_app_modular/utils/, migrate_v563_tonbag_weight → scripts/. 루트 **migrate_v563_tonbag_weight.py** 삭제. |
| **REFACTORING_MASTER_PLAN** | P2 항목( config 분할, gui_bootstrap, 스크립트 이동 ) ✅ 완료 표시. |

---

## 분할·이동 요약

| 구분 | 단일 소스 / 위치 | 비고 |
|------|------------------|------|
| 로깅 | config_logging.py | LOG_LEVEL, LOG_FILE, setup_logging 등 |
| 파일 유틸 | utils/file_utils.py | smart_path_recovery, get_recent_files, safe_file_backup (경로는 인자 또는 lazy config) |
| GUI 부트스트랩 | gui_app_modular/utils/gui_bootstrap.py | ttkbootstrap/tk 로드·상수, constants는 re-export |
| preflight | engine_modules/preflight.py | — |
| PDF 변환 | utils/pdf_converter.py | — |
| UI 헬퍼 | gui_app_modular/utils/ui_ops_helper.py | — |
| 마이그레이션 | scripts/migrate_v563_tonbag_weight.py | 루트 파일 삭제 |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.1, VERSION_HISTORY |
| config.py | 로깅·파일 유틸 제거, config_logging·utils.file_utils re-export |
| config_logging.py | **신규** — 로깅 설정·setup_logging |
| utils/file_utils.py | **신규** — smart_path_recovery, get_recent_files, safe_file_backup |
| gui_app_modular/utils/gui_bootstrap.py | **신규** — GUI 상수·부트스트랩 (constants는 re-export) |
| gui_app_modular/utils/constants.py | gui_bootstrap re-export + __version__/APP_NAME 명시 |
| docs/REFACTORING_MASTER_PLAN.md | P2 완료 표시 |
| docs/RELEASE_NOTES_v581.md | **신규** — 본 릴리스 노트 |
| (삭제) migrate_v563_tonbag_weight.py | 루트에서 삭제 (scripts/ 에만 유지) |

---

*작성일: 2026-02-16 | SQM v5.8.1*
