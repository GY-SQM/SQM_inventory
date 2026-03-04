# SQM v5.8.0 — P1 완료 (중복 함수 단일 소스)

## 개요
리팩토링 마스터 플랜 **P1** 을 완료한 버전입니다.  
validate_lot_no / validate_sap_no, format_number / format_weight / find_column 을 **단일 소스**로 통일했습니다.  
버전 **5.8.0** 반영.

---

## v5.8.0에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **validate_lot_no / validate_sap_no** | 단일 소스: **engine_modules/validators.py**. helpers는 bool 래퍼, database.validate_sap_no는 validators 위임. |
| **validate_sap_no 추가** | validators에 모듈 레벨 `validate_sap_no(sap_no) -> Tuple[bool, str]` 추가 (선택적·형식 검사). |
| **format_number / format_weight / find_column** | 단일 소스: **gui_app_modular/utils/formatters.py** 신규. safe_utils·helpers는 formatters import 후 re-export. |
| **REFACTORING_MASTER_PLAN** | P1 두 항목 ✅ 완료 표시. |

---

## 단일 소스 정리

| 함수 | 단일 소스 | 사용처 |
|------|-----------|--------|
| validate_lot_no | engine_modules.validators | helpers(래퍼), 기타 |
| validate_sap_no | engine_modules.validators | helpers(래퍼), database(위임) |
| format_number, format_weight, format_weight_mt, format_weight_kg | gui_app_modular.utils.formatters | safe_utils, helpers re-export |
| find_column | gui_app_modular.utils.formatters | safe_utils, helpers re-export |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.0, VERSION_HISTORY |
| engine_modules/validators.py | validate_sap_no 추가 |
| engine_modules/database.py | validate_sap_no → validators 위임 |
| gui_app_modular/utils/helpers.py | validate_* → validators, format_* / find_column → formatters |
| gui_app_modular/utils/safe_utils.py | format_* / find_column → formatters re-export |
| gui_app_modular/utils/formatters.py | **신규** — format_number, format_weight*, find_column |
| docs/REFACTORING_MASTER_PLAN.md | P1 완료 표시 |

---

*작성일: 2026-02-16 | SQM v5.8.0*
