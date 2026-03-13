# RELEASE NOTES — SQM v7.0.0 최종 통합판

📅 릴리즈: 2026-03-08
🔧 작성자: Ruby

---

## 개요

이번 릴리즈는 **두 브랜치를 완전 통합**한 최종 안정판입니다.

| 소스 | 기여 내용 |
|------|-----------|
| `v6.5.1 (Stage1~4)` | tonbag_no 3자리, S00 샘플, Integrity Engine, 스캔 검증 |
| `v6.9.0 (Ruby v2)` | IntegrityChecker 완전판, BUG-4 수정, pyflakes 0건 |

---

## Stage별 변경 내용

### Stage 1
- `tonbag_no` 3자리 고정 (`001`, `002`, ..., `S00`)
- `tonbag_uid = lot_no || '-' || tonbag_no`
- `sample = S00` 통일

### Stage 2
- 무게 계산식 공식화: `(LOT 총무게 - 1kg) / mxbg_pallet`
- 500kg / 1000kg 모두 동일 계산식

### Stage 3
- Random 출고 스캔 검증 강화
- `is_scannable_status()` 통합 (`core/outbound_scan_validation_patch.py`)
- 허용/차단 상태 명확화

### Stage 4
- `inventory_validator.py` — Rack 용량(20), 창고 용량(A/B 각 3500), Location 형식
- `lot_balance_checker.py` — LOT 중량 잔액 검사
- `integrity_engine.py` — 무결성 스냅샷 검증

---

## v6.9.0 개선 내용 (신규 통합)

### 🔴 HIGH
- **`utils/integrity_check.py`** → 9가지 자동 검사 통합판 (v690 6가지 + Stage4 3가지)
  - 중복 LOT, 고아 톤백, 날짜 형식, 중량 무결성, 상태 일관성, FK 무결성
  - Rack 용량, 창고 용량, Location 코드 형식 (Stage4 통합)
- **`parsers/document_parser_modular/packing_mixin.py`** → BUG-4 오파싱 수정

### 🟡 MEDIUM (코드품질)
- `features/pdf_parser/gemini_parser.py` — 명시적 import
- `gui_app_modular/utils/constants.py` — 명시적 import
- `engine_modules/preflight.py` — 변수명 정리
- `gui_app_modular/handlers/outbound_handlers.py` — modal 옵션 적용
- `gui_app_modular/mixins/menu_mixin.py` — 다크모드 감지
- `gui_app_modular/utils/safe_utils.py` — Ruby v2 정리
- `gui_app_modular/utils/helpers.py` — re-export 정리

### 🆕 신규 추가
- `sqm_parsing_runtime/__init__.py` — 파싱 런타임 패키지
- `tests/test_v660_new_methods.py` — v6.6.0 단위 테스트

---

## 파일 통계

| 구분 | 수량 |
|------|------|
| 전체 Python 파일 | 232개 |
| Stage1~4 전용 모듈 | 6개 |
| 테스트 파일 | 8개 |
| 통합 신규 작성 | 1개 (integrity_check.py) |

---

## 주요 불변 조건 (SQM Core)

```
1 LOT = 톤백 N개(500kg 또는 1000kg) + 샘플 1개(1kg)
LOT 총무게 = (톤백수 × 단가) + 1kg
tonbag_uid = lot_no-001 / lot_no-S00
Rack 최대: 20개 / 창고 최대: 3500개 / 시스템 최대: 7000개
```
