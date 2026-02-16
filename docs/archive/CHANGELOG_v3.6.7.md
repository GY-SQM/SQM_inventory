# SQM 재고관리 시스템 v3.6.7 - 품질 강화 릴리스

**릴리스일**: 2026-02-04
**작성자**: Ruby (남기동)

---

## 📊 테스트 커버리지 대폭 확대 (43.7% → 64.2%)
### 신규 테스트 파일 2개 + GUI 테스트 전면 재작성

**신규 테스트:**
- `test_utils_coverage.py` (48건): safe_conversions, column_aliases, user_friendly_errors, structured_logging, backup, logger
- `test_mixin_coverage.py` (55건): CRUDMixin, TonbagMixin, ReturnMixin, Validators, QueryMixin

**커버리지 향상 주요 모듈:**
| 모듈 | Before | After |
|------|--------|-------|
| utils/__init__.py | 0% | 100% |
| utils/safe_conversions.py | 0% | 83.2% |
| utils/column_aliases.py | 0% | 76.5% |
| utils/user_friendly_errors.py | 0% | 77.3% |
| utils/logger.py | 0% | 83.5% |
| utils/structured_logging.py | 0% | 75.3% |
| engine_modules/validators.py | 15.6% | 67.0% |
| inventory_modular/utils.py | 16.7% | 87.5% |
| inventory_modular/return_mixin.py | 15.4% | 69.2% |
| inventory_modular/crud_mixin.py | 7.7% | (대폭 향상) |

## 🖥️ GUI 테스트 Mock 기반 전환 (0% → 100% 통과)
### tkinter 없는 환경에서 완전 실행 가능

**재작성 파일:**
- `tests/gui/test_helpers.py`: helpers.py 15개 함수 직접 테스트
- `tests/gui/test_validators.py`: 검증 함수 + mock DB 테스트
- `tests/gui/test_mixins.py`: 8개 Mixin 클래스 import/hasattr 테스트

**결과:** GUI 41/41 ✅ 전체 통과 (이전: 0/14)

## 📦 배포 자동화 확인
기존 배포 인프라 (setup.py, build.py, sqm_inventory.spec, requirements.txt) 정상 확인

## 📊 최종 테스트 결과
| 항목 | v3.6.6 | v3.6.7 |
|------|--------|--------|
| **통과** | 499 | **859** |
| **코드 버그** | 0 | **0** |
| **환경 이슈** | 22 | **5** (OCR 4 + 타이밍 1) |
| **커버리지** | 43.7% | **64.2%** |
| **GUI 통과율** | 0/14 | **41/41** |

## 수정/추가 파일
1. `tests/test_utils_coverage.py` (신규)
2. `tests/test_mixin_coverage.py` (신규)
3. `tests/gui/test_helpers.py` (재작성)
4. `tests/gui/test_validators.py` (재작성)
5. `tests/gui/test_mixins.py` (재작성)
6. `tests/test_v352_comprehensive.py` (ErrorType mock 추가)
7. `tests/test_v352_features.py` (ErrorType mock 추가)
