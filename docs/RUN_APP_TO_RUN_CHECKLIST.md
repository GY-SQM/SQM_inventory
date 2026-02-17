# run_app.py → run.py 변경 반영 체크리스트

> 검증일: 2026-02-16 기준

---

## 🔴 카테고리 1: 실행에 직접 영향 — **전부 반영됨 ✅**

| # | 파일 | 요구 사항 | 현재 상태 |
|---|------|-----------|-----------|
| 1 | **run.py** (구 run_app.py) | 파일명 run.py, docstring/로그에 run.py | ✅ run.py만 존재, docstring에 run.py 사용법만 기재 |
| 2 | **gui_app_modular/__main__.py** | import run, run.main() | ✅ `import run` / `run.main()` 사용 중 |
| 3 | **sqm_inventory.spec** | 진입점 ['run.py'] | ✅ `Analysis(['run.py'], ...)` |
| 4 | **SQM_실행.bat** | python run.py, 주석 run.py | ✅ `python run.py`, 주석 "(진입점: run.py)" |

→ **프로그램 실행/빌드에 필요한 수정은 모두 반영되었습니다.**

---

## 🟡 카테고리 2: 문서/정합성 (선택 수정)

| # | 파일 | run_app 참조 | 비고 |
|---|------|--------------|------|
| 5 | docs/REFACTORING_MASTER_PLAN.md | 1곳 | "run_app_bootstrap" 는 제안 모듈명(현재 run_bootstrap.py). run_app.py와 무관. |
| 6 | docs/RELEASE_NOTES_v579.md | 5곳 | **변경 이력**이므로 "run_app.py → run.py 로 바뀜" 기록으로 유지 권장. |
| 7 | docs/SQM_코드검토_보고서_v5.4.6.md | 5곳 | 현재 실행 안내로 쓴다면 run.py로 수정 권장. |
| 8 | SQM_개발계획서_v5.4.6.md (루트) | 8곳 | 위와 동일. |
| 9 | docs/#Ub514#Ubc84#Uae45_#Uc804_#Ubc31#Uc5c5_#Uc548#Ub0b4.md | 1곳 | 실행 명령어만 run.py로 수정 가능. |
| — | **docs/archive/** 내 문서 | 다수 | 과거 버전 기록이므로 **수정하지 않음** (원칙). |

---

## 결론

- **실행·빌드(필수): 4개 파일 모두 run.py 기준으로 반영 완료.**
- **문서**: archive 제외한 일부 문서에 run_app.py 표기가 남아 있음. 정합성을 위해 수정하려면 위 표의 7·8·9번 파일에서 run_app.py → run.py, `python run_app.py` → `python run.py` 로 치환하면 됨.

---

*작성: 2026-02-16 | run_app → run 검증*
