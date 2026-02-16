# SQM v5.8.2 — P3 완료 (run.py 슬림화)

## 개요
리팩토링 마스터 플랜 **P3** 를 완료한 버전입니다.  
진단·백업·GUI/CLI 실행 로직을 **run_bootstrap.py** 로 분리하고, **run.py** 는 진입점만 유지합니다.  
버전 **5.8.2** 반영.

---

## v5.8.2에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **run_bootstrap.py** | **신규**. run_self_diagnostic, check_dependencies, run_auto_backup, run_gui, run_backup_only, run_cli, run_self_check, print_self_check_report 이관. |
| **run.py 슬림화** | 경로/인코딩 설정, 버전 import, main() 만 유지. 나머지는 run_bootstrap 호출로 위임. |
| **진입점 줄 수** | run.py **약 96줄** (목표 100줄 이하 달성). |
| **REFACTORING_MASTER_PLAN** | P3 항목 ✅ 완료 표시. |

---

## 구조 요약

| 파일 | 역할 |
|------|------|
| run.py | 유일 진입점. main() 에서 run_bootstrap 함수들 호출. |
| run_bootstrap.py | 진단(자동 설치 시도·설정·DB·Gemini), 환경 점검, 백업/GUI/CLI 실행. |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.2, VERSION_HISTORY |
| run.py | 진단·백업·run_gui/run_cli 제거, run_bootstrap import 위임 |
| run_bootstrap.py | **신규** — 진단·백업·실행 로직 |
| docs/REFACTORING_MASTER_PLAN.md | P3 완료 표시 |
| docs/RELEASE_NOTES_v582.md | **신규** — 본 릴리스 노트 |

---

*작성일: 2026-02-16 | SQM v5.8.2*
