# P2_BATCH_A 리팩토링 완료 보고서

## 작업 개요
- **대상**: `gui_app_modular/dialogs/onestop_inbound.py` (4196줄)
- **목적**: 파싱/검증/DB저장 로직을 parser/validator/repository/service로 안전하게 분리
- **완료일**: 2026-04-07

## 단계별 결과

| 단계 | 작업 | 상태 | 비고 |
|------|------|------|------|
| S1 | 기능 맵 작성 | PASS | docs/P2_FUNCTION_MAP.md |
| S2 | Parser 분리 | PASS | features/parsers/inbound_parser.py |
| S3 | Validator 분리 | PASS | features/validators/inbound_validator.py |
| S4 | Repository 분리 | PASS | features/repositories/inbound_repository.py |
| S5 | Service 도입 | PASS | features/services/inbound_service.py |
| S6 | 통합 테스트 | PASS | 32/32 테스트 통과 |

## 생성/수정 파일

### 신규 생성
| 파일 | 역할 |
|------|------|
| `features/parsers/inbound_parser.py` | InboundParser — 파싱 + 데이터 병합 로직 |
| `features/validators/inbound_validator.py` | InboundValidator — 검증 로직 |
| `features/repositories/inbound_repository.py` | InboundRepository — DB 저장 로직 |
| `features/services/inbound_service.py` | InboundService — 파이프라인 오케스트레이터 |
| `tests/test_p2_inbound_refactor.py` | 통합 테스트 (32 케이스) |
| `docs/P2_FUNCTION_MAP.md` | 기능 맵 |
| `backup/onestop_inbound_backup.py` | 원본 백업 |

### 수정
| 파일 | 변경 사항 |
|------|-----------|
| `gui_app_modular/dialogs/onestop_inbound.py` | _parse_thread → InboundParser 위임, _merge_results → 위임, _amd_validate_date/_amd_calc_dates → InboundValidator 위임, _has_required_docs → 위임 |
| `gui_app_modular/dialogs/inbound_upload_mixin.py` | _preflight_validate_preview_data → InboundValidator 위임, _save_to_db → InboundRepository 위임 |
| `engine_modules/constants.py` | `from typing import Tuple` 추가 (기존 버그 수정) |

## 코드 줄 수 변화
- **원본**: 4196줄 (onestop_inbound.py)
- **리팩토링 후**: 4121줄 (onestop_inbound.py) — 약 75줄 감소
- **분리된 코드**: ~650줄 (4개 파일)
- **테스트**: ~250줄

## 아키텍처

```
OneStopInboundDialog (UI)
    ├── InboundParser (파싱 + 병합)
    │     ├── init_parser()
    │     ├── extract_template_hints()
    │     ├── parse_documents()
    │     ├── merge_results()
    │     └── static: empty_row, format_bl, date_str, fill_do, lot_order_key
    ├── InboundValidator (검증)
    │     ├── validate_date()
    │     ├── calc_dates()
    │     ├── preflight_validate()
    │     └── has_required_docs()
    ├── InboundRepository (DB)
    │     ├── build_packing_dict()
    │     ├── build_doc_dicts()
    │     ├── save_lot()
    │     └── lot_exists()
    └── InboundService (오케스트레이터)
          ├── validate_preview()
          ├── validate_date() / calc_dates()
          ├── check_required_docs()
          └── save_single_lot()
```

## 테스트 결과
```
32 passed in 0.11s
- TestInboundParser: 10 tests
- TestInboundValidator: 10 tests
- TestInboundRepository: 3 tests
- TestInboundService: 6 tests
- TestOnestopInboundImport: 3 tests (구문 검사 + 컬럼 일관성)
```

## 기능 변경 없음
- 모든 기존 메서드는 위임(delegate) 패턴으로 래핑
- UI 동작 변경 없음
- DB 저장 로직 동일
- 원본 backup/onestop_inbound_backup.py 보존
