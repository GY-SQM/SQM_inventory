# SQM v5.7.9 — 엔트리 run.py 통일 및 P0 완료

## 개요
엔트리 포인트를 **run.py** 로 통일하고, 리팩토링 마스터 플랜 **P0** 를 완료한 버전입니다.  
버전 **5.7.9** 반영.

---

## v5.7.9에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **엔트리 파일** | `run_app.py` → **`run.py`** 로 변경. 실행 시 `python run.py` 로 짧게 입력 가능. |
| **P0 완료** | run.bat 삭제, **SQM_실행.bat** 생성(run.py 호출), 문서 전반에서 run_app.py/main.py → run.py·SQM_실행.bat 으로 수정. |
| **PyInstaller** | `sqm_inventory.spec` 진입 스크립트를 `run.py` 로 변경. |
| **패키지 진입** | `gui_app_modular/__main__.py` 가 `run.main()` 위임 유지 (run 모듈 import). |
| **문서** | REFACTORING_MASTER_PLAN, ENTRY_POINT_AND_LIBRARY_REVIEW, 개발자 가이드, 매뉴얼, 퀵스타트 등 run.py 기준으로 정리. |

---

## 실행 방법 (변경 없음, 파일명만 변경)

```bash
python run.py
# 또는
python -m gui_app_modular
```

Windows: **SQM_실행.bat** 더블클릭 (내부에서 `python run.py` 실행)

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.7.9, VERSION_HISTORY |
| run.py | 신규 (run_app.py 내용 이전) |
| run_app.py | 삭제 |
| gui_app_modular/__main__.py | import run, run.main() |
| SQM_실행.bat, SQM_#Uc2e4#Ud589.bat | python run.py 호출 |
| sqm_inventory.spec | 진입 스크립트 run.py |
| PROJECT_STRUCTURE.md, README.md, QUICK_START.md, CONTRIBUTING.md | run.py 기준 수정 |
| docs/* (다수) | run_app.py → run.py, run_app → run 반영 |

---

*작성일: 2026-02-16 | SQM v5.7.9*
